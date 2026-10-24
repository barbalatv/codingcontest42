// Chained-beam builder for level 6: repeatedly searches for the shortest tick block
// that produces the next accepted copy, starting from the real post-accept state.
// g++ -O2 -march=native -o beam beam.cpp
#include <bits/stdc++.h>
using namespace std;
typedef unsigned long long u64;
typedef unsigned char u8;
static const int NW = 6;

struct Mask { u64 w[NW]; };
static inline int pc(const Mask&a){ int s=0; for(int i=0;i<NW;i++) s+=__builtin_popcountll(a.w[i]); return s; }
static inline bool covers(const Mask&a,const Mask&b){ for(int i=0;i<NW;i++) if((a.w[i]&b.w[i])!=b.w[i]) return false; return true; }
static inline bool common(const Mask&a,const Mask&b){ for(int i=0;i<NW;i++) if(a.w[i]&b.w[i]) return true; return false; }

struct Inst {
    int r, K, nrel, L, curL;
    int init[6];
    Mask target, forbid;
    vector<array<Mask,6>> rays;
};
static vector<Inst> load(const string& path) {
    ifstream f(path); string line; vector<Inst> out;
    while (getline(f, line)) {
        if (line.empty()) continue;
        istringstream ss(line); string tag; ss >> tag;
        if (tag == "case") {
            Inst in; string ds; int idx;
            ss >> ds >> idx >> in.r >> in.K >> in.nrel >> in.L;
            in.L = 6*in.r; in.rays.assign(in.L, {}); in.curL = 0;
            out.push_back(in);
        } else if (tag == "cur") { int v; ss >> v; out.back().curL = v; }
        else if (tag == "init") { for (int i=0;i<6;i++) ss >> out.back().init[i]; }
        else if (tag == "target") { for (int i=0;i<NW;i++) ss >> out.back().target.w[i]; }
        else if (tag == "forbid") { for (int i=0;i<NW;i++) ss >> out.back().forbid.w[i]; }
        else if (tag == "ray") { int p,d; ss >> p >> d; for (int i=0;i<NW;i++) ss >> out.back().rays[p][d].w[i]; }
    }
    return out;
}

struct St {
    u8 pos[6]; u8 active; Mask matter; int count;
    inline void apply(const Inst& in, const u8* act) {
        for (int i=0;i<6;i++) {
            int a = act[i];
            if (a==1) pos[i] = (u8)((pos[i]+in.L-1)%in.L);
            else if (a==2) pos[i] = (u8)((pos[i]+1)%in.L);
            else if (a==3) active ^= (1u<<i);
        }
        Mask one{}, two{}, three{};
        for (int i=0;i<6;i++) if (active>>i&1) {
            const Mask& ray = in.rays[pos[i]][i];
            for (int k=0;k<NW;k++) { three.w[k] |= two.w[k]&ray.w[k]; two.w[k] |= one.w[k]&ray.w[k]; one.w[k] |= ray.w[k]; }
        }
        for (int k=0;k<NW;k++) { u64 h2 = two.w[k] & ~three.w[k]; matter.w[k] = (matter.w[k]|h2) & ~three.w[k]; }
        if (covers(matter, in.target) && !common(matter, in.forbid)) {
            count++;
            for (int k=0;k<NW;k++) matter.w[k] &= ~in.target.w[k];
        }
    }
};

static vector<array<u8,6>> ACT;
static void init_actions() {
    if (!ACT.empty()) return;
    for (int a0=0;a0<4;a0++) for (int a1=0;a1<4;a1++) for (int a2=0;a2<4;a2++)
    for (int a3=0;a3<4;a3++) for (int a4=0;a4<4;a4++) for (int a5=0;a5<4;a5++) {
        if (!(a0|a1|a2|a3|a4|a5)) continue;
        ACT.push_back({{(u8)a0,(u8)a1,(u8)a2,(u8)a3,(u8)a4,(u8)a5}});
    }
}

struct Node { St st; u8 act[6]; int key; };

static bool beam_once(const Inst& in, const St& start, int width, int maxDepth,
                      vector<array<u8,6>>& out, long long& evals) {
    init_actions();
    int need = pc(in.target);
    vector<vector<Node>> layers;
    vector<Node> cur, nxt;
    Node root{}; root.st = start; memset(root.act,0,6); root.key=0;
    layers.push_back({root}); cur.push_back(root);
    for (int d=1; d<=maxDepth; d++) {
        nxt.clear(); nxt.reserve(cur.size()*ACT.size());
        for (size_t a=0;a<cur.size();a++) {
            const St base = cur[a].st;
            for (const auto& ac : ACT) {
                Node ch; ch.st = base; ch.st.apply(in, ac.data());
                memcpy(ch.act, ac.data(), 6);
                int un = need - pc(ch.st.matter); if (un<0) un=0;
                int fm=0; for(int k=0;k<NW;k++) fm += __builtin_popcountll(ch.st.matter.w[k] & in.forbid.w[k]);
                ch.key = un*16 + fm*4;
                nxt.push_back(ch);
            }
        }
        evals += (long long)nxt.size();
        int hit=-1;
        for (size_t a=0;a<nxt.size();a++) if (nxt[a].st.count > start.count) { hit=(int)a; break; }
        if (hit>=0) { out.assign(1, {{nxt[hit].act[0],nxt[hit].act[1],nxt[hit].act[2],nxt[hit].act[3],nxt[hit].act[4],nxt[hit].act[5]}}); return true; }
        auto lessState=[](const Node&a,const Node&b){
            for (int i=0;i<6;i++) if (a.st.pos[i]!=b.st.pos[i]) return a.st.pos[i]<b.st.pos[i];
            if (a.st.active!=b.st.active) return a.st.active<b.st.active;
            for (int k=0;k<NW;k++) if (a.st.matter.w[k]!=b.st.matter.w[k]) return a.st.matter.w[k]<b.st.matter.w[k];
            return false; };
        sort(nxt.begin(), nxt.end(), lessState);
        nxt.erase(unique(nxt.begin(), nxt.end(), [](const Node&a,const Node&b){
            for (int i=0;i<6;i++) if (a.st.pos[i]!=b.st.pos[i]) return false;
            if (a.st.active!=b.st.active) return false;
            for (int k=0;k<NW;k++) if (a.st.matter.w[k]!=b.st.matter.w[k]) return false;
            return true; }), nxt.end());
        if ((int)nxt.size()>width) {
            nth_element(nxt.begin(), nxt.begin()+width, nxt.end(), [](const Node&a,const Node&b){return a.key<b.key;});
            nxt.resize(width);
        }
        sort(nxt.begin(), nxt.end(), [](const Node&a,const Node&b){return a.key<b.key;});
        layers.push_back(nxt); cur.swap(nxt);
        if (cur.empty()) return false;
    }
    return false;
}

int main(int argc, char** argv){
    auto insts = load("cases.txt");
    int width = argc>1?atoi(argv[1]):1500;
    int maxDepth = argc>2?atoi(argv[2]):70;
    int from = argc>3?atoi(argv[3]):0, to = argc>4?atoi(argv[4]):(int)insts.size();
    fprintf(stderr, "loaded %zu cases\n", insts.size());
    for (int i=from;i<min(to,(int)insts.size());i++){
        const Inst& in = insts[i];
        auto t0=chrono::steady_clock::now();
        St s{}; setInit(s, in);
        long long ev=0;
        vector<array<u8,6>> prog;
        bool bad=false;
        while (s.count < in.K) {
            vector<array<u8,6>> block;
            if (!beam_once(in, s, width, maxDepth, block, ev)) { bad=true; break; }
            for (auto& a : block) { s.apply(in, a.data()); prog.push_back(a); }
        }
        double ms=chrono::duration<double,milli>(chrono::steady_clock::now()-t0).count();
        printf("case %d r=%d K=%d nT=%d curL=%d beamL=%d evals=%lld ms=%.0f%s\n",
               i, in.r, in.K, pc(in.target), in.curL, (int)prog.size(), ev, ms, bad?" BAD":"");
        fflush(stdout);
        if (getenv("DUMP") && !bad && (int)prog.size() < in.curL) {
            string fn = string("beamok_") + to_string(i) + ".txt";
            FILE* f = fopen(fn.c_str(), "w");
            for (auto& a : prog) { for (int q=0;q<6;q++) fprintf(f, "%c ", "-FBT"[a[q]]); fprintf(f,"\n"); }
            fclose(f);
        }
    }
}
