// Max number of target cells a single pose can create (sampled), per case.
#include <bits/stdc++.h>
using namespace std;
typedef unsigned long long u64;
typedef unsigned char u8;
static const int NW = 6;
struct Mask { u64 w[NW]; };
static inline int pc(const Mask&a){ int s=0; for(int i=0;i<NW;i++) s+=__builtin_popcountll(a.w[i]); return s; }
struct Inst { int r,K,nrel,L,curL; int init[6]; Mask target,forbid; vector<array<Mask,6>> rays; };
static vector<Inst> load(const string& path){
    ifstream f(path); string line; vector<Inst> out;
    while(getline(f,line)){ if(line.empty())continue; istringstream ss(line); string tag; ss>>tag;
        if(tag=="case"){ Inst in; string ds; int idx; ss>>ds>>idx>>in.r>>in.K>>in.nrel>>in.L; in.L=6*in.r; in.rays.assign(in.L,{}); in.curL=0; out.push_back(in);}
        else if(tag=="cur"){int v; ss>>v; out.back().curL=v;}
        else if(tag=="init"){for(int i=0;i<6;i++) ss>>out.back().init[i];}
        else if(tag=="target"){for(int i=0;i<NW;i++) ss>>out.back().target.w[i];}
        else if(tag=="forbid"){for(int i=0;i<NW;i++) ss>>out.back().forbid.w[i];}
        else if(tag=="ray"){int p,d; ss>>p>>d; for(int i=0;i<NW;i++) ss>>out.back().rays[p][d].w[i];}
    }
    return out;
}
struct Rng{ u64 s; Rng(u64 x):s(x?x:88172645463325252ull){} inline u64 n(){s^=s<<13;s^=s>>7;s^=s<<17;return s;} inline int i(int m){return (int)(n()%(u64)m);} };

int main(int argc,char**argv){
    auto insts=load("cases.txt");
    int samples=argc>1?atoi(argv[1]):200000;
    fprintf(stderr,"loaded %zu samples %d\n", insts.size(), samples);
    for(size_t k=0;k<insts.size();k++){
        const Inst& in=insts[k];
        Rng rng(0x1234567ull*(k+1));
        int best=0, bestClean=0;
        for(int s=0;s<samples;s++){
            Mask one{},two{},three{};
            for(int i=0;i<6;i++){
                const Mask& ray=in.rays[rng.i(in.L)][i];
                for(int q=0;q<NW;q++){ three.w[q]|=two.w[q]&ray.w[q]; two.w[q]|=one.w[q]&ray.w[q]; one.w[q]|=ray.w[q]; }
            }
            Mask h2; for(int q=0;q<NW;q++) h2.w[q]=two.w[q]&~three.w[q];
            int t=0; for(int q=0;q<NW;q++) t+=__builtin_popcountll(h2.w[q]&in.target.w[q]);
            if(t>best) best=t;
            int f=0; for(int q=0;q<NW;q++) f+=__builtin_popcountll(h2.w[q]&in.forbid.w[q]);
            if(!f && t>bestClean) bestClean=t;
        }
        printf("case %zu nT=%d curL=%d brush=%d clean=%d bound=%d\n", k, pc(in.target), in.curL, best, bestClean,
               (pc(in.target)+max(bestClean,1)-1)/max(bestClean,1));
        fflush(stdout);
    }
}
