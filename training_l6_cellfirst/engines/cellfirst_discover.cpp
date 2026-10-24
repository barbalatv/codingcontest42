// Universal cell-first scheduler, C++20. Geometry masks are supplied by the
// audited repository geometry; acceptance and all temporal transitions live here.
#include <algorithm>
#include <array>
#include <bit>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <functional>
#include <numeric>
#include <random>
#include <unordered_map>
#include <unordered_set>
#include <vector>
using namespace std;
using U=uint64_t;using Clock=chrono::steady_clock;
constexpr int MW=8;
struct Bits {array<U,MW>b{};bool operator==(const Bits&)const=default;};
int R,L,W,NT,K,H,WIDTH,MODE,SEED;Bits target,skirt;
array<array<Bits,256>,6> ray;
array<array<array<Bits,2>,256>,6> nearRay;
array<array<array<int,4>,256>,6> nextByte;
vector<array<int,6>> origin;
vector<int> targetCells,skirtCells;
Clock::time_point deadline;mt19937 rng;long long evaluations,configurations,bridges;
U mix(U x){x^=x>>30;x*=0xbf58476d1ce4e5b9ULL;x^=x>>27;x*=0x94d049bb133111ebULL;return x^(x>>31);}
int pc(U x){return popcount(x);}
bool isset(const Bits&a,int c){return (a.b[c/64]>>(c%64))&1;}
struct Effect{Bits one,two,three;};
struct State{U pose=0;Bits m;int made=0;};
struct Node{State s;int parent=-1,score=0;vector<int>seq;};
struct History{int parent;vector<int>seq;};
vector<History> history;
vector<int> bestProgram;vector<pair<U,vector<int>>> found;
vector<int> nearProgram;int nearCost;
vector<U> referencePoses;U goalPose;State startState;
unordered_set<U>cycleTried;
Effect effect(U pose){Effect v;for(int e=0;e<6;e++){auto&r=ray[e][(pose>>(8*e))&255];for(int w=0;w<W;w++){v.three.b[w]|=v.two.b[w]&r.b[w];v.two.b[w]|=v.one.b[w]&r.b[w];v.one.b[w]|=r.b[w];}}return v;}
bool applyEffect(State&s,const Effect&v){bool ok=true;for(int w=0;w<W;w++){s.m.b[w]=(s.m.b[w]|v.two.b[w])&~v.three.b[w];ok&=(s.m.b[w]&target.b[w])==target.b[w]&&!(s.m.b[w]&skirt.b[w]);}if(ok){s.m=Bits();s.made++;}return ok;}
State step(State s,int action){U q=0;for(int e=0;e<6;e++)q|=U(nextByte[e][(s.pose>>(8*e))&255][(action>>(2*e))&3])<<(8*e);s.pose=q;applyEffect(s,effect(q));evaluations++;return s;}
int distance(U a,U b){int d=0;for(int e=0;e<6;e++){int p=(a>>(8*e))&127,q=(b>>(8*e))&127,v=abs(p-q);d=max(d,min(v,L-v)+int(((a^b)>>(8*e+7))&1));}return d;}
int byteDistance(int a,int b){int d=abs((a&127)-(b&127));return min(d,L-d)+int((a&128)!=(b&128));}
U fingerprint(const State&s){U h=mix(s.pose)^mix(s.made+391);for(int w=0;w<W;w++)h^=mix(s.m.b[w]+w*31337ULL);return h;}
vector<int> recover(int parent,const vector<int>&seq){vector<vector<int>>chunks={seq};for(int p=parent;p>=0;p=history[p].parent)chunks.push_back(history[p].seq);vector<int>out;for(auto it=chunks.rbegin();it!=chunks.rend();it++)out.insert(out.end(),it->begin(),it->end());return out;}
void captureNear(const State&s,int parent,const vector<int>&seq){if(s.made>=K)return;int cost=max(0,K-s.made-1)*(NT*3+16);for(int w=0;w<W;w++)cost+=pc(target.b[w]&~s.m.b[w])*3+pc(skirt.b[w]&s.m.b[w])*4;if(cost<nearCost){nearCost=cost;nearProgram=recover(parent,seq);}}
bool save(const vector<int>&p){State s=startState;for(int t=0;t<(int)p.size();t++){s=step(s,p[t]);if(s.made>=K){if(s.made!=K||(goalPose!=UINT64_MAX&&s.pose!=goalPose))return false;vector<int>q(p.begin(),p.begin()+t+1);if(bestProgram.empty()||q.size()<bestProgram.size())bestProgram=q;if(found.size()<32)found.push_back({s.pose,q});return true;}}return false;}
void cycleCompletion(const vector<int>&p){if(K<2||goalPose!=UINT64_MAX)return;State s=startState;unordered_map<U,pair<int,int>>at;at[s.pose]={0,0};for(int t=0;t<(int)p.size();t++){int old=s.made;s=step(s,p[t]);if(s.made==old)continue;auto it=at.find(s.pose);if(it!=at.end()){int a=it->second.second;vector<int>cycle(p.begin()+a,p.begin()+t+1),answer(p.begin(),p.begin()+t+1);if(cycle.empty())return;while(s.made<K&&answer.size()<size_t(H)){for(int action:cycle){s=step(s,action);answer.push_back(action);if(s.made==K){if(answer.size()<=size_t(H))save(answer);return;}if(answer.size()>=size_t(H))return;}}return;}at[s.pose]={s.made,t+1};}}
int stateScore(const State&s,int variant){int good=0,bad=0,potential=0;auto v=effect(s.pose);for(int w=0;w<W;w++){good+=pc(s.m.b[w]&target.b[w]);bad+=pc(s.m.b[w]&skirt.b[w]);potential+=pc(v.one.b[w]&target.b[w]&~s.m.b[w]);}
 int score=s.made*(NT*200+200)+good*200-bad*(variant%3==0?140:variant%3==1?250:380)+potential*9;
 // Distance-to-cell is a lookahead heuristic, never a claimed lower bound.
 vector<int>missing;for(int c:targetCells)if(!isset(s.m,c))missing.push_back(c);
 int penalty=0;for(int j=0;j<min(8,(int)missing.size());j++){int c=missing[(j*missing.size())/min(8,(int)missing.size())];int a=999,b=999;for(int e=0;e<6;e++){int d=byteDistance((s.pose>>(8*e))&255,origin[c][e]+128);if(d<a){b=a;a=d;}else b=min(b,d);}penalty+=b;}
 score-=penalty*4;if(goalPose!=UINT64_MAX)score-=distance(s.pose,goalPose)*28;return score;}
void keep(vector<Node>&pool,Node n,int cap){auto cmp=[](const Node&a,const Node&b){return a.score>b.score;};if((int)pool.size()<cap){pool.push_back(move(n));push_heap(pool.begin(),pool.end(),cmp);}else if(n.score>pool.front().score){pop_heap(pool.begin(),pool.end(),cmp);pool.back()=move(n);push_heap(pool.begin(),pool.end(),cmp);}}
void prune(vector<Node>&pool){sort(pool.begin(),pool.end(),[](const Node&a,const Node&b){return a.score>b.score;});unordered_set<U>seen,boards;array<int,7>activities{};vector<Node>out;for(int pass=0;pass<3&&(int)out.size()<WIDTH;pass++)for(auto&n:pool){if((int)out.size()>=WIDTH)break;U h=fingerprint(n.s);if(seen.count(h))continue;U bh=mix(n.s.made+391);for(int w=0;w<W;w++)bh^=mix(n.s.m.b[w]+w*31337ULL);int active=0;for(int e=0;e<6;e++)active+=((n.s.pose>>(8*e+7))&1);if(pass==0&&(boards.count(bh)||activities[active]>=max(2,WIDTH/5)))continue;if(pass==1&&activities[active]>=max(4,WIDTH/3))continue;seen.insert(h);boards.insert(bh);activities[active]++;history.push_back({n.parent,n.seq});n.parent=int(history.size())-1;n.seq.clear();out.push_back(move(n));}pool=move(out);}
int snapshotScore(const State&s,U pose){auto v=effect(pose);int score=0;for(int w=0;w<W;w++){U h2=v.two.b[w]&~v.three.b[w],m=s.m.b[w];score+=pc(h2&target.b[w]&~m)*100+pc(v.three.b[w]&skirt.b[w]&m)*110-pc(v.three.b[w]&target.b[w]&m)*85-pc(h2&skirt.b[w]&~m)*70-pc(v.three.b[w]&target.b[w])*8;}return score;}
// Master: assign an unmet cell to any of its fifteen possible emitter pairs.
// Remaining emitters are joint clippers or useful rays, with reachability built in.
vector<U> configurationsFrom(const State&s,int D,bool chordOnly){vector<pair<int,U>>pool;unordered_set<U>seen;vector<int>cells;
 for(int c:targetCells)if(!isset(s.m,c))cells.push_back(c);
 if(cells.empty())cells=targetCells;
 shuffle(cells.begin(),cells.end(),rng);if(cells.size()>10)cells.resize(10);
 for(int c:skirtCells)if(isset(s.m,c)&&cells.size()<14)cells.push_back(c);
 int attempts=0;
 for(int c:cells){array<int,15>pairs; iota(pairs.begin(),pairs.end(),0);shuffle(pairs.begin(),pairs.end(),rng);int ix=0;
 vector<pair<int,int>>ee;for(int a=0;a<6;a++)for(int b=a+1;b<6;b++)ee.push_back({a,b});
 for(int z:pairs){auto[a,b]=ee[z];if(chordOnly&&b!=a+3)continue;
  int aa=origin[c][a]+128,bb=origin[c][b]+128;
  if(byteDistance((s.pose>>(8*a))&255,aa)>D||byteDistance((s.pose>>(8*b))&255,bb)>D)continue;
  U pose=(s.pose&~((255ULL<<(8*a))|(255ULL<<(8*b))))|(U(aa)<<(8*a))|(U(bb)<<(8*b));
  // Coordinate subproblem on physically reachable ray choices. Non-pair rays
  // can mask dirty cells or build another group; inactive rays keep their pose.
  for(int pass=0;pass<2;pass++)for(int j=0;j<6;j++){int e=(j+SEED+pass)%6;if(e==a||e==b)continue;int before=(s.pose>>(8*e))&255;vector<int>options={before,before^128};
   for(int delta=-D;delta<=D;delta++){int p=((before&127)+delta+L)%L;options.push_back(p+(before&128));if(abs(delta)+1<=D)options.push_back(p+((before&128)^128));}
   int best=snapshotScore(s,pose);U chosen=pose;
   for(int q:options){if(byteDistance(before,q)>D)continue;U next=(pose&~(255ULL<<(8*e)))|(U(q)<<(8*e));int value=snapshotScore(s,next);configurations++;if(value>best||(value==best&&(rng()%9==0))){best=value;chosen=next;}}pose=chosen;
  }
  if(seen.insert(pose).second)pool.push_back({snapshotScore(s,pose),pose});
  if(++attempts>=36)break;
 }if(attempts>=36)break;}
 sort(pool.rbegin(),pool.rend());vector<U>out;for(int i=0;i<min(12,(int)pool.size());i++)out.push_back(pool[i].second);
 for(U q:referencePoses)if(distance(s.pose,q)<=D&&out.size()<16)out.push_back(q);
 return out;}
vector<int> schedule(U start,U finish,int D,int timing){vector<int>out(D);for(int e=0;e<6;e++){int a=(start>>(8*e))&255,b=(finish>>(8*e))&255;int d=((b&127)-(a&127)+L+L/2)%L-L/2;vector<int>ops(abs(d),d>0?2:1);if((a&128)!=(b&128)){if((timing+e)%2==0)ops.insert(ops.begin(),3);else ops.push_back(3);}if((int)ops.size()>D)return {};int slack=D-int(ops.size()),off=timing==0?0:timing==1?slack:int(rng()%(slack+1));for(int j=0;j<(int)ops.size();j++)out[j+off]|=ops[j]<<(2*e);}return out;}
void submit(const Node&parent,const vector<int>&seq,int t,vector<vector<Node>>&layers,int cap){if(seq.empty())return;State s=parent.s;vector<int>prefix;for(int a:seq){s=step(s,a);prefix.push_back(a);if(s.made>=K){if(s.made==K&&(goalPose==UINT64_MAX||s.pose==goalPose))save(recover(parent.parent,prefix));return;}}captureNear(s,parent.parent,seq);Node n;n.s=s;n.parent=parent.parent;n.seq=seq;n.score=stateScore(s,SEED);keep(layers[t+seq.size()],move(n),cap);}
struct Triple {U pose=0;Effect v;array<Bits,2>nearOne,nearTwo;int action=0;};
array<Triple,64> triples(U pose,int first){array<Triple,64>out{};for(int code=0;code<64;code++){auto&z=out[code];for(int j=0;j<3;j++){int e=first+j,op=(code>>(2*j))&3,b=nextByte[e][(pose>>(8*e))&255][op];z.pose|=U(b)<<(8*e);z.action|=op<<(2*e);auto&r=ray[e][b];for(int w=0;w<W;w++){z.v.three.b[w]|=z.v.two.b[w]&r.b[w];z.v.two.b[w]|=z.v.one.b[w]&r.b[w];z.v.one.b[w]|=r.b[w];for(int h=0;h<2;h++){U nr=nearRay[e][b][h].b[w];z.nearTwo[h].b[w]|=z.nearOne[h].b[w]&nr;z.nearOne[h].b[w]|=nr;}}}}return out;}
void commandExpand(const Node&parent,int t,vector<vector<Node>>&layers,int cap,bool exhaustive){auto aa=triples(parent.s.pose,0),bb=triples(parent.s.pose,3);for(auto&a:aa)for(auto&b:bb){if(!exhaustive&&((rng()&7)!=0))continue;if((++evaluations&4095)==0&&Clock::now()>=deadline)return;Effect v;for(int w=0;w<W;w++){v.one.b[w]=a.v.one.b[w]|b.v.one.b[w];v.two.b[w]=a.v.two.b[w]|b.v.two.b[w]|(a.v.one.b[w]&b.v.one.b[w]);v.three.b[w]=a.v.three.b[w]|b.v.three.b[w]|(a.v.two.b[w]&b.v.one.b[w])|(a.v.one.b[w]&b.v.two.b[w]);}State s=parent.s;s.pose=a.pose|b.pose;bool accepted=applyEffect(s,v);vector<int>seq={a.action|b.action};if(s.made>=K){if(accepted&&s.made==K&&(goalPose==UINT64_MAX||s.pose==goalPose))save(recover(parent.parent,seq));continue;}
 if(accepted&&s.made>=2&&cycleTried.insert(mix(s.pose)^mix(s.made)).second)cycleCompletion(recover(parent.parent,seq));
 captureNear(s,parent.parent,seq);Node n;n.s=s;n.parent=parent.parent;n.seq=seq;n.score=s.made*(NT*200+200);for(int w=0;w<W;w++){U m=s.m.b[w];n.score+=pc(m&target.b[w])*200-pc(m&skirt.b[w])*(SEED%3==0?140:SEED%3==1?250:380)+pc(v.one.b[w]&target.b[w]&~m)*6;for(int h=0;h<2;h++){U near=a.nearTwo[h].b[w]|b.nearTwo[h].b[w]|(a.nearOne[h].b[w]&b.nearOne[h].b[w]);n.score+=pc(near&target.b[w]&~m)*(h==0?25:8);}}if(goalPose!=UINT64_MAX)n.score-=distance(s.pose,goalPose)*28;keep(layers[t+1],move(n),cap);}}
void forward(){history.clear();vector<vector<Node>>layers(H+1);Node root;root.s=startState;layers[0].push_back(root);int cap=WIDTH*5;
 for(int t=0;t<H&&Clock::now()<deadline;t++){auto&beam=layers[t];if(beam.empty())continue;prune(beam);for(auto&n:beam){if(Clock::now()>=deadline)return;if(goalPose!=UINT64_MAX&&distance(n.s.pose,goalPose)>H-t)continue;
  if(MODE==0)commandExpand(n,t,layers,cap,true);
  else{
   // A sparse command safety net preserves neutral and temporarily worse moves.
   commandExpand(n,t,layers,cap,false);
   int maxD=(MODE==1?2:4);
   for(int D=1;D<=min(maxD,H-t);D++){
    auto configs=configurationsFrom(n.s,D,MODE==2);
    for(U q:configs)for(int timing=0;timing<(D==1?1:3);timing++){if(Clock::now()>=deadline)return;submit(n,schedule(n.s.pose,q,D,timing),t,layers,cap);}
   }
   // Long-range master configurations guide bounded 2-4 tick prefixes. This
   // lets a large pattern plan toward cells outside the immediate macro radius.
   if(MODE==1||MODE==3){int D=min(R+2,H-t);if(D>maxD)for(U q:configurationsFrom(n.s,D,false))for(int timing=0;timing<2;timing++){auto seq=schedule(n.s.pose,q,D,timing);for(int h=2;h<=min(4,D);h++){if(Clock::now()>=deadline)return;submit(n,vector<int>(seq.begin(),seq.begin()+h),t,layers,cap);}}}
  }
 }}
}
struct Back{U pose=0;Bits ones,zeros;vector<int>tail;int score=0;};
vector<Back> regressFrontier(int maxDepth,int width){vector<Back>beam;vector<U>ends=referencePoses;auto extra=configurationsFrom(startState,min(6,H),false);ends.insert(ends.end(),extra.begin(),extra.end());for(U p:ends){Back b;b.pose=p;b.ones=target;b.zeros=skirt;beam.push_back(b);}vector<Back>checkpoints;
 for(int depth=0;depth<maxDepth&&Clock::now()<deadline;depth++){vector<Back>pool;for(auto&n:beam){auto v=effect(n.pose);bool valid=true;Bits ones,zeros;for(int w=0;w<W;w++){if((v.three.b[w]&n.ones.b[w])|((v.two.b[w]&~v.three.b[w])&n.zeros.b[w]))valid=false;ones.b[w]=n.ones.b[w]&~v.two.b[w];zeros.b[w]=n.zeros.b[w]&~v.three.b[w];}if(!valid)continue; // Invalid endpoint only rejects this root.
 auto aa=triples(n.pose,0),bb=triples(n.pose,3);for(auto&a:aa)for(auto&b:bb){if((++evaluations&4095)==0&&Clock::now()>=deadline)return checkpoints;Back z;z.pose=a.pose|b.pose;int dist=distance(startState.pose,z.pose);if(dist+depth+1>H)continue;z.ones=ones;z.zeros=zeros;int backward=a.action|b.action,forward=0;for(int e=0;e<6;e++){int op=(backward>>(2*e))&3;forward|=(op==1?2:op==2?1:op)<<(2*e);}z.tail={forward};z.tail.insert(z.tail.end(),n.tail.begin(),n.tail.end());int rem=0,zz=0;for(int w=0;w<W;w++){rem+=pc(ones.b[w]);zz+=pc(zeros.b[w]);}z.score=-rem*100-zz*12-dist*35;pool.push_back(move(z));if(pool.size()>size_t(width*12)){nth_element(pool.begin(),pool.begin()+width*4,pool.end(),[](auto&a,auto&b){return a.score>b.score;});pool.resize(width*4);}}}
 sort(pool.begin(),pool.end(),[](auto&a,auto&b){return a.score>b.score;});unordered_set<U>seen;beam.clear();for(auto&n:pool){U h=mix(n.pose);for(int w=0;w<W;w++)h^=mix(n.ones.b[w]+w)^mix(n.zeros.b[w]+w+713);if(!seen.insert(h).second)continue;beam.push_back(n);if(beam.size()>=size_t(width))break;}for(int i=0;i<min(12,(int)beam.size());i++)checkpoints.push_back(beam[i]);}
 return checkpoints;}
void bidirectional(){auto overall=deadline;auto now=Clock::now();deadline=now+(overall-now)/3;auto backs=regressFrontier(min(H-1,5),max(8,WIDTH/2));deadline=overall;if(backs.empty())return;history.clear();vector<vector<Node>>layers(H+1);Node root;root.s=startState;layers[0].push_back(root);
 for(int t=0;t<H&&Clock::now()<deadline;t++){auto&beam=layers[t];if(beam.empty())continue;prune(beam);for(auto&n:beam){for(auto&b:backs){int D=distance(n.s.pose,b.pose);if(t+D+int(b.tail.size())>H||D>4)continue;for(int slack=0;slack<=min(1,H-t-D-int(b.tail.size()));slack++)for(int timing=0;timing<3;timing++){auto seq=schedule(n.s.pose,b.pose,D+slack,timing);State st=n.s;for(int a:seq)st=step(st,a);bridges++;bool ok=st.made==0;for(int w=0;w<W;w++)ok&=!(b.ones.b[w]&~st.m.b[w])&&!(b.zeros.b[w]&st.m.b[w]);if(ok){seq.insert(seq.end(),b.tail.begin(),b.tail.end());save(recover(n.parent,seq));}}}
 if(t+1<H)commandExpand(n,t,layers,WIDTH*4,MODE==4);
 if(MODE>=5)for(int D=2;D<=min(4,H-t);D++)for(U q:configurationsFrom(n.s,D,MODE==6))submit(n,schedule(n.s.pose,q,D,rng()%3),t,layers,WIDTH*4);
 if(Clock::now()>=deadline)return;}}
}
struct Evaluation{int cost=0,finish=0;vector<State>states;};
Evaluation evaluate(const vector<int>&p){Evaluation v;State s=startState;v.states.push_back(s);for(int t=0;t<(int)p.size();t++){s=step(s,p[t]);v.states.push_back(s);if(s.made==K&&!v.finish)v.finish=t+1;}if(v.finish&&(goalPose==UINT64_MAX||v.states[v.finish].pose==goalPose)){v.cost=0;return v;}int missing=0,dirty=0;for(int w=0;w<W;w++){missing+=pc(target.b[w]&~s.m.b[w]);dirty+=pc(skirt.b[w]&s.m.b[w]);}v.cost=max(0,K-s.made-1)*(NT*3+16)+missing*3+dirty*4;if(s.made>=K)v.cost=10+abs(s.made-K)*(NT*3+16);if(goalPose!=UINT64_MAX)v.cost+=distance(v.finish?v.states[v.finish].pose:s.pose,goalPose)*5;v.cost=max(1,v.cost);return v;}
void emitterPath(vector<int>&p,int e,int lo,int hi,int a,int b){for(int t=lo;t<hi;t++){array<int,4>opts;int n=0;for(int op=0;op<4;op++)if(byteDistance(nextByte[e][a][op],b)<=hi-t-1)opts[n++]=op;if(!n)return;int op=opts[rng()%n],old=(p[t]>>(2*e))&3;if((rng()%3)&&find(opts.begin(),opts.begin()+n,old)!=opts.begin()+n)op=old;p[t]=(p[t]&~(3<<(2*e)))|(op<<(2*e));a=nextByte[e][a][op];}}
bool cellMutation(vector<int>&p,const Evaluation&v){auto&end=v.states.back();vector<pair<int,bool>>defects;for(int c:targetCells)if(!isset(end.m,c))defects.push_back({c,false});for(int c:skirtCells)if(isset(end.m,c))defects.push_back({c,true});if(defects.empty())return false;auto[cell,erase]=defects[rng()%defects.size()];int tick=1+rng()%H;int radius=2+rng()%min(H,8),lo=max(0,tick-radius),hi=min(H,tick+radius);vector<pair<int,int>>choices;for(int e=0;e<6;e++){int q=origin[cell][e]+128,a=(v.states[lo].pose>>(8*e))&255,b=(v.states[hi].pose>>(8*e))&255;if(byteDistance(a,q)<=tick-lo&&(hi==H&&goalPose==UINT64_MAX||byteDistance(q,b)<=hi-tick))choices.push_back({e,q});}shuffle(choices.begin(),choices.end(),rng);if(choices.size()<size_t(erase?3:2))return false;for(int i=0;i<(erase?3:2);i++){auto[e,q]=choices[i];int a=(v.states[lo].pose>>(8*e))&255,b=(v.states[hi].pose>>(8*e))&255;emitterPath(p,e,lo,tick,a,q);if(hi==H&&goalPose==UINT64_MAX){int now=q;for(int t=tick;t<hi;t++){int op=(p[t]>>(2*e))&3;now=nextByte[e][now][op];}}else emitterPath(p,e,tick,hi,q,b);}configurations++;return true;}
// Cell-assignment LNS / CEGIS: defect cells are master assignments; emitter
// paths solve the temporal subproblem, exact simulation feeds conflicts back.
void assignmentSearch(const vector<int>&hint,bool useCells){if(hint.empty()||H<1)return;int restarts=0;while(Clock::now()<deadline){vector<int>p=hint;int cut=rng()%p.size();while(p.size()>size_t(H))p.erase(p.begin()+min(cut,int(p.size())-1));while(p.size()<size_t(H))p.push_back(0);auto ev=evaluate(p);for(int it=0;it<14000&&Clock::now()<deadline;it++){
 if(ev.cost==0){save(p);return;}auto trial=p;bool changed=false;
 if(useCells&&rng()%3==0)changed=cellMutation(trial,ev);
 if(!changed){int e=rng()%6,a=rng()%H,b=(rng()%4==0)?rng()%H:min(H-1,max(0,a+int(rng()%9)-4));int x=(trial[a]>>(2*e))&3,y=(trial[b]>>(2*e))&3;if(rng()%4==0||a==b)trial[a]=(trial[a]&~(3<<(2*e)))|((rng()%4)<<(2*e));else{trial[a]=(trial[a]&~(3<<(2*e)))|(y<<(2*e));trial[b]=(trial[b]&~(3<<(2*e)))|(x<<(2*e));}}
 auto next=evaluate(trial);double temperature=.06+1.5*(1.-double(it%3500)/3500.);if(next.cost<=ev.cost||double(rng())/4294967296.<exp(double(ev.cost-next.cost)/temperature)){p=move(trial);ev=move(next);}if(ev.cost<nearCost){nearCost=ev.cost;nearProgram=p;}
 }restarts++;}}
struct Configuration{U pose=0;int active=0;Effect v;int coverage=0;};
vector<Configuration> chordLibrary(){vector<Configuration>out;unordered_set<U>seen;for(int axis=0;axis<3;axis++)for(int p=0;p<L;p++){
 auto&line=ray[axis][p+128];int q=((3-2*axis)*R-p+2*L)%L;int good=0;vector<int>dirty;for(int w=0;w<W;w++){good+=pc(line.b[w]&target.b[w]);U bits=line.b[w]&skirt.b[w];while(bits){int c=countr_zero(bits);dirty.push_back(w*64+c);bits&=bits-1;}}
 if(!good||dirty.size()>4)continue;
 U base=(U(p+128)<<(8*axis))|(U(q+128)<<(8*(axis+3)));int mask=(1<<axis)|(1<<(axis+3));
 function<void(int,U,int)>dfs=[&](int i,U pose,int active){if(i==(int)dirty.size()){
 auto v=effect(pose);int bad=0,covered=0;for(int w=0;w<W;w++){bad+=pc((v.two.b[w]&~v.three.b[w])&skirt.b[w])+pc(v.three.b[w]&target.b[w]);covered+=pc(v.two.b[w]&~v.three.b[w]&target.b[w]);}
 configurations++;if(bad<=3&&covered&&seen.insert(pose).second)out.push_back({pose,active,v,covered});return;}
  for(int e=0;e<6;e++)if(!(active>>e&1)){int pos=origin[dirty[i]][e];if(pos<0)continue;dfs(i+1,pose|(U(pos+128)<<(8*e)),active|(1<<e));}
 };dfs(0,base,mask);
 }
 // Every target cell can also choose any of the twelve non-collinear pairs.
 // These small safe groups complete cells unavailable to a chord-only master.
 for(int cell:targetCells)for(int a=0;a<6;a++)for(int b=a+1;b<6;b++)if(b!=a+3){U pose=(U(origin[cell][a]+128)<<(8*a))|(U(origin[cell][b]+128)<<(8*b));if(!seen.insert(pose).second)continue;auto v=effect(pose);int covered=0;for(int w=0;w<W;w++)covered+=pc(v.two.b[w]&~v.three.b[w]&target.b[w]);out.push_back({pose,(1<<a)|(1<<b),v,covered});configurations++;}
 return out;}
void libraryScheduling(){auto library=chordLibrary();if(library.empty())return;history.clear();vector<vector<Node>>layers(H+1);Node root;root.s=startState;layers[0].push_back(root);int cap=WIDTH*5;
 for(int t=0;t<H&&Clock::now()<deadline;t++){auto&beam=layers[t];if(beam.empty())continue;prune(beam);for(auto&n:beam){vector<pair<double,int>>rank;rank.reserve(library.size());for(int i=0;i<(int)library.size();i++){auto&c=library[i];U pose=c.pose;for(int e=0;e<6;e++)if(!(c.active>>e&1))pose|=((n.s.pose>>(8*e))&127)<<(8*e);int D=max(1,distance(n.s.pose,pose));if(t+D>H)continue;int gain=0,clear=0;for(int w=0;w<W;w++){gain+=pc(c.v.two.b[w]&~c.v.three.b[w]&target.b[w]&~n.s.m.b[w]);clear+=pc(c.v.three.b[w]&skirt.b[w]&n.s.m.b[w]);}double value=(gain*100.+clear*120.)/(D+1.)+c.coverage*0.2+(rng()%100)*0.001;rank.push_back({value,i});}sort(rank.rbegin(),rank.rend());if(rank.size()>18)rank.resize(18);
 for(auto[value,i]:rank){auto&c=library[i];U pose=c.pose;for(int e=0;e<6;e++)if(!(c.active>>e&1))pose|=((n.s.pose>>(8*e))&127)<<(8*e);int D=max(1,distance(n.s.pose,pose));for(int timing=0;timing<3;timing++){if(Clock::now()>=deadline)return;auto seq=schedule(n.s.pose,pose,D,timing);State s=n.s;vector<int>prefix;for(int a:seq){int old=s.made;s=step(s,a);prefix.push_back(a);if(s.made>=K){save(recover(n.parent,prefix));break;}if(s.made>old&&s.made>=2)cycleCompletion(recover(n.parent,prefix));}if(s.made>=K)continue;captureNear(s,n.parent,seq);Node next;next.s=s;next.parent=n.parent;next.seq=seq;next.score=stateScore(s,SEED);keep(layers[t+D],move(next),cap);}
 }
 // A hold lets a safe full-pattern configuration produce subsequent copies.
 if(t+1<=H)submit(n,{0},t,layers,cap);
 }}}
int main(){ios::sync_with_stdio(false);cin.tie(nullptr);int ms;while(cin>>R>>W>>NT>>K>>H>>WIDTH>>ms>>SEED>>MODE>>startState.pose>>goalPose){
 L=6*R;if(W<1||W>MW||L>128)return 2;target=Bits();skirt=Bits();for(int w=0;w<W;w++)cin>>target.b[w];for(int w=0;w<W;w++)cin>>skirt.b[w];for(int e=0;e<6;e++)for(int p=0;p<L;p++){ray[e][p]=Bits();ray[e][p+128]=Bits();for(int w=0;w<W;w++)cin>>ray[e][p+128].b[w];for(int a=0;a<2;a++){int b=p+128*a;nextByte[e][b]={b,(p+L-1)%L+128*a,(p+1)%L+128*a,p+128*(1-a)};}}
 startState.m=Bits();startState.made=0;for(int w=0;w<W;w++)cin>>startState.m.b[w];int n;cin>>n;vector<int>hint(n);for(int&a:hint)cin>>a;cin>>n;referencePoses.resize(n);for(U&p:referencePoses)cin>>p;
 rng.seed(SEED);evaluations=configurations=bridges=0;bestProgram.clear();found.clear();nearProgram.clear();nearCost=1000000000;cycleTried.clear();auto begin=Clock::now();deadline=begin+chrono::milliseconds(ms);
 origin.assign(W*64,{});targetCells.clear();skirtCells.clear();for(int c=0;c<W*64;c++){if(isset(target,c))targetCells.push_back(c);if(isset(skirt,c))skirtCells.push_back(c);if(!isset(target,c)&&!isset(skirt,c))continue;for(int e=0;e<6;e++){origin[c][e]=-1;for(int p=0;p<L;p++)if(isset(ray[e][p+128],c)){origin[c][e]=p;break;}if(origin[c][e]<0)return 3;}}
 if(MODE==9){State s=startState;cout<<hint.size();for(int a:hint){s=step(s,a);cout<<' '<<s.pose<<' '<<s.made;for(int w=0;w<W;w++)cout<<' '<<s.m.b[w];}cout<<'\n'<<flush;continue;}
 for(int e=0;e<6;e++)for(int a=0;a<2;a++)for(int p=0;p<L;p++){int byte=p+a*128;for(int h=0;h<2;h++){nearRay[e][byte][h]=Bits();for(int q=0;q<L;q++)if(byteDistance(byte,q+128)<=(h==0?1:3))for(int w=0;w<W;w++)nearRay[e][byte][h].b[w]|=ray[e][q+128].b[w];}}
 if(MODE==10)libraryScheduling();else if(MODE==7||MODE==8)assignmentSearch(hint,MODE==7);else if(MODE>=4)bidirectional();else forward();
 auto elapsed=chrono::duration_cast<chrono::milliseconds>(Clock::now()-begin).count();cout<<bestProgram.size()<<' '<<evaluations<<' '<<configurations<<' '<<elapsed<<' '<<bridges;for(int a:bestProgram)cout<<' '<<a;cout<<' '<<found.size();for(auto&[q,p]:found){cout<<' '<<q<<' '<<p.size();for(int a:p)cout<<' '<<a;}cout<<' '<<nearCost<<' '<<nearProgram.size();for(int a:nearProgram)cout<<' '<<a;cout<<'\n'<<flush;
 }}
