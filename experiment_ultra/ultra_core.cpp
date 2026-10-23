#include <iostream>
#include <vector>
#include <array>
#include <unordered_set>
#include <unordered_map>
#include <algorithm>
#include <chrono>
#include <cstdint>
#include <intrin.h>
using namespace std;
using Clock=chrono::steady_clock;
constexpr int MW=8;
struct Bits{array<uint64_t,MW> b{};};
struct State{uint64_t pose=0;Bits matter;};
struct Entry{State s;int score=0,parent=-1,action=0;uint64_t hash=0;};
struct History{int parent,action;};
struct Combo{Bits one,two,three;array<Bits,4> nearOne,nearTwo;uint64_t pose=0;int action=0;};
int R,L,W,NT,WIDTH;Bits target,forbid,hardTarget,randomTarget;vector<array<Bits,6>> rays;
uint64_t evaluations;Clock::time_point deadline;
Bits nearMask[6][256][4];bool forceGoal=false;uint64_t wantedGoal=0;
bool capturePartial=false;int partialMerit=0;vector<int> partialProgram;State partialEnd;
inline uint64_t mix(uint64_t x){x^=x>>30;x*=0xbf58476d1ce4e5b9ULL;x^=x>>27;x*=0x94d049bb133111ebULL;return x^(x>>31);}
inline uint64_t fingerprint(const State&s){uint64_t h=mix(s.pose);for(int w=0;w<W;w++)h^=mix(s.matter.b[w]+uint64_t(w)*0x9e3779b97f4a7c15ULL);return h;}
inline int pc(uint64_t x){return (int)__popcnt64(x);}
#ifdef PHASE2_DUAL
bool dualSolve(const vector<string>&,const vector<pair<int,int>>&,const vector<vector<int>>&,int,int,int,int,int,vector<int>&);
#endif
#ifdef PHASE2_REGRESS
bool regressSolve(uint64_t,int,int,vector<int>&);
extern uint64_t regressResultPose;
extern Bits regressOnes,regressZeros;
extern bool regressWindow;
extern uint64_t windowStartPose;
extern Bits windowStartMatter;
#endif
void combos(const State&s,int start,array<Combo,64>&out){
  int p[3][4],a[3][4];
  for(int j=0;j<3;j++){
    int v=(s.pose>>(8*(start+j)))&255,old=v&127,active=(v>>7)&1;
    p[j][0]=old;p[j][1]=(old+L-1)%L;p[j][2]=(old+1)%L;p[j][3]=old;
    for(int k=0;k<4;k++)a[j][k]=active^(k==3);
  }
  for(int code=0;code<64;code++){
    Combo c;int z=code;
    for(int j=0;j<3;j++){
      int k=z&3;z>>=2;int i=start+j;
      c.pose|=uint64_t(p[j][k]+a[j][k]*128)<<(8*i);
      c.action|=k<<(2*i);
      for(int h=0;h<4;h++)for(int w=0;w<W;w++){auto mask=nearMask[i][p[j][k]+a[j][k]*128][h].b[w];c.nearTwo[h].b[w]|=c.nearOne[h].b[w]&mask;c.nearOne[h].b[w]|=mask;}
      if(a[j][k])for(int w=0;w<W;w++){
        uint64_t ray=rays[p[j][k]][i].b[w];
        c.three.b[w]|=c.two.b[w]&ray;c.two.b[w]|=c.one.b[w]&ray;c.one.b[w]|=ray;
      }
    }
    out[code]=c;
  }
}
bool search(const State&start,int maxDepth,int variant,vector<int>&result,State&finish){
  partialProgram.clear();partialMerit=0;
  vector<Entry> beam(1);beam[0].s=start;beam[0].parent=-1;
  vector<History> history;unordered_set<uint64_t> visited;visited.reserve(WIDTH*maxDepth*2);
  visited.insert(fingerprint(start));
  const int KEEP=WIDTH*6;
  for(int depth=0;depth<maxDepth;depth++){
    if(Clock::now()>=deadline)return false;
    vector<Entry> pool;pool.reserve(KEEP+1);
    auto worse=[](const Entry&a,const Entry&b){return a.score>b.score;};
    for(const Entry&parent:beam){
      array<Combo,64> aa,bb;combos(parent.s,0,aa);combos(parent.s,3,bb);
      for(const Combo&a:aa)for(const Combo&b:bb){
        evaluations++;
        State next;next.pose=a.pose|b.pose;
        int good=0,bad=0,potential=0,erasePotential=0,overload=0,hard=0,randomGood=0;
        for(int w=0;w<W;w++){
          uint64_t one=a.one.b[w]|b.one.b[w];
          uint64_t two=a.two.b[w]|b.two.b[w]|(a.one.b[w]&b.one.b[w]);
          uint64_t three=a.three.b[w]|b.three.b[w]|(a.two.b[w]&b.one.b[w])|(a.one.b[w]&b.two.b[w]);
          uint64_t matter=(parent.s.matter.b[w]|two)&~three;
          next.matter.b[w]=matter;
          good+=pc(matter&target.b[w]);bad+=pc(matter&forbid.b[w]);
          hard+=pc(matter&hardTarget.b[w]);randomGood+=pc(matter&randomTarget.b[w]);
          potential+=pc(one&target.b[w]&~matter);
          erasePotential+=pc(two&matter&forbid.b[w]);
          overload+=pc(three&target.b[w]);
        }
        if(good==NT&&bad==0){
          if(forceGoal&&next.pose!=wantedGoal)continue;
          vector<int> reverse={a.action|b.action};
          for(int i=parent.parent;i>=0;i=history[i].parent)reverse.push_back(history[i].action);
          result.assign(reverse.rbegin(),reverse.rend());finish=next;finish.matter=Bits();return true;
        }
        if(capturePartial){
          int merit=good*120-bad*180-(depth+1)*100;
          if(merit>partialMerit){
            partialMerit=merit;partialEnd=next;
            vector<int> reverse={a.action|b.action};
            for(int i=parent.parent;i>=0;i=history[i].parent)reverse.push_back(history[i].action);
            partialProgram.assign(reverse.rbegin(),reverse.rend());
          }
        }
        int badWeight=variant%3==0?140:variant%3==1?220:320;
        int score=good*256-bad*badWeight+potential*5+erasePotential*4-overload*2;
        for(int h=0;h<4;h++)for(int w=0;w<W;w++){
          auto near2=a.nearTwo[h].b[w]|b.nearTwo[h].b[w]|(a.nearOne[h].b[w]&b.nearOne[h].b[w]);
          score+=pc(near2&target.b[w]&~next.matter.b[w])*(h==0?30:h==1?18:h==2?10:5);
        }
        if(variant==3)score+=hard*96;
        if(variant>=4)score+=randomGood*192;
        if((int)pool.size()>=KEEP&&score<=pool[0].score)continue;
        uint64_t hash=fingerprint(next);if(visited.count(hash))continue;
        Entry child;child.s=next;child.score=score;child.parent=parent.parent;child.action=a.action|b.action;child.hash=hash;
        if((int)pool.size()<KEEP){pool.push_back(child);push_heap(pool.begin(),pool.end(),worse);}
        else{pop_heap(pool.begin(),pool.end(),worse);pool.back()=child;push_heap(pool.begin(),pool.end(),worse);}
      }
    }
    if(pool.empty())return false;
    sort(pool.begin(),pool.end(),[](const Entry&a,const Entry&b){return a.score>b.score;});
    unordered_set<uint64_t> unique;beam.clear();
    // Diverse scores avoid a beam made solely of slight pose variations of one board.
    unordered_set<uint64_t> boards;
    for(int pass=0;pass<2&&(int)beam.size()<WIDTH;pass++)for(Entry&e:pool){
      if((int)beam.size()>=WIDTH)break;
      if(unique.count(e.hash))continue;
      uint64_t board=0;for(int w=0;w<W;w++)board^=mix(e.s.matter.b[w]+w);
      if(pass==0&&boards.count(board))continue;
      boards.insert(board);unique.insert(e.hash);visited.insert(e.hash);
      history.push_back({e.parent,e.action});e.parent=(int)history.size()-1;beam.push_back(e);
    }
  }
  return false;
}

int main(){
  ios::sync_with_stdio(false);cin.tie(nullptr);
  int required,incumbent,budget,maxdepth,variant;
  while(cin>>R>>required>>incumbent>>WIDTH>>budget>>maxdepth>>variant){
    vector<string> rows(2*R+1);for(string&s:rows)cin>>s;
    auto begin=Clock::now();deadline=begin+chrono::milliseconds(budget);evaluations=0;L=6*R;
    vector<pair<int,int>> cells;vector<vector<int>> index(2*R+1,vector<int>(4*R+1,-1));
    for(int y=1;y<2*R;y++)for(int x=0;x<=4*R;x++)if(rows[y][x]=='O'||rows[y][x]=='M'){
      index[y][x]=(int)cells.size();cells.push_back({y,x});
    }
    W=((int)cells.size()+63)/64;target=Bits();forbid=Bits();hardTarget=Bits();randomTarget=Bits();NT=0;
    int dy[6]={0,1,1,0,-1,-1},dx[6]={2,1,-1,-2,-1,1};
    for(int k=0;k<(int)cells.size();k++){
      auto[y,x]=cells[k];if(rows[y][x]=='M'){target.b[k/64]|=1ULL<<(k%64);NT++;}
      else for(int i=0;i<6;i++){
        int yy=y+dy[i],xx=x+dx[i];
        if(yy>=0&&yy<=2*R&&xx>=0&&xx<=4*R&&rows[yy][xx]=='M')forbid.b[k/64]|=1ULL<<(k%64);
      }
    }
    for(int k=0;k<(int)cells.size();k++)if((target.b[k/64]>>(k%64))&1){
      auto[y,x]=cells[k];
      for(int i=0;i<6;i++){
        int yy=y+dy[i],xx=x+dx[i];
        if(yy>=0&&yy<=2*R&&xx>=0&&xx<=4*R){int j=index[yy][xx];
          if(j>=0&&((forbid.b[j/64]>>(j%64))&1))hardTarget.b[k/64]|=1ULL<<(k%64);
        }
      }
      if(mix(k+uint64_t(variant)*31337)&1)randomTarget.b[k/64]|=1ULL<<(k%64);
    }
    rays.assign(L,{});pair<int,int> corners[6]={{R,0},{2*R,R},{2*R,3*R},{R,4*R},{0,3*R},{0,R}};
    for(int side=0;side<6;side++)for(int j=0;j<R;j++){
      auto[y,x]=corners[side];auto[yy,xx]=corners[(side+1)%6];y+=j*(yy-y)/R;x+=j*(xx-x)/R;
      int p=side*R+j;
      for(int i=0;i<6;i++){
        int ny=y+dy[i],nx=x+dx[i];
        while(ny>=0&&ny<=2*R&&nx>=0&&nx<=4*R){
          int k=index[ny][nx];if(k>=0)rays[p][i].b[k/64]|=(1ULL<<(k%64))&(target.b[k/64]|forbid.b[k/64]);
          ny+=dy[i];nx+=dx[i];
        }
      }
    }
    for(int i=0;i<6;i++)for(int v=0;v<256;v++)for(int h=0;h<4;h++)nearMask[i][v][h]=Bits();
    for(int i=0;i<6;i++)for(int p=0;p<L;p++)for(int active=0;active<2;active++)for(int q=0;q<L;q++){
      int dist=min((p-q+L)%L,(q-p+L)%L)+(active?0:1);
      for(int h=0;h<4;h++)if(dist<=h+1)for(int w=0;w<W;w++)nearMask[i][p+128*active][h].b[w]|=rays[q][i].b[w];
    }
    State state;int initial[6]={0,5*R,4*R,3*R,2*R,R};for(int i=0;i<6;i++)state.pose|=uint64_t(initial[i])<<(8*i);
    if(variant>=100){
      cin>>state.pose>>wantedGoal;forceGoal=wantedGoal!=UINT64_MAX;
      vector<int> fragment;State end;bool okay=search(state,maxdepth,variant-100,fragment,end);
      auto ms=chrono::duration_cast<chrono::milliseconds>(Clock::now()-begin).count();
      cout<<(okay?fragment.size():0)<<' '<<evaluations<<' '<<ms<<' '<<(okay?end.pose:0);
      if(okay)for(int a:fragment)cout<<' '<<a;cout<<'\n'<<flush;continue;
    }
#ifdef PHASE2_REGRESS
    uint64_t endPose;cin>>endPose;vector<int> regressProgram;
    regressWindow=variant>=60;
    if(regressWindow){
      cin>>windowStartPose;for(int w=0;w<W;w++)cin>>windowStartMatter.b[w];
      Bits goal;for(int w=0;w<W;w++)cin>>goal.b[w];
      NT=0;for(int w=0;w<W;w++){uint64_t relevant=target.b[w]|forbid.b[w];target.b[w]=goal.b[w]&relevant;forbid.b[w]=relevant&~target.b[w];NT+=pc(target.b[w]);}
    }
    bool regressSuccess=regressSolve(endPose,maxdepth,variant,regressProgram);
    auto regressMillis=chrono::duration_cast<chrono::milliseconds>(Clock::now()-begin).count();
    cout<<(regressSuccess?regressProgram.size():0)<<' '<<evaluations<<' '<<regressMillis<<' '<<(regressSuccess&&variant>=30?regressResultPose:uint64_t(regressSuccess));
    if(regressSuccess&&variant>=40&&variant<60){for(int w=0;w<W;w++)cout<<' '<<regressOnes.b[w];for(int w=0;w<W;w++)cout<<' '<<regressZeros.b[w];}
    if(regressSuccess)for(int action:regressProgram)cout<<' '<<action;cout<<'\n'<<flush;continue;
#endif
#ifdef PHASE2_DUAL
    vector<int> dualProgram;
    bool dualSuccess=dualSolve(rows,cells,index,required,incumbent,budget,maxdepth,variant,dualProgram);
    auto dualMillis=chrono::duration_cast<chrono::milliseconds>(Clock::now()-begin).count();
    cout<<(dualSuccess?dualProgram.size():0)<<' '<<evaluations<<' '<<dualMillis<<' '<<dualSuccess;
    if(dualSuccess)for(int action:dualProgram)cout<<' '<<action;cout<<'\n'<<flush;continue;
#endif
#ifdef PHASE2_PARTIAL
    cin>>state.pose;for(int w=0;w<W;w++)cin>>state.matter.b[w];
    capturePartial=true;vector<int> fragment;State fragmentEnd;
    bool complete=search(state,maxdepth,variant,fragment,fragmentEnd);
    if(!complete)fragment=partialProgram;
    auto millis=chrono::duration_cast<chrono::milliseconds>(Clock::now()-begin).count();
    cout<<fragment.size()<<' '<<evaluations<<' '<<millis<<' '<<complete;
    for(int action:fragment)cout<<' '<<action;cout<<'\n'<<flush;continue;
#endif
    vector<int> program;unordered_map<uint64_t,pair<int,int>> endpoints;
    endpoints[state.pose]={0,0};int made=0;bool success=true;
    while(made<required&&Clock::now()<deadline&&(int)program.size()<incumbent){
      vector<int> segment;State end;
      if(!search(state,min(maxdepth,incumbent-(int)program.size()-1),variant,segment,end)){success=false;break;}
      program.insert(program.end(),segment.begin(),segment.end());made++;state=end;
      auto it=endpoints.find(state.pose);
      if(it!=endpoints.end()){
        int cycleCopies=made-it->second.first,cycleStart=it->second.second;
        vector<int> cycle(program.begin()+cycleStart,program.end());
        while(made+cycleCopies<=required&&(int)program.size()+int(cycle.size())<incumbent){program.insert(program.end(),cycle.begin(),cycle.end());made+=cycleCopies;}
      }
      endpoints[state.pose]={made,(int)program.size()};
    }
    if(made!=required||(int)program.size()>=incumbent)success=false;
    long long elapsed=chrono::duration_cast<chrono::milliseconds>(Clock::now()-begin).count();
    cout<<(success?program.size():0)<<' '<<evaluations<<' '<<elapsed<<' '<<made;
    if(success)for(int action:program)cout<<' '<<action;
    cout<<'\n'<<flush;
  }
}
