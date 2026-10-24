// Period synthesis for level 6.
// Finds a closed pose-walk of p ticks that accepts the pattern m times (rate p/m),
// i.e. directly minimises the steady-state cost per copy.
// g++ -O3 -march=native -o cycle_sa cycle_sa.cpp
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
    vector<array<u8,6>> prog;
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
        else if (tag == "prog") {
            int v; while (ss >> v) { array<u8,6> a{}; for (int e=0;e<6;e++) a[e]=(u8)((v>>(2*e))&3); out.back().prog.push_back(a); }
        }
        else if (tag == "init") { for (int i=0;i<6;i++) ss >> out.back().init[i]; }
        else if (tag == "target") { for (int i=0;i<NW;i++) ss >> out.back().target.w[i]; }
        else if (tag == "forbid") { for (int i=0;i<NW;i++) ss >> out.back().forbid.w[i]; }
        else if (tag == "ray") { int p,d; ss >> p >> d; for (int i=0;i<NW;i++) ss >> out.back().rays[p][d].w[i]; }
    }
    return out;
}

struct St { u8 pos[6]; u8 active; Mask matter; int count; };
static inline void applyTok(const Inst& in, St& s, const u8* act) {
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

struct Rng { u64 s; Rng(u64 x):s(x?x:88172645463325252ull){}
    inline u64 n(){ s^=s<<13; s^=s>>7; s^=s<<17; return s; }
    inline int i(int m){ return (int)(n()%(u64)m); }
    inline double d(){ return (double)(n()>>11) * (1.0/9007199254740992.0); } };

// ---------------------------------------------------------------- incumbent analysis
struct AccInfo { vector<int> ticks; vector<array<int,6>> pos; vector<int> act; };

static AccInfo traceAccepts(const Inst& in) {
    AccInfo a;
    St s{}; for (int i=0;i<6;i++) s.pos[i]=(u8)in.init[i];
    s.active=0; memset(&s.matter,0,sizeof(Mask)); s.count=0;
    for (size_t t=0;t<in.prog.size();t++) {
        int c0 = s.count;
        applyTok(in, s, in.prog[t].data());
        if (s.count != c0) {
            a.ticks.push_back((int)t+1);
            a.pos.push_back({s.pos[0],s.pos[1],s.pos[2],s.pos[3],s.pos[4],s.pos[5]});
            a.act.push_back(s.active);
        }
    }
    return a;
}

// minimal p,m such that the last two accept states coincide
static bool incumbentRate(const AccInfo& a, int& p, int& m) {
    int n = (int)a.ticks.size();
    if (n < 2) return false;
    for (int back=1; back<n; back++) {
        int i = n-1-back, j = n-1;
        if (a.pos[i]==a.pos[j] && a.act[i]==a.act[j]) { p = a.ticks[j]-a.ticks[i]; m = back; return true; }
    }
    p = a.ticks[n-1]-a.ticks[n-2]; m = 1;
    return true;
}

// ---------------------------------------------------------------- cycle search
struct Cyc {
    int p=0, A=0;
    int base[6] = {0,0,0,0,0,0};
    vector<array<int,6>> step;   // -1,0,1  (0 = no move)
    vector<array<u8,6>> tog;     // 1 = toggle
    int accepts=0, closeErr=0;
};

static int REP = 3;

// Simulate REP repetitions of the block from (base, A, empty matter).
// Returns a smooth score; accepts are what matter, painted cells give the gradient.
static int evalCycle(const Inst& in, const Cyc& c, int* accOut=nullptr, int* closeOut=nullptr) {
    St s{}; for (int i=0;i<6;i++) s.pos[i]=(u8)c.base[i];
    s.active=(u8)c.A; memset(&s.matter,0,sizeof(Mask)); s.count=0;
    int reps = REP;
    if (c.p*reps > 48) reps = max(1, 48/c.p);
    for (int r=0;r<reps;r++) for (int t=0;t<c.p;t++) {
        u8 tok[6];
        for (int i=0;i<6;i++) {
            if (c.tog[t][i]) tok[i]=3;
            else if (c.step[t][i]==1) tok[i]=2;
            else if (c.step[t][i]==-1) tok[i]=1;
            else tok[i]=0;
        }
        applyTok(in, s, tok);
    }
    int painted = pc(s.matter);
    int f=0; for (int k=0;k<NW;k++) f += __builtin_popcountll(s.matter.w[k] & in.forbid.w[k]);
    if (accOut) *accOut = s.count;
    if (closeOut) *closeOut = 0;
    return s.count*1000 + painted - f*3;
}

static void repairClosure(const Inst& in, Cyc& c) {
    for (int i=0;i<6;i++) {
        int sum=0, tg=0;
        for (int t=0;t<c.p;t++) { sum += c.step[t][i]; tg ^= c.tog[t][i]; }
        // fix displacement: flip steps toward zero, keeping move/toggle exclusivity
        int guard=0;
        while (sum != 0 && guard++ < 64) {
            if (sum > 0) {
                bool done=false;
                for (int t=0;t<c.p && !done;t++) if (c.step[t][i]==1) { c.step[t][i]=0; sum--; done=true; }
                for (int t=0;t<c.p && !done;t++) if (c.step[t][i]==0 && !c.tog[t][i]) { c.step[t][i]=-1; sum--; done=true; }
                if (!done) break;
            } else {
                bool done=false;
                for (int t=0;t<c.p && !done;t++) if (c.step[t][i]==-1) { c.step[t][i]=0; sum++; done=true; }
                for (int t=0;t<c.p && !done;t++) if (c.step[t][i]==0 && !c.tog[t][i]) { c.step[t][i]=1; sum++; done=true; }
                if (!done) break;
            }
        }
        if (tg) { for (int t=0;t<c.p && tg;t++) if (c.tog[t][i]) { c.tog[t][i]=0; c.step[t][i]=0; tg^=1; } }
    }
}

static void saCycles(const Inst& in, Cyc& best, int p, int iters, u64 seed, double T0, double T1) {
    Rng rng(seed);
    Cyc cur; cur.p = p; cur.A = best.A;
    for (int i=0;i<6;i++) cur.base[i] = best.base[i];
    cur.step.assign(p, {0,0,0,0,0,0});
    cur.tog.assign(p, {0,0,0,0,0,0});
    for (int t=0;t<p && t<(int)best.step.size();t++){ cur.step[t]=best.step[t]; cur.tog[t]=best.tog[t]; }
    int curS = evalCycle(in, cur);
    Cyc bestLocal = cur; int bestS = curS;
    int bestAcc=0, bestClo=0; evalCycle(in, bestLocal, &bestAcc, &bestClo);
    for (int it=0; it<iters; it++) {
        double T = T0 * pow(T1/T0, (double)it/iters);
        int kind = rng.i(13);
        Cyc cand = cur;
        if (kind >= 10) {
            int i = rng.i(6);
            cand.base[i] = (cand.base[i] + (rng.i(2)?1:-1) + in.L) % in.L;
        } else if (kind < 5) {
            int t = rng.i(p), i = rng.i(6);
            static const int opts[3] = {-1,0,1};
            cand.step[t][i] = opts[rng.i(3)];
            if (cand.step[t][i] != 0) cand.tog[t][i] = 0;
        } else if (kind < 9) {
            int t = rng.i(p), i = rng.i(6);
            cand.tog[t][i] ^= 1;
            if (cand.tog[t][i]) cand.step[t][i] = 0;
        } else if (kind < 10) {
            int t = rng.i(p), i = rng.i(6);
            cand.tog[t][i] ^= 1;
            if (cand.tog[t][i]) cand.step[t][i] = 0;
            int t2 = rng.i(p);
            cand.step[t2][i] = (cand.step[t2][i]==1)?-1:1;
        }
        int sc = evalCycle(in, cand);
        if (sc >= curS || rng.d() < exp((sc - curS)/T)) {
            cur = cand; curS = sc;
            if (sc > bestS) { bestS = sc; bestLocal = cand; }
        }
    }
    int a=0, clo=0; evalCycle(in, bestLocal, &a, &clo);
    if (a*1000 - clo*5 > (best.accepts*1000 - best.closeErr*5)) {
        best = bestLocal; best.accepts=a; best.closeErr=clo;
    }
}

int main(int argc, char** argv){
    auto insts = load("cases.txt");
    int iters = argc>1?atoi(argv[1]):100000;
    int from  = argc>2?atoi(argv[2]):0;
    int to    = argc>3?atoi(argv[3]):(int)insts.size();
    int maxP  = argc>4?atoi(argv[4]):14;
    fprintf(stderr,"loaded %zu\n", insts.size());
    for (int i=from;i<min(to,(int)insts.size());i++){
        const Inst& in = insts[i];
        if (in.K < 2 || in.prog.empty()) continue;
        AccInfo a = traceAccepts(in);
        int q=0, m=0;
        if (!incumbentRate(a, q, m)) { printf("case %d NO_ACC\n", i); continue; }
        double curRate = (double)q/m;
        // search for a block with a better rate
        int bestP=q, bestM=m; Cyc bestPlan; bestPlan.p=q; bestPlan.A=0; bestPlan.accepts=0; bestPlan.closeErr=0;
        Cyc seed; seed.p=q; seed.A=0;
        seed.step.assign(q, {0,0,0,0,0,0}); seed.tog.assign(q, {0,0,0,0,0,0});
        {
            int n=(int)a.ticks.size(), si=n-2;
            int p2 = a.ticks[n-1]-a.ticks[si], m2 = 1;
            seed.p=p2; seed.A=a.act[si];
            for (int e=0;e<6;e++) seed.base[e]=a.pos[si][e];
            seed.step.assign(p2, {0,0,0,0,0,0});
            seed.tog.assign(p2, {0,0,0,0,0,0});
            for (int t=0;t<p2;t++) {
                array<u8,6> tok = in.prog[a.ticks[si]+t];
                for (int e=0;e<6;e++) {
                    if (tok[e]==3) seed.tog[t][e]=1;
                    else if (tok[e]==2) seed.step[t][e]=1;
                    else if (tok[e]==1) seed.step[t][e]=-1;
                }
            }
            int sa=0, sc=0; evalCycle(in, seed, &sa, &sc);
            if (getenv("VERBOSE")) fprintf(stderr, "[case %d seed p=%d accepts=%d]\n", i, p2, sa);
            q=p2; m=m2;
        }
        bestPlan = seed;
        bool improved=false;
        for (int p=1; p<=maxP; p++) {
            if (p*m > 3*q + 4) break;
            Cyc cand = seed; cand.p = p;
            cand.step.assign(p, {0,0,0,0,0,0}); cand.tog.assign(p, {0,0,0,0,0,0});
            cand.accepts=0; cand.closeErr=0;
            for (int rs=0; rs<4; rs++)
                saCycles(in, cand, p, iters, (0x9E3779B97F4A7C15ull*(i+1)) ^ (0xD1B54A32D192ED03ull*(p+1)) ^ (rs*7919ull), 60.0, 0.4);
            if (cand.accepts > 0 && (double)cand.accepts/p > (double)bestM/bestP + 1e-9) {
                bestP = p; bestM = cand.accepts; bestPlan = cand; improved = true;
            }
        }
        if (improved) {
            printf("case %d r=%d K=%d nT=%d seed p=%d -> p=%d accepts=%d rate=%.3f\n",
                   i, in.r, in.K, pc(in.target), q, bestP, bestM, (double)bestM/bestP);
            char fn[64]; snprintf(fn, sizeof fn, "cyc_%d.txt", i);
            FILE* f=fopen(fn,"w");
            fprintf(f,"A %d\n", bestPlan.A);
            for (int t=0;t<bestP;t++) {
                for (int e=0;e<6;e++) {
                    char ch = bestPlan.tog[t][e] ? 'T' : (bestPlan.step[t][e]==1?'B':(bestPlan.step[t][e]==-1?'F':'-'));
                    fprintf(f,"%c ", ch);
                }
                fprintf(f,"\n");
            }
            fclose(f);
        } else {
            printf("case %d r=%d K=%d nT=%d seed p=%d no better\n", i, in.r, in.K, pc(in.target), q);
        }
        fflush(stdout);
    }
}
