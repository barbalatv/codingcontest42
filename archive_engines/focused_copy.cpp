#include <string>
#define main construction_main
#include "cyclesearch.cpp"
#undef main
#include <unordered_set>
#include <chrono>
using Row=array<int,6>;
struct Frame {array<int,6> p; int active=0,parent=-1,tick=0,produced=0; Bits matter,seen; double score=0;};
struct CopyKey {unsigned long long p; Bits matter,seen; bool operator==(const CopyKey& b)const{return p==b.p&&matter==b.matter&&seen==b.seen;}};
struct CopyHash {size_t operator()(const CopyKey& a)const{return a.p^(hash<Bits>{}(a.matter)*1664525)^(hash<Bits>{}(a.seen)*1013904223);}};
struct CopyEffect {Bits made,erased;};
struct CopySearch:Search {
 vector<Row> original,best; vector<Frame> anchors;
 unordered_map<unsigned long long,CopyEffect> effects;
 vector<int> targetCells,skirtCells; vector<double> weights;
 chrono::steady_clock::time_point deadline;
 unsigned long long config(const Frame& b){
  unsigned long long k=0;
  for(int a=0;a<3;a++){int x=b.p[a]|(((b.active>>a)&1)<<5),y=b.p[a+3]|(((b.active>>(a+3))&1)<<5);if(x>y)swap(x,y);k|=(unsigned long long)x<<(12*a);k|=(unsigned long long)y<<(12*a+6);}return k;
 }
 CopyEffect get(const Frame& b){
  auto p=b.p;for(int i=0;i<6;i++)if(!(b.active&(1<<i)))p[i]=-1;
  for(int a=0;a<3;a++)if(p[a]>p[a+3])swap(p[a],p[a+3]);
  auto k=key(p);auto it=effects.find(k);if(it!=effects.end())return it->second;
  Bits once,twice,thrice;for(int i=0;i<6;i++)if(p[i]>=0){auto ray=rays[i][p[i]];thrice|=twice&ray;twice|=once&ray;once|=ray;}
  CopyEffect e{twice&~thrice&(target|skirt),thrice&(target|skirt)};
  if(effects.size()<600000)effects.emplace(k,e);return e;
 }
 Row between(const Frame& a,const Frame& b){Row row{};for(int i=0;i<6;i++)if((a.active^b.active)&(1<<i))row[i]=3;else if(a.p[i]!=b.p[i]){int d=(origins[i][b.p[i]]-origins[i][a.p[i]]+6*r)%(6*r);if(d!=1&&d!=6*r-1)throw runtime_error("move");row[i]=d==1?1:2;}return row;}
 int reach(const Frame& a,int c,bool triple=false){int x=10000,y=x,z=x;for(int i=0;i<6;i++){int d=abs(a.p[i]-cellAxes[c][i%3])+!(a.active&(1<<i));if(d<x){z=y;y=x;x=d;}else if(d<y){z=y;y=d;}else if(d<z)z=d;}return triple?z:y;}
 void record(){
  array<int,6> pos;for(int i=0;i<6;i++)pos[i]=i*r;
  Frame a;a.p.fill(r-1);anchors.push_back(a);
  for(int t=0;t<(int)original.size();t++){
   for(int i=0;i<6;i++){int op=original[t][i];if(op==1)pos[i]=(pos[i]+1)%(6*r);if(op==2)pos[i]=(pos[i]+6*r-1)%(6*r);if(op==3)a.active^=1<<i;}
   bool valid=true;Bits once,twice,thrice;
   for(int i=0;i<6;i++){auto it=find(origins[i].begin(),origins[i].end(),pos[i]);if(it==origins[i].end()){valid=false;continue;}a.p[i]=it-origins[i].begin();if(a.active&(1<<i)){auto ray=rays[i][a.p[i]];thrice|=twice&ray;twice|=once&ray;once|=ray;}}
   a.matter=((a.matter|twice)&~thrice)&(target|skirt);
   if(a.matter==target){a.produced++;a.matter.reset();a.tick=t+1;if(valid)anchors.push_back(a);}
  }
 }
 bool save(const Frame& goal,const vector<Frame>& pool,const Frame& anchor){
  vector<Frame> frames;auto cur=goal;while(cur.parent>=0){frames.push_back(cur);cur=pool[cur.parent];}reverse(frames.begin(),frames.end());
  if(frames.empty())return false;
  vector<Row> result(original.begin(),original.begin()+anchor.tick);Frame state=anchor;int produced=anchor.produced;state.matter.reset();
  auto emit=[&](const Frame& next){
   if(result.size()+1>=best.size())return false;
   result.push_back(between(state,next));state.p=next.p;state.active=next.active;auto e=get(state);state.matter=(state.matter|e.made)&~e.erased;
   if(state.matter==target){produced++;state.matter.reset();}return true;
  };
  for(auto& next:frames){if(!emit(next))return false;if(produced==need){best=result;return true;}}
  for(int copy=0;copy<need+2;copy++){
   if(copy%2==0){for(int j=(int)frames.size()-1;j>=0;j--){if(!emit(frames[j]))return false;if(produced==need){best=result;return true;}}}
   else {for(auto& next:frames){if(!emit(next))return false;if(produced==need){best=result;return true;}}}
  }
  return false;
 }
 bool search(Frame anchor,int bound,int width,int mode,int trial){
  anchor.matter.reset();anchor.seen.reset();anchor.parent=-1;
  vector<Frame> beam{anchor},pool;unordered_set<CopyKey,CopyHash> visited;
  for(int depth=0;depth<bound;depth++){
   if(chrono::steady_clock::now()>deadline)return false;
   vector<Frame> candidates;unordered_set<CopyKey,CopyHash> seen;
   for(auto node:beam){
    if(!visited.insert({config(node),node.matter,node.seen}).second)continue;
    int parent=pool.size();pool.push_back(node);Frame next=node;bool found=false;
    auto add=[&](){
     auto e=get(next);
     if(mode==0){if((e.erased&target).any()||(e.made&skirt).any())return;}
     else if(((((e.erased&target)|(e.made&skirt)))&~node.seen).any())return;
     Frame b=next;b.matter=(node.matter|e.made)&~e.erased;b.seen=mode?(node.seen|e.made|e.erased):Bits{};b.parent=parent;
     if(b.matter==target){if(save(b,pool,anchor))found=true;return;}
     if(depth+1==bound)return;
     int maximum=0,sum=0;double quality=0;int remaining=bound-depth-1;
     for(int c:targetCells){if(b.matter[c])quality+=weights[c];else{int d=reach(b,c);if(d>remaining)return;maximum=max(maximum,d);sum+=d;}}
     int bad=0;for(int c:skirtCells)if(b.matter[c]){int d=reach(b,c,true);if(d>remaining)return;maximum=max(maximum,d);sum+=d;bad++;}
     if(bad>10)return;
     CopyKey k{config(b),b.matter,b.seen};if(visited.count(k)||!seen.insert(k).second)return;
     b.score=quality-bad*(1.3+trial*.2)-maximum*(.25+trial*.05)-sum*.018+double(rng()%1000)*.00002;
     candidates.push_back(b);
    };
    auto all=[&](auto&& self,int i)->void{
     if(found)return;
     if(i==6){add();return;}
     int active=next.active;
     for(int p=max(0,node.p[i]-1);p<=min(n-1,node.p[i]+1);p++){next.p[i]=p;self(self,i+1);if(found)break;}
     next.p[i]=node.p[i];next.active=active^(1<<i);self(self,i+1);next.active=active;
    };
    all(all,0);if(found)return true;
   }
   if(candidates.empty())return false;
   int size=min(width,(int)candidates.size());partial_sort(candidates.begin(),candidates.begin()+size,candidates.end(),[](const Frame&a,const Frame&b){return a.score>b.score;});candidates.resize(size);beam=move(candidates);
  }
  return false;
 }
 vector<Row> run(int seconds,int width){
  best=original;if(need<2)return best;record();
  for(int c=0;c<(int)cells.size();c++){if(target[c])targetCells.push_back(c);if(skirt[c])skirtCells.push_back(c);}
  weights.resize(cells.size(),1.0);vector<int> freq(cells.size());
  for(auto a:anchors){auto e=get(a);for(int c:targetCells)freq[c]+=e.made[c];}
  deadline=chrono::steady_clock::now()+chrono::seconds(seconds);
  unordered_set<unsigned long long> done;
  for(int trial=0;trial<3;trial++)for(int j=1;j<(int)anchors.size()-1;j++){
   auto a=anchors[j];if(need-a.produced<2)continue;
   auto code=config(a);if(trial==0&&!done.insert(code).second)continue;
   int bound=((int)best.size()-a.tick-1)/(need-a.produced);if(bound<2)continue;
   int nextTick=j+1<(int)anchors.size()?anchors[j+1].tick:100000;
   bound=min(bound,nextTick-a.tick-1);
   for(int c:targetCells)weights[c]=1.0+((c+trial)%3==0?.28:0.0);
   if(bound>=2)search(a,bound,width,trial?1:0,trial);
   if(chrono::steady_clock::now()>deadline)return best;
  }
  return best;
 }
};
int main(int argc,char**argv){
 if(argc<3)return 1;int seconds=argc>3?stoi(argv[3]):12,width=argc>4?stoi(argv[4]):512;
 ifstream in(argv[1]);ofstream out(argv[2]);int total;in>>total;out<<total<<'\n';int saved=0;
 for(int index=0;index<total;index++){
  CopySearch s;int lines;in>>s.r>>s.need>>s.m>>lines;s.limit=lines;s.rng.seed(941+index);s.init();
  vector<pair<int,int>> pat;for(int j=0;j<s.m;j++){int y,x;in>>y>>x;pat.emplace_back(y,x);}
  for(int j=0;j<(int)s.cells.size();j++){auto p=s.cells[j];if(find(pat.begin(),pat.end(),p)!=pat.end())s.target.set(j);else for(auto q:pat)for(int i=0;i<6;i++)if(q.first+s.dirsY[i]==p.first&&q.second+s.dirsX[i]==p.second)s.skirt.set(j);}
  s.original.resize(lines);for(auto& row:s.original)for(auto& x:row)in>>x;
  auto result=s.run(seconds,width);saved+=lines-result.size();out<<result.size()<<'\n';for(auto row:result){for(int x:row)out<<x<<' ';out<<'\n';}out.flush();cout<<index<<' '<<lines<<" -> "<<result.size()<<" saved "<<saved<<endl;
 }
 return 0;
}
