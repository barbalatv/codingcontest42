// Executable parameterized rewrites; every emitted transition is simulated.
struct Rewrite{vector<int>a,b;};
vector<Rewrite>transferRules;vector<vector<int>>motifOrders;
array<double,5>transferWeights;int operatorMask=31,variantMask=0;
struct OpStat{long long attempts=0,edges=0,fullValid=0,wins=0,saved=0;double seconds=0;};
array<OpStat,5>opStats;int winningOperator=-1,winningMask=0;long long traceChecks=0;
void readTransferConfig(){int n;cin>>n;transferRules.resize(n);for(auto&r:transferRules){int a,b;cin>>a>>b;r.a.resize(a);r.b.resize(b);for(int&x:r.a)cin>>x;for(int&x:r.b)cin>>x;}for(double&w:transferWeights)cin>>w;cin>>operatorMask>>variantMask>>n;motifOrders.resize(n);for(auto&v:motifOrders){int z;cin>>z;v.resize(z);for(int&c:v)cin>>c;}}
struct TEdge{U a,b;int copies,mask;vector<int>p;};
struct EKey{U a,b;int k;bool operator==(const EKey&)const=default;};
struct EHash{size_t operator()(const EKey&x)const{return mix(x.a)^mix(x.b+19)^mix(x.k);}};
struct TGraph{
 vector<TEdge>edges;vector<U>nodes;unordered_set<U>ns;unordered_map<EKey,int,EHash>index;
 void node(U q){if(ns.insert(q).second&&nodes.size()<768)nodes.push_back(q);}
 bool add(U a,U b,int k,const vector<int>&p,int mask){if(k<1||k>4||p.empty()||edges.size()>=16000)return false;EKey key{a,b,k};auto it=index.find(key);if(it!=index.end()){auto&e=edges[it->second];if(e.p.size()<=p.size())return false;e={a,b,k,mask,p};return true;}index[key]=edges.size();edges.push_back({a,b,k,mask,p});node(a);node(b);return true;}
 int walk(U pose,const vector<int>&p,int mask){State s;s.pose=pose;vector<tuple<int,U,int>>anchors={{0,pose,0}};int added=0;
  for(int t=0;t<(int)p.size();t++){int old=s.made;s=step(s,p[t]);if(s.made==old)continue;for(int j=max(0,int(anchors.size())-4);j<(int)anchors.size();j++){auto[a,q,k]=anchors[j];added+=add(q,s.pose,s.made-k,vector<int>(p.begin()+a,p.begin()+t+1),mask);}anchors.push_back({t+1,s.pose,s.made});if(s.made>=K)break;}return added;
 }
 pair<vector<int>,int>dp(int bound){
  struct P{int cost=1000000000,edge=-1,oldk=-1;U oldq=0;};vector<unordered_map<U,P>>states(K+1);states[0][startState.pose]={0,-1,-1,0};unordered_map<U,vector<int>>adj;for(int z=0;z<(int)edges.size();z++)adj[edges[z].a].push_back(z);
  for(int k=0;k<K;k++){
   if(states[k].size()>768){vector<pair<int,U>>rank;for(auto&[q,p]:states[k])rank.push_back({p.cost,q});sort(rank.begin(),rank.end());for(int j=768;j<(int)rank.size();j++)states[k].erase(rank[j].second);}
   for(auto&[q,p]:states[k]){auto it=adj.find(q);if(it==adj.end())continue;for(int z:it->second){auto&e=edges[z];int n=k+e.copies,nc=p.cost+e.p.size();if(n>K||nc>=bound)continue;auto v=states[n].find(e.b);if(v==states[n].end()||v->second.cost>nc)states[n][e.b]={nc,z,k,q};}}
  }
  if(states[K].empty())return {{},0};auto end=min_element(states[K].begin(),states[K].end(),[](auto&a,auto&b){return a.second.cost<b.second.cost;});U q=end->first;int k=K;vector<int>path;while(k){auto p=states[k].at(q);path.push_back(p.edge);k=p.oldk;q=p.oldq;}reverse(path.begin(),path.end());vector<int>out;int mask=0;for(int z:path){out.insert(out.end(),edges[z].p.begin(),edges[z].p.end());mask|=edges[z].mask;}return {out,mask};
 }
};
vector<int>tInverse(vector<int>p){reverse(p.begin(),p.end());for(int&a:p)for(int e=0;e<6;e++){int op=(a>>(2*e))&3;if(op==1||op==2)a^=3<<(2*e);}return p;}
vector<int>tVariant(const vector<int>&p,int v){if(p.empty())return {};auto inv=tInverse(p);switch(v){case 0:return inv;case 1:inv.pop_back();inv.insert(inv.begin(),0);return inv;case 2:inv.erase(inv.begin());inv.push_back(0);return inv;case 3:inv.pop_back();return inv;case 4:inv.erase(inv.begin());return inv;case 5:{auto q=p;rotate(q.begin(),q.begin()+1,q.end());return q;}case 6:{auto q=p;rotate(q.begin(),q.end()-1,q.end());return q;}case 7:{auto q=p;q.pop_back();return q;}default:return vector<int>(p.begin()+1,p.end());}}
vector<int>tFinish(const vector<int>&p){State s=startState;for(int t=0;t<(int)p.size();t++){s=step(s,p[t]);if(s.made==K)return vector<int>(p.begin(),p.begin()+t+1);}return {};}
void considerTransfer(const vector<int>&p,int op,int mask){if(p.empty()||p.size()>size_t(H))return;int old=bestProgram.empty()?H+1:bestProgram.size();if(p.size()>=size_t(old))return;if(save(p)&&bestProgram.size()<size_t(old)){opStats[op].wins++;opStats[op].saved+=old-bestProgram.size();winningOperator=op;winningMask=mask;}}
void addWhole(TGraph&g,const vector<int>&p,int op){auto q=tFinish(p);if(q.empty())return;opStats[op].fullValid++;opStats[op].edges+=g.walk(startState.pose,q,1<<op);considerTransfer(q,op,1<<op);}
int shiftedAction(int action,int shift,bool reflect){int out=0;for(int e=0;e<6;e++){int op=(action>>(2*e))&3;if(reflect&&(op==1||op==2))op=3-op;int f=reflect?(shift-e+12)%6:(e+shift)%6;out|=op<<(2*f);}return out;}
void transferBurst(TGraph&g,const vector<int>&inc,int op){
 if(g.edges.empty())return;auto begin=Clock::now();auto&stats=opStats[op];
 for(int attempt=0;attempt<24&&Clock::now()<deadline;attempt++){
  stats.attempts++;
  if(op<2){
   int z=rng()%g.edges.size();TEdge e=g.edges[z];if(e.p.size()<2)continue;
   vector<int>variants;for(int v=0;v<9;v++)if((op==0&&v<5&&(variantMask>>v&1))||(op==1&&v>=5))variants.push_back(v);if(variants.empty())continue;
   int v=variants[rng()%variants.size()];auto p=tVariant(e.p,v);U q=e.b;
   if(rng()%2&&g.nodes.size()){
    if(rng()%3==0)q=g.nodes[rng()%g.nodes.size()];
    else{int bd=999;for(int j=0;j<min(12,int(g.nodes.size()));j++){U n=g.nodes[rng()%g.nodes.size()];int d=distance(n,e.a);if(d<bd){bd=d;q=n;}}}
   }
   stats.edges+=g.walk(q,p,1<<op);
  }else if(op==2){
   int a=rng()%inc.size(),n=min(int(inc.size())-a,2+int(rng()%7));if(n<2)continue;
   vector<int>q=inc;int kind=rng()%3;
   if(kind==0){int b=a+1+rng()%(n-1);int mask=1+rng()%63;for(int e=0;e<6;e++)if(mask>>e&1){int x=(q[a]>>(2*e))&3,y=(q[b]>>(2*e))&3;q[a]=(q[a]&~(3<<(2*e)))|(y<<(2*e));q[b]=(q[b]&~(3<<(2*e)))|(x<<(2*e));}}
   else{
    vector<vector<int>>ops(6);for(int t=a;t<a+n;t++)for(int e=0;e<6;e++){int op=(inc[t]>>(2*e))&3;if(op)ops[e].push_back(op);}
    if(kind==2)for(auto&v:ops)for(int j=0;j+1<(int)v.size();j++)if((v[j]==1&&v[j+1]==2)||(v[j]==2&&v[j+1]==1)){v.erase(v.begin()+j,v.begin()+j+2);break;}
    int D=n-1;bool ok=true;for(auto&v:ops)ok&=v.size()<=size_t(D);if(!ok)continue;vector<int>middle(D);
    for(int e=0;e<6;e++){int off=rng()%(D-ops[e].size()+1);for(int j=0;j<(int)ops[e].size();j++)middle[j+off]|=ops[e][j]<<(2*e);}
    q.erase(q.begin()+a,q.begin()+a+n);q.insert(q.begin()+a,middle.begin(),middle.end());
   }
   addWhole(g,q,op);
  }else if(op==3){
   if(transferRules.empty())continue;auto&r=transferRules[rng()%transferRules.size()];if(r.a.size()>inc.size())continue;int shift=rng()%6;bool reflect=rng()%2;vector<int>a,b;for(int x:r.a)a.push_back(shiftedAction(x,shift,reflect));for(int x:r.b)b.push_back(shiftedAction(x,shift,reflect));
   int offset=rng()%(inc.size()-a.size()+1);for(int j=0;j<=int(inc.size()-a.size());j++){int at=(offset+j)%(inc.size()-a.size()+1);if(equal(a.begin(),a.end(),inc.begin()+at)){vector<int>q(inc.begin(),inc.begin()+at);q.insert(q.end(),b.begin(),b.end());q.insert(q.end(),inc.begin()+at+a.size(),inc.end());addWhole(g,q,op);break;}}
  }else{
   if(motifOrders.empty())continue;auto&order=motifOrders[rng()%motifOrders.size()];int a=rng()%6,b=rng()%6;if(a==b||abs(a-b)==3)continue;auto p=buildBirth(a,b,order);if(p.empty())continue;
   // Only a fresh prefix enters this hybrid graph; positions are never reset.
   if(p.size()>size_t(H))p.resize(H);stats.edges+=g.walk(startState.pose,p,1<<op);
  }
 }
 auto[p,mask]=g.dp(bestProgram.empty()?H+1:int(bestProgram.size()));considerTransfer(p,op,mask);stats.seconds+=chrono::duration<double>(Clock::now()-begin).count();
}
void transferSearch(const vector<int>&inc){
 for(auto&s:opStats)s=OpStat();winningOperator=-1;winningMask=0;
 auto overall=deadline;bool composed=MODE==15||MODE==16;bool hybrid=MODE==16;
 vector<int>fresh;
 if(hybrid){auto begin=Clock::now();deadline=begin+(overall-begin)*30/100;pureSynthesis({},false);fresh=nearProgram;deadline=overall;if(!bestProgram.empty()){winningOperator=4;winningMask=16;opStats[4].wins++;opStats[4].saved=inc.size()-bestProgram.size();}opStats[4].seconds+=chrono::duration<double>(Clock::now()-begin).count();}
 array<TGraph,5>graphs;for(auto&g:graphs)g.walk(startState.pose,inc,0);
 if(hybrid&&!fresh.empty())graphs[0].walk(startState.pose,fresh,1<<4);
 int cycle=0;while(Clock::now()<deadline){int op=0;
  if(MODE==13){for(int j=0;j<5;j++){op=cycle++%5;if(operatorMask>>op&1)break;}}
  else{vector<double>w;for(int j=0;j<5;j++)w.push_back(operatorMask>>j&1?max(.01,transferWeights[j]):0.);discrete_distribution<int>d(w.begin(),w.end());op=d(rng);}
  int gindex=composed?0:op;transferBurst(graphs[gindex],inc,op);
 }
}
