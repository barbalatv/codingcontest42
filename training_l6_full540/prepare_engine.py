from common import *
from build import build
s=(BASE/'engines/physics_search_base.cpp').read_text()
s=s.replace('#include <iostream>','#include <iostream>\n#include <ctime>')
s=s.replace('int R,L,W,NT,K,H,WIDTH,MODE,SEED;','int expandedDepth=0;\nint R,L,W,NT,K,H,WIDTH,MODE,SEED;')
hook='void recordPartialDiscovery(const State&,int,const vector<int>&);\n'
pos=s.index('void captureNear(');s=s[:pos]+hook+s[pos:]
s=s.replace('void captureNear(const State&s,int parent,const vector<int>&seq){','void captureNear(const State&s,int parent,const vector<int>&seq){recordPartialDiscovery(s,parent,seq);')
s=s.replace('for(int t=0;t<H&&Clock::now()<deadline;t++){','for(int t=0;t<H&&Clock::now()<deadline;t++){expandedDepth=max(expandedDepth,t);')
s=s.replace('int main(){','#include "pure_engine.hpp"\nint main(){',1)
s=s.replace('L=6*R;if(W<1||W>MW||L>128)return 2;','L=6*R;if(W<1||W>MW||L>128||H<0||H>256||WIDTH<1||WIDTH>128)return 2;')
s=s.replace('rng.seed(SEED);evaluations=', 'expandedDepth=0;pureEdges.clear();pureEdgeKeys.clear();independentBirth.clear();birthConflicts=0;birthAttempts=0;clock_t cpuBegin=clock();rng.seed(SEED);evaluations=')
s=s.replace('if(MODE==10)libraryScheduling();','if(MODE==11||MODE==12)pureSynthesis(hint,MODE==12);else if(MODE==10)libraryScheduling();')
s=s.replace("for(int a:nearProgram)cout<<' '<<a;cout<<'\\n'<<flush;", "for(int a:nearProgram)cout<<' '<<a;cout<<' '<<1000000LL*(clock()-cpuBegin)/CLOCKS_PER_SEC<<' '<<expandedDepth<<' '<<birthConflicts<<' '<<birthAttempts<<' '<<(Clock::now()>=deadline)<<' '<<independentBirth.size();for(int a:independentBirth)cout<<' '<<a;cout<<' '<<pureEdges.size();for(auto&e:pureEdges){cout<<' '<<e.pose<<' '<<e.copies<<' '<<e.program.size();for(int a:e.program)cout<<' '<<a;}cout<<'\\n'<<flush;")
(BASE/'engines/cellfirst.cpp').write_text(s)
assert 'cpuBegin' in s and 'pureSynthesis(hint' in s
build('cellfirst.cpp')
