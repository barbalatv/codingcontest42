// Regression test for the compressed C++ model.
// Replays every incumbent program from cases.txt and asserts it accepts exactly K copies
// on the last tick. A broken model (wrong init pose, wrong rays, wrong order of
// operations) fails immediately here - this is what caught the memcpy(u8[6], int[6]) bug.
// g++ -O2 -o selftest selftest.cpp
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
    for (int i=0;i<6;i++) s.pos[i] = (u8)in.init[i];
    s.active = 0; memset(&s.matter, 0, sizeof(Mask)); s.count = 0;
}
static inline void apply(const Inst& in, St& s, const u8* act) {
    for (int i=0;i<6;i++) { int a=act[i];
        if(a==1) s.pos[i]=(u8)((s.pos[i]+in.L-1)%in.L);
        else if(a==2) s.pos[i]=(u8)((s.pos[i]+1)%in.L);
        else if(a==3) s.active^=(1u<<i);
    }
    Mask one{},two{},three{};
    for (int i=0;i<6;i++) if (s.active>>i&1) { const Mask& ray=in.rays[s.pos[i]][i];
        for (int k=0;k<NW;k++){ three.w[k]|=two.w[k]&ray.w[k]; two.w[k]|=one.w[k]&ray.w[k]; one.w[k]|=ray.w[k]; } }
    for (int k=0;k<NW;k++){ u64 h2=two.w[k]&~three.w[k]; s.matter.w[k]=(s.matter.w[k]|h2)&~three.w[k]; }
    if (covers(s.matter,in.target) && !common(s.matter,in.forbid)) {
        s.count++; for (int k=0;k<NW;k++) s.matter.w[k]&=~in.target.w[k]; }
}

int main(){
    auto insts=load("cases.txt");
    int fail=0, ok=0;
    for (size_t ci=0; ci<insts.size(); ci++) {
        const Inst& in = insts[ci];
        if (in.prog.empty()) { printf("case %zu has no program\n", ci); fail++; continue; }
        St s{}; setInit(s, in);
        int lastAcc=-1, prev=0;
        for (size_t t=0;t<in.prog.size();t++) {
            apply(in, s, in.prog[t].data());
            if (s.count>prev) { lastAcc=(int)t+1; prev=s.count; }
        }
        bool good = (s.count==in.K) && (lastAcc==(int)in.prog.size());
        if (good) ok++; else { fail++; printf("FAIL case %zu %s#%d: count=%d/%d lastAccept=%d/%zu\n",
                                             ci, in.ds.c_str(), in.idx, s.count, in.K, lastAcc, in.prog.size()); }
    }
    printf("selftest: %d ok, %d failed, %zu cases\n", ok, fail, insts.size());
    return fail?1:0;
}
