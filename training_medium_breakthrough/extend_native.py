from pathlib import Path
p=Path('training_medium_breakthrough/engines/geometry_search.cpp');s=p.read_text()
s=s.replace('int C,seed0;', 'int C,seed0;vector<pair<U,vector<int>>> discoveries;unordered_set<U> discoveredPoses;int goalDistances[8][6][256];')
s=s.replace('if(goalPose!=UINT64_MAX)score-=pdist(s.pose,goalPose)*(s.made+1==C?32:10);', 'if(goalPose!=UINT64_MAX){int best=100;for(int mask=0;mask<8;mask++){int d=0;for(int e=0;e<6;e++)d=max(d,goalDistances[mask][e][(s.pose>>(8*e))&255]);best=min(best,d);}score-=best*(s.made+1==C?32:10);}')
s=s.replace('answerCopies=s.made;}return true;', 'answerCopies=s.made;}U canon=canonical(s.pose);if(discoveries.size()<24&&discoveredPoses.insert(canon).second)discoveries.push_back({s.pose,vector<int>(p.begin(),p.begin()+t)});return true;')
s=s.replace('if(!answer.empty()&&t+1>=(int)answer.size())break;', '// Continue at equal/larger horizon to retain alternative acceptance poses.')
s=s.replace('gen.seed(seed0);visitedN=bridgeN=0;', 'for(int mask=0;mask<8;mask++){U q=transformPose(goalPose==UINT64_MAX?rootPose:goalPose,mask);for(int e=0;e<6;e++)for(int a=0;a<2;a++)for(int p=0;p<L;p++){int v=(q>>(8*e))&255,d=min((p-(v&127)+L)%L,((v&127)-p+L)%L)+int(a!=bool(v&128));goalDistances[mask][e][p+128*a]=d;}}gen.seed(seed0);visitedN=bridgeN=0;discoveries.clear();discoveredPoses.clear();')
s=s.replace("for(int a:answer)cout<<' '<<a;cout<<'\\n'<<flush;", "for(int a:answer)cout<<' '<<a;cout<<' '<<discoveries.size();for(auto &d:discoveries){cout<<' '<<d.second.size()<<' '<<d.first;for(int a:d.second)cout<<' '<<a;}cout<<'\\n'<<flush;")
s=s.replace('if(seen.count(hash))continue;\n z.score=', 'if(!seen.insert(hash).second)continue;\n z.score=')
# Structural endpoint candidates: aligned opposing beams plus 4 masks, built
# independently of current incumbent endpoints, kept only if last-tick valid.
s=s.replace('void meetSearch(const vector<U>&ends,int horizon,int variant){vector<Back> beam;for(U end:ends)', '''vector<U> geometricEnds(const vector<U>&refs){vector<pair<int,U>> pool;unordered_set<U> used;
 for(int axis=0;axis<3;axis++)for(int p=0;p<L;p++){
  U chord=rays[p][axis].b[0];if(!(chord&T))continue;int q=((3-2*axis)*R-p+2*L)%L;int clip[4],nc=0;for(int e=0;e<6;e++)if(e!=axis&&e!=axis+3)clip[nc++]=e;
  vector<int> opts[4];for(int j=0;j<4;j++){int e=clip[j];opts[j].push_back((refs.empty()?0:(refs[0]>>(8*e))&127));for(int v=0;v<L;v++)if(rays[v][e].b[0]&&!(rays[v][e].b[0]&chord&T))opts[j].push_back(v+128);}
  U base=(U(p+128)<<(8*axis))|(U(q+128)<<(8*(axis+3)));
  for(int a:opts[0])for(int b:opts[1])for(int c:opts[2])for(int d:opts[3]){U pose=base|(U(a)<<(8*clip[0]))|(U(b)<<(8*clip[1]))|(U(c)<<(8*clip[2]))|(U(d)<<(8*clip[3]));Effect z=effect(pose);if((z.three&T)|((z.two&~z.three)&F))continue;U can=canonical(pose);if(!used.insert(can).second)continue;int score=pc(z.two&~z.three&T)*128+pc(z.three&F)*24-pdist(pose,rootPose)*12;pool.push_back({score,pose});}
 }
 sort(pool.rbegin(),pool.rend());vector<U> result=refs;for(int i=0;i<min(64,(int)pool.size());i++)result.push_back(pool[i].second);return result;
}
void meetSearch(const vector<U>&inputEnds,int horizon,int variant){auto ends=geometricEnds(inputEnds);vector<Back> beam;for(U end:ends)''')
p.write_text(s)
