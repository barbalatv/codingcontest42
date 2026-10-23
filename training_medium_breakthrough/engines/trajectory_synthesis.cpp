#include "geometry_library.hpp"
#include <map>
#include <cmath>
struct PathOption{vector<U> masks;vector<int> actions;int initial;};
vector<PathOption> options[6];vector<int> oldHint;U hintRoot=0;vector<array<int,6>> warmChoices;vector<pair<int,int>> paired[3];
long long checked=0;int desired=1,period=0,lambdaBad=3;
int costMasks(const vector<Effect>&others,int emitter,int idx){U matter=0;int made=0,last=0;const auto&masks=options[emitter][idx].masks;for(int t=0;t<period;t++){U ray=masks[t];U two=others[t].two|(others[t].one&ray),three=others[t].three|(others[t].two&ray);matter=(matter|two)&~three;if((matter&T)==T&&!(matter&F)){made++;last=t+1;matter&=~T;}}
 checked++;if(made==desired&&last==period)return 0;if(made>=desired)return 10+32*abs(made-desired)+period-last+pc(matter&(T|F));return 48*max(0,desired-made-1)+2*pc(T&~matter)+lambdaBad*pc(F&matter);}
vector<Effect> excluding(const array<int,6>&choice,int skip,int skip2=-1){vector<Effect> out(period);for(int t=0;t<period;t++)for(int e=0;e<6;e++)if(e!=skip&&e!=skip2){U ray=options[e][choice[e]].masks[t];out[t].three|=out[t].two&ray;out[t].two|=out[t].one&ray;out[t].one|=ray;}return out;}
int costPair(const vector<Effect>&others,int axis,pair<int,int> op){auto out=others;for(int t=0;t<period;t++){U ray=options[axis+3][op.second].masks[t];out[t].three|=out[t].two&ray;out[t].two|=out[t].one&ray;out[t].one|=ray;}return costMasks(out,axis,op.first);}
int rootDistance(int initial,int e){int p0[6]={0,5*R,4*R,3*R,2*R,R};int d=abs((initial&127)-p0[e]);return min(d,L-d)+int(bool(initial&128));}
vector<vector<int>> templates(int H,mt19937&rng){vector<vector<int>> out;vector<int> path;function<void(int,int,int)> dfs=[&](int t,int net,int parity){if(abs(net)>H-t)return;if(t==H){if(net==0&&!parity)out.push_back(path);return;}for(int op=0;op<4;op++){path.push_back(op);dfs(t+1,net+(op==1?-1:op==2?1:0),parity^(op==3));path.pop_back();}};
 if(H<=6)dfs(0,0,0);else{
  out.push_back(vector<int>(H));for(int k=0;k<180;k++){vector<int> p(H);for(int j=0;j+1<H;j+=2){int op=1+rng()%3;p[j]=op;p[j+1]=op==3?3:3-op;}shuffle(p.begin(),p.end(),rng);out.push_back(p);}
 }
 if(H>5&&out.size()>220){shuffle(out.begin(),out.end(),rng);out.resize(220);}return out;}
vector<int> compressEmitter(int e,int H,int cut){vector<int> ops,times;for(int t=0;t<(int)oldHint.size();t++){int z=(oldHint[t]>>(2*e))&3;if(z){ops.push_back(z);times.push_back(t);}}while((int)ops.size()>H){int j=0;while(j+1<(int)ops.size()&&!((ops[j]==1&&ops[j+1]==2)||(ops[j]==2&&ops[j+1]==1)||(ops[j]==3&&ops[j+1]==3)))j++;if(j+1==(int)ops.size())return {};ops.erase(ops.begin()+j,ops.begin()+j+2);}vector<int> out(H);int prev=-1;for(int j=0;j<(int)ops.size();j++){int ideal=times.size()==ops.size()?times[j]-(times[j]>=cut):j*H/max(1,(int)ops.size());int slot=max(prev+1,min(H-(int)ops.size()+j,ideal));out[slot]=ops[j];prev=slot;}return out;}
void makeOptions(int H,mt19937&rng){auto common=templates(H,rng);for(int amp=1;amp<=H/2;amp++)for(int timing=0;timing<3;timing++){vector<int> p(H);for(int i=0;i<amp;i++){p[i]=1;p[amp+i]=2;}if(H-2*amp>=2&&timing){p[2*amp]=3;p[H-1]=3;}for(int rot=0;rot<H;rot++){common.push_back(p);rotate(p.begin(),p.begin()+1,p.end());}}warmChoices.clear();vector<map<vector<U>,int>> indices(6);
for(int e=0;e<6;e++){map<vector<U>,PathOption> unique;auto scripts=common;for(int cut=0;cut<(int)oldHint.size();cut++){auto p=compressEmitter(e,H,cut);if(!p.empty())scripts.push_back(p);}

 for(int initial=0;initial<L;initial++)for(int active=0;active<2;active++)for(auto&script:scripts){int b=initial+128*active;PathOption op;op.initial=b;op.actions=script;for(int a:script){b=moveByte[e][b][a];op.masks.push_back(rayByte[e][b]);}if(b!=op.initial)continue;auto it=unique.find(op.masks);if(it==unique.end()||rootDistance(op.initial,e)<rootDistance(it->second.initial,e))unique[op.masks]=move(op);}
 options[e].clear();for(auto &[mask,p]:unique){indices[e][mask]=options[e].size();options[e].push_back(move(p));}}
 for(int cut=0;cut<(int)oldHint.size();cut++){array<int,6> warm;bool valid=true;for(int e=0;e<6;e++){auto p=compressEmitter(e,H,cut);if(p.empty()){valid=false;break;}int b=(hintRoot>>(8*e))&255;vector<U> masks;for(int a:p){b=moveByte[e][b][a];masks.push_back(rayByte[e][b]);}auto it=indices[e].find(masks);if(it==indices[e].end()){valid=false;break;}warm[e]=it->second;}if(valid)warmChoices.push_back(warm);}

 for(int axis=0;axis<3;axis++){map<vector<U>,int> other;for(int i=0;i<(int)options[axis+3].size();i++)other[options[axis+3][i].masks]=i;paired[axis].clear();for(int i=0;i<(int)options[axis].size();i++){auto it=other.find(options[axis][i].masks);if(it!=other.end())paired[axis].push_back({i,it->second});}}
}
int main(){ios::sync_with_stdio(false);cin.tie(nullptr);int budget;while(cin>>R>>desired>>period>>budget>>seed0){vector<string> rows(2*R+1);for(auto&s:rows)cin>>s;int nh;cin>>nh>>hintRoot;oldHint.resize(nh);for(int&a:oldHint)cin>>a;auto began=Clock::now();init_geometry(rows,seed0%7);T=target.b[0];F=forbid.b[0];for(int e=0;e<6;e++)for(int a=0;a<2;a++)for(int p=0;p<L;p++){int b=p+128*a;rayByte[e][b]=a?rays[p][e].b[0]:0;moveByte[e][b]={b,(p+L-1)%L+128*a,(p+1)%L+128*a,p+128*(1-a)};}mt19937 rng(seed0);makeOptions(period,rng);auto deadline=Clock::now()+chrono::milliseconds(budget);checked=0;int bestCost=100000,restarts=0;array<int,6> best;bool found=false;
 while(Clock::now()<deadline&&!found){lambdaBad=1+rng()%4;array<int,6> choice;for(int e=0;e<6;e++)choice[e]=rng()%options[e].size();if(!warmChoices.empty()&&rng()%4)choice=warmChoices[rng()%warmChoices.size()];int axis=rng()%3;if(warmChoices.empty()&&!paired[axis].empty()){auto z=paired[axis][rng()%paired[axis].size()];choice[axis]=z.first;choice[axis+3]=z.second;}int stall=0;
 for(int sweep=0;sweep<30&&Clock::now()<deadline;sweep++){
  int previous=costMasks(excluding(choice,0),0,choice[0]);if(previous==0){best=choice;found=true;break;}
  array<int,6> order={0,1,2,3,4,5};shuffle(order.begin(),order.end(),rng);
  for(int e:order){auto other=excluding(choice,e);int selected=choice[e],cost=costMasks(other,e,selected),ties=1;
   for(int o=0;o<(int)options[e].size();o++){if((checked&2047)==0&&Clock::now()>=deadline)break;int v=costMasks(other,e,o);if(v<cost){cost=v;selected=o;ties=1;}else if(v==cost&&rng()%++ties==0)selected=o;if(v==0)break;}
   choice[e]=selected;if(cost==0){best=choice;found=true;break;}
  }if(found)break;
  for(int axis=0;axis<3;axis++){auto other=excluding(choice,axis,axis+3);pair<int,int> selected={choice[axis],choice[axis+3]};int cost=costPair(other,axis,selected),ties=1;for(auto op:paired[axis]){if((checked&2047)==0&&Clock::now()>=deadline)break;int v=costPair(other,axis,op);if(v<cost){cost=v;selected=op;ties=1;}else if(v==cost&&rng()%++ties==0)selected=op;if(v==0)break;}choice[axis]=selected.first;choice[axis+3]=selected.second;if(cost==0){best=choice;found=true;break;}}
  if(found)break;int cost=costMasks(excluding(choice,0),0,choice[0]);if(cost<bestCost){bestCost=cost;best=choice;}if(cost>=previous)stall++;else stall=0;
  if(stall>=1&&cost<=6){
   for(int e=0;e<6&&!found&&Clock::now()<deadline;e++)for(int j=e+1;j<6&&!found&&Clock::now()<deadline;j++)if(j!=e+3){
    auto other=excluding(choice,e,j);vector<pair<int,int>> xx,yy;
    auto oe=other,oj=other;for(int t=0;t<period;t++){U re=options[e][choice[e]].masks[t],rj=options[j][choice[j]].masks[t];oe[t].three|=oe[t].two&rj;oe[t].two|=oe[t].one&rj;oe[t].one|=rj;oj[t].three|=oj[t].two&re;oj[t].two|=oj[t].one&re;oj[t].one|=re;}
    for(int a=0;a<(int)options[e].size();a++)xx.push_back({costMasks(oe,e,a),a});for(int b=0;b<(int)options[j].size();b++)yy.push_back({costMasks(oj,j,b),b});shuffle(xx.begin(),xx.end(),rng);shuffle(yy.begin(),yy.end(),rng);stable_sort(xx.begin(),xx.end(),[](auto&a,auto&b){return a.first<b.first;});stable_sort(yy.begin(),yy.end(),[](auto&a,auto&b){return a.first<b.first;});xx.resize(min(96,(int)xx.size()));yy.resize(min(96,(int)yy.size()));
    for(auto xb:xx){if(Clock::now()>=deadline)break;for(auto yb:yy){auto tmp=other;for(int t=0;t<period;t++){U ray=options[j][yb.second].masks[t];tmp[t].three|=tmp[t].two&ray;tmp[t].two|=tmp[t].one&ray;tmp[t].one|=ray;}int v=costMasks(tmp,e,xb.second);if(v<cost){choice[e]=xb.second;choice[j]=yb.second;cost=v;}if(v==0){best=choice;found=true;break;}}if(found)break;}
   }
  }
  if(found)break;if(cost<bestCost){bestCost=cost;best=choice;}if(stall>=2){for(int n=0;n<2+rng()%2;n++){int e=rng()%6;choice[e]=rng()%options[e].size();}stall=0;}
 }
 restarts++;}
 vector<int> program;U root=0;if(found){program.resize(period);for(int e=0;e<6;e++){auto &p=options[e][best[e]];root|=U(p.initial)<<(8*e);for(int t=0;t<period;t++)program[t]|=p.actions[t]<<(2*e);}Node st;st.pose=root;for(int a:program)st=step(st,a);if(st.made!=desired||st.pose!=root||st.m){program.clear();found=false;}}
 auto ms=chrono::duration_cast<chrono::milliseconds>(Clock::now()-began).count();cout<<program.size()<<' '<<bestCost<<' '<<ms<<' '<<root<<' '<<checked<<' '<<restarts;for(int a:program)cout<<' '<<a;U nearRoot=0;vector<int> nearProgram(period);if(bestCost<100000||found){for(int e=0;e<6;e++){auto&p=options[e][best[e]];nearRoot|=U(p.initial)<<(8*e);for(int t=0;t<period;t++)nearProgram[t]|=p.actions[t]<<(2*e);}}cout<<' '<<nearRoot;for(int a:nearProgram)cout<<' '<<a;cout<<'\n'<<flush;
 }}
