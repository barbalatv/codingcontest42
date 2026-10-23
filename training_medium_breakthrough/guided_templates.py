from pathlib import Path
p=Path('training_medium_breakthrough/engines/trajectory_synthesis.cpp');s=p.read_text()
s=s.replace('vector<PathOption> options[6];', 'vector<PathOption> options[6];vector<int> oldHint;U hintRoot=0;vector<array<int,6>> warmChoices;')
s=s.replace('void makeOptions(int H,mt19937&rng){auto scripts=templates(H,rng);for(int e=0;e<6;e++){map<vector<U>,PathOption> unique;', '''vector<int> compressEmitter(int e,int H,int cut){vector<int> ops,times;for(int t=0;t<(int)oldHint.size();t++){int z=(oldHint[t]>>(2*e))&3;if(z){ops.push_back(z);times.push_back(t);}}while((int)ops.size()>H){int j=0;while(j+1<(int)ops.size()&&!((ops[j]==1&&ops[j+1]==2)||(ops[j]==2&&ops[j+1]==1)||(ops[j]==3&&ops[j+1]==3)))j++;if(j+1==(int)ops.size())return {};ops.erase(ops.begin()+j,ops.begin()+j+2);}vector<int> out(H);int prev=-1;for(int j=0;j<(int)ops.size();j++){int ideal=times.size()==ops.size()?times[j]-(times[j]>=cut):j*H/max(1,(int)ops.size());int slot=max(prev+1,min(H-(int)ops.size()+j,ideal));out[slot]=ops[j];prev=slot;}return out;}
void makeOptions(int H,mt19937&rng){auto common=templates(H,rng);for(int amp=1;amp<=H/2;amp++)for(int timing=0;timing<3;timing++){vector<int> p(H);for(int i=0;i<amp;i++){p[i]=1;p[amp+i]=2;}if(H-2*amp>=2&&timing){p[2*amp]=3;p[H-1]=3;}for(int rot=0;rot<H;rot++){common.push_back(p);rotate(p.begin(),p.begin()+1,p.end());}}warmChoices.clear();vector<map<vector<U>,int>> indices(6);
for(int e=0;e<6;e++){map<vector<U>,PathOption> unique;auto scripts=common;for(int cut=0;cut<(int)oldHint.size();cut++){auto p=compressEmitter(e,H,cut);if(!p.empty())scripts.push_back(p);}
''')
s=s.replace('options[e].clear();for(auto &[mask,p]:unique)options[e].push_back(move(p));}', '''options[e].clear();for(auto &[mask,p]:unique){indices[e][mask]=options[e].size();options[e].push_back(move(p));}}
 for(int cut=0;cut<(int)oldHint.size();cut++){array<int,6> warm;bool valid=true;for(int e=0;e<6;e++){auto p=compressEmitter(e,H,cut);if(p.empty()){valid=false;break;}int b=(hintRoot>>(8*e))&255;vector<U> masks;for(int a:p){b=moveByte[e][b][a];masks.push_back(rayByte[e][b]);}auto it=indices[e].find(masks);if(it==indices[e].end()){valid=false;break;}warm[e]=it->second;}if(valid)warmChoices.push_back(warm);}
''')
s=s.replace('for(auto&s:rows)cin>>s;auto began=', 'for(auto&s:rows)cin>>s;int nh;cin>>nh>>hintRoot;oldHint.resize(nh);for(int&a:oldHint)cin>>a;auto began=')
s=s.replace('int axis=rng()%3;if(!paired[axis].empty())', 'if(!warmChoices.empty()&&rng()%4)choice=warmChoices[rng()%warmChoices.size()];int axis=rng()%3;if(warmChoices.empty()&&!paired[axis].empty())')
p.write_text(s)
# A separate coordinator reads actual closed multi-copy incumbent windows.
p=Path('training_medium_breakthrough/synthesis_experiment.py');s=p.read_text();s=s.replace("before=len(load_programs(BASE/'best'/NAME)[i]);seed=", "before=len(load_programs(BASE/'best'/NAME)[i]);seed=")
s=s.replace("data=f'{c[0]} {copies} {H} {args.ms} {seed}\\n{board(c)}\\n';", "hint=[];hintroot=key(ss[aa[0]])\n    for ja,a in enumerate(aa):\n     if ja+copies>=len(aa):continue\n     b=aa[ja+copies]\n     if b-a==H+1 and ss[a][:2]==ss[b][:2]:hint=best[a:b];hintroot=key(ss[a]);break\n    data=f'{c[0]} {copies} {H} {args.ms} {seed}\\n{board(c)}\\n{len(hint)} {packed(hintroot)}\\n'+' '.join(str(sum('-FBT'.index(ch)<<(2*e) for e,ch in enumerate(row))) for row in hint)+'\\n';")
p.write_text(s)
