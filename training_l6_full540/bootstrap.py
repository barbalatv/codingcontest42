from pathlib import Path
import sys,shutil
sys.dont_write_bytecode=True
B=Path(__file__).resolve().parent;R=B.parent;OLD=R/'training_l6_cellfirst'
for d in ['baseline','best','engines','cellfirst','hybrid','repair','edges','experiments','checkpoints','experiments/pass1','experiments/pass2','experiments/pure_birth']:(B/d).mkdir(parents=True,exist_ok=True)
for f in ['common.py','native.py','validate_sandbox.cjs','build.py','test_native.py','compare_traces.cjs']:
    target=B/f
    if not target.exists():shutil.copyfile(OLD/f,target)
shutil.copyfile(OLD/'repair/exact_model.py',B/'repair/exact_model.py')
s=(B/'common.py').read_text();s=s.replace('from pathlib import Path','import sys\nsys.dont_write_bytecode=True\nfrom pathlib import Path',1).replace("BASE/'results.csv'","BASE/'improvements.csv'")
(B/'common.py').write_text(s)
shutil.copyfile(OLD/'scheduler/graph_adapter.py',B/'hybrid/graph_adapter.py')
shutil.copyfile(OLD/'engines/cellfirst_discover.cpp',B/'engines/physics_search_base.cpp')
print('ISOLATED_RUNTIME_READY',B)
