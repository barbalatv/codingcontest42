// Geometry-first planning with exact transition costs, stage 5 of the audit plan:
// beam search over (matter state) where every move is a real configuration reached by
// a real command sequence whose tick cost is computed exactly.
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

struct Inst { int r,K,nrel,L,curL; int init[6]; Mask target,forbid; vector<array<Mask,6>> rays; string ds; int idx; };
static vector<Inst> load(const string& path) {
    ifstream f(path); string line; vector<Inst> out;
    while (getline(f,line)) { if(line.empty()) continue; istringstream ss(line); string tag; ss>>tag;
        if(tag=="case"){ Inst in; ss>>in.ds>>in.idx>>in.r>>in.K>>in.nrel>>in.L; in.L=6*in.r; in.rays.assign(in.L,{}); in.curL=0; out.push_back(in);}
        else if(tag=="cur"){int v; ss>>v; out.back().curL=v;}
        else if(tag=="init"){for(int i=0;i<6;i++) ss>>out.back().init[i];}
        else if(tag=="target"){for(int i=0;i<NW;i++) ss>>out.back().target.w[i];}
        else if(tag=="forbid"){for(int i=0;i<NW;i++) ss>>out.back().forbid.w[i];}
        else if(tag=="ray"){int p,d; ss>>p>>d; for(int i=0;i<NW;i++) ss>>out.back().rays[p][d].w[i];}
    } return out;
}
struct St { u8 pos[6]; u8 active; Mask matter; int count; };
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
struct Rng { u64 s; Rng(u64 x):s(x?x:88172645463325252ull){} inline u64 n(){s^=s<<13;s^=s>>7;s^=s<<17;return s;} inline int i(int m){return (int)(n()%(u64)m);} };

struct Config { array<u8,6> pos; u8 mask; };

static int dist1(int a,int b,int L){ int d=(b-a)%L; if(d<0)d+=L; if(d>L/2)d-=L; return abs(d); }

// exact tick cost + token sequence to reach the configuration and fire it once
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

int main(int argc,char**argv){
    auto insts=load("cases.txt");
    int width = getenv("W")?atoi(getenv("W")):64;
    int depth = getenv("D")?atoi(getenv("D")):8;
    int libN  = getenv("LIB")?atoi(getenv("LIB")):300;
    vector<int> want; for(int a=1;a<argc;a++) want.push_back(atoi(argv[a]));
    fprintf(stderr,"loaded %zu  width=%d depth=%d libN=%d\n", insts.size(), width, depth, libN);
    for (int ci : want) {
        const Inst& in = insts[ci];
        int nT = pc(in.target);
        Rng rng(0x77777ull*(ci+11));
        // --- library: sample poses, keep the useful ones
        vector<Config> lib; vector<int> gain;
        set<array<u64,3>> seen;
        for (int s=0;s<60000 && (int)lib.size()<libN*4;s++) {
            Config c; Mask one{},two{},three{};
            c.mask=(s%6==0)?(u8)(1+rng.i(63)):(u8)63;
            for(int i=0;i<6;i++){ c.pos[i]=(u8)rng.i(in.L); if(!((c.mask>>i)&1))continue;
                const Mask& ray=in.rays[c.pos[i]][i];
                for(int k=0;k<NW;k++){ three.w[k]|=two.w[k]&ray.w[k]; two.w[k]|=one.w[k]&ray.w[k]; one.w[k]|=ray.w[k]; } }
            Mask h2; for(int k=0;k<NW;k++) h2.w[k]=two.w[k]&~three.w[k];
            int f=0,g=0;
            for(int k=0;k<NW;k++){ g+=__builtin_popcountll(h2.w[k]&in.target.w[k]); f+=__builtin_popcountll(h2.w[k]&in.forbid.w[k]); }
            if(f||g<2) continue;
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
        St s0{}; memcpy(s0.pos,in.init,6); s0.active=0; memset(&s0.matter,0,sizeof(Mask)); s0.count=0;
        struct Node { St st; int cost; int par; int cfg; vector<array<u8,6>> steps; };
        vector<Node> cur, nxt;
        Node root; root.st=s0; root.cost=0; root.par=-1; root.cfg=-1;
        cur.push_back(root);
        int bestTotal=INT_MAX; vector<array<u8,6>> bestProg;
        for (int d=0; d<depth && !cur.empty(); d++) {
            nxt.clear();
            for (auto& nd : cur) for (int j=0;j<(int)lib.size();j++) {
                vector<array<u8,6>> steps; int cost=build_steps(in, nd.st, lib[j], steps);
                Node ch; ch.st=nd.st; for(auto&a:steps) apply(in,ch.st,a.data());
                ch.cost=nd.cost+cost; ch.cfg=j; ch.steps=steps;
                if (ch.st.count>0) {
                    if (nd.cost+cost < bestTotal) { bestTotal=nd.cost+cost; bestProg.clear();
                        // rebuild program: walk the ancestor chain is not stored; keep incremental
                    }
                }
                int painted=0; for(int k=0;k<NW;k++) painted+=__builtin_popcountll(ch.st.matter.w[k]&in.target.w[k]);
                if (painted==0) continue;                       // no progress
                nxt.push_back(ch);
            }
            // dedupe by matter+pose, keep cheapest
            sort(nxt.begin(),nxt.end(),[](const Node&a,const Node&b){return a.cost<b.cost;});
            vector<Node> keep;
            set<array<u64,2>> seenN;
            for (auto& n : nxt) {
                array<u64,2> key{ n.st.matter.w[0]^ (u64)n.st.pos[0]<<56, n.st.matter.w[1]^ (u64)n.st.pos[1]<<56 };
                if (!seenN.insert(key).second) continue;
                if ((int)keep.size()<width) keep.push_back(n);
                if ((int)keep.size()>=width) break;
            }
            cur.swap(keep);
        }
        // report the best painted state at the last depth (no accept found means no valid plan)
        int bestPainted=0; for (auto& n : cur) { int p=0; for(int k=0;k<NW;k++) p+=__builtin_popcountll(n.st.matter.w[k]&in.target.w[k]); bestPainted=max(bestPainted,p); }
        double ms=chrono::duration<double,milli>(chrono::steady_clock::now()-t0).count();
        printf("case %d %s#%d nT=%d K=%d curL=%d lib=%zu plan=%s painted=%d/%d ms=%.0f\n",
               ci, in.ds.c_str(), in.idx, nT, in.K, in.curL, lib.size(),
               bestTotal==INT_MAX?"none":to_string(bestTotal).c_str(), bestPainted, nT, ms);
        fflush(stdout);
    }
}
