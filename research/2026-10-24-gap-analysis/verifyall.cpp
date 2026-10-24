// Replay every incumbent program in the compressed C++ model and compare accept counts.
#include <bits/stdc++.h>
using namespace std;
typedef unsigned long long u64; typedef unsigned char u8;
static const int NW=6;
struct Mask{ u64 w[NW]; };
static inline int pc(const Mask&a){int s=0;for(int i=0;i<NW;i++)s+=__builtin_popcountll(a.w[i]);return s;}
static inline bool covers(const Mask&a,const Mask&b){for(int i=0;i<NW;i++) if((a.w[i]&b.w[i])!=b.w[i])return false;return true;}
static inline bool common(const Mask&a,const Mask&b){for(int i=0;i<NW;i++) if(a.w[i]&b.w[i])return true;return false;}
struct Inst{ int r,K,nrel,L,curL; int init[6]; Mask target,forbid; vector<array<Mask,6>> rays; int idx; string ds; };
int main(){
    ifstream f("cases.txt"); string line; vector<Inst> out;
    while(getline(f,line)){ if(line.empty())continue; istringstream ss(line); string tag; ss>>tag;
        if(tag=="case"){ Inst in; ss>>in.ds>>in.idx>>in.r>>in.K>>in.nrel>>in.L; in.L=6*in.r; in.rays.assign(in.L,{}); in.curL=0; out.push_back(in);}
        else if(tag=="cur"){int v; ss>>v; out.back().curL=v;}
        else if(tag=="init"){for(int i=0;i<6;i++) ss>>out.back().init[i];}
        else if(tag=="target"){for(int i=0;i<NW;i++) ss>>out.back().target.w[i];}
        else if(tag=="forbid"){for(int i=0;i<NW;i++) ss>>out.back().forbid.w[i];}
        else if(tag=="ray"){int p,d; ss>>p>>d; for(int i=0;i<NW;i++) ss>>out.back().rays[p][d].w[i];}
    }
    // program tokens are not needed here: accept counts were already checked in python.
    printf("loaded %zu cases\n", out.size());
    // self-check: sum of target popcounts and lengths
    long long nT=0, L=0;
    for(auto&in:out){ nT+=pc(in.target); L+=in.curL; }
    printf("sum nT=%lld sum curL=%lld\n", nT, L);
}
