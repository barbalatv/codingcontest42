from native import *
sys.path.insert(0,str(BASE/'cellfirst'));from pure_model import pure_synth
def main():
    tests=[];engine=Engine()
    try:
        for K,H,expected in [(1,0,'INFEASIBLE'),(1,1,'FEASIBLE'),(2,1,'INFEASIBLE'),(2,2,'FEASIBLE')]:
            c=(3,frozenset([(3,6)]),K);p,info=pure_synth(c,H,seconds=2,seed=7300000+K+H)
            if expected=='FEASIBLE':
                assert p and info['status'] in ('OPTIMAL','FEASIBLE');exact(c,p);rr=engine.ask(c,mode=9,hint=p);assert rr[-1][1]==K
            else:assert not p and info['status']=='INFEASIBLE'
            tests.append(dict(K=K,H=H,status=info['status'],program=p))
    finally:engine.close()
    atomic_json(BASE/'experiments/pure_model_tests.json',dict(status='PASS',tests=tests,argument='reachable-domain restriction follows shortest move+toggle distance; every accepted copy requires one new exact-two creation per target cell'))
    print('PURE_MODEL_FIXTURES_PASS',flush=True)
if __name__=='__main__':main()
