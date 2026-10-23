#include <iostream>
#include <vector>
#include <string>
#include <array>
#include <algorithm>
#include <chrono>
#include <cstdint>
#include <intrin.h>

using namespace std;

constexpr int MW = 8;
struct Bits {
    array<uint64_t, MW> b{};
    bool operator==(const Bits& o) const { return b == o.b; }
};

struct State {
    uint64_t pose = 0; // 8 bits per emitter: bit 7 = active, bits 0..6 = pos
    Bits matter;
    int accepted = 0;
};

int R, L_perim, W_words, NT;
Bits target_mask, forbid_mask;
vector<array<Bits, 6>> rays;

inline int pc(uint64_t x) { return (int)__popcnt64(x); }

inline State apply_step(const State& s, int action) {
    State next;
    uint64_t pose = 0;
    Bits one{}, two{}, three{};

    for (int i = 0; i < 6; i++) {
        int act = (action >> (2 * i)) & 3;
        int p = (s.pose >> (8 * i)) & 127;
        int a = (s.pose >> (8 * i + 7)) & 1;

        if (act == 1) p = (p + L_perim - 1) % L_perim;
        else if (act == 2) p = (p + 1) % L_perim;
        else if (act == 3) a ^= 1;

        pose |= (uint64_t(p) | (uint64_t(a) << 7)) << (8 * i);

        if (a) {
            for (int w = 0; w < W_words; w++) {
                uint64_t ray = rays[p][i].b[w];
                three.b[w] |= two.b[w] & ray;
                two.b[w] |= one.b[w] & ray;
                one.b[w] |= ray;
            }
        }
    }
    next.pose = pose;
    next.accepted = s.accepted;

    // Update matter
    int good = 0, bad = 0;
    for (int w = 0; w < W_words; w++) {
        uint64_t m = (s.matter.b[w] | two.b[w]) & ~three.b[w];
        next.matter.b[w] = m;
        good += pc(m & target_mask.b[w]);
        bad += pc(m & forbid_mask.b[w]);
    }

    if (good == NT && bad == 0) {
        next.accepted++;
        for (int w = 0; w < W_words; w++) {
            next.matter.b[w] &= ~target_mask.b[w];
        }
    }

    return next;
}

const char CHARS[4] = {'-', 'F', 'B', 'T'};

int token_to_act(char ch) {
    if (ch == 'F') return 1;
    if (ch == 'B') return 2;
    if (ch == 'T') return 3;
    return 0;
}

// Find all single emitter paths of length L that reach (gp, ga) from (p0, a0)
void get_single_emitter_paths(int p0, int a0, int gp, int ga, int L, vector<vector<int>>& out_paths) {
    out_paths.clear();
    vector<int> cur(L);

    auto dfs = [&](auto& self, int step, int cp, int ca) -> void {
        if (step == L) {
            if (cp == gp && ca == ga) {
                out_paths.push_back(cur);
            }
            return;
        }
        for (int op = 0; op < 4; op++) {
            int np = cp, na = ca;
            if (op == 1) np = (np + L_perim - 1) % L_perim;
            else if (op == 2) np = (np + 1) % L_perim;
            else if (op == 3) na ^= 1;
            cur[step] = op;
            self(self, step + 1, np, na);
        }
    };

    dfs(dfs, 0, p0, a0);
}

bool search_window_fast(const State& s0, const State& s1, int target_L, vector<int>& best_plan, int max_combos = 50000) {
    vector<vector<int>> cand_paths[6];
    uint64_t total_combos = 1;

    for (int i = 0; i < 6; i++) {
        int cp = (s0.pose >> (8 * i)) & 127;
        int ca = (s0.pose >> (8 * i + 7)) & 1;
        int gp = (s1.pose >> (8 * i)) & 127;
        int ga = (s1.pose >> (8 * i + 7)) & 1;

        get_single_emitter_paths(cp, ca, gp, ga, target_L, cand_paths[i]);
        if (cand_paths[i].empty()) return false;

        total_combos *= cand_paths[i].size();
        if (total_combos > (uint64_t)max_combos) return false;
    }

    // Iterate cartesian product
    vector<int> chosen(6, 0);
    bool found = false;

    auto explore = [&](auto& self, int em_idx) -> bool {
        if (em_idx == 6) {
            // Simulate target_L steps
            State st = s0;
            vector<int> actions(target_L, 0);
            for (int step = 0; step < target_L; step++) {
                int act = 0;
                for (int i = 0; i < 6; i++) {
                    act |= cand_paths[i][chosen[i]][step] << (2 * i);
                }
                actions[step] = act;
                st = apply_step(st, act);
            }

            if (st.pose == s1.pose && st.accepted == s1.accepted && st.matter == s1.matter) {
                best_plan = actions;
                return true;
            }
            return false;
        }

        for (int p_idx = 0; p_idx < (int)cand_paths[em_idx].size(); p_idx++) {
            chosen[em_idx] = p_idx;
            if (self(self, em_idx + 1)) return true;
        }
        return false;
    };

    return explore(explore, 0);
}


#include <random>
#include <cmath>
using Clock=chrono::steady_clock;
mt19937 rng;
int evaluate(const vector<int>& p,State start, int *first=nullptr){
    State s=start;
    for(int t=0;t<(int)p.size();++t){
        s=apply_step(s,p[t]);
        if(s.accepted){
            if(first)*first=t+1;
            // A clean endpoint allows the same trajectory to repeat exactly.
            if(t==(int)p.size()-1) return 0;
            return 4+(int)p.size()-1-t;
        }
    }
    int cost=0;
    for(int w=0;w<W_words;w++)cost+=2*pc(target_mask.b[w]&~s.matter.b[w])+3*pc(forbid_mask.b[w]&s.matter.b[w]);
    return cost;
}
vector<int> compressed(const vector<int>& old,int H){
    vector<int> out(H); int cut=rng()%old.size();
    for(int e=0;e<6;e++){
        vector<int> ops;
        for(int a:old){int op=(a>>(2*e))&3;if(op)ops.push_back(op);}
        while((int)ops.size()>H){
            vector<int> c;
            for(int j=0;j+1<(int)ops.size();j++)if((ops[j]==1&&ops[j+1]==2)||(ops[j]==2&&ops[j+1]==1)||(ops[j]==3&&ops[j+1]==3))c.push_back(j);
            if(c.empty())return {};
            int j=c[rng()%c.size()];ops.erase(ops.begin()+j,ops.begin()+j+2);
        }
        vector<int> times;for(int t=0;t<(int)old.size();t++)if((old[t]>>(2*e))&3)times.push_back(t);
        int localcut=(rng()%4==0)?rng()%old.size():cut;
        int prev=-1;
        for(int j=0;j<(int)ops.size();j++){
            int ideal=(times.size()==ops.size()?times[j]-(times[j]>=localcut):j*H/(int)ops.size());
            int slot=max(prev+1,min(H-(int)ops.size()+j,ideal));
            out[slot]|=ops[j]<<(2*e);prev=slot;
        }
    }
    return out;
}

struct Transform {Bits keep,set;};
struct FastSchedule{
 int H,N;vector<int>& p;vector<uint64_t> poses;vector<Transform> tr;
 FastSchedule(vector<int>& prog,State root):p(prog){
  H=(int)p.size();N=1;while(N<H)N*=2;tr.resize(2*N);poses.resize(H+1);poses[0]=root.pose;
  for(int t=0;t<H;t++){
   uint64_t z=poses[t];
   for(int e=0;e<6;e++){int v=(z>>(8*e))&255,op=(p[t]>>(2*e))&3;int at=v&127,a=v&128;
    if(op==1)at=(at+L_perim-1)%L_perim;else if(op==2)at=(at+1)%L_perim;else if(op==3)a^=128;
    z=(z&~(255ULL<<(8*e)))|(uint64_t(at|a)<<(8*e));}
   poses[t+1]=z;leaf(t);
  }
  for(int t=H;t<N;t++)for(int w=0;w<W_words;w++)tr[N+t].keep.b[w]=~0ULL;
  for(int k=N-1;k;k--)merge(k);
 }
 void leaf(int t){
  Bits one{},two{},three{};uint64_t z=poses[t+1];
  for(int e=0;e<6;e++)if((z>>(8*e))&128){int at=(z>>(8*e))&127;
   for(int w=0;w<W_words;w++){auto ray=rays[at][e].b[w];three.b[w]|=two.b[w]&ray;two.b[w]|=one.b[w]&ray;one.b[w]|=ray;}}
  for(int w=0;w<W_words;w++){tr[N+t].keep.b[w]=~two.b[w];tr[N+t].set.b[w]=two.b[w]&~three.b[w];}
 }
 void merge(int k){for(int w=0;w<W_words;w++){
  tr[k].keep.b[w]=tr[2*k].keep.b[w]&tr[2*k+1].keep.b[w];
  tr[k].set.b[w]=(tr[2*k].set.b[w]&tr[2*k+1].keep.b[w])|tr[2*k+1].set.b[w];}}
 void refresh(int a,int b,int e){if(a>b)swap(a,b);
  for(int t=a;t<=b;t++){
   int v=(poses[t]>>(8*e))&255,op=(p[t]>>(2*e))&3;int at=v&127,on=v&128;
   if(op==1)at=(at+L_perim-1)%L_perim;else if(op==2)at=(at+1)%L_perim;else if(op==3)on^=128;
   uint64_t z=(poses[t+1]&~(255ULL<<(8*e)))|(uint64_t(at|on)<<(8*e));
   if(z!=poses[t+1]){poses[t+1]=z;leaf(t);for(int k=(N+t)/2;k;k/=2)merge(k);}
  }
 }
 int cost(State root){int v=0;
  for(int w=0;w<W_words;w++){uint64_t m=(root.matter.b[w]&tr[1].keep.b[w])|tr[1].set.b[w];v+=2*pc(target_mask.b[w]&~m)+3*pc(forbid_mask.b[w]&m);}

  return v;
 }
};
vector<int> anneal(vector<int> old,State root,int ms,int seed){
    rng.seed(seed);auto deadline=Clock::now()+chrono::milliseconds(ms);
    vector<int> answer=old;
    while(answer.size()>1&&Clock::now()<deadline){
        int H=(int)answer.size()-1;vector<int> best;int bestcost=100000;
        int stall=0;bool solved=false;
        while(Clock::now()<deadline&&!solved){
            vector<int> curr=compressed(answer,H);if(curr.empty())break;
            FastSchedule fast(curr,root); int cost=fast.cost(root);
            for(int it=0;it<12000;it++){
                if((it&511)==0&&Clock::now()>=deadline)break;
                if(cost==0){answer=curr;solved=true;break;}
                int e=rng()%6, a=rng()%H,b=(rng()%16==0)?rng()%H:(a+1+rng()%3)%H;if(a==b)continue;
                int x=(curr[a]>>(2*e))&3,y=(curr[b]>>(2*e))&3;
                int mode=rng()%8;
                int nx=y,ny=x;
                if(mode==0 && x==0&&y==0){nx=1+rng()%3;ny=nx==3?3:3-nx;}
                else if(mode==1 && ((x==1&&y==2)||(x==2&&y==1)||(x==3&&y==3))){nx=ny=0;}
                if(mode==2){
                    vector<pair<int,int>> opts;
                    auto d=[](int z){return z==1?-1:z==2?1:0;};
                    for(int aa=0;aa<4;aa++)for(int bb=0;bb<4;bb++)if(d(aa)+d(bb)==d(x)+d(y)&&((aa==3)^(bb==3))==((x==3)^(y==3)))opts.push_back({aa,bb});
                    auto v=opts[rng()%opts.size()];nx=v.first;ny=v.second;
                }
                if(x==nx&&y==ny)continue;
                int oa=curr[a],ob=curr[b];curr[a]=(oa&~(3<<(2*e)))|(nx<<(2*e));curr[b]=(ob&~(3<<(2*e)))|(ny<<(2*e));
                fast.refresh(a,b,e); int nc=fast.cost(root);
                double temp=0.05+1.0*(1.0-double(it%4000)/4000);
                if(nc<=cost || double(rng())/4294967296.0<exp((cost-nc)/temp))cost=nc;
                else{curr[a]=oa;curr[b]=ob;fast.refresh(a,b,e);}
                if(cost<bestcost){bestcost=cost;best=curr;stall=0;}
                else stall++;
                if(it%4000==3999&&!best.empty()){curr=best;fast.~FastSchedule();new (&fast) FastSchedule(curr,root);cost=bestcost;}
            }
        }
        cerr<<"H="<<H<<" bestcost="<<bestcost<<" solved="<<solved<<"\n";
        if(!solved)break;
    }
    return answer;
}
int main(int argc, char** argv) {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int required, incumbent;
    while (cin >> R >> required >> incumbent) {
        L_perim = 6 * R;
        vector<string> rows(2 * R + 1);
        for (string& s : rows) cin >> s;

        vector<pair<int, int>> cells;
        vector<vector<int>> index(2 * R + 1, vector<int>(4 * R + 1, -1));
        for (int y = 1; y < 2 * R; y++) {
            for (int x = 0; x <= 4 * R; x++) {
                if (rows[y][x] == 'O' || rows[y][x] == 'M') {
                    index[y][x] = (int)cells.size();
                    cells.push_back({y, x});
                }
            }
        }
        W_words = ((int)cells.size() + 63) / 64;
        target_mask = Bits();
        forbid_mask = Bits();
        NT = 0;

        int dy[6] = {0, 1, 1, 0, -1, -1};
        int dx[6] = {2, 1, -1, -2, -1, 1};

        for (int k = 0; k < (int)cells.size(); k++) {
            auto [y, x] = cells[k];
            if (rows[y][x] == 'M') {
                target_mask.b[k / 64] |= 1ULL << (k % 64);
                NT++;
            } else {
                for (int i = 0; i < 6; i++) {
                    int yy = y + dy[i], xx = x + dx[i];
                    if (yy >= 0 && yy <= 2 * R && xx >= 0 && xx <= 4 * R && rows[yy][xx] == 'M') {
                        forbid_mask.b[k / 64] |= 1ULL << (k % 64);
                    }
                }
            }
        }

        rays.assign(L_perim, {});
        pair<int, int> corners[6] = {{R, 0}, {2 * R, R}, {2 * R, 3 * R}, {R, 4 * R}, {0, 3 * R}, {0, R}};
        for (int side = 0; side < 6; side++) {
            for (int j = 0; j < R; j++) {
                auto [y, x] = corners[side];
                auto [yy, xx] = corners[(side + 1) % 6];
                y += j * (yy - y) / R;
                x += j * (xx - x) / R;
                int p = side * R + j;
                for (int i = 0; i < 6; i++) {
                    int ny = y + dy[i], nx = x + dx[i];
                    while (ny >= 0 && ny <= 2 * R && nx >= 0 && nx <= 4 * R) {
                        int k = index[ny][nx];
                        if (k >= 0) {
                            rays[p][i].b[k / 64] |= (1ULL << (k % 64)) & (target_mask.b[k / 64] | forbid_mask.b[k / 64]);
                        }
                        ny += dy[i];
                        nx += dx[i];
                    }
                }
            }
        }

        int prog_len;
        cin >> prog_len;
        vector<int> program(prog_len);
        for (int t = 0; t < prog_len; t++) {
            int act = 0;
            for (int i = 0; i < 6; i++) {
                char ch;
                cin >> ch;
                act |= token_to_act(ch) << (2 * i);
            }
            program[t] = act;
        }

        // Initial state
        int initial[6] = {0, 5 * R, 4 * R, 3 * R, 2 * R, R};
        State start_state;
        for (int i = 0; i < 6; i++) {
            start_state.pose |= uint64_t(initial[i]) << (8 * i);
        }


        // Stochastic retiming of an entire periodic six-emitter trajectory.
        // Commands may change timing and intermediate matter; only endpoint pose
        // and a clean pickup are constraints.
        start_state.pose=0;
        unsigned long long rootpose; cin >> rootpose;
        start_state.pose=rootpose;
        for(int w=0;w<W_words;w++)cin>>start_state.matter.b[w];
        for(int w=0;w<W_words;w++)cin>>target_mask.b[w];
        for(int w=0;w<W_words;w++)cin>>forbid_mask.b[w];
        NT=0;for(int w=0;w<W_words;w++)NT+=pc(target_mask.b[w]);
        int budget, seed; cin >> budget >> seed;
        program=anneal(program,start_state,budget,seed);
        int total_saved=prog_len-(int)program.size();
        // Output result
        cout << program.size() << " " << total_saved;
        for (int act : program) {
            cout << " ";
            for (int i = 0; i < 6; i++) {
                cout << CHARS[(act >> (2 * i)) & 3];
            }
        }
        cout << "\n" << flush;
    }
    return 0;
}
