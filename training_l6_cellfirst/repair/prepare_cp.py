from pathlib import Path
base=Path(__file__).resolve().parents[1];repo=base.parent
# Reuse the already exact matter/iff-acceptance model, isolated from its old
# output-mutating functions. The original source remains unchanged.
source=(repo/'training_medium_codex/exact_acceptance.py').read_text()
begin=source.index('def synth(');end=source.index('\ndef update(',begin)
function=source[begin:end]
function=function.replace('root_radius=0):','root_radius=0,free_slots=None):')
function=function.replace("if free and e not in free:m.add(v==old[0][e]+L*((old[1]>>e)&1))", "if (free and e not in free) or (free_slots is not None and (t,e) not in free_slots):m.add(v==old[0][e]+L*((old[1]>>e)&1))")
# A bounded subproblem, not a naive all-dataset CP model.
function=function.replace('solver.parameters.num_search_workers=4','solver.parameters.num_search_workers=2')
function=function.replace('status=solver.solve(m);prog=None','solver.parameters.max_memory_in_mb=1024\n status=solver.solve(m);prog=None')
(base/'repair/exact_model.py').write_text('from common import *\nfrom ortools.sat.python import cp_model\nfrom solve_l6 import delta\n'+function)
