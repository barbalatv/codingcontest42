#define REVERSE_NO_MAIN
#include "reversebeam.cpp"

using Row=array<int,6>;
struct Prefix {Node state;Bits matter;int length,produced;};
struct SuffixSearch:ToggleSearch{
 vector<Row> original,result;
 vector<Prefix> prefixes;
 int required=1;
 int prefixMinimum() override {for(auto&prefix:prefixes)if(prefix.produced==required-1)return prefix.length;return 0;}
 void baseline(){
  array<int,6> position;for(int i=0;i<6;i++)position[i]=i*r;
  Prefix prefix;prefix.state.p.fill(r-1);prefix.state.active=0;prefix.length=0;prefix.produced=0;
  prefixes.push_back(prefix);
  for(auto row:original){
   for(int i=0;i<6;i++){
    if(row[i]==1)position[i]=(position[i]+1)%(6*r);
    else if(row[i]==2)position[i]=(position[i]+6*r-1)%(6*r);
    else if(row[i]==3)prefix.state.active^=1<<i;
   }
   bool valid=true;Bits once,twice,thrice;
   for(int i=0;i<6;i++){
    auto it=find(origins[i].begin(),origins[i].end(),position[i]);
    if(it==origins[i].end()){valid=false;prefix.state.p[i]=r-1;}
    else {prefix.state.p[i]=it-origins[i].begin();if(prefix.state.active&(1<<i)){auto b=rays[i][prefix.state.p[i]];thrice|=twice&b;twice|=once&b;once|=b;}}
   }
   prefix.matter=((prefix.matter|twice)&~thrice)&(target|skirt);
   if(prefix.matter==target){prefix.produced++;prefix.matter.reset();}
   prefix.length++;
   if(valid){prefixes.push_back(prefix);seeds.push_back(prefix.state);}
  }
  if(prefix.produced!=required)throw runtime_error("Invalid baseline");
  result=original;
 }
 bool accept(const Node& node,const vector<Node>& pool,int parent,int depth,vector<Node>&best,int&bound) override{
  for(const auto& prefix:prefixes){
   if(prefix.produced!=required-1||prefix.length+depth>=bound)continue;
   if((node.covered&~prefix.matter).any()||(node.emptyNeeded&prefix.matter).any())continue;
   int flip=-1;
   for(int mask=0;mask<8&&flip<0;mask++){
    bool valid=true;
    for(int i=0;i<6;i++){
     int j=mask&(1<<(i%3))?(i+3)%6:i;
     if(abs(node.p[i]-prefix.state.p[j])>1||
       (bool(node.active&(1<<i))!=bool(prefix.state.active&(1<<j))&&node.p[i]!=prefix.state.p[j])){valid=false;break;}
    }
    if(valid)flip=mask;
   }
   if(flip<0)continue;
   vector<Node> route;for(int j=parent;j>=0;j=pool[j].parent)route.push_back(pool[j]);
   vector<Row> candidate(original.begin(),original.begin()+prefix.length);
   Node current=prefix.state;
   for(const Node& next:route){
    Row row{};
    for(int i=0;i<6;i++){
     int j=flip&(1<<(i%3))?(i+3)%6:i;
     if(bool(current.active&(1<<j))!=bool(next.active&(1<<i)))row[j]=3;
     else if(current.p[j]!=next.p[i]){
      int delta=(origins[j][next.p[i]]-origins[j][current.p[j]]+6*r)%(6*r);
      if(delta!=1&&delta!=6*r-1)throw runtime_error("Invalid suffix transition");
      row[j]=delta==1?1:2;
     }
    }
    candidate.push_back(row);
    current.active=0;
    for(int i=0;i<6;i++){int j=flip&(1<<(i%3))?(i+3)%6:i;current.p[j]=next.p[i];if(next.active&(1<<i))current.active|=1<<j;}
   }
   result=move(candidate);bound=result.size();best=route;
  }
  return false;
 }
};
int main(int argc,char**argv){
 if(argc<3)return 1;int offset=argc>=4?stoi(argv[3]):0;int budgetMs=argc>=5?stoi(argv[4]):4000;
 ifstream in(argv[1]);ofstream out(argv[2]);int total;in>>total;out<<total<<'\n';int saved=0;
 for(int index=0;index<total;index++){
  SuffixSearch s;int lines;in>>s.r>>s.required>>s.m>>lines;s.need=1;s.limit=lines;s.rng.seed(891213+offset+index);s.init();
  vector<pair<int,int>> pat;for(int j=0;j<s.m;j++){int y,x;in>>y>>x;pat.emplace_back(y,x);}
  for(int j=0;j<(int)s.cells.size();j++){
   auto p=s.cells[j];if(find(pat.begin(),pat.end(),p)!=pat.end())s.target.set(j);
   else for(auto q:pat)for(int i=0;i<6;i++)if(q.first+s.dirsY[i]==p.first&&q.second+s.dirsX[i]==p.second)s.skirt.set(j);
  }
  s.original.resize(lines);for(auto&row:s.original)for(auto&op:row)in>>op;s.baseline();
  reverseDeadline=std::chrono::steady_clock::now()+std::chrono::milliseconds(budgetMs);
  if(lines>=14)s.search();
  auto result=s.result;saved+=lines-result.size();
  out<<result.size()<<'\n';for(auto row:result){for(int x:row)out<<x<<' ';out<<'\n';}out.flush();
  if(index%5==4||index+1==total)cout<<index+1<<'/'<<total<<" saved "<<saved<<endl;
 }
}
