"""Generate isolated reference and weighted engines from preserved source bytes."""
from common_bn import *
import shutil
def replace_once(s,a,b):
    assert s.count(a)==1,(a,s.count(a)); return s.replace(a,b)
def main():
    src=REPO/'training_l6_full540/engines/cellfirst_v2.cpp'
    shutil.copyfile(src,BASE/'archive/cellfirst_v2.cpp')
    shutil.copyfile(REPO/'training_l6_full540/engines/pure_engine.hpp',BASE/'archive/pure_engine.hpp')
    s=src.read_text()
    s=s.replace('#include <iostream>','#include <iostream>\n#include <sstream>\n#include <string>\n#include <stdexcept>')
    s=s.replace('Clock::time_point deadline;','long long evalLimit=0; int weightMode=0,localCap=0,scoreTick=0; vector<pair<int,int>> weights;\nClock::time_point deadline;')
    s=s.replace('vector<History> history;','vector<History> history; U selectionDigest=0,configDigest=0;')
    s=s.replace('out.push_back(move(n));}pool=move(out);','selectionDigest=mix(selectionDigest^fingerprint(n.s)^U(n.score));out.push_back(move(n));}pool=move(out);')
    s=s.replace(' return out;}\nvector<int> schedule',' for(U q:out)configDigest=mix(configDigest^q);return out;}\nvector<int> schedule')
    s=s.replace('expandedDepth=0;pureEdges.clear();','selectionDigest=configDigest=0;expandedDepth=0;pureEdges.clear();')
    s=s.replace("for(int a:e.program)cout<<' '<<a;}cout<<'\\n'<<flush;", "for(int a:e.program)cout<<' '<<a;}cout<<' '<<selectionDigest<<' '<<configDigest<<'\\n'<<flush;")
    s=s.replace('U mix(U x)', 'bool expired(){return evalLimit>0?evaluations>=evalLimit:Clock::now()>=deadline;}\nU mix(U x)')
    s=s.replace('Clock::now()>=deadline','expired()').replace('Clock::now()<deadline','!expired()')
    s=s.replace('return evalLimit>0?evaluations>=evalLimit:expired();','return evalLimit>0?evaluations>=evalLimit:Clock::now()>=deadline;')
    s=s.replace('expandedDepth=max(expandedDepth,t);','expandedDepth=max(expandedDepth,t);scoreTick=t;')
    old='int main(){ios::sync_with_stdio(false);cin.tie(nullptr);int ms;while(cin>>R>>W>>NT>>K>>H>>WIDTH>>ms>>SEED>>MODE>>startState.pose>>goalPose){'
    new='''int main(){ios::sync_with_stdio(false);std::cin.tie(nullptr);int ms;string frame;while(getline(std::cin,frame)){
 istringstream cin(frame);string version;cin>>version;
 if(version!="BN1"){cout<<"ERR VERSION\\n"<<flush;continue;}
 if(!(cin>>R>>W>>NT>>K>>H>>WIDTH>>ms>>SEED>>MODE>>startState.pose>>goalPose)){cout<<"ERR HEADER\\n"<<flush;continue;}'''
    s=replace_once(s,old,new)
    s=s.replace('return 2;','{cout<<"ERR LIMIT\\n"<<flush;continue;}')
    s=s.replace('L=6*R;if(W<1','L=6*R;if(R<1||ms<0||ms>120000||K<1||K>256||W<1')
    old='int n;cin>>n;vector<int>hint(n);for(int&a:hint)cin>>a;cin>>n;referencePoses.resize(n);for(U&p:referencePoses)cin>>p;'
    new='''int n=0;cin>>n;if(n<0||n>1024){cout<<"ERR HINT\\n"<<flush;continue;}vector<int>hint(n);for(int&a:hint)cin>>a;cin>>n;if(n<0||n>1024){cout<<"ERR REFS\\n"<<flush;continue;}referencePoses.resize(n);for(U&p:referencePoses)cin>>p;
 int nw=-1;cin>>weightMode>>localCap>>evalLimit>>nw;weights.clear();bool bad=!cin||nw<0||nw>W*64||weightMode<0||weightMode>3||localCap<0||evalLimit<0;unordered_set<int>seenWeights;
 for(int j=0;j<max(0,min(nw,W*64));j++){int c=-1,v=-1;cin>>c>>v;if(!cin||c<0||c>=W*64||v<100||v>500||!isset(target,c)||!seenWeights.insert(c).second)bad=true;else if(v!=100)weights.push_back({c,v-100});}
 string extra;if(!cin||cin>>extra)bad=true;
 for(int a:hint)if(a<0||a>4095)bad=true;
 for(int e=0;e<6;e++)if(((startState.pose>>(8*e))&127)>=L)bad=true;
 if(bad){cout<<"ERR PAYLOAD\\n"<<flush;continue;}'''
    s=replace_once(s,old,new)
    # Audit mode returns original scores and complete physics for a supplied trace.
    marker=' if(MODE==9){'
    audit=''' if(MODE==90){State s=startState;cout<<hint.size();for(int a:hint){s=step(s,a);cout<<' '<<stateScore(s,SEED)<<' '<<snapshotScore(s,s.pose)<<' '<<s.pose<<' '<<s.made;for(int w=0;w<W;w++)cout<<' '<<s.m.b[w];}cout<<'\\n'<<flush;continue;}
'''
    s=replace_once(s,marker,audit+marker)
    header=(BASE/'archive/pure_engine.hpp').read_text().replace('Clock::now()>=deadline','expired()').replace('Clock::now()<deadline','!expired()')
    (BASE/'engines/pure_engine.hpp').write_text(header)
    (BASE/'engines/reference_beam.cpp').write_text(s)
    helper='''// Additional fixed-point deficit only. All-100 is exactly zero.
int phase(const State&s){if(weightMode==0)return 100;if(weightMode==1)return min(100,100*(scoreTick+1)/max(1,H));if(weightMode==2)return max(0,min(100,200*(scoreTick+1)/max(1,H)-100));int good=0;for(int w=0;w<W;w++)good+=pc(s.m.b[w]&target.b[w]);return 25+75*good/max(1,NT);}
int stateDelta(const State&s){if(weights.empty())return 0;int total=0,filled=0;for(auto[c,d]:weights){total+=d;if(isset(s.m,c))filled+=d;}return 2*(s.made*total+filled-total)*phase(s)/100;}
int snapshotDelta(const State&s,U pose){if(weights.empty())return 0;auto v=effect(pose);int delta=0;for(auto[c,raw]:weights){int d=localCap?min(raw,max(0,localCap-100)):raw;bool old=isset(s.m,c),three=isset(v.three,c),two=isset(v.two,c)&&!three;delta+=two&&!old?d:0;delta-=three&&old?d*85/100:0;delta-=three?d*8/100:0;}return delta*phase(s)/100;}
'''
    s=replace_once(s,'int stateScore(',helper+'int stateScore(')
    s=replace_once(s,'return score;}\nvoid keep','return score+stateDelta(s);}\nvoid keep')
    s=replace_once(s,'pc(v.three.b[w]&target.b[w])*8;}return score;}', 'pc(v.three.b[w]&target.b[w])*8;}return score+snapshotDelta(s,pose);}')
    s=replace_once(s,'if(goalPose!=UINT64_MAX)n.score-=distance(s.pose,goalPose)*28;keep','n.score+=stateDelta(s);if(goalPose!=UINT64_MAX)n.score-=distance(s.pose,goalPose)*28;keep')
    # Geometry configurations remain sampled from unmet cells, then ranked with
    # snapshotDelta. Candidate pruning consumes the corresponding weighted score.
    (BASE/'engines/bottleneck_beam.cpp').write_text(s)
    print('Generated isolated engines from',sha(src))
if __name__=='__main__':main()
