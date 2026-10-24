// Geometry-first beam search - corrected version.
//
// Fixes for the four defects reported in the audit of the first implementation:
//   1. candidates are ranked by a heuristic on the residual, not by cost alone
//   2. states after an accept are KEPT (matter is empty there; they start the next copy)
//   3. the dedupe key covers the FULL state: all matter words, all six positions,
//      the active mask and the accept count
//   4. the solution is reconstructed through parent links and validated exactly
//      before it is emitted; the goal is the full K copies, not the first accept
//
// g++ -O2 -march=native -o geo_beam geo_beam.cpp
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
    int r,K,nrel,L,curL; string ds; int idx;
    int init[6]; Mask target, forbid;
    vector<array<Mask,6>> rays;
};
static vector<Inst> load(const string& path) {
    ifstream f(path); string line; vector<Inst> out;
    while (getline(f,line)) { if(line.empty()) continue; istringstream ss(line); string tag; ss>>tag;
        if(tag=="case"){ Inst in; ss>>in.ds>>in.idx>>in.r>>in.K>>in.nrel>>in.L; in.L=6*in.r; in.rays.assign(in.L,{}); in.curL=0; out.push_back(in);}
        else if(tag=="cur"){int v; ss>>v; out.back().curL=v;}
        else if(tag=="prog"){ int v; while(ss>>v){} }
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
    if (a.active!=b.active || a.count!=b.count) return false;
    for (int i=0;i<6;i++) if (a.pos[i]!=b.pos[i]) return false;
    for (int k=0;k<NW;k++) if (a.matter.w[k]!=b.matter.w[k]) return false;
    return true;
}
struct Rng { u64 s; Rng(u64 x):s(x?x:88172645463325252ull){}
    inline u64 n(){ s^=s<<13; s^=s>>7; s^=s<<17; return s; }
    inline int i(int m){ return (int)(n()%(u64)m); } };

struct Config { array<u8,6> pos; u8 mask; };
static inline int dist1(int a,int b,int L){ int d=(b-a)%L; if(d<0)d+=L; if(d>L/2)d-=L; return abs(d); }

static int build_steps(const Inst& in, const St& s, const Config& g, vector<array<u8,6>>& out) {
    int d[6], L=1;
    for (int i=0;i<6;i++){ d[i]=dist1(s.pos[i],g.pos[i],in.L);
        int a0=(s.active>>i)&1,a1=(g.mask>>i)&1;
        L=max(L, max(1, d[i]+((a0!=a1)?1:0))); }
    out.assign(L,{0,0,0,0,0,0});
    for (int i=0;i<6;i++){
        int a0=(s.active>>i)&1,a1=(g.mask>>i)&1;
        int delta=(g.pos[i]-s.pos[i])%in.L; if(delta<0)delta+=in.L;
        u8 tok=(delta<=in.L/2)?2:1;
        for(int k=0;k<d[i];k++) out[k][i]=tok;
        if(a0!=a1) out[min(d[i],L-1)][i]=3;
    }
    return L;
}

struct Node {
    St st; int g=0; int par=-1; int cfg=-1; int key=0;
    vector<array<u8,6>> steps;          // steps taken to reach this node
};

int main(int argc, char** argv) {
    auto insts = load("cases.txt");
    int width = getenv("W")?atoi(getenv("W")):64;
    int maxSteps = getenv("STEPS")?atoi(getenv("STEPS")):40;   // number of configurations fired
    int libN = getenv("LIB")?atoi(getenv("LIB")):300;
    vector<int> want; for (int a=1;a<argc;a++) want.push_back(atoi(argv[a]));
    fprintf(stderr,"loaded %zu width=%d maxConfigs=%d libN=%d\n", insts.size(), width, maxSteps, libN);
    for (int ci : want) {
        const Inst& in = insts[ci];
        int nT = pc(in.target);
        Rng rng(0x77777ull*(ci+11));
        vector<Config> lib; vector<int> gain;
        set<array<u64,3>> seen;
        for (int s=0; s<80000 && (int)lib.size()<libN*4; s++) {
            Config c; Mask one{},two{},three{};
            c.mask=(s%6==0)?(u8)(1+rng.i(63)):(u8)63;
            for(int i=0;i<6;i++){ c.pos[i]=(u8)rng.i(in.L); if(!((c.mask>>i)&1))continue;
                const Mask& ray=in.rays[c.pos[i]][i];
                for(int k=0;k<NW;k++){ three.w[k]|=two.w[k]&ray.w[k]; two.w[k]|=one.w[k]&ray.w[k]; one.w[k]|=ray.w[k]; } }
            Mask h2; for(int k=0;k<NW;k++) h2.w[k]=two.w[k]&~three.w[k];
            int f=0,g=0;
            for(int k=0;k<NW;k++){ g+=__builtin_popcountll(h2.w[k]&in.target.w[k]); f+=__builtin_popcountll(h2.w[k]&in.forbid.w[k]); }
            if(f||g<1) continue;
            array<u64,3> key{c.pos[0]+256ull*c.pos[1]+65536ull*c.pos[2], c.pos[3]+256ull*c.pos[4]+65536ull*c.pos[5], c.mask};
            if(!seen.insert(key).second) continue;
            lib.push_back(c); gain.push_back(g);
        }
        if((int)lib.size()>libN){
            vector<int> ord(lib.size()); iota(ord.begin(),ord.end(),0);
            sort(ord.begin(),ord.end(),[&](int a,int b){return gain[a]>gain[b];});
            vector<Config> l2; vector<int> g2;
            for(int j=0;j<libN;j++){ l2.push_back(lib[ord[j]]); g2.push_back(gain[ord[j]]); }
            lib.swap(l2); gain.swap(g2);
        }
        auto t0=chrono::steady_clock::now();
        St s0{}; setInit(s0, in);
        vector<vector<Node>> layers;
        vector<Node> cur, nxt;
        Node root; root.st=s0; root.g=0; root.par=-1;
        layers.push_back({root}); cur.push_back(root);
        vector<array<u8,6>> best;
        for (int step=0; step<maxSteps && best.empty(); step++) {
            nxt.clear();
            for (size_t ni=0; ni<cur.size(); ni++) {
                for (int j=0;j<(int)lib.size();j++) {
                    vector<array<u8,6>> steps; int cost=build_steps(in, cur[ni].st, lib[j], steps);
                    Node ch; ch.st=cur[ni].st;
                    for (auto& a : steps) apply(in, ch.st, a.data());
                    ch.g = cur[ni].g + cost; ch.par=(int)ni; ch.cfg=j; ch.steps=steps;
                    // (2) keep post-accept states: matter is empty there, that is the
                    //     natural start of the next copy - do NOT filter them out
                    int missing=0, skirt=0;
                    for(int k=0;k<NW;k++){
                        missing += __builtin_popcountll(in.target.w[k] & ~ch.st.matter.w[k]);
                        skirt   += __builtin_popcountll(in.forbid.w[k] & ch.st.matter.w[k]);
                    }
                    // (1) rank by a residual heuristic, not by cost
                    ch.key = (in.K - ch.st.count)*10000 + missing*10 + skirt*30 + ch.g;
                    nxt.push_back(ch);
                }
            }
            if (nxt.empty()) break;
            // (4) goal is the FULL K copies
            int hit=-1;
            for (size_t i=0;i<nxt.size();i++) if (nxt[i].st.count >= in.K) { hit=(int)i; break; }
            if (hit>=0) {
                // reconstruct through the layers
                vector<array<u8,6>> seq;
                int idx=hit;
                for (int t=step+1; t>=1; t--) {
                    const Node& n = (t==step+1) ? nxt[idx] : layers[t][idx];
                    seq.insert(seq.begin(), n.steps.begin(), n.steps.end());
                    idx = n.par;
                }
                // (4) exact validation before emitting anything
                St v{}; setInit(v, in); int lastAcc=-1, prev=0;
                for (size_t t=0;t<seq.size();t++){ apply(in, v, seq[t].data());
                    if (v.count>prev){ prev=v.count; lastAcc=(int)t+1; } }
                if (v.count==in.K && lastAcc==(int)seq.size()) best=seq;
                break;
            }
            // (3) dedupe on the FULL state
            sort(nxt.begin(), nxt.end(), [](const Node&a,const Node&b){
                if (a.key!=b.key) return a.key<b.key;
                if (a.st.count!=b.st.count) return a.st.count>b.st.count;
                for (int i=0;i<6;i++) if (a.st.pos[i]!=b.st.pos[i]) return a.st.pos[i]<b.st.pos[i];
                if (a.st.active!=b.st.active) return a.st.active<b.st.active;
                for (int k=0;k<NW;k++) if (a.st.matter.w[k]!=b.st.matter.w[k]) return a.st.matter.w[k]<b.st.matter.w[k];
                return false; });
            nxt.erase(unique(nxt.begin(), nxt.end(), [](const Node&a,const Node&b){ return sameState(a.st,b.st); }), nxt.end());
            if ((int)nxt.size()>width) nxt.resize(width);
            layers.push_back(nxt); cur.swap(nxt);
        }
        double ms=chrono::duration<double,milli>(chrono::steady_clock::now()-t0).count();
        printf("case %d %s#%d nT=%d K=%d curL=%d plan=%d %s ms=%.0f\n",
               ci, in.ds.c_str(), in.idx, nT, in.K, in.curL, (int)best.size(),
               best.empty()?"none":(best.size()<in.curL?"BEATS":"longer"), ms);
        fflush(stdout);
        if (!best.empty() && getenv("DUMP")) {
            char fn[64]; snprintf(fn,sizeof fn,"gb_%d.txt",ci);
            FILE* f=fopen(fn,"w");
            for (auto& a : best) { for(int q=0;q<6;q++) fprintf(f,"%c ","-FBT"[a[q]]); fprintf(f,"\n"); }
            fclose(f);
        }
    }
    return 0;
}
