#include <string>
#include <chrono>
#define main constructive_search_main
#include "cyclesearch.cpp"
#undef main
#include <unordered_set>

static std::chrono::steady_clock::time_point reverseDeadline=std::chrono::steady_clock::time_point::max();
struct Node{array<int,6> p;int active;Bits covered,emptyNeeded;int setup,parent;double score;};
struct Key{unsigned long long p;Bits covered,emptyNeeded;bool operator==(const Key&b)const{return p==b.p&&covered==b.covered&&emptyNeeded==b.emptyNeeded;}};
struct KeyHash{size_t operator()(const Key&k)const{return k.p^(hash<Bits>{}(k.covered)*1664525)^(hash<Bits>{}(k.emptyNeeded)*1013904223);}};
struct MatterEffect{Bits made,erased;};
struct ToggleSearch:Search{
 vector<Node> seeds;
 unordered_map<unsigned long long,MatterEffect> dynamicCache;
 int mode=0;
 MatterEffect get(const Node& node){
  auto p=node.p;for(int i=0;i<6;i++)if(!(node.active&(1<<i)))p[i]=-1;
  for(int a=0;a<3;a++)if(p[a]>p[a+3])swap(p[a],p[a+3]);
  auto k=key(p);auto it=dynamicCache.find(k);if(it!=dynamicCache.end())return it->second;
  Bits once,twice,thrice;
  for(int i=0;i<6;i++)if(p[i]>=0){auto b=rays[i][p[i]];thrice|=twice&b;twice|=once&b;once|=b;}
  MatterEffect e{twice&~thrice&(target|skirt),thrice&(target|skirt)};
  if(dynamicCache.size()<400000)dynamicCache.emplace(k,e);return e;
 }
 unsigned long long code(const Node& node){
  unsigned long long result=0;
  for(int a=0;a<3;a++){
   int x=node.p[a]|(((node.active>>a)&1)<<5),y=node.p[a+3]|(((node.active>>(a+3))&1)<<5);
   if(x>y)swap(x,y);result|=(unsigned long long)x<<(a*12);result|=(unsigned long long)y<<(a*12+6);
  }
  return result;
 }
 int reach(const Node& b,int c){
  int first=10000,second=10000;
  for(int i=0;i<6;i++){int d=abs(b.p[i]-cellAxes[c][i%3])+!(b.active&(1<<i));if(d<first){second=first;first=d;}else if(d<second)second=d;}
  return second;
 }
 int duration(const Node& node){
  int best=0;for(int p:node.p)best=max(best,abs(p-(r-1)));return best;
 }
 bool adjacent(const Node&a,const Node&b){
  for(int i=0;i<6;i++)if(abs(a.p[i]-b.p[i])>1||(((a.active^b.active)&(1<<i))&&a.p[i]!=b.p[i]))return false;
  return true;
 }
 virtual bool accept(const Node& node,const vector<Node>& pool,int parent,int depth,vector<Node>&best,int&bound){
  if(node.covered.any())return false;
  vector<Node> route;for(int j=parent;j>=0;j=pool[j].parent)route.push_back(pool[j]);
  trim(route);int cost=(int)render(route).size();
  if(cost<bound)bound=cost,best=route;
  return true;
 }
 virtual int prefixMinimum(){return 0;}
 void trim(vector<Node>& route){
  bool changed=true;
  while(changed){
   changed=false;
   for(int i=0;i<(int)route.size()&&!changed;i++)for(int j=min((int)route.size(),i+16);j>i;j--){
    if(i&&j<(int)route.size()&&!adjacent(route[i-1],route[j]))continue;
    Bits matter;int finish=-1;
    for(int at=0;at<(int)route.size();at++)if(at<i||at>=j){
     auto e=get(route[at]);matter=(matter|e.made)&~e.erased;
     if(matter==target){finish=at;break;}
    }
    if(finish>=0){
     vector<Node> kept;for(int at=0;at<=finish;at++)if(at<i||at>=j)kept.push_back(route[at]);
     route=move(kept);changed=true;break;
    }
   }
  }
 }
 vector<array<int,6>> schedule(const vector<array<int,6>>& program){
  vector<pair<int,int>> activations[6];array<int,6> positions{},cursor{};int active=0;
  for(int i=0;i<6;i++)positions[i]=i*r;
  for(int t=0;t<(int)program.size();t++)for(int i=0;i<6;i++){
   int op=program[t][i];
   if(op==1)positions[i]=(positions[i]+1)%(6*r);
   else if(op==2)positions[i]=(positions[i]+6*r-1)%(6*r);
   else if(op==3){if(!(active&(1<<i)))activations[i].emplace_back(t,positions[i]);active^=1<<i;}
  }
  int remove=program.size();
  for(int i=0;i<6;i++)if(!activations[i].empty()){
   auto [t,p]=activations[i][0];int d=abs(p-i*r);d=min(d,6*r-d);remove=min(remove,t-d);
  }
  if(remove<0||remove>=(int)program.size())return program;
  vector<array<int,6>> result;active=0;for(int i=0;i<6;i++)positions[i]=i*r;
  for(int t=remove;t<(int)program.size();t++){
   array<int,6> row{};
   for(int i=0;i<6;i++){
    int op=program[t][i];
    if(op==3){if(!(active&(1<<i)))cursor[i]++;active^=1<<i;row[i]=op;}
    else if(active&(1<<i)){row[i]=op;if(op==1)positions[i]=(positions[i]+1)%(6*r);else if(op==2)positions[i]=(positions[i]+6*r-1)%(6*r);}
    else if(cursor[i]<(int)activations[i].size()){
     int d=(activations[i][cursor[i]].second-positions[i]+6*r)%(6*r);if(d>3*r)d-=6*r;
     if(d){row[i]=d>0?1:2;positions[i]=(positions[i]+(d>0?1:6*r-1))%(6*r);}
    }
   }
   result.push_back(row);
  }
  return result;
 }
 vector<Node> search(){
  vector<Node> best;int bound=limit;
  vector<Node> expanded;
  unordered_set<unsigned long long> roots;
  // A backward root is a possible final tick, not necessarily a tick present
  // in the incumbent. Search several local maxima of final target coverage.
  vector<int> targetCells;for(int c=0;c<(int)cells.size();c++)if(target[c])targetCells.push_back(c);
  for(int attempt=0;attempt<640;attempt++){
   if(std::chrono::steady_clock::now()>reverseDeadline)return best;
   Node b;b.active=1+rng()%63;
   for(int i=0;i<6;i++)b.p[i]=cellAxes[targetCells[rng()%targetCells.size()]][i%3];
   auto value=[&](const Node& q){auto e=get(q);return 8.0*(e.made&target).count()-40.0*((e.erased&target).count()+(e.made&skirt).count())+.02*(e.erased&skirt).count();};
   for(int pass=0;pass<3;pass++)for(int i=0;i<6;i++){
    double highest=-1e20;int selected=b.p[i];
    for(int p=0;p<n;p++){b.p[i]=p;double v=value(b)+(rng()%1000)*.0003;if(v>highest)highest=v,selected=p;}
    b.p[i]=selected;
   }
   seeds.push_back(b);
  }
  // Pure final erasures are important roots for backward planning.
  for(int c=0;c<(int)cells.size();c++)if(skirt[c])for(int mask=0;mask<8;mask++){
   Node b;b.p.fill(r-1);b.active=0;
   for(int a=0;a<3;a++){int i=a+((mask&(1<<a))?3:0);b.p[i]=cellAxes[c][a];b.active|=1<<i;}seeds.push_back(b);
  }
  for(auto seed:seeds)for(int active=1;active<64;active++){
   if(std::chrono::steady_clock::now()>reverseDeadline)return best;
   seed.active=active;
   if(!roots.insert(code(seed)).second)continue;
   auto e=get(seed);if((e.erased&target).any()||(e.made&skirt).any())continue;
   if((e.made&target).none()&&(e.erased&skirt).none())continue;
   seed.covered=target&~e.made;seed.emptyNeeded=skirt&~e.erased;seed.setup=duration(seed);seed.parent=-1;expanded.push_back(seed);
  }
  vector<int> targets;for(int c=0;c<(int)cells.size();c++)if(target[c])targets.push_back(c);
  vector<int> frequency(cells.size());
  for(auto&b:expanded)for(int c:targets)if(!b.covered[c])frequency[c]++;
  auto rare=targets;sort(rare.begin(),rare.end(),[&](int a,int b){return frequency[a]<frequency[b];});
  Bits hard;for(int j=0;j<min(12,(int)rare.size()/3);j++)hard.set(rare[j]);
  for(int trial=0;trial<3;trial++){
   auto score=[&](const Node& b){
    return double((target&~b.covered).count())+double((hard&~b.covered).count())*.9*trial
           -double(duration(b))/need*(.12+.08*trial);
   };
   vector<Node> beam,pool;
   unordered_map<Key,int,KeyHash> visited;
   for(auto b:expanded)beam.push_back(b);
   for(auto&b:beam)b.score=score(b)+double(rng()%1000)*.0001;
   sort(beam.begin(),beam.end(),[](const auto&a,const auto&b){return a.score>b.score;});
   if(beam.size()>512)beam.resize(512);
   for(int depth=1;!beam.empty()&&depth*need+prefixMinimum()<bound;depth++){
    vector<Node> candidates;unordered_set<Key,KeyHash> seen;
    for(auto node:beam){
     if(std::chrono::steady_clock::now()>reverseDeadline)return best;
     Key stateKey{code(node),node.covered,node.emptyNeeded};
     int stateCost=depth*need;
     auto old=visited.find(stateKey);if(old!=visited.end()&&old->second<=stateCost)continue;
     visited[stateKey]=stateCost;
     int parent=pool.size();pool.push_back(node);
     if(accept(node,pool,parent,depth,best,bound))continue;
     int guide=-1,minimum=10000;
     for(int c:targets)if(node.covered[c]){
      int d=reach(node,c);
      if(d<minimum){minimum=d;guide=c;}
     }
     auto add=[&](Node b){
      auto e=get(b);if((e.erased&node.covered).any()||(e.made&node.emptyNeeded).any())return;
      b.covered=node.covered&~e.made;b.emptyNeeded=node.emptyNeeded&~e.erased;
      auto old=visited.find({code(b),b.covered,b.emptyNeeded});
      if(old!=visited.end()&&old->second<=(depth+1)*need)return;
      if(!seen.insert({code(b),b.covered,b.emptyNeeded}).second)return;
      b.parent=parent;b.setup=node.setup;b.score=score(b)+double(rng()%1000)*.0001;candidates.push_back(b);
     };
     Node next=node;
     auto enumerate=[&](auto&& self,int i)->void{
      if(i==6){add(next);return;}
      if(node.active&(1<<i)){
       for(int p=max(0,node.p[i]-1);p<=min(n-1,node.p[i]+1);p++){next.p[i]=p;self(self,i+1);}
      }else{
       next.p[i]=node.p[i];self(self,i+1);
       if(guide>=0&&node.p[i]!=cellAxes[guide][i%3]){next.p[i]=node.p[i]+(node.p[i]<cellAxes[guide][i%3]?1:-1);self(self,i+1);}
      }
     };
     enumerate(enumerate,0);
     for(int active=1;active<64;active++){next=node;next.active=active;add(next);}
     // Toggle selected emitters while the other emitters move concurrently.
     for(int a=0;a<128;a++){
      next=node;int toggles=1<<(rng()%6);if(a%4==0)toggles|=1<<(rng()%6);next.active^=toggles;
      for(int i=0;i<6;i++)if(!(toggles&(1<<i)))next.p[i]=clamp(node.p[i]+int(rng()%3)-1,0,n-1);
      add(next);
     }
    }
    if(candidates.empty())break;
    int shortlist=min(1800,(int)candidates.size());
    partial_sort(candidates.begin(),candidates.begin()+shortlist,candidates.end(),[](const auto&a,const auto&b){return a.score>b.score;});
    candidates.resize(shortlist);
    for(auto&b:candidates){
     int maximum=0,sum=0;
     for(int c:targets)if(b.covered[c]){
      int d=reach(b,c);
      maximum=max(maximum,d);sum+=d;
     }
     b.score-=maximum*(trial?.45:.25)+sum*.025;
    }
    sort(candidates.begin(),candidates.end(),[](const auto&a,const auto&b){return a.score>b.score;});
    array<int,64> groups{};unordered_map<Bits,int> requirementCounts;beam.clear();
    for(auto b:candidates){if(groups[b.active]>=64||requirementCounts[b.covered]>=32)continue;groups[b.active]++;requirementCounts[b.covered]++;beam.push_back(b);if(beam.size()>=240)break;}
   }
  }
  return best;
 }
 vector<array<int,6>> render(vector<Node> route){
  auto estimate=[&](bool reversed){
   int ticks=duration(reversed?route.back():route.front()),produced=0;Bits matter;
   for(int cycle=0;cycle<=2*need+1;cycle++)for(int t=0;t<(int)route.size();t++){
    int at=(bool(cycle%2)^reversed)?route.size()-1-t:t;
    auto e=get(route[at]);matter=(matter|e.made)&~e.erased;ticks++;
    if(matter==target){produced++;matter.reset();if(produced==need)return ticks;}
   }
   return 100000000;
  };
  if(estimate(true)<estimate(false))reverse(route.begin(),route.end());
  int flip=0,cost=6*r;
  for(int f=0;f<8;f++){
   int d=0;for(int i=0;i<6;i++){int j=(f&(1<<(i%3)))?(i+3)%6:i;int x=abs(origins[j][route[0].p[i]]-j*r);d=max(d,min(x,6*r-x));}
   if(d<cost)cost=d,flip=f;
  }
  auto physical=[&](int i){return(flip&(1<<(i%3)))?(i+3)%6:i;};
  vector<array<int,6>> program;array<int,6> ds;
  for(int i=0;i<6;i++){int j=physical(i);int d=(origins[j][route[0].p[i]]-j*r+6*r)%(6*r);if(d>3*r)d-=6*r;ds[i]=d;}
  for(int t=0;t<cost;t++){
   array<int,6> row{};for(int i=0;i<6;i++)if(t<abs(ds[i]))row[physical(i)]=ds[i]>0?1:2;program.push_back(row);
  }
  array<int,6> row{};for(int i=0;i<6;i++)if(route[0].active&(1<<i))row[physical(i)]=3;program.push_back(row);
  Bits matter=get(route[0]).made;int made=matter==target;if(made)matter.reset();
  Node current=route[0];
  for(int cycle=0;made<need&&cycle<=2*need+1;cycle++){
   for(int t=cycle?0:1;t<(int)route.size()&&made<need;t++){
    Node next=route[cycle%2?route.size()-1-t:t];array<int,6> instruction{};
    for(int i=0;i<6;i++){
     int j=physical(i);
     if((current.active^next.active)&(1<<i))instruction[j]=3;
     else if(current.p[i]!=next.p[i]){
      int delta=(origins[j][next.p[i]]-origins[j][current.p[i]]+6*r)%(6*r);
      if(delta!=1&&delta!=6*r-1)throw runtime_error("Invalid route transition");instruction[j]=delta==1?1:2;
     }
    }
    program.push_back(instruction);auto e=get(next);matter=(matter|e.made)&~e.erased;
    if(matter==target){made++;matter.reset();}current=next;
   }
  }
  if(made!=need)throw runtime_error("Incomplete production cycle");
  return schedule(program);
 }
};
#ifndef REVERSE_NO_MAIN
int main(int argc,char**argv){
 if(argc<3)return 1;int offset=argc>=4?stoi(argv[3]):0;int budgetMs=argc>=5?stoi(argv[4]):4000;
 ifstream in(argv[1]);ofstream out(argv[2]);int total;in>>total;out<<total<<'\n';
 for(int index=0;index<total;index++){
  ToggleSearch s;int lines;in>>s.r>>s.need>>s.m>>lines;s.limit=lines;s.rng.seed(13988021+offset+index);s.init();
  vector<pair<int,int>> pat;for(int j=0;j<s.m;j++){int y,x;in>>y>>x;pat.emplace_back(y,x);}
  for(int j=0;j<(int)s.cells.size();j++){
   auto p=s.cells[j];if(find(pat.begin(),pat.end(),p)!=pat.end())s.target.set(j);
   else for(auto q:pat)for(int i=0;i<6;i++)if(q.first+s.dirsY[i]==p.first&&q.second+s.dirsX[i]==p.second)s.skirt.set(j);
  }
  array<int,6> position;for(int i=0;i<6;i++)position[i]=i*s.r;int active=0;vector<array<int,6>> original(lines);
  for(int t=0;t<lines;t++){
   for(int i=0;i<6;i++){int op;in>>op;original[t][i]=op;if(op==1)position[i]=(position[i]+1)%(6*s.r);else if(op==2)position[i]=(position[i]+6*s.r-1)%(6*s.r);else if(op==3)active^=1<<i;}
   Node node;node.active=active;bool valid=true;
   for(int i=0;i<6;i++){
    auto it=find(s.origins[i].begin(),s.origins[i].end(),position[i]);
    if(it==s.origins[i].end()){valid=false;break;}node.p[i]=it-s.origins[i].begin();
   }
   if(valid)s.seeds.push_back(node);
  }
  vector<array<int,6>> result=original;
  reverseDeadline=std::chrono::steady_clock::now()+std::chrono::milliseconds(budgetMs);
  if(lines>=20){auto route=s.search();if(!route.empty()){auto p=s.render(route);if(p.size()<result.size())result=p;}}
  out<<result.size()<<'\n';for(auto row:result){for(int x:row)out<<x<<' ';out<<'\n';}out.flush();
  if(index%10==9||index+1==total)cout<<index+1<<'/'<<total<<" complete"<<endl;
 }
}
#endif
