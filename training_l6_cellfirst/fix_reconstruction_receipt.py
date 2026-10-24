from common import *
p=BASE/'experiments/source_reconstruction.json';s=json.loads(p.read_text())
s.pop('cellfirst_stage_a.exe',None)
s['stage_a']={'status':'RECONSTRUCTED_SOURCE','original_binary_code_hash_comparison':'NOT_AVAILABLE'}
atomic_json(p,s)
