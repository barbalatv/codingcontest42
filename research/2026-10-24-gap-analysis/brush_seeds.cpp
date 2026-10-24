// Build a library of "clean brush" poses per case: poses whose double-hit cells
// are all inside the target and touch no skirting cell.
// usage: ./brush_seeds <samples> <topN> [caseFrom caseTo]
#include <bits/stdc++.h>
using namespace std;
typedef unsigned long long u64; typedef unsigned char u8;
static const int NW=6;
struct Mask{ u64 w[NW]; };
static inline int pc(const Mask&a){int s=0;for(int i=0;i<NW;i++)s+=__builtin_popcountll(a.w[i]);return s;}
struct Inst{ int r,K,nrel,L,curL; int init[6]; Mask target,forbid; vector<array<Mask,6>> rays; };
static vector<Inst> load(const string& path){ ifstream f(path); string line; vector<Inst> out;
    while(getline(f,line)){ if(line.empty())continue; istringstream ss(line); string tag; ss>>tag;
        if(tag=="case"){ Inst in; string ds; int idx; ss>>ds>>idx>>in.r>>in.K>>in.nrel>>in.L; in.L=6*in.r; in.rays.assign(in.L,{}); in.curL=0; out.push_back(in);}
        else if(tag=="cur"){int v; ss>>v; out.back().curL=v;}
        else if(tag=="init"){for(int i=0;i<6;i++) ss>>out.back().init[i];}
        else if(tag=="target"){for(int i=0;i<NW;i++) ss>>out.back().target.w[i];}
        else if(tag=="forbid"){for(int i=0;i<NW;i++) ss>>out.back().forbid.w[i];}
        else if(tag=="ray"){int p,d; ss>>p>>d; for(int i=0;i<NW;i++) ss>>out.back().rays[p][d].w[i];}
    } return out; }
struct Rng{ u64 s; Rng(u64 x):s(x?x:88172645463325252ull){} inline u64 n(){s^=s<<13;s^=s>>7;s^=s<<17;return s;} inline int i(int m){return (int)(n()%(u64)m);} };
int main(int argc,char**argv){
    auto insts=load("cases.txt");
    int samples=argc>1?atoi(argv[1]):200000;
    int topN=argc>2?atoi(argv[2]):5;
    int from=argc>3?atoi(argv[3]):0, to=argc>4?atoi(argv[4]):(int)insts.size();
    for(int k=from;k<min(to,(int)insts.size());k++){
        const Inst& in=insts[k];
        Rng rng(0x5DEECE66Dull*(k+7));
        vector<pair<int,array<int,6>>> best;   // (covered, pose)
        set<array<int,6>> seen;
        int maskLim = 64;
        for(int s=0;s<samples;s++){
            array<int,6> pose;
            Mask one{},two{},three{};
            int act = (s%4==0) ? (1+rng.i(63)) : 63;   // mix full beam and partial masks
            for(int i=0;i<6;i++){
                pose[i]=rng.i(in.L);
                if(!((act>>i)&1)) continue;
                const Mask& ray=in.rays[pose[i]][i];
                for(int q=0;q<NW;q++){ three.w[q]|=two.w[q]&ray.w[q]; two.w[q]|=one.w[q]&ray.w[q]; one.w[q]|=ray.w[q]; }
            }
            Mask h2; for(int q=0;q<NW;q++) h2.w[q]=two.w[q]&~three.w[q];
            int f=0; for(int q=0;q<NW;q++) f+=__builtin_popcountll(h2.w[q]&in.forbid.w[q]);
            if(f) continue;
            int t=0; for(int q=0;q<NW;q++) t+=__builtin_popcountll(h2.w[q]&in.target.w[q]);
            int other=pc(h2)-t;
            if(other) continue;                       // every double-hit cell must be useful
            if(t<3) continue;
            if(seen.count(pose)) continue;
            seen.insert(pose);
            best.push_back({t,pose});
        }
        sort(best.begin(),best.end(),[](auto&a,auto&b){return a.first>b.first;});
        printf("case %d nT=%d brush=%d need=%d\n", k, pc(in.target), best.empty()?0:best[0].first,
               best.empty()?0:(pc(in.target)+best[0].first-1)/best[0].first);
        for(int j=0;j<(int)min((size_t)topN,best.size());j++)
            printf("   cover=%3d pose %d %d %d %d %d %d\n", best[j].first,
                   best[j].second[0],best[j].second[1],best[j].second[2],
                   best[j].second[3],best[j].second[4],best[j].second[5]);
        fflush(stdout);
    }
}
