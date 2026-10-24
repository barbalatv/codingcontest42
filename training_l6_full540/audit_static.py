from native import *
def main():
    out=BASE/'experiments/static_witnesses';out.mkdir(exist_ok=True);E=Engine();count=0
    try:
        for ds in DATASETS:
            pp=programs(ds,'baseline')
            for i in range(len(pp)):
                r=json.loads((BASE/'experiments/static_all'/f'{ds}_{i+1}.json').read_text())
                if r['program']:
                    p=[tuple(z) for z in r['program']];c=cases(ds)[i];exact(c,p);rr=E.ask(c,mode=9,hint=p);assert rr[-1][1]==c[2];pp[i]=p;count+=1
            save_programs(out/name(ds),pp)
    finally:E.close()
    r=subprocess.run(['node',str(BASE/'validate_sandbox.cjs'),str(out.relative_to(BASE))],check=True,capture_output=True,text=True);atomic_json(BASE/'experiments/static_oracle_validation.json',dict(status='CPP_PYTHON_ORIGINAL_JS_PASS',witnesses=count,log=r.stdout));print('STATIC_WITNESSES_ORACLE_PASS',count,flush=True)
if __name__=='__main__':main()
