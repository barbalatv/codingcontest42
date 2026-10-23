#include <iostream>
#include <vector>
#include <algorithm>
#include <cstdint>
using namespace std;

int main(){
  ios::sync_with_stdio(false);cin.tie(nullptr);
  int n0,n1,allowed;
  while(cin>>n0>>n1>>allowed){
    vector<int> need[2];need[0].resize(n0);need[1].resize(n1);
    for(int &x:need[0])cin>>x;
    for(int &x:need[1])cin>>x;
    bool live0=any_of(need[0].begin(),need[0].end(),[](int x){return x!=0;});
    bool live1=any_of(need[1].begin(),need[1].end(),[](int x){return x!=0;});
    int total=n0*n1*256;
    vector<int> parent(total,-2),queue;queue.reserve(total);
    vector<uint8_t> actions(total);
    auto encode=[&](int p0,int p1,int c0,int c1,int rows,int scans){
      return (((((p0*n1+p1)*4+c0)*4+c1)*4+rows)*4+scans);
    };
    int root=encode(0,0,0,0,0,0);parent[root]=-1;queue.push_back(root);
    int goal=-1;
    for(size_t head=0;head<queue.size()&&goal<0;head++){
      int old=queue[head],code=old;
      int scans=code%4;code/=4;int rows=code%4;code/=4;
      int c1=code%4;code/=4;int c0=code%4;code/=4;
      int p1=code%n1,p0=code/n1;
      if(p0==n0-1&&p1==n1-1&&c0==need[0][p0]&&c1==need[1][p1]){goal=old;break;}
      for(int a0=0;a0<3;a0++)for(int a1=0;a1<3;a1++){
        if(a0==1&&(p0+1>=n0||c0!=need[0][p0]))continue;
        if(a1==1&&(p1+1>=n1||c1!=need[1][p1]))continue;
        int q0=p0+(a0==1),q1=p1+(a1==1);
        int cc0=a0==1?0:c0,cc1=a1==1?0:c1;
        int ss=scans^((a0==2)?1:0)^((a1==2)?2:0);
        if((!live0&&(ss&1))||(!live1&&(ss&2)))continue;
        for(int rr=0;rr<4;rr++){
          if(rr&~allowed)continue;
          if((ss&1)&&(rr&~need[0][q0]))continue;
          if((ss&2)&&(rr&~need[1][q1]))continue;
          int nc0=cc0|((ss&1)?rr:0),nc1=cc1|((ss&2)?rr:0);
          int next=encode(q0,q1,nc0,nc1,rr,ss);
          if(parent[next]!=-2)continue;
          parent[next]=old;actions[next]=uint8_t(rr*9+a0*3+a1);queue.push_back(next);
        }
      }
    }
    if(goal<0){cout<<"-1\n"<<flush;continue;}
    vector<int> result;
    for(int p=goal;parent[p]!=-1;p=parent[p])result.push_back(actions[p]);
    reverse(result.begin(),result.end());
    cout<<result.size();for(int x:result)cout<<' '<<x;cout<<'\n'<<flush;
  }
}
