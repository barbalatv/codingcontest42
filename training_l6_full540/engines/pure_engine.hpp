// Independent target-to-rays synthesis. No incumbent is consulted by births
// or mode 11. Mode 12 records the point at which historical structure enters.
vector<int> independentBirth;long long birthConflicts=0;int birthAttempts=0;bool recordingPure=false;
struct PureEdge{U pose;int copies;vector<int>program;};
vector<PureEdge>pureEdges;unordered_set<U>pureEdgeKeys;
void recordPartialDiscovery(const State&s,int parent,const vector<int>&seq){
 if(!recordingPure||s.made<1||pureEdges.size()>=16||Clock::now()>=deadline)return;
 for(int w=0;w<W;w++)if(s.m.b[w])return;
 U key=mix(s.pose)^mix(s.made);if(pureEdgeKeys.count(key))return;
 auto p=recover(parent,seq);State st=startState;int last=0;
 for(int t=0;t<(int)p.size();t++){int old=st.made;st=step(st,p[t]);if(st.made>old)last=t+1;}
 if(last!=(int)p.size())return;
 pureEdgeKeys.insert(key);pureEdges.push_back({s.pose,s.made,p});
}
int deltaRail(int a,int b){return (b-a+L+L/2)%L-L/2;}
vector<int> buildBirth(int a,int b,const vector<int>&order){
 State st=startState;vector<int>out;
 auto emit=[&](int action){st=step(st,action);out.push_back(action);return st.made>=K;};
 auto route=[&](int cell,bool first)->bool{
  int pa=(st.pose>>(8*a))&127,pb=(st.pose>>(8*b))&127;
  int da=deltaRail(pa,origin[cell][a]),db=deltaRail(pb,origin[cell][b]);
  int na=abs(da),nb=abs(db),D=max(na,nb);
  if(first){
   for(int t=0;t<D;t++){int action=0;if(t<na)action|=(da>0?2:1)<<(2*a);if(t<nb)action|=(db>0?2:1)<<(2*b);if(emit(action))return true;}
   return emit((3<<(2*a))|(3<<(2*b)));
  }
  if(!D)return emit(0);
  for(int timing=0;timing<4;timing++){
   vector<int>plan(D);for(int t=0;t<D;t++){
    int offA=(timing&1)?D-na:0,offB=(timing&2)?D-nb:0;
    if(t>=offA&&t<offA+na)plan[t]|=(da>0?2:1)<<(2*a);
    if(t>=offB&&t<offB+nb)plan[t]|=(db>0?2:1)<<(2*b);
   }
   State test=st;bool safe=true;
   for(int action:plan){test=step(test,action);for(int w=0;w<W;w++)if(test.m.b[w]&skirt.b[w])safe=false;if(!safe)break;}
   if(!safe){birthConflicts++;continue;}
   for(int action:plan)if(emit(action))return true;
   return false;
  }
  // Conflict feedback: a dirty active transit is replaced by an overlapping
  // single-beam transit. Positions are retained; no global pose reset is used.
  bool offA=max(na+2,nb)<=max(nb+2,na);int off=offA?a:b;
  D=offA?max(na+2,nb):max(nb+2,na);vector<int>plan(D);
  plan[0]|=3<<(2*off);plan[D-1]|=3<<(2*off);
  for(int t=0;t<na;t++)plan[t+(offA?1:0)]|=(da>0?2:1)<<(2*a);
  for(int t=0;t<nb;t++)plan[t+(offA?0:1)]|=(db>0?2:1)<<(2*b);
  for(int action:plan)if(emit(action))return true;
  return false;
 };
 if(route(order[0],true))return out;
 for(int sweep=0;sweep<K+2;sweep++){
  vector<int>routeCells=order;if(sweep&1)reverse(routeCells.begin(),routeCells.end());
  if(sweep&&emit(0))return out;
  for(int j=1;j<(int)routeCells.size();j++)if(route(routeCells[j],false))return out;
 }
 return {};
}
void generateBirths(){independentBirth.clear();birthConflicts=0;birthAttempts=0;
 auto stop=min(deadline,Clock::now()+chrono::milliseconds(110));
 vector<pair<int,int>>pairs;for(int a=0;a<6;a++)for(int b=a+1;b<6;b++)if(b!=a+3)pairs.push_back({a,b});shuffle(pairs.begin(),pairs.end(),rng);
 for(auto[a,b]:pairs)for(int variant=0;variant<4;variant++){
  vector<int>order=targetCells;int major=(variant&1)?b:a,minor=(variant&1)?a:b;
  int p0=(startState.pose>>(8*major))&127,q0=(startState.pose>>(8*minor))&127;
  sort(order.begin(),order.end(),[&](int x,int y){int X=deltaRail(p0,origin[x][major]),Y=deltaRail(p0,origin[y][major]);if(X!=Y)return (variant&2)?X>Y:X<Y;int u=deltaRail(q0,origin[x][minor]),v=deltaRail(q0,origin[y][minor]);return (X&1)?u>v:u<v;});
  auto p=buildBirth(a,b,order);birthAttempts++;
  if(!p.empty()&&(independentBirth.empty()||p.size()<independentBirth.size()))independentBirth=move(p);
  if(!independentBirth.empty()&&Clock::now()>=stop)return;
 }
}
void pureSynthesis(const vector<int>&incumbent,bool hybrid){
 if(!hybrid&&(!incumbent.empty()||!referencePoses.empty()||goalPose!=UINT64_MAX)){cerr<<"PURE_PROVENANCE_VIOLATION\n";return;}
 auto overall=deadline;auto begin=Clock::now();generateBirths();
 if(!independentBirth.empty()&&independentBirth.size()<=size_t(H))save(independentBirth);
 referencePoses.clear();int savedMode=MODE;recordingPure=true;
 // A new six-emitter configuration search is initialized solely from geometry.
 deadline=min(overall,begin+(overall-begin)*45/100);MODE=3;forward();MODE=savedMode;recordingPure=false;
 auto freshNear=nearProgram;deadline=overall;
 if(Clock::now()>=deadline)return;
 if(hybrid&&!incumbent.empty()){
  // The independent plan is the source of the prefix. Historical commands
  // enter only here, and exact all-cell feedback repairs the join.
  vector<int>fresh=freshNear.empty()?independentBirth:freshNear;
  int cut=min(H,max(1,min((int)fresh.size(),max(2,H/4))));
  vector<int>seed;for(int t=0;t<H;t++)seed.push_back(t<cut&&t<(int)fresh.size()?fresh[t]:incumbent[min(t,(int)incumbent.size()-1)]);
  assignmentSearch(seed,true);
 }else{
  vector<int>seed=freshNear.empty()?independentBirth:freshNear;
  if(!seed.empty())assignmentSearch(seed,true);
 }
}
