const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const root=__dirname,repo=path.resolve(root,'../..');
let html=fs.readFileSync(path.join(repo,'level-6/sandbox-level-6.html'),'utf8');
let code=html.slice(html.indexOf('const INSTR_NOOP '),html.indexOf('\nconst globalState ='));
code=code.replace('    init(gameState, elements);','    return {parseHexInput,parseHexSolution,resetEmitterIndices,applyEmitterStep};');
const ctx=vm.createContext({});vm.runInContext(code+'\nglobalThis.makeSimulator=nanofabricator;',ctx);
const data=JSON.parse(fs.readFileSync(path.join(root,'inventory.json')));
function run(b,program,options={}){
 const input=fs.readFileSync(path.join(repo,`level-6/in_level-6_${b.kind}.txt`),'utf8').trim().split(/\r?\n/);input.shift();let p=0,block;
 for(let i=1;i<=b.case;i++){while(!input[p].trim())p++;let h=+input[p].split(/\s+/)[1];block=input.slice(p,p+h+1).join('\n');p+=h+1;}
 const gs={radius:0,cols:0,rows:0,pattern:{},acceptedPatterns:0,emitter:{},program:[],inputParseErrors:[],solutionParseErrors:[],precomputedStates:[]};
 const api=ctx.makeSimulator({gameState:gs,elements:{}});api.parseHexInput(gs,block);api.parseHexSolution(gs,program.map(l=>l.join(' ')).join('\n'));api.resetEmitterIndices();
 const ats=[];let prev=0;
 for(let t=0;t<gs.program.length;t++){api.applyEmitterStep(t);if(gs.acceptedPatterns>prev)ats.push(t+1);prev=gs.acceptedPatterns;}
 assert.equal(gs.acceptedPatterns,options.expected??gs.pattern.count);assert.equal(gs.inputParseErrors.length+gs.solutionParseErrors.length,0);
 if(options.state)return {gs,api};
 return {accepted:gs.acceptedPatterns,ticks:gs.program.length,accept_times:ats};
}
const verified=[];
for(const file of fs.readdirSync(root).filter(n=>/^probe_.*\.json$/.test(n)||n==='symmetry_results.json')){
 for(const result of JSON.parse(fs.readFileSync(path.join(root,file))))if(result.program){
  const res=run(result,result.program);verified.push({file,kind:result.kind,case:result.case,...res});console.log('SANDBOX_PASS',JSON.stringify(verified.at(-1)));
 }
}

// Microexperiment: create one target while erasing a neighbor, retaining distant matter.
const b=data.bundles['2-medium'][0],r=3,rows=[];
for(let y=0;y<=2*r;y++){
 let pad=Math.abs(r-y),n=2*r-pad+1,chars=Array(n).fill('O');if(y===0||y===2*r)chars.fill('*');else{chars[0]='*';chars[n-1]='*';}
 rows.push('-'.repeat(pad)+chars.join('-')+'-'.repeat(pad));
}
const target=[r,2*r],guard=[r,2*r+2],irrelevant=[1,4];rows[target[0]]=rows[target[0]].substring(0,target[1])+'M'+rows[target[0]].substring(target[1]+1);
const gs={radius:0,cols:0,rows:0,pattern:{},acceptedPatterns:0,emitter:{},program:[],inputParseErrors:[],solutionParseErrors:[],precomputedStates:[]};
const api=ctx.makeSimulator({gameState:gs,elements:{}});api.parseHexInput(gs,`${r} ${2*r+1} ${4*r+1} 3\n`+rows.join('\n'));
assert.equal(gs.inputParseErrors.length,0);
const rays=gs.emitter.rayCells;
const hits=(p,i,q)=>rays[p][i].some(c=>c.r===q[0]&&c.c===q[1]);
const origin=q=>Array.from({length:6},(_,i)=>rays.findIndex((a,p)=>hits(p,i,q)));
const ot=origin(target),og=origin(guard);let found;
for(let code=0;code<3**6&&!found;code++){
 let z=code,p=[],a=[];
 for(let i=0;i<6;i++){let v=z%3;z=Math.floor(z/3);a.push(v>0);p.push(v===2?og[i]:ot[i]);}
 const count=q=>a.reduce((n,on,i)=>n+(on&&hits(p[i],i,q)),0);
 const neighbors=[[0,2],[1,1],[1,-1],[0,-2],[-1,-1],[-1,1]].map(([dy,dx])=>[r+dy,2*r+dx]);
 if(count(target)===2&&count(guard)>=3&&count(irrelevant)<3&&neighbors.every(q=>count(q)!==2))found={p,a};
}
assert(found);gs.emitter.indices=found.p;gs.emitter.active=found.a;gs.emitter.grid[guard[0]][guard[1]]='M';gs.emitter.grid[irrelevant[0]][irrelevant[1]]='M';gs.program=[Array(6).fill('-')];api.applyEmitterStep(0);
assert.equal(gs.acceptedPatterns,1);assert.equal(gs.emitter.grid[target[0]][target[1]],'x');assert.equal(gs.emitter.grid[guard[0]][guard[1]],'d');assert.equal(gs.emitter.grid[irrelevant[0]][irrelevant[1]],'M');
const micro={positions:found.p,active:found.a,accepted:1,target:'x',guard:'d',irrelevant:'M'};
api.applyEmitterStep(0);assert.equal(gs.acceptedPatterns,2);
api.applyEmitterStep(0);assert.equal(gs.acceptedPatterns,3);micro.repeat_accepts=gs.acceptedPatterns;
console.log('MICRO_PASS',JSON.stringify(micro));
const loopSweep=[];
const positive=JSON.parse(fs.readFileSync(path.join(root,'probe_2-medium_2_0_0_0_36-159.json'))).filter(x=>x.solution);
const normalized=gs=>JSON.stringify({p:gs.emitter.indices,a:gs.emitter.active,m:gs.emitter.grid.map(row=>row.map(c=>(c==='M'||c==='m')?1:0))});
for(const result of positive){
 const original=data.bundles[result.kind][result.case-1].program,rec=data.records.find(r=>r.kind===result.kind&&r.case===result.case);
 const first=rec.accept_times[0],second=rec.accept_times[1],single=original.slice(first,second);
 for(let k=2;k<=8;k++){
  const cycle=[...Array.from({length:Math.floor(k/2)},()=>result.solution.lines).flat(),...(k%2?single:[])];
  const {gs,api}=run(result,original.slice(0,first),{expected:1,state:true});
  gs.program=cycle;for(let t=0;t<cycle.length;t++)api.applyEmitterStep(t);assert.equal(gs.acceptedPatterns,1+k);const warm=normalized(gs);
  for(let t=0;t<cycle.length;t++)api.applyEmitterStep(t);assert.equal(gs.acceptedPatterns,1+2*k);assert.equal(normalized(gs),warm);
  loopSweep.push({kind:result.kind,case:result.case,copies:k,ticks:cycle.length,full_matter_closed_after_warmup:true});
 }
}
console.log('FULL_STATE_CYCLE_SWEEP_PASS',JSON.stringify(loopSweep));
fs.writeFileSync(path.join(root,'sandbox_results.json'),JSON.stringify({verified,micro,loopSweep},null,2));
