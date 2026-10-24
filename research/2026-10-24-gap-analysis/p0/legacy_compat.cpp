// Acceptance-Constrained Endgame Repair.
//
// Takes the incumbent program and tries to replace its last W ticks with W-1 ticks
// that still deliver the final accept exactly on the last tick. Works on K=1 cases
// first (no suffix to stay compatible with), then on the final interval of K>1 cases.
//
// The beam is pruned by an admissible lower bound on the remaining ticks:
// for every still-missing cell, the cheapest emitter pair that can cover it needs
// `minDistance` ticks, and the maximum over cells is a valid lower bound.
//
//   ./endgame [caseIdx...]        env: WMIN WMAX WIDTH (defaults 4 10 300)
//
// g++ -O2 -march=native -o endgame endgame.cpp
#include "../portable.hpp"
using namespace std;
typedef unsigned long long u64;
typedef unsigned char u8;
static const int NW = 6;

struct Mask { u64 w[NW]; };
static inline int pc(const Mask&a){ int s=0; for(int i=0;i<NW;i++) s+=__builtin_popcountll(a.w[i]); return s; }
static inline bool covers(const Mask&a,const Mask&b){ for(int i=0;i<NW;i++) if((a.w[i]&b.w[i])!=b.w[i]) return false; return true; }
static inline bool common(const Mask&a,const Mask&b){ for(int i=0;i<NW;i++) if(a.w[i]&b.w[i]) return true; return false; }
static inline bool sameMask(const Mask&a,const Mask&b){ for(int i=0;i<NW;i++) if(a.w[i]!=b.w[i]) return false; return true; }

struct Inst {
    int r,K,nrel,L,curL; string ds; int idx;
    int init[6]; Mask target, forbid;
    vector<array<Mask,6>> rays;
    vector<array<u8,6>> prog;
};
static vector<Inst> load(const string& path) {
    ifstream f(path); string line; vector<Inst> out;
    while (getline(f,line)) { if(line.empty()) continue; istringstream ss(line); string tag; ss>>tag;
        if(tag=="case"){ Inst in; ss>>in.ds>>in.idx>>in.r>>in.K>>in.nrel>>in.L; in.L=6*in.r; in.rays.assign(in.L,{}); in.curL=0; out.push_back(in);}
        else if(tag=="cur"){int v; ss>>v; out.back().curL=v;}
        else if(tag=="prog"){ int v; while(ss>>v){ array<u8,6> a{}; for(int e=0;e<6;e++) a[e]=(u8)((v>>(2*e))&3); out.back().prog.push_back(a);} }
        else if(tag=="init"){for(int i=0;i<6;i++) ss>>out.back().init[i];}
        else if(tag=="target"){for(int i=0;i<NW;i++) ss>>out.back().target.w[i];}
        else if(tag=="forbid"){for(int i=0;i<NW;i++) ss>>out.back().forbid.w[i];}
        else if(tag=="ray"){int p,d; ss>>p>>d; for(int i=0;i<NW;i++) ss>>out.back().rays[p][d].w[i];}
    } return out;
}

struct St { u8 pos[6]; u8 active; Mask matter; int count; };
static inline void setInit(St& s, const Inst& in) {
    for (int i=0;i<6;i++) s.pos[i]=(u8)in.init[i];
    s.active=0; memset(&s.matter,0,sizeof(Mask)); s.count=0;
}
static inline void apply(const Inst& in, St& s, const u8* act) {
    for (int i=0;i<6;i++) { int a=act[i];
        if(a==1) s.pos[i]=(u8)((s.pos[i]+in.L-1)%in.L);
        else if(a==2) s.pos[i]=(u8)((s.pos[i]+1)%in.L);
        else if(a==3) s.active^=(1u<<i); }
    Mask one{},two{},three{};
    for (int i=0;i<6;i++) if (s.active>>i&1) { const Mask& ray=in.rays[s.pos[i]][i];
        for (int k=0;k<NW;k++){ three.w[k]|=two.w[k]&ray.w[k]; two.w[k]|=one.w[k]&ray.w[k]; one.w[k]|=ray.w[k]; } }
    for (int k=0;k<NW;k++){ u64 h2=two.w[k]&~three.w[k]; s.matter.w[k]=(s.matter.w[k]|h2)&~three.w[k]; }
    if (covers(s.matter,in.target) && !common(s.matter,in.forbid)) {
        s.count++; for (int k=0;k<NW;k++) s.matter.w[k]&=~in.target.w[k]; }
}
static inline bool sameState(const St&a,const St&b){
    if(a.active!=b.active||a.count!=b.count) return false;
    for (int i=0;i<6;i++) if(a.pos[i]!=b.pos[i]) return false;
    for (int k=0;k<NW;k++) if(a.matter.w[k]!=b.matter.w[k]) return false;
    return true;
}

// positions of each track that cover a given relevant cell
struct Cover {
    vector<vector<vector<int>>> byTrack;   // [track][cell] -> positions
    void build(const Inst& in, int nrel) {
        byTrack.assign(6, vector<vector<int>>(nrel));
        for (int i=0;i<6;i++) for (int c=0;c<nrel;c++) {
            int w=c/64,b=c%64;
            for (int p=0;p<in.L;p++) if ((in.rays[p][i].w[w]>>b)&1) byTrack[i][c].push_back(p);
        }
    }
};

static inline int dist1(int a,int b,int L){ int d=(b-a)%L; if(d<0)d+=L; if(d>L/2)d-=L; return abs(d); }

// admissible lower bound on the number of ticks still needed
static int lowerBound(const Inst& in, const Cover& cv, const St& s) {
    int worst = 0;
    for (int k=0;k<NW;k++) {
        u64 miss = in.target.w[k] & ~s.matter.w[k];
        while (miss) {
            int b=__builtin_ctzll(miss), c=k*64+b;
            int need = INT_MAX;
            for (int i=0;i<6 && need>0;i++) for (int j=i+1;j<6 && need>0;j++) {
                const auto& pi=cv.byTrack[i][c]; const auto& pj=cv.byTrack[j][c];
                if (pi.empty()||pj.empty()) continue;
                for (int x : pi) for (int y : pj) {
                    int d = max(dist1(s.pos[i],x,in.L), dist1(s.pos[j],y,in.L));
                    need = min(need, d);
                }
            }
            if (need==INT_MAX) return 99;
            worst = max(worst, need);
            miss &= miss-1;
        }
    }
    return worst;
}

static vector<array<u8,6>>* gAll = nullptr;
static vector<array<u8,6>>& allActions() {
    static vector<array<u8,6>> ALL;
    if (ALL.empty()) for (int m=0;m<4096;m++) {
        array<u8,6> a{}; int x=m; bool any=false;
        for (int i=0;i<6;i++){ a[i]=(u8)(x&3); x>>=2; if(a[i]) any=true; }
        if (any) ALL.push_back(a);
    }
    return ALL;
}
// true when some single action completes the copy on the very next tick
static bool canFinishInOne(const Inst& in, const St& s, int goalCount, array<u8,6>* which=nullptr) {
    for (const auto& a : allActions()) {
        St t=s; apply(in,t,a.data());
        if (t.count==goalCount && !common(t.matter,in.forbid) && covers(t.matter,in.target)) {
            if (which) *which=a; return true; }
    }
    return false;
}

struct Rng { u64 s; Rng(u64 x):s(x?x:88172645463325252ull){}
    inline u64 n(){ s^=s<<13; s^=s>>7; s^=s<<17; return s; }
    inline int i(int m){ return (int)(n()%(u64)m); } };

struct Node { St st; int par; u8 act[6]; int key; bool lookahead=false; };

static void score(const Inst& in, const Cover& cv, Node& n) {
    int miss=0, skirt=0;
    for(int k=0;k<NW;k++){
        miss += __builtin_popcountll(in.target.w[k] & ~n.st.matter.w[k]);
        skirt += __builtin_popcountll(in.forbid.w[k] & n.st.matter.w[k]);
    }
    n.key = miss*100 + skirt*50 + lowerBound(in,cv,n.st);
}

// Search from `start` for a sequence of exactly `ticks` ticks whose LAST tick performs
// the accept (count == goalCount, target covered, no skirting). Free final pose.
static vector<array<u8,6>> endgameSearch(const Inst& in, const Cover& cv, const St& start,
                                         int goalCount, int ticks, int width) {
    vector<vector<Node>> layers;
    vector<Node> cur, nxt;
    Node root; root.st=start; root.par=-1; memset(root.act,0,6); score(in,cv,root);
    layers.push_back({root}); cur.push_back(root);
    for (int d=1; d<=ticks; d++) {
        nxt.clear();
        int remaining = ticks - d;
        for (size_t ni=0; ni<cur.size(); ni++) {
            const St& s = cur[ni].st;
            // FULL joint action space: every emitter independently does one of
            // {- nothing, F, B, T } -> 4^6 = 4096 combinations. This is the complete
            // multi-emitter action set (audit problem C: the old generator was narrow).
            static vector<array<u8,6>> ALL;
            if (ALL.empty()) {
                for (int m=0;m<4096;m++) {
                    array<u8,6> a{}; int x=m; bool any=false;
                    for (int i=0;i<6;i++){ a[i]=(u8)(x&3); x>>=2; if(a[i]) any=true; }
                    if (any) ALL.push_back(a);
                }
            }
            const vector<array<u8,6>>& cand = ALL;
            for (const auto& a : cand) {
                bool any=false; for(int q=0;q<6;q++) if(a[q]) any=true;
                if(!any) continue;
                Node ch; ch.st=s; apply(in, ch.st, a.data());
                if (ch.st.count > goalCount) continue;
                bool last = (d==ticks);
                if (last) {
                    // the accept must happen exactly on the final tick
                    if (ch.st.count != goalCount) continue;
                    if (common(ch.st.matter, in.forbid)) continue;
                    if (!covers(ch.st.matter, in.target)) continue;
                } else {
                    if (ch.st.count != start.count) continue;      // no early accept
                }
                score(in,cv,ch);
                if (lowerBound(in,cv,ch.st) > remaining) continue;   // admissible prune
                ch.par=(int)ni; memcpy(ch.act,a.data(),6);
                if (last) {
                    vector<array<u8,6>> seq(d);
                    memcpy(seq[d-1].data(), a.data(), 6);
                    int idx=(int)ni;
                    for (int t=d-1;t>=1;t--) { const Node& nn = layers[t][idx];
                        memcpy(seq[t-1].data(), nn.act, 6); idx=nn.par; }
                    return seq;
                }
                nxt.push_back(ch);
            }
        }
        if (getenv("DEBUG")) {
            int bl=1<<30, bm=1<<30;
            for (auto& n : nxt) { bl=min(bl,n.key/1000); }
            for (auto& n : cur) { int m=0; for(int k=0;k<NW;k++) m+=__builtin_popcountll(in.target.w[k]&~n.st.matter.w[k]); bm=min(bm,m); }
            fprintf(stderr,"  d=%d/%d states=%zu minLB=%d minMissing(prev)=%d\n", d, ticks, nxt.size(), bl, bm);
        }
        if (nxt.empty()) { if (getenv("DEBUG")) fprintf(stderr,"  d=%d beam died\n", d); return {}; }
        if (d == ticks-1) {
            // one-tick lookahead: prefer states that can actually be completed
            for (auto& n : nxt) { n.lookahead = canFinishInOne(in, n.st, goalCount); n.key = n.lookahead ? 0 : n.key; }
            stable_sort(nxt.begin(), nxt.end(), [](const Node&a,const Node&b){ return a.key<b.key; });
            for (auto& n : nxt) if (n.lookahead) {
                array<u8,6> act;
                if (canFinishInOne(in, n.st, goalCount, &act)) {
                    vector<array<u8,6>> seq(d+1);
                    memcpy(seq[d].data(), act.data(), 6);
                    int idx=(int)(&n - nxt.data());
                    // n may have been produced from layers[d-1]; allow duplicate search
                    for (int t=d;t>=1;t--) {
                        const Node& nn = (t==d) ? n : layers[t][idx];
                        memcpy(seq[t-1].data(), nn.act, 6); idx = nn.par;
                    }
                    return seq;
                }
            }
        }
        sort(nxt.begin(), nxt.end(), [](const Node&a,const Node&b){ return a.key<b.key; });
        nxt.erase(unique(nxt.begin(), nxt.end(), [](const Node&a,const Node&b){ return sameState(a.st,b.st); }), nxt.end());
        if ((int)nxt.size()>width) nxt.resize(width);
        layers.push_back(nxt); cur = nxt;
    }
    return {};
}

static bool validate(const Inst& in, const vector<array<u8,6>>& prog) {
    St s{}; setInit(s,in); int prev=0,lastAcc=-1;
    for (size_t t=0;t<prog.size();t++){ apply(in,s,prog[t].data()); if(s.count>prev){prev=s.count;lastAcc=(int)t+1;} }
    return s.count==in.K && lastAcc==(int)prog.size();
}

int main(int argc, char** argv) {
    auto insts = load("cases.txt");
    int wmin = getenv("WMIN")?atoi(getenv("WMIN")):4;
    int wmax = getenv("WMAX")?atoi(getenv("WMAX")):10;
    int width = getenv("WIDTH")?atoi(getenv("WIDTH")):300;
    vector<int> want; for(int a=1;a<argc;a++) want.push_back(atoi(argv[a]));
    fprintf(stderr,"loaded %zu cases wmin=%d wmax=%d width=%d\n", insts.size(), wmin, wmax, width);
    for (int ci : want) {
        const Inst& in = insts[ci];
        Cover cv; cv.build(in, in.nrel);
        vector<array<u8,6>> best = in.prog;
        if (!validate(in,best)) { printf("case %d BAD_INPUT\n", ci); continue; }
        int startLen=(int)best.size();
        auto t0=chrono::steady_clock::now();
        int wins=0;
        bool improved=true;
        while (improved) {
            improved=false;
            vector<St> S(best.size()+1);
            setInit(S[0],in);
            for (size_t t=0;t<best.size();t++){ S[t+1]=S[t]; apply(in,S[t+1],best[t].data()); }
            int T=(int)best.size();
            for (int W=wmin; W<=wmax && !improved; W++) {
                int a=T-W; if (a<0) continue;
                auto repl = endgameSearch(in, cv, S[a], S[T].count, W-1, width);
                if (repl.empty()) continue;
                vector<array<u8,6>> cand;
                cand.insert(cand.end(), best.begin(), best.begin()+a);
                cand.insert(cand.end(), repl.begin(), repl.end());
                if ((int)cand.size()<(int)best.size() && validate(in,cand)) {
                    printf("  case %d: endgame W=%d -> %d saved 1 tick (total %zu -> %zu)\n",
                           ci, W, W-1, best.size(), cand.size());
                    best=cand; wins++; improved=true;
                }
            }
        }
        double ms=chrono::duration<double,milli>(chrono::steady_clock::now()-t0).count();
        printf("case %d %s#%d nT=%d K=%d curL=%d endgame=%zu wins=%d %s ms=%.0f\n",
               ci, in.ds.c_str(), in.idx, pc(in.target), in.K, startLen, best.size(), wins,
               ((int)best.size()<startLen?"SHORTER":"same"), ms);
        fflush(stdout);
        if ((int)best.size()<startLen && getenv("DUMP")) {
            char fn[64]; snprintf(fn,sizeof fn,"eg_%d.txt",ci);
            FILE* f=fopen(fn,"w");
            for (auto& a : best){ for(int q=0;q<6;q++) fprintf(f,"%c ","-FBT"[a[q]]); fprintf(f,"\n"); }
            fclose(f);
        }
    }
}
