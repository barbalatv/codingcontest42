#include <algorithm>
#include <array>
#include <bitset>
#include <fstream>
#include <iostream>
#include <random>
#include <unordered_set>
#include <vector>
using namespace std;
using Bits=bitset<512>;
using Row=array<int,6>;
struct State{array<int,6> p; int active=0,count=0; Bits matter;};
struct Key{Bits matter;int count;bool operator==(const Key& b)const{return count==b.count&&matter==b.matter;}};
struct KeyHash{size_t operator()(const Key& k)const{return hash<Bits>{}(k.matter)^(size_t(k.count)*1234567);}};
struct Optimizer{
 int r,required; Bits target,skirt,relevant; vector<Bits> rays[6]; mt19937 rng;
 vector<pair<int,int>> cells;
 void init(const vector<pair<int,int>>& pattern){
  for(int y=1;y<2*r;y++)for(int x=abs(r-y)+2;x<4*r-abs(r-y);x+=2)cells.emplace_back(y,x);
  for(int j=0;j<(int)cells.size();j++)if(find(pattern.begin(),pattern.end(),cells[j])!=pattern.end())target.set(j);
  int dy[]={0,1,1,0,-1,-1},dx[]={2,1,-1,-2,-1,1};
  for(int j=0;j<(int)cells.size();j++)if(!target[j])for(auto [y,x]:pattern)for(int k=0;k<6;k++)
   if(cells[j]==make_pair(y+dy[k],x+dx[k]))skirt.set(j);
  relevant=target|skirt;
  for(auto &v:rays)v.resize(6*r);
  int y=r,x=0,p=0,sy[]={-1,0,1,1,0,-1},sx[]={1,2,1,-1,-2,-1};
  for(int side=0;side<6;side++)for(int t=0;t<r;t++,p++){
   for(int i=0;i<6;i++)for(int k=1;k<4*r;k++){
    auto it=find(cells.begin(),cells.end(),make_pair(y+k*dy[i],x+k*dx[i]));
    if(it!=cells.end())rays[i][p].set(it-cells.begin());
   }
   y+=sy[side];x+=sx[side];
  }
 }
 State initial(){State s;for(int i=0;i<6;i++)s.p[i]=i*r;return s;}
 void tick(State &s,const Row& row){
  for(int i=0;i<6;i++){
   if(row[i]==1)s.p[i]=(s.p[i]+1)%(6*r);
   else if(row[i]==2)s.p[i]=(s.p[i]+6*r-1)%(6*r);
   else if(row[i]==3)s.active^=1<<i;
  }
  Bits once,twice,thrice;
  for(int i=0;i<6;i++)if(s.active&(1<<i)){
   auto &b=rays[i][s.p[i]];thrice|=twice&b;twice|=once&b;once|=b;
  }
  s.matter=((s.matter|twice)&~thrice)&relevant;
  if((s.matter&target)==target&&(s.matter&skirt).none()){s.count++;s.matter&=~target;}
 }
 bool equivalent(const State&a,const State&b){return a.p==b.p&&a.active==b.active&&a.count==b.count&&a.matter==b.matter;}
 vector<Row> solve(vector<Row> program){
  bool changed=true;int totalEvaluated=0;
  while(changed){
   changed=false;vector<State> states{initial()};
   for(auto row:program){auto s=states.back();tick(s,row);states.push_back(s);}
   for(int length=min(12,(int)program.size());length>=2&&!changed;length--){
    for(int begin=0;begin+length<=(int)program.size()&&!changed;begin++){
     State start=states[begin],end=states[begin+length];int lower=1;
     for(int i=0;i<6;i++){
      int d=abs(end.p[i]-start.p[i]);d=min(d,6*r-d);
      lower=max(lower,d+bool((start.active^end.active)&(1<<i)));
     }
     if(lower>=length||lower>3)continue;
     for(int ticks=lower;ticks<=min(3,length-1)&&!changed;ticks++){
      vector<array<int,3>> options[6];bool possible=true;
      for(int i=0;i<6;i++){
       for(int code=0;code<(1<<(2*ticks));code++){
        int p=start.p[i],active=(start.active>>i)&1;array<int,3> seq{};
        for(int t=0;t<ticks;t++){
         int op=seq[t]=(code>>(2*t))&3;
         if(op==1)p=(p+1)%(6*r);else if(op==2)p=(p+6*r-1)%(6*r);else if(op==3)active^=1;
        }
        if(p==end.p[i]&&active==((end.active>>i)&1))options[i].push_back(seq);
       }
       if(options[i].empty()){possible=false;break;}
       shuffle(options[i].begin(),options[i].end(),rng);
      }
      if(!possible)continue;
      array<Row,3> candidate;int evaluated=0;
      unordered_set<Key,KeyHash> seen;
      int budget=ticks==3?2048:4096;
      auto enumerate=[&](auto&& self,int i)->void{
       if(changed||evaluated>=budget||totalEvaluated>=250000)return;
       if(i<6){
        for(auto seq:options[i]){for(int t=0;t<ticks;t++)candidate[t][i]=seq[t];self(self,i+1);if(changed||evaluated>=budget||totalEvaluated>=250000)break;}
        return;
       }
       evaluated++;totalEvaluated++;State s=start;
       int prefixFinish=-1;
       for(int t=0;t<ticks;t++){tick(s,candidate[t]);if(s.count>=required){prefixFinish=t;break;}}
       int suffixEnd=begin+length;
       bool success=prefixFinish>=0;
       if(!success){
        if(!seen.insert({s.matter,s.count}).second)return;
        if(equivalent(s,end))success=true,suffixEnd=program.size();
        else for(int at=begin+length;at<(int)program.size();at++){
         if(s.count+(int)program.size()-at<required)break;
         tick(s,program[at]);
         if(s.count>=required){success=true;suffixEnd=at+1;break;}
        }
       }
       if(!success)return;
       vector<Row> replacement(program.begin(),program.begin()+begin);
       for(int t=0;t<ticks&&(prefixFinish<0||t<=prefixFinish);t++)replacement.push_back(candidate[t]);
       if(prefixFinish<0)replacement.insert(replacement.end(),program.begin()+begin+length,program.begin()+suffixEnd);
       if(replacement.size()<program.size()){program=move(replacement);changed=true;}
      };
      enumerate(enumerate,0);
     }
    }
   }
  }
  // Reschedule longer windows using the shortest motion of each emitter.
  for(int pass=0;pass<4;pass++){
   bool improved=false;int evaluated=0;
   vector<State> states{initial()};
   for(auto row:program){auto s=states.back();tick(s,row);states.push_back(s);}
   for(int length:{48,32,24,16,12,8,6,5}){
    if(improved||evaluated>=40000)break;
    for(int begin=0;begin+length<=(int)program.size()&&!improved&&evaluated<40000;begin++){
     State start=states[begin],end=states[begin+length];int lower=1;array<int,6> deltas;
     for(int i=0;i<6;i++){
      int d=(end.p[i]-start.p[i]+6*r)%(6*r);if(d>3*r)d-=6*r;deltas[i]=d;
      lower=max(lower,abs(d)+bool((start.active^end.active)&(1<<i)));
     }
     if(lower>=length||lower>20)continue;
     unordered_set<Key,KeyHash> seen;
     for(int attempt=0;attempt<192&&!improved&&evaluated<40000;attempt++){
      int ticks=lower+(attempt%3);if(ticks>=length)ticks=lower;
      vector<Row> candidate(ticks);array<int,6> order{0,1,2,3,4,5};
      for(int i:order){
       vector<int> ops;
       for(int j=0;j<abs(deltas[i]);j++)ops.push_back(deltas[i]>0?1:2);
       if((start.active^end.active)&(1<<i))ops.push_back(3);
       if(ticks-(int)ops.size()>=2&&attempt%4==0){ops.push_back(1);ops.push_back(2);}
       else if(ticks-(int)ops.size()>=2&&attempt%4==1){ops.push_back(3);ops.push_back(3);}
       ops.resize(ticks,0);shuffle(ops.begin(),ops.end(),rng);
       for(int t=0;t<ticks;t++)candidate[t][i]=ops[t];
      }
      evaluated++;State s=start;int finish=-1;
      for(int t=0;t<ticks;t++){tick(s,candidate[t]);if(s.count>=required){finish=t;break;}}
      int suffixEnd=begin+length;bool success=finish>=0;
      if(!success){
       if(!seen.insert({s.matter,s.count}).second)continue;
       if(equivalent(s,end))success=true,suffixEnd=program.size();
       else for(int at=begin+length;at<(int)program.size();at++){
        if(s.count+(int)program.size()-at<required)break;
        tick(s,program[at]);if(s.count>=required){success=true;suffixEnd=at+1;break;}
       }
      }
      if(!success)continue;
      vector<Row> replacement(program.begin(),program.begin()+begin);
      replacement.insert(replacement.end(),candidate.begin(),finish<0?candidate.end():candidate.begin()+finish+1);
      if(finish<0)replacement.insert(replacement.end(),program.begin()+begin+length,program.begin()+suffixEnd);
      if(replacement.size()<program.size()){program=move(replacement);improved=true;}
     }
    }
   }
   if(!improved)break;
  }
  auto s=initial();for(auto row:program)tick(s,row);
  if(s.count!=required)throw runtime_error("Invalid optimized program");
  return program;
 }
};
int main(int argc,char**argv){
 if(argc!=3)return 1;ifstream in(argv[1]);ofstream out(argv[2]);int total;in>>total;out<<total<<'\n';
 int before=0,after=0;
 for(int index=0;index<total;index++){
  Optimizer o;int size,lines;in>>o.r>>o.required>>size>>lines;o.rng.seed(8753+index);
  vector<pair<int,int>> pattern;for(int j=0;j<size;j++){int y,x;in>>y>>x;pattern.emplace_back(y,x);}o.init(pattern);
  vector<Row> program(lines);for(auto &row:program)for(auto &op:row)in>>op;
  auto result=o.solve(program);out<<result.size()<<'\n';for(auto row:result){for(auto op:row)out<<op<<' ';out<<'\n';}out.flush();
  before+=lines;after+=result.size();if(index%20==19||index+1==total)cout<<index+1<<'/'<<total<<" saved "<<before-after<<endl;
 }
}
