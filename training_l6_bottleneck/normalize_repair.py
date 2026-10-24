"""Explicitly attribute beam-prefix repair to its actual control/treatment source."""
from common_bn import *
def main():
    path=BASE/'experiments/repair/selection.json'
    if not path.exists():return
    sources={}
    for x in json.loads(path.read_text()):
        upstream=json.loads((BASE/x['source']).read_text())
        r=next(r for r in upstream['rows'] if r['method']==x['method'])
        sources[x['case']]=dict(prefix_source_method=r['method'],prefix_source_weighted=bool(r.get('weights')),prefix_source_record=x['source'])
    for f in (BASE/'experiments/repair').glob('case_*.json'):
        x=json.loads(f.read_text());src=sources[x['case']]
        for r in x['rows']:
            r.update(src)
            if 'beam_plus_LNS' in r['method']:
                new='weighted_beam_plus_LNS' if src['prefix_source_weighted'] else 'standard_beam_plus_LNS'
                if new!=r['method']:r['original_method_label']=r['method'];r['method']=new
        atomic_json(f,x)
    for f in (BASE/'checkpoints').glob('*.json'):
        x=json.loads(f.read_text())
        if 'beam_plus_LNS' not in x.get('method',''):continue
        src=sources[x['case']];x.update(src);new='weighted_beam_plus_LNS' if src['prefix_source_weighted'] else 'standard_beam_plus_LNS'
        if new!=x['method']:x['original_method_label']=x['method'];x['method']=new
        atomic_json(f,x)
    print('Repair prefix attribution preserved:',sources)
if __name__=='__main__':main()
