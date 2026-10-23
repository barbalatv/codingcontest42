#define main regular_splice_main
#include "splicesearch.cpp"
#undef main

struct SymOptimizer:Optimizer{
 Row swapRow(Row row,int mask){
  for(int a=0;a<3;a++)if(mask&(1<<a)){
   swap(row[a],row[a+3]);
   for(int i:{a,a+3})if(row[i]==1)row[i]=2;else if(row[i]==2)row[i]=1;
  }
  return row;
 }
 State swapState(State state,int mask){
  for(int a=0;a<3;a++)if(mask&(1<<a)){
   int constant=(2*a+3)*r,p=state.p[a];
   state.p[a]=(constant-state.p[a+3]+6*r)%(6*r);
   state.p[a+3]=(constant-p+6*r)%(6*r);
   bool x=state.active&(1<<a),y=state.active&(1<<(a+3));
   if(x!=y)state.active^=(1<<a)|(1<<(a+3));
  }
  return state;
 }
 vector<Row> solveSym(vector<Row> program){
  int totalEvaluated=0;
  for(int pass=0;pass<8;pass++){
   bool changed=false;vector<State> states{initial()};vector<Bits> made,erased;
   for(auto row:program){
    State s=states.back();tick(s,row);states.push_back(s);Bits once,twice,thrice;
    for(int i=0;i<6;i++)if(s.active&(1<<i)){auto b=rays[i][s.p[i]];thrice|=twice&b;twice|=once&b;once|=b;}
    made.push_back(twice&~thrice&relevant);erased.push_back(thrice&relevant);
   }
   for(int length=min(24,(int)program.size());length>=2&&!changed;length--){
    for(int begin=0;begin+length<=(int)program.size()&&!changed;begin++)for(int mask=1;mask<8&&!changed;mask++){
     State start=states[begin],end=swapState(states[begin+length],mask);int lower=0;
     for(int i=0;i<6;i++){int d=abs(end.p[i]-start.p[i]);d=min(d,6*r-d);lower=max(lower,d+bool((start.active^end.active)&(1<<i)));}
     if(lower>=length||lower>3)continue;
     for(int ticks=lower;ticks<=min(3,length-1)&&!changed;ticks++){
      if(ticks==0){
       if(!equivalent(start,end))continue;
       vector<Row> replacement(program.begin(),program.begin()+begin);
       for(int j=begin+length;j<(int)program.size();j++)replacement.push_back(swapRow(program[j],mask));
       program=move(replacement);changed=true;break;
      }
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
      array<Row,3> candidate;int evaluated=0;int budget=ticks==3?2048:4096;
      unordered_set<Key,KeyHash> seen;
      auto enumerate=[&](auto&& self,int i)->void{
       if(changed||evaluated>=budget||totalEvaluated>=400000)return;
       if(i<6){for(auto seq:options[i]){for(int t=0;t<ticks;t++)candidate[t][i]=seq[t];self(self,i+1);if(changed||evaluated>=budget||totalEvaluated>=400000)break;}return;}
       evaluated++;totalEvaluated++;State s=start;int prefixFinish=-1;
       for(int t=0;t<ticks;t++){tick(s,candidate[t]);if(s.count>=required){prefixFinish=t;break;}}
       bool success=prefixFinish>=0;int suffixEnd=begin+length;
       if(!success){
        if(!seen.insert({s.matter,s.count}).second)return;
        if(equivalent(s,end)){success=true;suffixEnd=program.size();}
        else for(int at=begin+length;at<(int)program.size();at++){
         if(s.count+(int)program.size()-at<required)break;
         s.matter=((s.matter|made[at])&~erased[at])&relevant;
         if((s.matter&target)==target&&(s.matter&skirt).none()){s.count++;s.matter&=~target;}
         if(s.count>=required){success=true;suffixEnd=at+1;break;}
        }
       }
       if(!success)return;
       vector<Row> replacement(program.begin(),program.begin()+begin);
       for(int t=0;t<ticks&&(prefixFinish<0||t<=prefixFinish);t++)replacement.push_back(candidate[t]);
       if(prefixFinish<0)for(int at=begin+length;at<suffixEnd;at++)replacement.push_back(swapRow(program[at],mask));
       if(replacement.size()<program.size()){program=move(replacement);changed=true;}
      };
      enumerate(enumerate,0);
     }
    }
   }
   if(!changed||totalEvaluated>=400000)break;
  }
  State s=initial();for(auto row:program)tick(s,row);if(s.count!=required)throw runtime_error("Invalid symmetric splice");
  return program;
 }
};
int main(int argc,char**argv){
 if(argc!=3)return 1;ifstream in(argv[1]);ofstream out(argv[2]);int total;in>>total;out<<total<<'\n';int saved=0;
 for(int index=0;index<total;index++){
  SymOptimizer o;int m,lines;in>>o.r>>o.required>>m>>lines;o.rng.seed(518837+index);vector<pair<int,int>> pattern;
  for(int j=0;j<m;j++){int y,x;in>>y>>x;pattern.emplace_back(y,x);}o.init(pattern);
  vector<Row> original(lines);for(auto&row:original)for(auto&op:row)in>>op;
  auto result=o.solveSym(original);saved+=lines-result.size();out<<result.size()<<'\n';for(auto row:result){for(int op:row)out<<op<<' ';out<<'\n';}out.flush();
  if(index%20==19||index+1==total)cout<<index+1<<'/'<<total<<" saved "<<saved<<endl;
 }
 return 0;
}
