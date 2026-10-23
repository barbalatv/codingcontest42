from pathlib import Path
p=Path('training_medium_codex/compare_traces.py');s=p.read_text().replace('states.append(dict(accepted=ss[3],','states.append(dict(positions=ss[0],accepted=ss[3],');p.write_text(s)
p=Path('training_medium_codex/compare_traces.cjs');s=p.read_text().replace('const e=ex.states[t];','const e=ex.states[t];assert.equal(JSON.stringify(s.emitter.indices.map(v=>(s.emitter.perimeter.length-v)%s.emitter.perimeter.length)),JSON.stringify(e.positions));');p.write_text(s)
