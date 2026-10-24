// Execute the original parser, ray geometry and physics in an isolated VM.
// The only added physics-line hook observes the raw grid before pickup.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const root=path.join(__dirname,'..','level-6');
const html=fs.readFileSync(path.join(root,'sandbox-level-6.html'),'utf8');
let source=html.slice(html.indexOf('const INSTR_NOOP '),html.indexOf('\nconst globalState ='));
assert.equal(source.split('        detectAndAcceptPatterns();').length,2);
source=source.replace('    init(gameState, elements);','    return {parseHexInput,parseHexSolution,resetEmitterIndices,applyEmitterStep};');
source=source.replace('        detectAndAcceptPatterns();','        if(globalThis.rawHook)globalThis.rawHook(gameState);\n        detectAndAcceptPatterns();');
source+='\nglobalThis.makeSimulator=nanofabricator;';
const context=vm.createContext({});vm.runInContext(source,context,{timeout:10000});
const datasets={medium:'2-medium',large:'3-large',enormous:'4-enormous'};
function inputs(ds){
 const lines=fs.readFileSync(path.join(root,`in_level-6_${datasets[ds]}.txt`),'utf8').trim().split(/\r?\n/);let k=1,out=[];
 for(let i=0;i<Number(lines[0]);i++){while(!lines[k].trim())k++;const h=lines[k].trim().split(/\s+/).map(Number);out.push(lines.slice(k,k+1+h[1]).join('\n'));k+=1+h[1];}return out;
}
const ii=Object.fromEntries(Object.keys(datasets).map(ds=>[ds,inputs(ds)]));
const requests=JSON.parse(fs.readFileSync(0,'utf8'));let ticks=0,accepted=0;
for(const req of requests){
 const st={radius:0,cols:0,rows:0,pattern:{},acceptedPatterns:0,emitter:{},program:[],inputParseErrors:[],solutionParseErrors:[],precomputedStates:[]};
 const api=context.makeSimulator({gameState:st,elements:{}});api.parseHexInput(st,ii[req.dataset][req.case-1]);api.parseHexSolution(st,req.program.map(row=>row.join(' ')).join('\n'));
 assert.equal(st.inputParseErrors.length,0);assert.equal(st.solutionParseErrors.length,0);api.resetEmitterIndices();
 function matter(){let mask=0n;for(let i=0;i<req.cells.length;i++){const [y,x]=req.cells[i];if(['M','m'].includes(st.emitter.grid[y][x]))mask|=1n<<BigInt(i);}return mask.toString();}
 let raw;
 context.rawHook=()=>{raw=matter();};
 for(let t=0;t<st.program.length;t++){
  const exp=req.trace[t],label=`${req.dataset} ${req.case} tick ${t+1}`;
  assert.equal(matter(),exp.before,label+' before');api.applyEmitterStep(t);
  assert.equal(raw,exp.pre,label+' pre-pickup');assert.equal(matter(),exp.post,label+' post-pickup');assert.equal(st.acceptedPatterns,exp.accepted,label+' count');
  const L=6*(st.radius-1);assert.deepEqual(Array.from(st.emitter.indices),exp.pos.map(p=>(L-p)%L),label+' positions');
  assert.equal(st.emitter.active.reduce((v,a,e)=>v+(a?2**e:0),0),exp.active,label+' active');ticks++;
 }
 assert.equal(st.acceptedPatterns,st.pattern.count);assert.equal(req.trace.at(-1).accepted,st.pattern.count);accepted+=st.pattern.count;
}
console.log(JSON.stringify({status:'ORIGINAL_JS_ALL_TICK_TRACE_PASS',cases:requests.length,ticks,accepted_copies:accepted,source_sha256:crypto.createHash('sha256').update(html).digest('hex')}));
