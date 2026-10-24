// Geometry-first brush planning with exact transition costs.
//
// A "configuration" is (positions[6], activeMask). From a concrete state it has an
// exact effect: the cells created (exactly 2 hits) and destroyed (3+ hits).
// The planner repeatedly picks a configuration from a sampled library, executes the
// exact tick sequence that reaches it, and measures the real result by simulation.
// Two transit modes are supported:
//   productive (default): beams keep their state while moving
//   safe (-s):            every beam is switched off before moving and on again at the goal
//
// g++ -O2 -march=native -o geometry geometry.cpp
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
    string ds; int idx;
};
static vector<Inst> load(const string& path) {
    ifstream f(path); string line; vector<Inst> out;
    while (getline(f, line)) {
        if (line.empty()) continue;
        istringstream ss(line); string tag; ss >> tag;
        if (tag == "case") {
            Inst in; ss >> in.ds >> in.idx >> in.r >> in.K >> in.nrel >> in.L;
            in.L = 6*in.r; in.rays.assign(in.L, {}); in.curL = 0; out.push_back(in);
        } else if (tag == "cur") { int v; ss >> v; out.back().curL = v; }
        else if (tag == "init") { for (int i=0;i<6;i++) ss >> out.back().init[i]; }
        else if (tag == "target") { for (int i=0;i<NW;i++) ss >> out.back().target.w[i]; }
        else if (tag == "forbid") { for (int i=0;i<NW;i++) ss >> out.back().forbid.w[i]; }
        else if (tag == "ray") { int p,d; ss >> p >> d; for (int i=0;i<NW;i++) ss >> out.back().rays[p][d].w[i]; }
    }
    return out;
}

struct St { u8 pos[6]; u8 active; Mask matter; int count; };

static inline void apply(const Inst& in, St& s, const u8* act) {
    for (int i=0;i<6;i++) {
        int a = act[i];
        if (a==1) s.pos[i] = (u8)((s.pos[i]+in.L-1)%in.L);
        else if (a==2) s.pos[i] = (u8)((s.pos[i]+1)%in.L);
        else if (a==3) s.active ^= (1u<<i);
    }
    Mask one{}, two{}, three{};
    for (int i=0;i<6;i++) if (s.active>>i&1) {
        const Mask& ray = in.rays[s.pos[i]][i];
        for (int k=0;k<NW;k++) { three.w[k] |= two.w[k]&ray.w[k]; two.w[k] |= one.w[k]&ray.w[k]; one.w[k] |= ray.w[k]; }
    }
    for (int k=0;k<NW;k++) { u64 h2 = two.w[k] & ~three.w[k]; s.matter.w[k] = (s.matter.w[k]|h2) & ~three.w[k]; }
    if (covers(s.matter, in.target) && !common(s.matter, in.forbid)) {
        s.count++;
        for (int k=0;k<NW;k++) s.matter.w[k] &= ~in.target.w[k];
    }
}

// NOTE: positions are u8[6] while Inst::init is int[6] - copy element-wise, never memcpy.
static inline void setInit(St& s, const Inst& in) {
    for (int i=0;i<6;i++) s.pos[i] = (u8)in.init[i];
    s.active = 0; memset(&s.matter, 0, sizeof(Mask)); s.count = 0;
}

struct Rng { u64 s; Rng(u64 x):s(x?x:88172645463325252ull){}
    inline u64 n(){ s^=s<<13; s^=s>>7; s^=s<<17; return s; }
    inline int i(int m){ return (int)(n()%(u64)m); } };

struct Config { array<u8,6> pos; u8 mask; int gain; int dirty; };

static int dist(int a, int b, int L) {
    int d = (b - a) % L; if (d < 0) d += L;
    if (d > L/2) d -= L;
    return abs(d);
}

// Build the tick sequence that brings every emitter to the goal pose/mask.
// Productive transit: move first, then toggle (so the goal state holds on the last tick).
// Safe transit: toggle off, move, toggle on; no beam is active while moving.
static vector<array<u8,6>> make_steps(const Inst& in, const St& s, const Config& g, bool safe) {
    int d[6];
    for (int i=0;i<6;i++) d[i] = dist(s.pos[i], g.pos[i], in.L);
    int L = 1;
    for (int i=0;i<6;i++) {
        int a0 = (s.active>>i)&1, a1 = (g.mask>>i)&1;
        int end = safe ? (d[i] + (a0?1:0) + (a1?1:0) + (a1?1:0)) : (d[i] + ((a0!=a1)?1:0));
        L = max(L, max(1, end));
    }
    vector<array<u8,6>> steps(L);
    for (int t=0;t<L;t++) steps[t] = {0,0,0,0,0,0};
    for (int i=0;i<6;i++) {
        int a0 = (s.active>>i)&1, a1 = (g.mask>>i)&1;
        int delta = (g.pos[i] - s.pos[i]) % in.L; if (delta < 0) delta += in.L;
        u8 stepTok = (delta <= in.L/2) ? 2 : 1;     // B (+1) when walking forward
        int cur = 0;
        if (safe) {
            if (a0) { steps[0][i] = 3; cur = 1; }
            for (int k=0;k<d[i];k++) steps[cur+k][i] = stepTok;
            cur += d[i];
            if (a1) steps[min(cur, L-1)][i] = 3;
        } else {
            for (int k=0;k<d[i];k++) steps[k][i] = stepTok;
            if (a0 != a1) steps[min(d[i], L-1)][i] = 3;
        }
    }
    return steps;
}

int main(int argc, char** argv) {
    auto insts = load("cases.txt");
    int libSize = 40000;
    int beamWidth = 6;
    bool safe = false;
    bool cleanOnly = true;
    if (getenv("DIRTY")) cleanOnly = atoi(getenv("DIRTY")) == 0;
    vector<int> want;
    for (int a=1;a<argc;a++) {
        string s = argv[a];
        if (s == "-s") { safe = true; continue; }
        if (s[0]=='-' ) continue;
        want.push_back(atoi(argv[a]));
    }
    if (getenv("LIB")) libSize = atoi(getenv("LIB"));
    if (getenv("BEAM")) beamWidth = atoi(getenv("BEAM"));
    fprintf(stderr, "loaded %zu cases, lib=%d beam=%d safe=%d\n", insts.size(), libSize, beamWidth, (int)safe);
    for (int ci : want) {
        if (ci < 0 || ci >= (int)insts.size()) continue;
        const Inst& in = insts[ci];
        int nT = pc(in.target);
        Rng rng(0xABCDEFull*(ci+3));
        // ---- configuration library
        vector<Config> lib;
        lib.reserve(libSize);
        set<array<u64,2>> seen;
        for (int s=0;s<libSize;s++) {
            Config c;
            Mask one{}, two{}, three{};
            c.mask = (s%5==0) ? (u8)(1+rng.i(63)) : (u8)63;
            for (int i=0;i<6;i++) {
                c.pos[i] = (u8)rng.i(in.L);
                if (!((c.mask>>i)&1)) continue;
                const Mask& ray = in.rays[c.pos[i]][i];
                for (int k=0;k<NW;k++) { three.w[k] |= two.w[k]&ray.w[k]; two.w[k] |= one.w[k]&ray.w[k]; one.w[k] |= ray.w[k]; }
            }
            Mask h2; for (int k=0;k<NW;k++) h2.w[k] = two.w[k] & ~three.w[k];
            int g=0,f=0;
            for (int k=0;k<NW;k++) { g += __builtin_popcountll(h2.w[k]&in.target.w[k]); f += __builtin_popcountll(h2.w[k]&in.forbid.w[k]); }
            if (g < 1) continue;
            c.gain = g; c.dirty = f;
            if (cleanOnly && f) continue;
            lib.push_back(c);
        }
        auto t0 = chrono::steady_clock::now();
        // ---- planning loop
        St s{}; setInit(s, in);
        int ticks = 0; int accepted = 0;
        vector<array<u8,6>> program;
        int stall = 0;
        while (s.count < in.K && ticks < 400 && stall < 60) {
            int painted = pc(s.matter);
            // rank candidates by optimistic gain per tick
            vector<pair<double,int>> rank;
            rank.reserve(lib.size());
            for (int j=0;j<(int)lib.size();j++) {
                const Config& c = lib[j];
                int dmax = 1, tg = 0;
                for (int i=0;i<6;i++) {
                    int d = dist(s.pos[i], c.pos[i], in.L);
                    int t = (safe ? (((s.active>>i)&1)?1:0) + (((c.mask>>i)&1)?1:0)
                                  : ((((s.active>>i)&1) != ((c.mask>>i)&1)) ? 1 : 0));
                    dmax = max(dmax, d + t);
                    tg += t;
                }
                // optimistic: cells of this config still missing
                int gain = 0;
                if (c.dirty == 0 || true) {
                    // recompute the actual double-hit set intersection with the still-missing cells
                    Mask one{}, two{}, three{};
                    for (int i=0;i<6;i++) {
                        if (!((c.mask>>i)&1)) continue;
                        const Mask& ray = in.rays[c.pos[i]][i];
                        for (int k=0;k<NW;k++) { three.w[k] |= two.w[k]&ray.w[k]; two.w[k] |= one.w[k]&ray.w[k]; one.w[k] |= ray.w[k]; }
                    }
                    for (int k=0;k<NW;k++) {
                        u64 h2 = two.w[k] & ~three.w[k];
                        gain += __builtin_popcountll(h2 & in.target.w[k] & ~s.matter.w[k]);
                    }
                }
                if (gain <= 0) continue;
                double score = (double)gain / (double)dmax;
                // finishing moves: this configuration covers everything still missing
                {
                    Mask one{}, two{}, three{};
                    for (int i=0;i<6;i++) {
                        if (!((c.mask>>i)&1)) continue;
                        const Mask& ray = in.rays[c.pos[i]][i];
                        for (int k=0;k<NW;k++) { three.w[k] |= two.w[k]&ray.w[k]; two.w[k] |= one.w[k]&ray.w[k]; one.w[k] |= ray.w[k]; }
                    }
                    bool full=true; int extraSkirt=0;
                    for (int k=0;k<NW;k++) {
                        u64 h2 = two.w[k] & ~three.w[k];
                        if ((h2 | s.matter.w[k]) != (s.matter.w[k] | in.target.w[k])) full=false;
                        extraSkirt += __builtin_popcountll(h2 & in.forbid.w[k]);
                    }
                    if (full && extraSkirt==0) score += 1000.0;
                }
                rank.push_back({score, j});
            }
            if (rank.empty()) break;
            nth_element(rank.begin(), rank.begin()+min((int)rank.size(),beamWidth), rank.end(),
                        [](auto&a,auto&b){ return a.first > b.first; });
            if ((int)rank.size() > beamWidth) rank.resize(beamWidth);
            // exact evaluation of the top candidates
            int bestGain=-1, bestTicks=0; vector<array<u8,6>> bestSteps; St bestState{};
            for (auto& pr : rank) {
                const Config& c = lib[pr.second];
                auto steps = make_steps(in, s, c, safe);
                St t = s;
                for (auto& a : steps) apply(in, t, a.data());
                int gain = pc(t.matter) - painted;
                int dirt = 0; for (int k=0;k<NW;k++) dirt += __builtin_popcountll(t.matter.w[k] & in.forbid.w[k]);
                gain -= 2*dirt;
                if (t.count > s.count) gain += 100000;
                if (gain > bestGain) { bestGain = gain; bestTicks = (int)steps.size(); bestSteps = steps; bestState = t; }
            }
            if (bestGain <= 0) { stall++; if (stall > 20) break; }
            for (auto& a : bestSteps) {
                program.push_back(a);
                St t = s; apply(in, t, a.data()); s = t;
                if (getenv("DEBUG")) {
                    int pt=0, pf=0;
                    for (int k=0;k<NW;k++) { pt += __builtin_popcountll(s.matter.w[k]&in.target.w[k]); pf += __builtin_popcountll(s.matter.w[k]&in.forbid.w[k]); }
                    fprintf(stderr, "   t=%-3d target=%-3d skirt=%-2d acc=%d  %s\n", (int)program.size(), pt, pf, s.count,
                            ([&]{ string z; for (int q=0;q<6;q++) z += "-FBT"[a[q]]; return z; })().c_str());
                }
            }
            ticks += bestTicks;
            if (s.count > accepted) { accepted = s.count; stall = 0; }
        }
        double ms = chrono::duration<double,milli>(chrono::steady_clock::now()-t0).count();
        printf("case %d %s#%d nT=%d K=%d curL=%d lib=%zu plan=%d accepts=%d %s ms=%.0f\n",
               ci, in.ds.c_str(), in.idx, nT, in.K, in.curL, lib.size(), ticks, s.count,
               (s.count>=in.K?"OK":"FAIL"), ms);
        fflush(stdout);
        if (s.count >= in.K && getenv("DUMP")) {
            char fn[64]; snprintf(fn, sizeof fn, "geo_%d.txt", ci);
            FILE* f = fopen(fn, "w");
            for (auto& a : program) { for (int q=0;q<6;q++) fprintf(f, "%c ", "-FBT"[a[q]]); fprintf(f,"\n"); }
            fclose(f);
        }
    }
}
