#include <algorithm>
#include <array>
#include <bitset>
#include <fstream>
#include <iostream>
#include <random>
#include <unordered_map>
#include <vector>
using namespace std;
using Bits=bitset<512>;
struct Effect{Bits made; bool valid;};
struct Search {
 int r,n,m,need,limit,attempts=1200; Bits target,skirt; vector<pair<int,int>> cells;
 vector<array<int,3>> cellAxes; vector<int> origins[6];
 vector<Bits> rays[6]; unordered_map<unsigned long long,Effect> cache;
 mt19937 rng; array<int,6> dirsY{0,1,1,0,-1,-1},dirsX{2,1,-1,-2,-1,1};
 unsigned long long key(const array<int,6>& s){unsigned long long k=0;for(int i=0;i<6;i++)k|=(unsigned long long)(s[i]+1)<<(i*5);return k;}
 Effect effect(const array<int,6>& s){
  auto k=key(s);auto it=cache.find(k);if(it!=cache.end())return it->second;
  Bits once,twice,thrice;
  for(int i=0;i<6;i++)if(s[i]>=0){auto &b=rays[i][s[i]];thrice|=twice&b;twice|=once&b;once|=b;}
  Bits made=twice&~thrice;Effect e{made&target,!(thrice&target).any()&&!(made&skirt).any()};
  if(cache.size()<400000)cache.emplace(k,e);return e;
 }
 double value(const array<int,6>& s){
  Bits once,twice,thrice;
  for(int i=0;i<6;i++)if(s[i]>=0){auto &b=rays[i][s[i]];thrice|=twice&b;twice|=once&b;once|=b;}
  Bits made=twice&~thrice;
  return double((made&target).count())-20.0*((made&skirt).count()+(thrice&target).count());
 }
 void init(){
  n=2*r-1;
  for(int y=1;y<2*r;y++)for(int x=abs(r-y)+2;x<4*r-abs(r-y);x+=2)cells.emplace_back(y,x);
  for(int i=0;i<6;i++){rays[i].resize(n);origins[i].resize(n);}
  for(int j=0;j<(int)cells.size();j++){
   auto [y,x]=cells[j];int indices[3]={y-1,(x-y)/2,(x+y-2*r)/2};
   // Sorted diagonal keys start at 2-r and r+2 respectively.
   indices[1]=(x-y-(2-r))/2;indices[2]=(x+y-(r+2))/2;
   cellAxes.push_back({indices[0],indices[1],indices[2]});
   for(int i=0;i<6;i++)rays[i][indices[i%3]].set(j);
  }
  int y=r,x=0,p=0;int dy[]={-1,0,1,1,0,-1},dx[]={1,2,1,-1,-2,-1};
  for(int side=0;side<6;side++)for(int step=0;step<r;step++,p++){
   for(int i=0;i<6;i++)for(int k=1;k<4*r;k++){
    auto it=find(cells.begin(),cells.end(),make_pair(y+k*dirsY[i],x+k*dirsX[i]));
    if(it!=cells.end()){origins[i][cellAxes[it-cells.begin()][i%3]]=p;break;}
   }
   y+=dy[side];x+=dx[side];
  }
 }
 int setup(const array<int,6>& state){
  int best=6*r;
  for(int flips=0;flips<8;flips++){
   int cost=0;
   for(int i=0;i<6;i++)if(state[i]>=0){
    int j=(flips&(1<<(i%3)))?(i+3)%6:i;
    int d=abs(origins[j][state[i]]-j*r);cost=max(cost,min(d,6*r-d));
   }
   best=min(best,cost);
  }
  return best;
 }
 void bridge(vector<array<int,6>>& route){
  bool changed=true;
  while(changed){
   changed=false;vector<Bits> prefix(route.size()+1),suffix(route.size()+1);
   for(int i=0;i<(int)route.size();i++)prefix[i+1]=prefix[i]|effect(route[i]).made;
   for(int i=(int)route.size()-1;i>=0;i--)suffix[i]=suffix[i+1]|effect(route[i]).made;
   for(int i=1;i+2<(int)route.size()&&!changed;i++)for(int j=min((int)route.size()-1,i+8);j>i+1;j--){
    Bits missing=target&~(prefix[i]|suffix[j]);array<int,6> candidate;bool found=false;
    auto enumerate=[&](auto&& self,int k)->void{
     if(found)return;
     if(k==6){auto e=effect(candidate);if(e.valid&&(missing&~e.made).none())found=true;return;}
     if(route[i-1][k]<0){candidate[k]=-1;self(self,k+1);return;}
     int lo=max(0,max(route[i-1][k],route[j][k])-1),hi=min(n-1,min(route[i-1][k],route[j][k])+1);
     for(int p=lo;p<=hi&&!found;p++){candidate[k]=p;self(self,k+1);}
    };
    enumerate(enumerate,0);
    if(found){route[i]=candidate;route.erase(route.begin()+i+1,route.begin()+j);changed=true;break;}
   }
  }
  shorten(route);
 }
 void shorten(vector<array<int,6>>& route){
  bool changed=true;
  while(changed){
   changed=false;vector<Bits> prefix(route.size()+1),suffix(route.size()+1);
   for(int i=0;i<(int)route.size();i++)prefix[i+1]=prefix[i]|effect(route[i]).made;
   for(int i=(int)route.size()-1;i>=0;i--)suffix[i]=suffix[i+1]|effect(route[i]).made;
   for(int i=0;i<(int)route.size()&&!changed;i++){
    for(int j=min((int)route.size(),i+16);j>i;j--){
     if((prefix[i]|suffix[j])!=target)continue;
     bool adjacent=true;
     if(i>0&&j<(int)route.size())for(int k=0;k<6;k++)if(abs(route[i-1][k]-route[j][k])>1)adjacent=false;
     if(adjacent){route.erase(route.begin()+i,route.begin()+j);changed=true;break;}
    }
   }
  }
 }
 vector<array<int,6>> solve(){
  vector<array<int,6>> best;int bestCost=limit;
  for(int attempt=0;attempt<attempts;attempt++){
   array<int,6> state;for(int i=0;i<6;i++)state[i]=rng()%n;
   array<int,6> inactive{0,1,2,3,4,5};shuffle(inactive.begin(),inactive.end(),rng);
   int off=(attempt%20<1)?4:(attempt%20<5)?3:(attempt%20<10)?2:(attempt%20<15)?1:0;
   for(int j=0;j<off;j++)state[inactive[j]]=-1;
   for(int pass=0;pass<5;pass++){
    array<int,6> order{0,1,2,3,4,5};shuffle(order.begin(),order.end(),rng);
    for(int i:order){if(state[i]<0)continue;double bv=-1e9;int bp=state[i];
     for(int p=0;p<n;p++){state[i]=p;double v=value(state)+(rng()%1000)*0.0003;if(v>bv){bv=v;bp=p;}}
     state[i]=bp;
    }
   }
   auto e=effect(state);if(!e.valid||!e.made.any())continue;
   vector<array<int,6>> route{state};Bits covered=e.made;int stagnant=0;
   unordered_map<unsigned long long,int> visits;visits[key(state)]++;
   int cap=min(bestCost/need, int(target.count()*2+20));
   while(covered!=target&&(int)route.size()<cap){
    array<int,6> candidate=state,next=state;Bits nextMade;double bestScore=-1e20;
    int guide=-1,guideDistance=100000;
    for(int c=0;c<(int)cells.size();c++)if(target[c]&&!covered[c]){
     int d=100000;
     for(int i=0;i<6;i++)if(state[i]>=0)for(int j=i+1;j<6;j++)if(state[j]>=0&&i%3!=j%3)
      d=min(d,max(abs(state[i]-cellAxes[c][i%3]),abs(state[j]-cellAxes[c][j%3])));
     if(d<guideDistance){guideDistance=d;guide=c;}
    }
    // Enumerate one-tick movements; each emitter can stay or move one cell.
    auto enumerate=[&](auto&& self,int i)->void{
     if(i==6){auto f=effect(candidate);if(!f.valid)return;
      auto k=key(candidate);int gain=(f.made&~covered).count();
      double score=gain*100.0+double(f.made.count())*.05-2.0*visits[k]+(rng()%1000)*0.002;
      if(attempt%4&&guide>=0){
       int d=100000;
       for(int a=0;a<6;a++)if(candidate[a]>=0)for(int b=a+1;b<6;b++)if(candidate[b]>=0&&a%3!=b%3)
        d=min(d,max(abs(candidate[a]-cellAxes[guide][a%3]),abs(candidate[b]-cellAxes[guide][b%3])));
       score-=d*(attempt%4);
      }
      if(score>bestScore){bestScore=score;next=candidate;nextMade=f.made;}return;}
     if(state[i]<0){candidate[i]=-1;self(self,i+1);return;}
     for(int p=max(0,state[i]-1);p<=min(n-1,state[i]+1);p++){candidate[i]=p;self(self,i+1);}
    };
    enumerate(enumerate,0);if(bestScore<-1e19)break;
    if(!(nextMade&~covered).any()){if(++stagnant>18)break;}else stagnant=0;
    state=next;covered|=nextMade;route.push_back(state);visits[key(state)]++;
   }
   if(covered!=target)continue;
   shorten(route);
   bridge(route);
   int cost=route.size()*need+min(setup(route.front()),setup(route.back()));
   if(cost<bestCost){bestCost=cost;best=route;}
  }
  return best;
 }
};
int main(int argc,char**argv){
 if(argc!=3)return 1;ifstream in(argv[1]);ofstream out(argv[2]);int total;in>>total;out<<total<<'\n';
 for(int index=0;index<total;index++){
  Search s;in>>s.r>>s.need>>s.limit>>s.m;s.rng.seed(671939+index);s.init();
  vector<pair<int,int>> pat;for(int j=0;j<s.m;j++){int y,x;in>>y>>x;pat.emplace_back(y,x);}
  for(int j=0;j<(int)s.cells.size();j++){
   auto p=s.cells[j];if(find(pat.begin(),pat.end(),p)!=pat.end())s.target.set(j);
   else for(auto q:pat)for(int i=0;i<6;i++)if(q.first+s.dirsY[i]==p.first&&q.second+s.dirsX[i]==p.second)s.skirt.set(j);
  }
  auto route=s.solve();out<<route.size()<<'\n';for(auto p:route){for(auto x:p)out<<x<<' ';out<<'\n';}out.flush();
  if(index%10==9||index+1==total)cout<<index+1<<"/"<<total<<" complete"<<endl;
 }
 return 0;
}
