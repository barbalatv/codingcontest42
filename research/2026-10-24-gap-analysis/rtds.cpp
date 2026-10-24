// Residual-Target Directed Search (RTDS): shorten an EXISTING valid program by
// replacing a window with a shorter one synthesised from the cells still missing.
//
// For every accept interval and every window [a,b) inside it:
//   start = exact incumbent state before tick a
//   goal  = same number of accepts as at tick b and the same matter,
//           final pose FREE, no accept earlier than the last tick
//   search= beam over single ticks, expanded from the residual (positions that
//           cover still-missing cells) plus plain move/toggle actions
// A replacement is accepted only if it is strictly shorter AND the spliced program
// still passes the exact model with exactly K accepts on the last tick.
//
// g++ -O2 -march=native -o rtds rtds.cpp
#include <bits/stdc++.h>
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

struct Covers {
    vector<vector<vector<int>>> pos;   // [track][cell] -> positions covering it
    vector<int> weight;                // rarity weight (optional)
    bool weightsOn = false;
    void build(const Inst& in, int nrel) {
        pos.assign(6, vector<vector<int>>(nrel));
        for (int i=0;i<6;i++) for (int c=0;c<nrel;c++) {
            int w=c/64, b=c%64;
            for (int p=0;p<in.L;p++) if ((in.rays[p][i].w[w]>>b)&1) pos[i][c].push_back(p);
        }
        weight.assign(nrel, 10);
        weightsOn = getenv("WEIGHT") && atoi(getenv("WEIGHT")) != 0;
        for (int c=0;c<nrel;c++) {
            int tracks=0;
            for (int i=0;i<6;i++) if (!pos[i][c].empty()) tracks++;
            weight[c] = weightsOn ? (10 * 6 / max(1, tracks)) : 10;
        }
    }
};

struct Node { St st; int par; u8 act[6]; int key; };

static inline void stepTok(int from,int to,int L,u8& tok,int& cost){
    int d=(to-from)%L; if(d<0)d+=L;
    if(d==0){ tok=0; cost=0; }
    else if(d<=L/2){ tok=2; cost=d; }
    else { tok=1; cost=L-d; }
}

static void scoreNode(const Inst& in, const Covers& cv, Node& n) {
    int key = 0, skirt = 0;
    for (int k=0;k<NW;k++) {
        u64 miss = in.target.w[k] & ~n.st.matter.w[k];
        while (miss) { int b=__builtin_ctzll(miss); int c=k*64+b;
                       key += (c < (int)cv.weight.size()) ? cv.weight[c] : 10; miss&=miss-1; }
        skirt += __builtin_popcountll(in.forbid.w[k] & n.st.matter.w[k]);
    }
    n.key = key + skirt*40;
}

// returns the replacement sequence (strictly shorter than maxDepth+1) or empty
static vector<array<u8,6>> beamWindow(const Inst& in, const Covers& cv, const St& start,
                                      int goalCount, const Mask& goalMatter, bool finalAccept,
                                      int maxDepth, int width) {
    vector<vector<Node>> layers;
    vector<Node> cur, nxt;
    Node root; root.st=start; root.par=-1; memset(root.act,0,6); scoreNode(in,cv,root);
    layers.push_back({root}); cur.push_back(root);
    for (int d=1; d<=maxDepth; d++) {
        nxt.clear();
        for (size_t ni=0; ni<cur.size(); ni++) {
            const St& s = cur[ni].st;
            vector<array<u8,6>> cand;
            // (a) plain actions + all-toggle
            for (int i=0;i<6;i++) {
                array<u8,6> a{0,0,0,0,0,0};
                a[i]=1; cand.push_back(a);
                a[i]=2; cand.push_back(a);
                a[i]=3; cand.push_back(a);
            }
            cand.push_back({3,3,3,3,3,3});
            // (b) directed: cover one still-missing cell with the cheapest emitter pair
            vector<int> miss;
            for (int k=0;k<NW;k++) { u64 m = in.target.w[k] & ~s.matter.w[k];
                while (m) { int b=__builtin_ctzll(m); miss.push_back(k*64+b); m&=m-1; } }
            int budget = 12;
            for (int c : miss) {
                if (budget-- <= 0) break;
                for (int i=0;i<6;i++) for (int j=i+1;j<6;j++) {
                    const auto& pi = cv.pos[i][c]; const auto& pj = cv.pos[j][c];
                    if (pi.empty()||pj.empty()) continue;
                    int bc=INT_MAX, bx=pi[0], by=pj[0];
                    for (int x : pi) for (int y : pj) {
                        u8 t1,t2; int c1,c2;
                        stepTok(s.pos[i],x,in.L,t1,c1); stepTok(s.pos[j],y,in.L,t2,c2);
                        int cc=max(c1,c2); if (cc<bc){bc=cc;bx=x;by=y;} }
                    array<u8,6> a{0,0,0,0,0,0};
                    u8 t1,t2; int c1,c2;
                    stepTok(s.pos[i],bx,in.L,t1,c1); stepTok(s.pos[j],by,in.L,t2,c2);
                    a[i] = t1 ? t1 : 3;
                    a[j] = t2 ? t2 : 3;
                    cand.push_back(a);
                }
            }
            // (c) dense brush: greedily assign three disjoint emitter pairs to
            // different missing cells and move ALL six emitters toward that pose
            {
                bool used[6] = {false,false,false,false,false,false};
                int target[6]; for (int i=0;i<6;i++) target[i]=-1;
                for (int round=0; round<3; round++) {
                    int bestPair=-1, bi=-1, bj=-1, bestScore=-1;
                    for (int i=0;i<6;i++) if (!used[i]) for (int j=i+1;j<6;j++) if (!used[j]) {
                        // cheapest positions that add coverage of the residual
                        int bc=INT_MAX, bx=-1, by=-1;
                        for (int c : miss) {
                            const auto& pi = cv.pos[i][c]; const auto& pj = cv.pos[j][c];
                            if (pi.empty()||pj.empty()) continue;
                            for (int x : pi) for (int y : pj) {
                                u8 t1,t2; int c1,c2;
                                stepTok(s.pos[i],x,in.L,t1,c1); stepTok(s.pos[j],y,in.L,t2,c2);
                                int cc=max(c1,c2);
                                if (cc<bc) { bc=cc; bx=x; by=y; }
                            }
                        }
                        if (bx<0) continue;
                        int score = 20 - bc;
                        if (score>bestScore) { bestScore=score; bestPair=round*100; bi=i; bj=j;
                                               target[i]=bx; target[j]=by; }
                    }
                    (void)bestPair;
                    if (bi<0) break;
                    used[bi]=used[bj]=true;
                }
                if (target[0]>=0 || target[1]>=0 || target[2]>=0 || target[3]>=0 || target[4]>=0 || target[5]>=0) {
                    array<u8,6> a{0,0,0,0,0,0};
                    bool ok=false;
                    for (int i=0;i<6;i++) {
                        if (target[i]>=0) {
                            u8 t; int c; stepTok(s.pos[i],target[i],in.L,t,c);
                            a[i] = t ? t : 3;      // step if needed, else toggle on
                            if (a[i]) ok=true;
                        } else if (!((s.active>>i)&1)) { a[i]=3; ok=true; }
                    }
                    if (ok) cand.push_back(a);
                }
            }
            for (const auto& a : cand) {
                bool any=false; for(int q=0;q<6;q++) if(a[q]) any=true;
                if(!any) continue;
                Node ch; ch.st = s; apply(in, ch.st, a.data()); ch.par=(int)ni;
                memcpy(ch.act,a.data(),6);
                if (ch.st.count > goalCount) continue;
                if (finalAccept && ch.st.count == goalCount && common(ch.st.matter,in.forbid)) continue;
                scoreNode(in,cv,ch);
                nxt.push_back(ch);
            }
        }
        if (nxt.empty()) { if (getenv("DEBUG")) fprintf(stderr,"   depth %d: beam died\n", d); return {}; }
        if (getenv("DEBUG")) {
            int best=1<<30;
            for (auto& n : nxt) { int m=0; for(int k=0;k<NW;k++) m+=__builtin_popcountll(in.target.w[k]&~n.st.matter.w[k]); best=min(best,m); }
            fprintf(stderr,"   depth %d: states=%zu minMissing=%d\n", d, nxt.size(), best);
        }
        // exact goal test (full state: count + matter)
        int hit=-1;
        for (size_t i=0;i<nxt.size();i++) {
            if (nxt[i].st.count != goalCount) continue;
            bool ok = finalAccept ? !common(nxt[i].st.matter, in.forbid)
                                  : sameMask(nxt[i].st.matter, goalMatter);
            if (ok) { hit=(int)i; break; }
        }
        if (hit>=0) {
            // reconstruct through the layers
            vector<array<u8,6>> seq(d);
            int idx = hit;
            for (int t=d; t>=1; t--) {
                const Node& n = (t==d) ? nxt[idx] : layers[t][idx];
                memcpy(seq[t-1].data(), n.act, 6);
                idx = n.par;
            }
            return seq;
        }
        // dedupe on the FULL state (matter + pose + active + count)
        sort(nxt.begin(), nxt.end(), [](const Node&a,const Node&b){
            for (int i=0;i<6;i++) if (a.st.pos[i]!=b.st.pos[i]) return a.st.pos[i]<b.st.pos[i];
            if (a.st.active!=b.st.active) return a.st.active<b.st.active;
            if (a.st.count!=b.st.count) return a.st.count<b.st.count;
            for (int k=0;k<NW;k++) if (a.st.matter.w[k]!=b.st.matter.w[k]) return a.st.matter.w[k]<b.st.matter.w[k];
            return a.key<b.key; });
        nxt.erase(unique(nxt.begin(), nxt.end(), [](const Node&a,const Node&b){
            for (int i=0;i<6;i++) if (a.st.pos[i]!=b.st.pos[i]) return false;
            if (a.st.active!=b.st.active) return false;
            if (a.st.count!=b.st.count) return false;
            for (int k=0;k<NW;k++) if (a.st.matter.w[k]!=b.st.matter.w[k]) return false;
            return true; }), nxt.end());
        if ((int)nxt.size()>width) {
            nth_element(nxt.begin(), nxt.begin()+width, nxt.end(),
                        [](const Node&a,const Node&b){ return a.key<b.key; });
            nxt.resize(width);
        }
        layers.push_back(nxt);
        cur = nxt;
    }
    return {};
}

// full validation with the exact model
static bool validate(const Inst& in, const vector<array<u8,6>>& prog) {
    St s{}; setInit(s, in);
    int prev=0, lastAcc=-1;
    for (size_t t=0;t<prog.size();t++) {
        apply(in, s, prog[t].data());
        if (s.count>prev) { prev=s.count; lastAcc=(int)t+1; }
    }
    return s.count==in.K && lastAcc==(int)prog.size();
}

int main(int argc, char** argv) {
    auto insts = load("cases.txt");
    int width = getenv("W")?atoi(getenv("W")):400;
    int maxW  = getenv("MAXW")?atoi(getenv("MAXW")):8;
    vector<int> want; for (int a=1;a<argc;a++) want.push_back(atoi(argv[a]));
    fprintf(stderr,"loaded %zu cases, width=%d maxWindow=%d\n", insts.size(), width, maxW);
    for (int ci : want) {
        const Inst& in = insts[ci];
        Covers cv; cv.build(in, in.nrel);
        vector<array<u8,6>> best = in.prog;
        if (!validate(in, best)) { printf("case %d BAD_INPUT\n", ci); continue; }
        int startLen = (int)best.size();
        auto t0 = chrono::steady_clock::now();
        // states of the current best program
        int improved = 0;
        bool progress = true;
        int rounds = 0;
        while (progress && rounds < 6) {
            progress = false; rounds++;
            vector<St> S(best.size()+1); S[0]; setInit(S[0], in);
            for (size_t t=0;t<best.size();t++) { S[t+1]=S[t]; apply(in, S[t+1], best[t].data()); }
            int T=(int)best.size();
            // accept boundaries: matter is always empty there, so the goal of a
            // replacement block is simply "reach the next accept" with a free pose
            vector<int> bounds{0};
            for (int t=1;t<=T;t++) if (S[t].count > S[t-1].count) bounds.push_back(t);
            for (size_t bi=0; bi+1<bounds.size() && !progress; bi++) {
                int a=bounds[bi], b=bounds[bi+1];
                int len=b-a;
                if (len < 2) continue;
                auto repl = beamWindow(in, cv, S[a], S[b].count, S[b].matter, true, len-1, width);
                if (repl.empty()) continue;
                vector<array<u8,6>> cand;
                cand.insert(cand.end(), best.begin(), best.begin()+a);
                cand.insert(cand.end(), repl.begin(), repl.end());
                cand.insert(cand.end(), best.begin()+b, best.end());
                if ((int)cand.size() < (int)best.size() && validate(in, cand)) {
                    printf("  case %d: copy block [%d,%d) %d -> %d ticks (total %zu -> %zu)\n",
                           ci, a, b, len, (int)repl.size(), best.size(), cand.size());
                    best = cand; improved++; progress = true; break;
                }
            }
        }
        double ms=chrono::duration<double,milli>(chrono::steady_clock::now()-t0).count();
        printf("case %d %s#%d nT=%d K=%d curL=%d rtds=%zu improvements=%d %s ms=%.0f\n",
               ci, in.ds.c_str(), in.idx, pc(in.target), in.K, startLen, best.size(), improved,
               ((int)best.size()<startLen?"SHORTER":"same"), ms);
        fflush(stdout);
        if ((int)best.size()<startLen && getenv("DUMP")) {
            char fn[64]; snprintf(fn,sizeof fn,"rtds_%d.txt",ci);
            FILE* f=fopen(fn,"w");
            for (auto& a : best) { for(int q=0;q<6;q++) fprintf(f,"%c ","-FBT"[a[q]]); fprintf(f,"\n"); }
            fclose(f);
        }
    }
    return 0;
}
