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

int wanted=1;
uint64_t bridge_goal=~uint64_t(0);
int allowed_emitters[3]={0,1,2},n_allowed=6;
int pose_cost(uint64_t a,uint64_t b){int d=0;for(int e=0;e<6;e++){int p=(a>>(8*e))&127,q=(b>>(8*e))&127;int v=abs(p-q);d+=min(v,L_perim-v)+int(((a^b)>>(8*e+7))&1);}return d;}
int evaluate(const vector<int>& p,State start,int *first=nullptr){
 State st=start;
 for(int t=0;t<(int)p.size();t++){
  st=apply_step(st,p[t]);
  if(st.accepted>=wanted){if(first)*first=t+1;if(bridge_goal==~uint64_t(0)||st.pose==bridge_goal)return 0;return 1+pose_cost(st.pose,bridge_goal);}
 }
 int cost=2*NT*max(0,wanted-st.accepted-1);
 for(int w=0;w<W_words;w++)cost+=2*pc(target_mask.b[w]&~st.matter.b[w])+3*pc(forbid_mask.b[w]&st.matter.b[w]);
 return cost;
}
vector<int> anneal(vector<int> old,State root,int ms,int seed){
 rng.seed(seed);auto deadline=Clock::now()+chrono::milliseconds(ms);vector<int> ans=old;
 int rounds=0;
 while(ans.size()>1&&Clock::now()<deadline){
  bool solved=false;vector<int> best;int bestcost=100000;
  while(!solved&&Clock::now()<deadline){
   n_allowed=2+rng()%2;for(int j=0;j<n_allowed;j++)allowed_emitters[j]=rng()%6;
   int cut=rng()%ans.size(); /* Cross-acceptance neighborhoods start from actual material. */vector<int> curr=ans;curr.erase(curr.begin()+cut);int H=curr.size();
   int cost=evaluate(curr,root);int localbest=cost;
   for(int it=0;it<10000;it++){
    if((it&511)==0&&Clock::now()>=deadline)break;
    if(cost==0){int finish=H;evaluate(curr,root,&finish);curr.resize(finish);ans=curr;solved=true;break;}
    int e=(rounds%3==0)?rng()%6:allowed_emitters[rng()%n_allowed];int a;
    if(rng()%4){int radius=4+(it/1000)*2;a=max(0,min(H-1,cut+int(rng()%(2*radius+1))-radius));}
    else a=rng()%H;
    int b=(rng()%3)?max(0,min(H-1,a+int(rng()%7)-3)):rng()%H;
    int oa=curr[a],ob=curr[b],x=(oa>>(2*e))&3,y=(ob>>(2*e))&3;
    if(rng()%4||a==b)curr[a]=(oa&~(3<<(2*e)))|((rng()%4)<<(2*e));
    else {curr[a]=(oa&~(3<<(2*e)))|(y<<(2*e));curr[b]=(ob&~(3<<(2*e)))|(x<<(2*e));}
    int nc=evaluate(curr,root);double temp=0.06+0.95*(1.0-double(it%2500)/2500);
    if(nc<=cost||double(rng())/4294967296.0<exp((cost-nc)/temp))cost=nc;
    else{curr[a]=oa;curr[b]=ob;}
    if(cost<localbest)localbest=cost;
    if(cost<bestcost){bestcost=cost;best=curr;}
   }
   rounds++;
  }
  cerr<<"full H="<<ans.size()-1<<" best="<<bestcost<<" solved="<<solved<<" rounds="<<rounds<<"\n";
  if(!solved)break;
 }
 return ans;
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


        wanted=required;
        // Stochastic retiming of an entire periodic six-emitter trajectory.
        // Commands may change timing and intermediate matter; only endpoint pose
        // and a clean pickup are constraints.
        start_state.pose=0;
        unsigned long long rootpose; cin >> rootpose;
        start_state.pose=rootpose;
        for(int w=0;w<W_words;w++)cin>>start_state.matter.b[w];
        int budget, seed; cin >> budget >> seed >> bridge_goal;
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
