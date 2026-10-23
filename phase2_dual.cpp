#define PHASE2_DUAL
#include "phase2_beam.cpp"

struct Centre{int y,x;array<int,6> origin;vector<int> adjacent;};
struct Config{Bits two,three;};
struct DualNode{Bits matter;int a,b,type,score,parent,action,good,bad,cost;uint64_t hash;};

bool dualSolve(const vector<string>&rows,const vector<pair<int,int>>&cells,const vector<vector<int>>&index,
               int required,int incumbent,int budget,int maxDepth,int variant,vector<int>&output){
  bool wantPartial=variant>=10;variant%=10;
  int partialValue=0;vector<int> bestPartial;
  auto fallback=[&](){if(wantPartial&&!bestPartial.empty()){output=bestPartial;return true;}return false;};
  vector<Centre> centres;vector<vector<int>> ci(2*R+1,vector<int>(4*R+1,-1));
  vector<vector<int>> rail(2*R+1,vector<int>(4*R+1,-1));
  pair<int,int> corners[6]={{R,0},{2*R,R},{2*R,3*R},{R,4*R},{0,3*R},{0,R}};
  int dy[6]={0,1,1,0,-1,-1},dx[6]={2,1,-1,-2,-1,1};
  auto inside=[&](int y,int x){if(y<0||y>2*R||x<0||x>4*R||(x-y-R)%2)return false;int a=y-R,b=x-2*R;return max({abs(a),abs(a+b)/2,abs(b-a)/2})<=R;};
  for(int s=0;s<6;s++)for(int j=0;j<R;j++){
    auto[y,x]=corners[s];auto[yy,xx]=corners[(s+1)%6];rail[y+j*(yy-y)/R][x+j*(xx-x)/R]=s*R+j;
  }
  for(int y=0;y<=2*R;y++)for(int x=0;x<=4*R;x++)if(inside(y,x)&&rows[y][x]!='M'){
    Centre c;c.y=y;c.x=x;
    for(int i=0;i<6;i++){
      int yy=y,xx=x;while(inside(yy-dy[i],xx-dx[i])){yy-=dy[i];xx-=dx[i];}
      c.origin[i]=rail[yy][xx];if(c.origin[i]<0)return false;
    }
    ci[y][x]=(int)centres.size();centres.push_back(c);
  }
  int N=(int)centres.size();if(!N)return false;
  for(int a=0;a<N;a++){
    centres[a].adjacent.push_back(a);
    for(int d=0;d<6;d++){
      int y=centres[a].y+dy[d],x=centres[a].x+dx[d];
      if(y>=0&&y<=2*R&&x>=0&&x<=4*R&&ci[y][x]>=0){
        int b=ci[y][x];bool reachable=true;
        for(int i=0;i<6;i++)if(min((centres[a].origin[i]-centres[b].origin[i]+L)%L,(centres[b].origin[i]-centres[a].origin[i]+L)%L)>1)reachable=false;
        if(reachable)centres[a].adjacent.push_back(b);
      }
    }
  }
  int partition[4]={7,35,21,49}; // One direction from each opposing family; emitter 0 belongs to the first centre.
  vector<array<int,6>> cellOrigin(cells.size());
  for(int k=0;k<(int)cells.size();k++)for(int i=0;i<6;i++){
    auto[y,x]=cells[k];while(inside(y-dy[i],x-dx[i])){y-=dy[i];x-=dx[i];}
    cellOrigin[k][i]=rail[y][x];
  }
  vector<Config> configurations(4*N*N);
  for(int type=0;type<4;type++)for(int a=0;a<N;a++)for(int b=0;b<N;b++){
    Config cfg;Bits one;
    for(int i=0;i<6;i++){
      int p=((partition[type]>>i)&1)?centres[a].origin[i]:centres[b].origin[i];
      for(int w=0;w<W;w++){
        uint64_t ray=rays[p][i].b[w];cfg.three.b[w]|=cfg.two.b[w]&ray;cfg.two.b[w]|=one.b[w]&ray;one.b[w]|=ray;
      }
    }
    // Triple collisions must remain outside the target for this monotone macro model.
    for(int w=0;w<W;w++)if(cfg.three.b[w]&target.b[w])return false;
    configurations[(type*N+a)*N+b]=cfg;
  }
  if(Clock::now()>=deadline)return false;
  int initial[6]={0,5*R,4*R,3*R,2*R,R};
  vector<History> history;vector<DualNode> roots;
  auto hashnode=[&](const DualNode&node){uint64_t h=mix((node.type*N+node.a)*N+node.b);for(int w=0;w<W;w++)h^=mix(node.matter.b[w]+uint64_t(w)*31337);return h;};
  auto scoreNode=[&](DualNode&n,int cost){
    n.good=n.bad=0;int hard=0;
    for(int w=0;w<W;w++){n.good+=pc(n.matter.b[w]&target.b[w]);n.bad+=pc(n.matter.b[w]&forbid.b[w]);hard+=pc(n.matter.b[w]&hardTarget.b[w]);}
    n.score=n.good*256-n.bad*(variant==0?300:variant==2?450:180)-cost*3+(variant==3?hard*160:0);
    int eraseDistance=1000,readiness=0,checked=0;
    for(int w=0;w<W;w++){
      uint64_t bad=n.matter.b[w]&forbid.b[w];
      while(bad){unsigned long bit;_BitScanForward64(&bit,bad);int k=w*64+int(bit);bad&=bad-1;
        auto[y,x]=cells[k];
        for(int c:{n.a,n.b}){int dy=centres[c].y-y,dx=centres[c].x-x;eraseDistance=min(eraseDistance,max({abs(dy),abs(dy+dx)/2,abs(dx-dy)/2}));}
      }
      uint64_t missing=target.b[w]&~n.matter.b[w];
      while(missing&&checked<8){unsigned long bit;_BitScanForward64(&bit,missing);int k=w*64+int(bit);missing&=missing-1;checked++;
        auto[y,x]=cells[k];int aMin=1000,bMin=1000;
        for(int i=0;i<6;i++){
          int origin=cellOrigin[k][i];int p=((partition[n.type]>>i)&1)?centres[n.a].origin[i]:centres[n.b].origin[i];
          int d=min((p-origin+L)%L,(origin-p+L)%L);
          if((partition[n.type]>>i)&1)aMin=min(aMin,d);else bMin=min(bMin,d);
        }
        readiness=max(readiness,max(aMin,bMin));
      }
    }
    if(n.bad)n.score-=eraseDistance*24;
    if(n.good<NT)n.score-=readiness*16;
  };
  vector<pair<int,array<int,4>>> ranked;
  for(int type=0;type<4;type++)for(int a=0;a<N;a++)for(int b=0;b<N;b++){
    DualNode node{};node.a=a;node.b=b;node.type=type;
    const Config&cfg=configurations[(type*N+a)*N+b];
    for(int w=0;w<W;w++)node.matter.b[w]=cfg.two.b[w]&~cfg.three.b[w];
    int distance=0;
    for(int i=0;i<6;i++){
      int p=((partition[type]>>i)&1)?centres[a].origin[i]:centres[b].origin[i];
      distance=max(distance,min((p-initial[i]+L)%L,(initial[i]-p+L)%L));
    }
    scoreNode(node,distance+1);
    ranked.push_back({node.score-distance*100,{type,a,b,distance}});
  }
  sort(ranked.begin(),ranked.end(),[](const auto&a,const auto&b){return a.first>b.first;});
  unordered_set<uint64_t> initialBoards;
  for(const auto&candidate:ranked){
    auto[type,a,b,distance]=candidate.second;
    DualNode node{};node.a=a;node.b=b;node.type=type;node.parent=-1;
    const Config&cfg=configurations[(type*N+a)*N+b];for(int w=0;w<W;w++)node.matter.b[w]=cfg.two.b[w]&~cfg.three.b[w];
    uint64_t board=0;for(int w=0;w<W;w++)board^=mix(node.matter.b[w]+w);
    if(initialBoards.count(board))continue;initialBoards.insert(board);
    int positions[6];copy(begin(initial),end(initial),positions);
    for(int tick=0;tick<distance;tick++){
      int action=0;
      for(int i=0;i<6;i++){
        int p=((partition[type]>>i)&1)?centres[a].origin[i]:centres[b].origin[i];
        int d=(p-positions[i]+L/2)%L-L/2;
        if(d){int op=d>0?2:1;positions[i]=(positions[i]+(d>0?1:L-1))%L;action|=op<<(2*i);}
      }
      history.push_back({node.parent,action});node.parent=(int)history.size()-1;
    }
    history.push_back({node.parent,4095});node.parent=(int)history.size()-1; // All six toggles.
    node.cost=distance+1;scoreNode(node,node.cost);node.hash=hashnode(node);roots.push_back(node);
    if((int)roots.size()>=WIDTH)break;
  }
  auto reconstruct=[&](int parent){vector<int> reverse;for(int p=parent;p>=0;p=history[p].parent)reverse.push_back(history[p].action);return vector<int>(reverse.rbegin(),reverse.rend());};
  for(auto&node:roots){int value=node.good*120-node.bad*180-node.cost*100;if(value>partialValue){partialValue=value;bestPartial=reconstruct(node.parent);}}
  vector<DualNode> beam=roots;unordered_set<uint64_t> visited;for(auto&n:roots)visited.insert(n.hash);
  int made=0;unordered_map<uint64_t,pair<int,int>> endpoints;
  int KEEP=WIDTH*8;
  for(int depth=0;depth<maxDepth&&Clock::now()<deadline;depth++){
    bool rootGoal=false;
    for(auto&node:beam)if(node.good==NT&&node.bad==0){
      output=reconstruct(node.parent);if(required==1)return (int)output.size()<incumbent;
      DualNode end=node;end.matter=Bits();end.parent=-1;end.hash=hashnode(end);
      beam={end};history.clear();visited.clear();visited.insert(end.hash);
      made=1;endpoints[end.hash]={made,(int)output.size()};rootGoal=true;break;
    }
    if(rootGoal)break;
    vector<DualNode> pool;pool.reserve(KEEP+1);
    auto worse=[](const DualNode&a,const DualNode&b){return a.score>b.score;};
    for(const DualNode&node:beam)for(int a:centres[node.a].adjacent)for(int b:centres[node.b].adjacent){
      evaluations++;DualNode next;next.a=a;next.b=b;next.type=node.type;next.parent=node.parent;
      const Config&cfg=configurations[(node.type*N+a)*N+b];
      for(int w=0;w<W;w++)next.matter.b[w]=(node.matter.b[w]|cfg.two.b[w])&~cfg.three.b[w];
      next.cost=node.cost+1;scoreNode(next,next.cost);
      int action=0;for(int i=0;i<6;i++){
        int old=((partition[node.type]>>i)&1)?centres[node.a].origin[i]:centres[node.b].origin[i];
        int now=((partition[node.type]>>i)&1)?centres[a].origin[i]:centres[b].origin[i];
        int d=(now-old+L/2)%L-L/2;if(d)action|=(d>0?2:1)<<(2*i);
      }
      next.action=action;
      if(wantPartial){int value=next.good*120-next.bad*180-next.cost*100;if(value>partialValue){partialValue=value;bestPartial=reconstruct(node.parent);bestPartial.push_back(action);}}
      if(next.good==NT&&next.bad==0){
        output=reconstruct(node.parent);output.push_back(action);
        if(required==1)return (int)output.size()<incumbent;
        // Repeating the discovered closed walk produces another copy from the same pose.
        vector<int> forward;int p=node.parent;for(;p>=0;p=history[p].parent)forward.push_back(history[p].action);
        // Remaining copies are generated by searching from this accepted configuration below.
        made=1;beam.clear();next.matter=Bits();next.parent=-1;next.score=0;next.hash=hashnode(next);
        beam.push_back(next);history.clear();visited.clear();visited.insert(next.hash);endpoints[next.hash]={made,(int)output.size()};
        goto next_copy;
      }
      if((int)pool.size()>=KEEP&&next.score<=pool[0].score)continue;
      next.hash=hashnode(next);if(visited.count(next.hash))continue;
      if((int)pool.size()<KEEP){pool.push_back(next);push_heap(pool.begin(),pool.end(),worse);}
      else{pop_heap(pool.begin(),pool.end(),worse);pool.back()=next;push_heap(pool.begin(),pool.end(),worse);}
    }
    if(pool.empty())return fallback();
    sort(pool.begin(),pool.end(),[](const DualNode&a,const DualNode&b){return a.score>b.score;});
    beam.clear();{
      unordered_set<uint64_t> unique,boards;
      for(int pass=0;pass<2&&(int)beam.size()<WIDTH;pass++)for(auto&node:pool){
        if((int)beam.size()>=WIDTH)break;if(unique.count(node.hash))continue;
        uint64_t board=0;for(int w=0;w<W;w++)board^=mix(node.matter.b[w]+w);
        if(pass==0&&boards.count(board))continue;
        unique.insert(node.hash);boards.insert(board);visited.insert(node.hash);
        history.push_back({node.parent,node.action});node.parent=(int)history.size()-1;beam.push_back(node);
      }
    }
    continue;
next_copy:
    // A separate continuation loop below handles the same reduced search for each copy.
    break;
  }
  if(made==0)return fallback();
  while(made<required&&Clock::now()<deadline){
    vector<DualNode> current=beam;history.clear();visited.clear();for(auto&n:current)visited.insert(n.hash);
    bool found=false;
    for(int depth=0;depth<maxDepth&&Clock::now()<deadline;depth++){
      vector<DualNode> pool;pool.reserve(KEEP+1);auto worse=[](const DualNode&a,const DualNode&b){return a.score>b.score;};
      for(const auto&node:current)for(int a:centres[node.a].adjacent)for(int b:centres[node.b].adjacent){
        evaluations++;DualNode next;next.a=a;next.b=b;next.type=node.type;next.parent=node.parent;
        const Config&cfg=configurations[(node.type*N+a)*N+b];for(int w=0;w<W;w++)next.matter.b[w]=(node.matter.b[w]|cfg.two.b[w])&~cfg.three.b[w];
        next.cost=node.cost+1;scoreNode(next,next.cost);next.action=0;
        for(int i=0;i<6;i++){
          int old=((partition[node.type]>>i)&1)?centres[node.a].origin[i]:centres[node.b].origin[i];
          int now=((partition[node.type]>>i)&1)?centres[a].origin[i]:centres[b].origin[i];int d=(now-old+L/2)%L-L/2;
          if(d)next.action|=(d>0?2:1)<<(2*i);
        }
        if(next.good==NT&&next.bad==0){
          vector<int> segment=reconstruct(node.parent);segment.push_back(next.action);output.insert(output.end(),segment.begin(),segment.end());made++;
          next.matter=Bits();next.parent=-1;next.hash=hashnode(next);beam={next};
          auto it=endpoints.find(next.hash);if(it!=endpoints.end()){
            int copies=made-it->second.first;vector<int> cycle(output.begin()+it->second.second,output.end());
            while(made+copies<=required&&(int)output.size()+int(cycle.size())<incumbent){output.insert(output.end(),cycle.begin(),cycle.end());made+=copies;}
          }
          endpoints[next.hash]={made,(int)output.size()};found=true;goto finished_copy;
        }
        if((int)pool.size()>=KEEP&&next.score<=pool[0].score)continue;
        next.hash=hashnode(next);if(visited.count(next.hash))continue;
        if((int)pool.size()<KEEP){pool.push_back(next);push_heap(pool.begin(),pool.end(),worse);}else{pop_heap(pool.begin(),pool.end(),worse);pool.back()=next;push_heap(pool.begin(),pool.end(),worse);}
      }
      if(pool.empty())break;sort(pool.begin(),pool.end(),[](const DualNode&a,const DualNode&b){return a.score>b.score;});current.clear();unordered_set<uint64_t> unique,boards;
      for(int pass=0;pass<2&&(int)current.size()<WIDTH;pass++)for(auto&node:pool){
        if((int)current.size()>=WIDTH)break;if(unique.count(node.hash))continue;uint64_t board=0;for(int w=0;w<W;w++)board^=mix(node.matter.b[w]+w);if(pass==0&&boards.count(board))continue;
        unique.insert(node.hash);boards.insert(board);visited.insert(node.hash);history.push_back({node.parent,node.action});node.parent=(int)history.size()-1;current.push_back(node);
      }
    }
finished_copy:
    if(!found)return false;if((int)output.size()>=incumbent)return false;
  }
  return made==required&&(int)output.size()<incumbent;
}
