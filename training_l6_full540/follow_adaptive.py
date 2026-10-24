from common import *
def main():
    selected=json.loads((BASE/'experiments/adaptive_selection.json').read_text());extra=[]
    for folder in ['pass1','pure_cycles']:
        for f in (BASE/'experiments'/folder).glob('*.json'):
            x=json.loads(f.read_text())
            for r in x.get('rows',[]):
                if r['strategy']=='B' and r['saved']>0 and cases(r['dataset'])[r['case']-1][2]>=2:extra.append(dict(dataset=r['dataset'],case=r['case']))
    for ds in DATASETS:
        ids=sorted({r['case'] for r in extra+selected if r['dataset']==ds and cases(ds)[r['case']-1][2]>=2})
        if ids:subprocess.run([sys.executable,str(BASE/'consolidate.py'),'--datasets',ds,'--indices',','.join(map(str,ids)),'--queries','3','--ms','500'],check=True,cwd=REPO)
if __name__=='__main__':main()
