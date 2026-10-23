from pathlib import Path
src=Path('training_medium_codex/engines/acceptance_tail.cpp').read_text()
src=src.replace('int wanted=1;','int wanted=1;\nuint64_t bridge_goal=~uint64_t(0);\nint allowed_emitters[3]={0,1,2},n_allowed=6;\nint pose_cost(uint64_t a,uint64_t b){int d=0;for(int e=0;e<6;e++){int p=(a>>(8*e))&127,q=(b>>(8*e))&127;int v=abs(p-q);d+=min(v,L_perim-v)+int(((a^b)>>(8*e+7))&1);}return d;}')
src=src.replace('if(st.accepted>=wanted){if(first)*first=t+1;return 0;}','if(st.accepted>=wanted){if(first)*first=t+1;if(bridge_goal==~uint64_t(0)||st.pose==bridge_goal)return 0;return 1+pose_cost(st.pose,bridge_goal);}')
src=src.replace('int cut=rng()%ans.size();', 'n_allowed=2+rng()%2;for(int j=0;j<n_allowed;j++)allowed_emitters[j]=rng()%6;\n   int cut=rng()%ans.size();')
src=src.replace('int e=rng()%6;int a;', 'int e=(rounds%3==0)?rng()%6:allowed_emitters[rng()%n_allowed];int a;')
src=src.replace('int budget, seed; cin >> budget >> seed;', 'int budget, seed; cin >> budget >> seed >> bridge_goal;')
Path('training_medium_codex_v2/engines/edge_search.cpp').write_text(src)
