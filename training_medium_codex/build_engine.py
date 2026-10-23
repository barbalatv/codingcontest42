from pathlib import Path
p=Path('training_medium_codex/engines/acceptance_tail.cpp');s=Path('repair.cpp').read_text();s=s.replace('start_state.pose=rootpose;','start_state.pose=rootpose;\n        for(int w=0;w<W_words;w++)cin>>start_state.matter.b[w];');s=s.replace('int cut=rng()%ans.size();','int cut=rng()%ans.size(); /* Cross-acceptance neighborhoods start from actual material. */');p.write_text(s)

