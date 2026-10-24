from native import *
def main():
    root=BASE/'experiments/validated_arms';root.mkdir(exist_ok=True);checks=[]
    for label in ['A','B','C','B_birth','C_birth']:
        folder=root/label;folder.mkdir(exist_ok=True)
        for ds in DATASETS:
            bank=programs(ds,'baseline')
            for i in range(len(bank)):
                x=json.loads((BASE/'experiments/pass1'/f'{ds}_{i+1}.json').read_text());arm=label[0];r=next(r for r in x['rows'] if r['strategy']==arm)
                candidate=r['birth_program'] if label.endswith('_birth') else r['program']
                if candidate:bank[i]=[tuple(z) for z in candidate];exact(cases(ds)[i],bank[i])
                elif label.endswith('_birth'):raise AssertionError('independent birth missing')
            save_programs(folder/name(ds),bank)
        result=subprocess.run(['node',str(BASE/'validate_sandbox.cjs'),str(folder.relative_to(BASE))],check=True,capture_output=True,text=True)
        checks.append(dict(arm=label,status='ORIGINAL_JS_PASS',log=result.stdout,sha256={ds:hashlib.sha256((folder/name(ds)).read_bytes()).hexdigest() for ds in DATASETS}));print('ARM_ORIGINAL_JS_PASS',label,flush=True)
    atomic_json(BASE/'experiments/arm_oracle_validation.json',checks)
if __name__=='__main__':main()
