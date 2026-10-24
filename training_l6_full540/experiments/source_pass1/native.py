from common import *
import queue,threading,ctypes
from ctypes import wintypes
def process_cpu(handle):
    k=ctypes.windll.kernel32;k.GetProcessTimes.argtypes=[wintypes.HANDLE]+[ctypes.POINTER(wintypes.FILETIME)]*4;k.GetProcessTimes.restype=wintypes.BOOL
    a,b,c,d=(wintypes.FILETIME() for _ in range(4))
    if not k.GetProcessTimes(wintypes.HANDLE(int(handle)),ctypes.byref(a),ctypes.byref(b),ctypes.byref(c),ctypes.byref(d)):raise ctypes.WinError()
    return (((c.dwHighDateTime<<32)|c.dwLowDateTime)+((d.dwHighDateTime<<32)|d.dwLowDateTime))/10000000
class Engine:
    def __init__(self,exe='cellfirst.exe'):
        self.err=(BASE/'experiments/native_stderr.log').open('a')
        self.p=subprocess.Popen([str(BASE/'engines'/exe)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.err,text=True,bufsize=1)
        self.responses=queue.Queue()
        def read_responses():
            for line in self.p.stdout:self.responses.put(line)
            self.responses.put('')
        self.reader=threading.Thread(target=read_responses,daemon=True);self.reader.start()
    def ask(self,c,start=None,k=1,horizon=10,width=32,ms=300,seed=1,mode=1,goal=None,hint=(),refs=()):
        sim=Sim(c);start=sim.initial() if start is None else start
        r=c[0];W=(len(geometry(r)[1])+63)//64;mask=(1<<64)-1
        def words(x):return ' '.join(str((x>>(64*w))&mask) for w in range(W))
        data=f'{r} {W} {len(c[1])} {k} {horizon} {width} {ms} {seed} {mode} {packed(start)} {goal if goal is not None else (1<<64)-1}\n'
        data+=words(sim.target)+'\n'+words(sim.forbidden)+'\n'
        data+='\n'.join(words(sim.rays[p][e]&(sim.target|sim.forbidden)) for e in range(6) for p in range(6*r))+'\n'
        data+=words(start[2])+'\n'+str(len(hint))+' '+' '.join(map(str,encode(hint)))+'\n'+str(len(refs))+' '+' '.join(map(str,refs))+'\n'
        t=time.perf_counter();cpu0=process_cpu(self.p._handle);self.p.stdin.write(data);self.p.stdin.flush()
        try:line=self.responses.get(timeout=ms/1000+15)
        except queue.Empty:
            self.p.kill();raise TimeoutError('Native hard timeout; completed best checkpoints remain intact')
        cpu1=process_cpu(self.p._handle)
        if not line:raise RuntimeError(f'native exited: {self.p.poll()}')
        out=list(map(int,line.split()))
        if mode==9:
            assert out[0]==len(hint)
            return [out[1+j*(W+2):1+(j+1)*(W+2)] for j in range(len(hint))]
        n,ev,cfg,millis,bridge=out[:5];p=decode(out[5:5+n]);offset=5+n;nf=out[offset];offset+=1;edges=[]
        for _ in range(nf):
            pose,size=out[offset:offset+2];offset+=2;pp=decode(out[offset:offset+size]);offset+=size;edges.append((pose,pp))
        nearcost=1000000000;near=[]
        if offset<len(out):
            nearcost,nearn=out[offset:offset+2];offset+=2;near=decode(out[offset:offset+nearn]);offset+=nearn
        cpu_us,depth,conflicts,attempts,deadline_hit,nb=out[offset:offset+6];offset+=6
        birth=decode(out[offset:offset+nb]);offset+=nb;nd=out[offset];offset+=1;discoveries=[]
        for _ in range(nd):
            pose,copies,size=out[offset:offset+3];offset+=3;pp=decode(out[offset:offset+size]);offset+=size;discoveries.append(dict(pose=pose,copies=copies,program=pp))
        assert offset==len(out)
        return p,edges,dict(runtime=time.perf_counter()-t,cpu_seconds=cpu1-cpu0,reported_clock_seconds=cpu_us/1000000,evaluations=ev,configurations=cfg,native_ms=millis,bridges=bridge,near_cost=nearcost,near_program=near,expanded_depth=depth,birth_conflicts=conflicts,birth_attempts=attempts,deadline_hit=bool(deadline_hit),birth_program=birth,pure_discoveries=discoveries)
    def close(self):
        try:self.p.stdin.close()
        except OSError:pass
        self.p.wait(timeout=10);self.err.close()
