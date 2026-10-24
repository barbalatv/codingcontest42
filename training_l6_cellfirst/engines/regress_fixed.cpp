#define PHASE2_REGRESS
#include "phase2_beam.cpp"

uint64_t regressResultPose=0;
vector<uint64_t> regressionTestEnds;
Bits regressOnes,regressZeros;
bool regressWindow=false;uint64_t windowStartPose=0;Bits windowStartMatter;
struct Regression{uint64_t pose,hash,goalPose;Bits ones,zeros;int score,parent,action;};
bool regressSolve(uint64_t endPose,int maxdepth,int variant,vector<int>&output){
  bool wantHybrid=variant>=40&&variant<60;
  bool freeEnd=(variant>=20&&variant<40)||(variant>=50&&variant<60),wantCycle=regressWindow||(variant>=10&&variant<20)||(variant>=30&&variant<40);variant%=10;
  vector<History> history;
  int Z=0;for(int w=0;w<W;w++)Z+=pc(forbid.b[w]);
  auto hashnode=[&](const Regression&n){uint64_t h=mix(n.pose);if(wantCycle)h^=mix(n.goalPose+876521);for(int w=0;w<W;w++){h^=mix(n.ones.b[w]+w);h^=mix(n.zeros.b[w]+w*31337+12987654);}return h;};
  auto evaluate=[&](Regression&n,const Bits&one,int depth){
    int remaining=0,zeros=0,potential=0,conflicts=0;
    for(int w=0;w<W;w++){remaining+=pc(n.ones.b[w]);zeros+=pc(n.zeros.b[w]);potential+=pc(one.b[w]&n.ones.b[w]);if(regressWindow)conflicts+=pc(n.ones.b[w]&~windowStartMatter.b[w])+pc(n.zeros.b[w]&windowStartMatter.b[w]);}
    int zeroWeight=variant==0?80:variant==1?160:variant==2?256:400;
    if(wantCycle)zeroWeight/=2;
    n.score=(NT-remaining)*256+(Z-zeros)*zeroWeight+potential*5;
    if(regressWindow)n.score=-conflicts*512+(NT+Z-remaining-zeros)*8+potential*3;
    int initial[6]={0,5*R,4*R,3*R,2*R,R},setup=0;
    for(int i=0;i<6;i++){int p=(n.pose>>(8*i))&127;
      int goal=wantCycle?int((n.goalPose>>(8*i))&127):initial[i];
      int d=min((p-goal+L)%L,(goal-p+L)%L);
      if(wantCycle&&((n.pose>>(8*i))&128)!=((n.goalPose>>(8*i))&128))d++;
      setup=max(setup,d);
    }
    n.score-=setup*(wantCycle?96:12);
    return regressWindow?conflicts:remaining;
  };
  auto canClose=[&](const Regression&n){
    for(int i=0;i<6;i++){
      int current=(n.pose>>(8*i))&255,initial=(n.goalPose>>(8*i))&255;
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
        int now=(n.pose>>(8*i))&255,before=(n.goalPose>>(8*i))&255;
        if((now&128)!=(before&128))first|=3<<(2*i);
        else{int d=((now&127)-(before&127)+L+L/2)%L-L/2;if(d)first|=(d>0?2:1)<<(2*i);}
      }
      program.push_back(first);
      for(int p=n.parent;p>=0;p=history[p].parent)program.push_back(history[p].action);
      output=program;regressResultPose=n.goalPose;return;
    }
    int distance=0;for(int i=0;i<6;i++){int p=(n.pose>>(8*i))&127;distance=max(distance,min((p-positions[i]+L)%L,(positions[i]-p+L)%L));}
    for(int tick=0;tick<distance;tick++){
      int action=0;for(int i=0;i<6;i++){int p=(n.pose>>(8*i))&127,d=(p-positions[i]+L+L/2)%L-L/2;
        if(d){int op=d>0?2:1;positions[i]=(positions[i]+(d>0?1:L-1))%L;action|=op<<(2*i);}}
      program.push_back(action);
    }
    int toggle=0;for(int i=0;i<6;i++)if((n.pose>>(8*i))&128)toggle|=3<<(2*i);
    if(toggle)program.push_back(toggle);
    for(int p=n.parent;p>=0;p=history[p].parent)program.push_back(history[p].action);
    output=program;
  };
  bool hasHybrid=false;int hybridScore=1000000000;
  auto capture=[&](const Regression&n,int remaining,int depth,bool pending){
    if(!wantHybrid||remaining>32)return;
    int initial[6]={0,5*R,4*R,3*R,2*R,R},setup=0;
    for(int i=0;i<6;i++){int p=(n.pose>>(8*i))&127;setup=max(setup,min((p-initial[i]+L)%L,(initial[i]-p+L)%L));}
    int estimate=(depth+1)*100+remaining*160+setup*100;
    if(estimate>=hybridScore)return;
    hybridScore=estimate;hasHybrid=true;regressResultPose=n.pose;regressOnes=n.ones;regressZeros=n.zeros;
    output.clear();if(pending)output.push_back(n.action);
    for(int p=n.parent;p>=0;p=history[p].parent)output.push_back(history[p].action);
  };
  vector<uint64_t> endCandidates={endPose};
  if(freeEnd){
    vector<vector<int>> options(6);int initial[6]={0,5*R,4*R,3*R,2*R,R};
    for(int i=0;i<6;i++){
      options[i].push_back(initial[i]);
      for(int p=0;p<L;p++){bool nonempty=false;for(int w=0;w<W;w++)nonempty|=rays[p][i].b[w]!=0;if(nonempty)options[i].push_back(p+128);}
    }
    uint64_t random=0x9e3779b97f4a7c15ULL+R*37+NT;
    auto rng=[&](){random=mix(random+0x9e3779b97f4a7c15ULL);return random;};
    auto staticScore=[&](uint64_t pose,bool&valid){
      Bits one,two,three;for(int i=0;i<6;i++)if((pose>>(8*i))&128){int p=(pose>>(8*i))&127;for(int w=0;w<W;w++){
        uint64_t ray=rays[p][i].b[w];three.b[w]|=two.b[w]&ray;two.b[w]|=one.b[w]&ray;one.b[w]|=ray;
      }}
      int good=0,clear=0,bad=0,potential=0;
      for(int w=0;w<W;w++){
        good+=pc(two.b[w]&~three.b[w]&target.b[w]);clear+=pc(three.b[w]&forbid.b[w]);
        bad+=pc(three.b[w]&target.b[w])+pc(two.b[w]&~three.b[w]&forbid.b[w]);potential+=pc(one.b[w]&target.b[w]);
      }
      valid=bad==0;return good*256+clear*160-bad*1536+potential*2;
    };
    unordered_set<uint64_t> seen;
    for(int restart=0;restart<WIDTH*3&&Clock::now()<deadline;restart++){
      uint64_t pose=0;
      for(int i=0;i<6;i++){
        int choice=options[i][rng()%options[i].size()];pose|=uint64_t(choice)<<(8*i);
      }
      if(restart%3==0)pose=endPose;
      bool valid;int score=staticScore(pose,valid);
      for(int pass=0;pass<8;pass++){
        uint64_t next=pose;int best=score;
        int offset=rng()%6;
        for(int j=0;j<6;j++){int i=(j+offset)%6;
          for(int choice:options[i]){
            uint64_t p=(pose&~(255ULL<<(8*i)))|(uint64_t(choice)<<(8*i));bool okay;int value=staticScore(p,okay);
            if(value>best){best=value;next=p;}
          }
        }
        if(next==pose)break;pose=next;score=best;
        staticScore(pose,valid);if(valid&&seen.insert(pose).second)endCandidates.push_back(pose);
      }
      staticScore(pose,valid);if(valid&&seen.insert(pose).second)endCandidates.push_back(pose);
    }
  }
  if(!regressionTestEnds.empty())endCandidates=regressionTestEnds;
  vector<Regression> roots;
  for(uint64_t candidatePose:endCandidates){
  Regression root{};root.pose=candidatePose;root.goalPose=regressWindow?windowStartPose:candidatePose;root.parent=-1;
  Bits one,two,three;
  for(int i=0;i<6;i++)if((candidatePose>>(8*i))&128){int p=(candidatePose>>(8*i))&127;for(int w=0;w<W;w++){
    uint64_t ray=rays[p][i].b[w];three.b[w]|=two.b[w]&ray;two.b[w]|=one.b[w]&ray;one.b[w]|=ray;
  }}
  bool validRoot=true;
  for(int w=0;w<W;w++){
    if((three.b[w]&target.b[w])|((two.b[w]&~three.b[w])&forbid.b[w])){validRoot=false;break;}
    root.ones.b[w]=target.b[w]&~two.b[w];root.zeros.b[w]=forbid.b[w]&~three.b[w];
  }
  if(!validRoot){
#ifdef LEGACY_ROOT_BUG
    return false;
#else
    continue;
#endif
  }
  int rootRemaining=evaluate(root,one,0);capture(root,rootRemaining,0,false);
  if(rootRemaining==0&&(!wantCycle||canClose(root))){if(!wantHybrid)finish(root);return true;}
  root.hash=hashnode(root);roots.push_back(root);
  }
  sort(roots.begin(),roots.end(),[](const Regression&a,const Regression&b){return a.score>b.score;});
  if((int)roots.size()>WIDTH)roots.resize(WIDTH);
  vector<Regression> beam=roots;unordered_set<uint64_t> visited;for(auto&r:roots)visited.insert(r.hash);
  int KEEP=WIDTH*6;
  int minRemaining=NT,lastDepth=0;
  for(int depth=0;depth<maxdepth&&Clock::now()<deadline;depth++){
    lastDepth=depth;
    vector<Regression> pool;pool.reserve(KEEP+1);auto worse=[](const Regression&a,const Regression&b){return a.score>b.score;};
    for(auto&parent:beam){
      State fake;fake.pose=parent.pose;array<Combo,64> aa,bb;combos(fake,0,aa);combos(fake,3,bb);
      for(auto&a:aa)for(auto&b:bb){
        evaluations++;Regression next;next.pose=a.pose|b.pose;next.goalPose=parent.goalPose;bool valid=true;Bits hitOne;
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
        minRemaining=min(minRemaining,remaining);
        if(regressWindow){
          int distance=0;
          for(int i=0;i<6;i++){
            int p=(next.pose>>(8*i))&127,q=(windowStartPose>>(8*i))&127;
            int d=min((p-q+L)%L,(q-p+L)%L);
            if(((next.pose>>(8*i))&128)!=((windowStartPose>>(8*i))&128))d++;
            distance=max(distance,d);
          }
          if(depth+1+max(1,distance)>maxdepth)continue;
        }
        int backward=a.action|b.action,forward=0;
        for(int i=0;i<6;i++){int op=(backward>>(2*i))&3;if(op==1)op=2;else if(op==2)op=1;forward|=op<<(2*i);}
        next.parent=parent.parent;next.action=forward;
        capture(next,remaining,depth+1,true);
        if(remaining==0&&(!wantCycle||canClose(next))){
          if(wantHybrid)return true;
          history.push_back({next.parent,next.action});next.parent=(int)history.size()-1;finish(next);return true;
        }
        if((int)pool.size()>=KEEP&&next.score<=pool[0].score)continue;
        next.hash=hashnode(next);if(visited.count(next.hash))continue;
        if((int)pool.size()<KEEP){pool.push_back(next);push_heap(pool.begin(),pool.end(),worse);}else{pop_heap(pool.begin(),pool.end(),worse);pool.back()=next;push_heap(pool.begin(),pool.end(),worse);}
      }
    }
    if(pool.empty())return hasHybrid;sort(pool.begin(),pool.end(),[](const Regression&a,const Regression&b){return a.score>b.score;});
    unordered_set<uint64_t> unique,boards;beam.clear();
    for(int pass=0;pass<2&&(int)beam.size()<WIDTH;pass++)for(auto&node:pool){
      if((int)beam.size()>=WIDTH)break;if(unique.count(node.hash))continue;
      uint64_t board=0;for(int w=0;w<W;w++){board^=mix(node.ones.b[w]+w);board^=mix(node.zeros.b[w]+31337*w);}
      if(pass==0&&boards.count(board))continue;
      unique.insert(node.hash);boards.insert(board);visited.insert(node.hash);
      history.push_back({node.parent,node.action});node.parent=(int)history.size()-1;beam.push_back(node);
    }
  }
  if(NT>=250)cerr<<"regression incomplete: target="<<NT<<" remaining="<<minRemaining<<" depth="<<lastDepth<<"\n";
  return hasHybrid;
}
