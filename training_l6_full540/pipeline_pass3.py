from common import *
def main():
    commands=[
      ['adaptive.py','--replicates','--ms','1500','--seed','6700000','--pass-name','replicate_2'],
      ['adaptive.py','--replicates','--ms','1500','--seed','6900000','--pass-name','replicate_3'],
      ['static_all.py','--seconds','1','--workers','4'],
      ['pure_cycles.py','--ms','1500','--workers','4'],
      ['consolidate.py','--queries','0'],
      ['final_repair.py','--limit','24','--seconds','1.5']]
    events=[]
    for command in commands:
        if (BASE/'CANCEL').exists():raise RuntimeError('Cancellation requested; validated best files retained')
        t=time.perf_counter();subprocess.run([sys.executable,str(BASE/command[0]),*command[1:]],check=True,cwd=REPO);events.append(dict(command=command,wall_seconds=time.perf_counter()-t,scores={ds:sum(map(len,programs(ds))) for ds in DATASETS}));atomic_json(BASE/'experiments/pipeline_pass3.json',events);print('PASS3_STAGE',command[0],events[-1]['scores'],flush=True)
if __name__=='__main__':main()
