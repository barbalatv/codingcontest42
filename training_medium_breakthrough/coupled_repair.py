from pathlib import Path
p=Path('training_medium_breakthrough/engines/trajectory_synthesis.cpp');s=p.read_text()
old='if(cost>=previous)stall++;else stall=0;if(stall>=2){'
new='''if(cost<bestCost){bestCost=cost;best=choice;}if(cost>=previous)stall++;else stall=0;
  if(stall>=1&&cost<=6){
   for(int e=0;e<6&&!found&&Clock::now()<deadline;e++)for(int j=e+1;j<6&&!found&&Clock::now()<deadline;j++)if(j!=e+3){
    auto other=excluding(choice,e,j);vector<pair<int,int>> xx,yy;
    auto oe=other,oj=other;for(int t=0;t<period;t++){U re=options[e][choice[e]].masks[t],rj=options[j][choice[j]].masks[t];oe[t].three|=oe[t].two&rj;oe[t].two|=oe[t].one&rj;oe[t].one|=rj;oj[t].three|=oj[t].two&re;oj[t].two|=oj[t].one&re;oj[t].one|=re;}
    for(int a=0;a<(int)options[e].size();a++)xx.push_back({costMasks(oe,e,a),a});for(int b=0;b<(int)options[j].size();b++)yy.push_back({costMasks(oj,j,b),b});shuffle(xx.begin(),xx.end(),rng);shuffle(yy.begin(),yy.end(),rng);stable_sort(xx.begin(),xx.end(),[](auto&a,auto&b){return a.first<b.first;});stable_sort(yy.begin(),yy.end(),[](auto&a,auto&b){return a.first<b.first;});xx.resize(min(96,(int)xx.size()));yy.resize(min(96,(int)yy.size()));
    for(auto xb:xx){if(Clock::now()>=deadline)break;for(auto yb:yy){auto tmp=other;for(int t=0;t<period;t++){U ray=options[j][yb.second].masks[t];tmp[t].three|=tmp[t].two&ray;tmp[t].two|=tmp[t].one&ray;tmp[t].one|=ray;}int v=costMasks(tmp,e,xb.second);if(v<cost){choice[e]=xb.second;choice[j]=yb.second;cost=v;}if(v==0){best=choice;found=true;break;}}if(found)break;}
   }
  }
  if(found)break;if(cost<bestCost){bestCost=cost;best=choice;}if(stall>=2){'''
s=s.replace(old,new)
s=s.replace('bestCost=min(bestCost,cost);if(cost<bestCost)', 'if(cost<bestCost)')
s=s.replace("for(int a:program)cout<<' '<<a;cout<<'\\n'<<flush;", "for(int a:program)cout<<' '<<a;U nearRoot=0;vector<int> nearProgram(period);if(bestCost<100000||found){for(int e=0;e<6;e++){auto&p=options[e][best[e]];nearRoot|=U(p.initial)<<(8*e);for(int t=0;t<period;t++)nearProgram[t]|=p.actions[t]<<(2*e);}}cout<<' '<<nearRoot;for(int a:nearProgram)cout<<' '<<a;cout<<'\\n'<<flush;")
p.write_text(s)
# Reader stores nonzero-defect candidates for a genuinely local exact repair.
p=Path('training_medium_breakthrough/synthesis_experiment.py');s=p.read_text().replace('prog=actions(out[6:]);assert len(prog)==out[0];','prog=actions(out[6:6+out[0]]);assert len(prog)==out[0];\n    near_start=6+out[0];near_root=out[near_start];near_program=actions(out[near_start+1:]);\n    (BASE/\'experiments\'/f\'near_case{idx}_h{H}_c{copies}_s{seed}.json\').write_text(json.dumps(dict(case=idx,root=near_root,copies=copies,program=near_program,seed=seed,defect=out[1])))\n    ')
p.write_text(s)
