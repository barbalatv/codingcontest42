"""Retain old metrics while correcting pickup-reset attribution in early logs."""
from diagnostics import *
def main():
    changed=0;checked=0
    for f in (BASE/'experiments').glob('*/case_*.json'):
        x=json.loads(f.read_text());dirty=False
        for r in x.get('rows',[]):
            if not r.get('near_program') or not r.get('context'):continue
            ctx=r['context'];st=(tuple(ctx['start'][0]),*ctx['start'][1:]);d=near_diagnostics(cases('enormous')[r['case']-1],r['near_program'],st);d['required_copies']=ctx['copies'];checked+=1
            old=r.get('near_diagnostics')
            if old!=json.loads(json.dumps(d)):
                r['previous_near_diagnostics']=old;r['near_diagnostics']=d;dirty=True;changed+=1
            r['near_diagnostics_version']=2;dirty=True
        if dirty:atomic_json(f,x)
    atomic_json(BASE/'experiments/near_metric_refresh.json',dict(checked=checked,changed=changed,reason='Exclude acceptance reset from beam-destroyed cells; preserve previous metrics. Search programs and scores are unchanged.'))
    print('NEAR METRICS',checked,'checked',changed,'corrected')
if __name__=='__main__':main()
