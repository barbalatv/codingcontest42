from common_bn import *
import queue,threading,ctypes
from ctypes import wintypes
def process_cpu(handle):
    k=ctypes.windll.kernel32;k.GetProcessTimes.argtypes=[wintypes.HANDLE]+[ctypes.POINTER(wintypes.FILETIME)]*4;k.GetProcessTimes.restype=wintypes.BOOL
    a,b,c,d=(wintypes.FILETIME() for _ in range(4))
    if not k.GetProcessTimes(wintypes.HANDLE(int(handle)),ctypes.byref(a),ctypes.byref(b),ctypes.byref(c),ctypes.byref(d)):raise ctypes.WinError()
    return (((c.dwHighDateTime<<32)|c.dwLowDateTime)+((d.dwHighDateTime<<32)|d.dwLowDateTime))/1e7
class Engine:
    def __init__(self,exe='bottleneck_beam.exe'):
        self.exe=exe;self.p=None;self.err=(BASE/'experiments/native_stderr.log').open('a');self.start()
    def start(self):
        self.p=subprocess.Popen([str(BASE/'engines'/self.exe)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.err,text=True,bufsize=1)
        responses=queue.Queue();self.responses=responses
        def reader():
            for line in self.p.stdout:responses.put(line)
            responses.put('')
        self.reader=threading.Thread(target=reader,daemon=True);self.reader.start()
    def exchange(self,frame,timeout=20):
        if self.p.poll() is not None:self.start()
        t=time.perf_counter();cpu=process_cpu(self.p._handle)
        self.p.stdin.write(frame+'\n');self.p.stdin.flush()
        try:line=self.responses.get(timeout=timeout)
        except queue.Empty:
            self.p.kill();self.p.wait();raise TimeoutError('BN1 hard timeout; process killed; next request restarts')
        if not line:raise RuntimeError(f'native exited {self.p.poll()}')
        self.last_timing=dict(wall_seconds=time.perf_counter()-t,cpu_seconds=process_cpu(self.p._handle)-cpu)
        if line.startswith('ERR'):raise ValueError(line.strip())
        return line.strip()
    def frame(self,c,start=None,k=1,horizon=10,width=32,ms=1000,seed=1,mode=1,goal=None,hint=(),refs=(),weights=None,dynamic=0,cap=0,eval_limit=0):
        sim=Sim(c);start=sim.initial() if start is None else start;r=c[0];W=(len(geometry(r)[1])+63)//64;mask=(1<<64)-1
        weights=weights or {};assert len(weights)<=len(c[1])
        for cell,v in weights.items():assert type(cell)==int and 0<=cell<len(geometry(r)[1]) and sim.target>>cell&1 and type(v)==int and 100<=v<=500
        def words(x):return [str((x>>(64*w))&mask) for w in range(W)]
        data=['BN1',r,W,len(c[1]),k,horizon,width,ms,seed,mode,packed(start),goal if goal is not None else (1<<64)-1]
        data+=words(sim.target)+words(sim.forbidden)
        for e in range(6):
            for p in range(6*r):data+=words(sim.rays[p][e]&(sim.target|sim.forbidden))
        data+=words(start[2])+[len(hint)]+encode(hint)+[len(refs)]+list(refs)+[dynamic,cap,eval_limit,len(weights)]
        for cell,v in sorted(weights.items()):data +=[cell,v]
        return ' '.join(map(str,data))
    def ask(self,c,**kw):
        mode=kw.get('mode',1);W=(len(geometry(c[0])[1])+63)//64
        out=list(map(int,self.exchange(self.frame(c,**kw),timeout=kw.get('ms',1000)/1000+10).split()))
        if mode in (9,90):
            size=W+(2 if mode==9 else 4);assert out[0]==len(kw.get('hint',())) and len(out)==1+out[0]*size
            return [out[1+j*size:1+(j+1)*size] for j in range(out[0])]
        n,ev,cfg,millis,bridge=out[:5];p=decode(out[5:5+n]);offset=5+n;nf=out[offset];offset+=1;edges=[]
        for _ in range(nf):
            pose,size=out[offset:offset+2];offset+=2;pp=decode(out[offset:offset+size]);offset+=size;edges.append((pose,pp))
        nearcost,nearn=out[offset:offset+2];offset+=2;near=decode(out[offset:offset+nearn]);offset+=nearn
        cpu_us,depth,conflicts,attempts,deadline_hit,nb=out[offset:offset+6];offset+=6
        birth=decode(out[offset:offset+nb]);offset+=nb;nd=out[offset];offset+=1;discoveries=[]
        for _ in range(nd):
            pose,copies,size=out[offset:offset+3];offset+=3;pp=decode(out[offset:offset+size]);offset+=size;discoveries.append(dict(pose=pose,copies=copies,program=pp))
        selection_digest,configuration_digest=out[offset:offset+2];offset+=2
        assert offset==len(out)
        return p,edges,dict(**self.last_timing,reported_cpu_seconds=cpu_us/1e6,evaluations=ev,configurations=cfg,native_ms=millis,bridges=bridge,near_cost=nearcost,near_program=near,expanded_depth=depth,deadline_hit=bool(deadline_hit),birth_program=birth,pure_discoveries=discoveries,selection_digest=selection_digest,configuration_digest=configuration_digest)
    def close(self):
        if self.p.poll() is None:
            self.p.stdin.close()
            try:self.p.wait(timeout=3)
            except subprocess.TimeoutExpired:self.p.kill();self.p.wait()
        self.err.close()
