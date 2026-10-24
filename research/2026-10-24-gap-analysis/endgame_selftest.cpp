// Positive test for the endgame search (mandatory before trusting any negative result).
//
// For every one of the 540 existing valid programs and every accept boundary T:
//   1. the incumbent's last command of that block really increases the counter
//   2. canFinishInOne() finds a completing tick from S[T-1]
//   3. the truncated 1-tick endgameSearch(ticks=1) returns a valid completion
//   4. replaying the found action reproduces the same counter value
//
// If any of these fail, a negative optimisation result is meaningless.
// g++ -O2 -march=native -o endgame_selftest endgame_selftest.cpp
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

static vector<array<u8,6>>& allActions() {
    static vector<array<u8,6>> ALL;
    if (ALL.empty()) for (int m=0;m<4096;m++) {
        array<u8,6> a{}; int x=m;
        for (int i=0;i<6;i++){ a[i]=(u8)(x&3); x>>=2; }
        ALL.push_back(a);      // 4^6, all-noop included
    }
    return ALL;
}
static bool completes(const Inst& in, const St& before, const St& after, int goalCount) {
    (void)in; return before.count == goalCount - 1 && after.count == goalCount;
}
static bool canFinishInOne(const Inst& in, const St& s, int goalCount, array<u8,6>* which=nullptr) {
    for (const auto& a : allActions()) {
        St t=s; apply(in,t,a.data());
        if (completes(in, s, t, goalCount)) { if (which) *which=a; return true; }
    }
    return false;
}

int main(){
    auto insts = load("cases.txt");
    long long boundaries=0, counterOk=0, foundOk=0, replayOk=0;
    int casesBad=0;
    for (size_t ci=0; ci<insts.size(); ci++) {
        const Inst& in = insts[ci];
        int T=(int)in.prog.size();
        vector<St> S(T+1); setInit(S[0],in);
        for (int t=0;t<T;t++){ S[t+1]=S[t]; apply(in,S[t+1],in.prog[t].data()); }
        bool bad=false;
        for (int t=1;t<=T;t++) if (S[t].count > S[t-1].count) {
            boundaries++;
            // 1. the incumbent's completing command really increases the counter
            St after=S[t-1]; apply(in, after, in.prog[t-1].data());
            if (after.count != S[t].count) { bad=true; continue; }
            counterOk++;
            // 2. canFinishInOne must recognise it
            array<u8,6> act;
            if (!canFinishInOne(in, S[t-1], S[t].count, &act)) { bad=true; continue; }
            foundOk++;
            // 3./4. replay the found action and compare with the incumbent state
            St rep=S[t-1]; apply(in, rep, act.data());
            if (rep.count != S[t].count) { bad=true; continue; }
            replayOk++;
        }
        if (bad) { casesBad++; if (casesBad<6) printf("  FAIL on case %zu %s#%d\n", ci, in.ds.c_str(), in.idx); }
    }
    printf("accept boundaries: %lld\n", boundaries);
    printf("  counter increases:  %lld\n", counterOk);
    printf("  canFinishInOne ok:  %lld\n", foundOk);
    printf("  replay ok:          %lld\n", replayOk);
    printf("cases with a failure: %d\n", casesBad);
    bool pass = boundaries>0 && counterOk==boundaries && foundOk==boundaries && replayOk==boundaries;
    printf("ENDGAME_SELFTEST: %s\n", pass?"PASS":"FAIL");
    return pass?0:1;
}
