#define PHASE2_REGRESS
#include "phase2_beam.cpp"

struct Regression{uint64_t pose,hash;Bits ones,zeros;int score,parent,action;};
bool regressSolve(uint64_t endPose,int maxdepth,int variant,vector<int>&output){
  bool wantCycle=variant>=10;variant%=10;
  vector<History> history;
  int Z=0;for(int w=0;w<W;w++)Z+=pc(forbid.b[w]);
  auto hashnode=[&](const Regression&n){uint64_t h=mix(n.pose);for(int w=0;w<W;w++){h^=mix(n.ones.b[w]+w);h^=mix(n.zeros.b[w]+w*31337+12987654);}return h;};
  auto evaluate=[&](Regression&n,const Bits&one,int depth){
    int remaining=0,zeros=0,potential=0;
    for(int w=0;w<W;w++){remaining+=pc(n.ones.b[w]);zeros+=pc(n.zeros.b[w]);potential+=pc(one.b[w]&n.ones.b[w]);}
    int zeroWeight=variant==0?80:variant==1?160:variant==2?256:400;
    if(wantCycle)zeroWeight/=2;
    n.score=(NT-remaining)*256+(Z-zeros)*zeroWeight+potential*5;
    int initial[6]={0,5*R,4*R,3*R,2*R,R},setup=0;
    for(int i=0;i<6;i++){int p=(n.pose>>(8*i))&127;
      int goal=wantCycle?int((endPose>>(8*i))&127):initial[i];
      int d=min((p-goal+L)%L,(goal-p+L)%L);
      if(wantCycle&&((n.pose>>(8*i))&128)!=((endPose>>(8*i))&128))d++;
      setup=max(setup,d);
    }
    n.score-=setup*(wantCycle?96:12);
    return remaining;
  };
  auto canClose=[&](const Regression&n){
    for(int i=0;i<6;i++){
      int current=(n.pose>>(8*i))&255,initial=(endPose>>(8*i))&255;
      int p=current&127,q=initial&127,d=min((p-q+L)%L,(q-p+L)%L);
      if((current&128)!=(initial&128)){if(d)return false;}else if(d>1)return false;
    }
    return true;
  };
  auto finish=[&](const Regression&n){
    vector<int> program;int positions[6]={0,5*R,4*R,3*R,2*R,R};
    if(wantCycle){
      int first=0;
      for(int i=0;i<6;i++){
        int now=(n.pose>>(8*i))&255,before=(endPose>>(8*i))&255;
        if((now&128)!=(before&128))first|=3<<(2*i);
        else{int d=((now&127)-(before&127)+L/2)%L-L/2;if(d)first|=(d>0?2:1)<<(2*i);}
      }
      program.push_back(first);
      for(int p=n.parent;p>=0;p=history[p].parent)program.push_back(history[p].action);
      output=program;return;
    }
    int distance=0;for(int i=0;i<6;i++){int p=(n.pose>>(8*i))&127;distance=max(distance,min((p-positions[i]+L)%L,(positions[i]-p+L)%L));}
    for(int tick=0;tick<distance;tick++){
      int action=0;for(int i=0;i<6;i++){int p=(n.pose>>(8*i))&127,d=(p-positions[i]+L/2)%L-L/2;
        if(d){int op=d>0?2:1;positions[i]=(positions[i]+(d>0?1:L-1))%L;action|=op<<(2*i);}}
      program.push_back(action);
    }
    int toggle=0;for(int i=0;i<6;i++)if((n.pose>>(8*i))&128)toggle|=3<<(2*i);
    if(toggle)program.push_back(toggle);
    for(int p=n.parent;p>=0;p=history[p].parent)program.push_back(history[p].action);
    output=program;
  };
  Regression root{};root.pose=endPose;root.parent=-1;
  Bits one,two,three;
  for(int i=0;i<6;i++)if((endPose>>(8*i))&128){int p=(endPose>>(8*i))&127;for(int w=0;w<W;w++){
    uint64_t ray=rays[p][i].b[w];three.b[w]|=two.b[w]&ray;two.b[w]|=one.b[w]&ray;one.b[w]|=ray;
  }}
  for(int w=0;w<W;w++){
    if((three.b[w]&target.b[w])|((two.b[w]&~three.b[w])&forbid.b[w]))return false;
    root.ones.b[w]=target.b[w]&~two.b[w];root.zeros.b[w]=forbid.b[w]&~three.b[w];
  }
  if(evaluate(root,one,0)==0&&(!wantCycle||canClose(root))){finish(root);return true;}
  root.hash=hashnode(root);vector<Regression> beam={root};unordered_set<uint64_t> visited;visited.insert(root.hash);
  int KEEP=WIDTH*6;
  for(int depth=0;depth<maxdepth&&Clock::now()<deadline;depth++){
    vector<Regression> pool;pool.reserve(KEEP+1);auto worse=[](const Regression&a,const Regression&b){return a.score>b.score;};
    for(auto&parent:beam){
      State fake;fake.pose=parent.pose;array<Combo,64> aa,bb;combos(fake,0,aa);combos(fake,3,bb);
      for(auto&a:aa)for(auto&b:bb){
        evaluations++;Regression next;next.pose=a.pose|b.pose;bool valid=true;Bits hitOne;
        for(int w=0;w<W;w++){
          uint64_t two=a.two.b[w]|b.two.b[w]|(a.one.b[w]&b.one.b[w]);
          uint64_t three=a.three.b[w]|b.three.b[w]|(a.two.b[w]&b.one.b[w])|(a.one.b[w]&b.two.b[w]);
          if((three&parent.ones.b[w])|((two&~three)&parent.zeros.b[w])){valid=false;break;}
          next.ones.b[w]=parent.ones.b[w]&~two;
          next.zeros.b[w]=parent.zeros.b[w]&~three;
          hitOne.b[w]=a.one.b[w]|b.one.b[w];
        }
        if(!valid)continue;
        int remaining=evaluate(next,hitOne,depth+1);
        int backward=a.action|b.action,forward=0;
        for(int i=0;i<6;i++){int op=(backward>>(2*i))&3;if(op==1)op=2;else if(op==2)op=1;forward|=op<<(2*i);}
        next.parent=parent.parent;next.action=forward;
        if(remaining==0&&(!wantCycle||canClose(next))){
          history.push_back({next.parent,next.action});next.parent=(int)history.size()-1;finish(next);return true;
        }
        if((int)pool.size()>=KEEP&&next.score<=pool[0].score)continue;
        next.hash=hashnode(next);if(visited.count(next.hash))continue;
        if((int)pool.size()<KEEP){pool.push_back(next);push_heap(pool.begin(),pool.end(),worse);}else{pop_heap(pool.begin(),pool.end(),worse);pool.back()=next;push_heap(pool.begin(),pool.end(),worse);}
      }
    }
    if(pool.empty())return false;sort(pool.begin(),pool.end(),[](const Regression&a,const Regression&b){return a.score>b.score;});
    unordered_set<uint64_t> unique,boards;beam.clear();
    for(int pass=0;pass<2&&(int)beam.size()<WIDTH;pass++)for(auto&node:pool){
      if((int)beam.size()>=WIDTH)break;if(unique.count(node.hash))continue;
      uint64_t board=0;for(int w=0;w<W;w++){board^=mix(node.ones.b[w]+w);board^=mix(node.zeros.b[w]+31337*w);}
      if(pass==0&&boards.count(board))continue;
      unique.insert(node.hash);boards.insert(board);visited.insert(node.hash);
      history.push_back({node.parent,node.action});node.parent=(int)history.size()-1;beam.push_back(node);
    }
  }
  return false;
}
