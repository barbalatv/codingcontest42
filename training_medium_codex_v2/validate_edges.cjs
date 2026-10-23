const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const base=__dirname,root=path.join(base,'..','level-6'),html=fs.readFileSync(path.join(root,'sandbox-level-6.html'),'utf8');let source=html.slice(html.indexOf('const INSTR_NOOP '),html.indexOf('\nconst globalState =')).replace('    init(gameState, elements);','    return {parseHexInput,parseHexSolution,resetEmitterIndices,applyEmitterStep};');source+='\nglobalThis.makeSimulator=nanofabricator;';const ctx=vm.createContext({});vm.runInContext(source,ctx);
const lines=fs.readFileSync(path.join(root,'in_level-6_2-medium.txt'),'utf8').trim().split(/\r?\n/);const n=Number(lines.shift()),inputs=[];let k=0,edges=0,ticks=0;
for(let i=0;i<n;i++){while(!lines[k].trim())k++;const h=lines[k].trim().split(/\s+/).map(Number);inputs.push(lines.slice(k,k+1+h[1]).join('\n'));k+=1+h[1];}
for(const file of fs.readdirSync(path.join(base,'edges')).filter(f=>/^case\d+\.json$/.test(f)).sort()){
 const bank=JSON.parse(fs.readFileSync(path.join(base,'edges',file)));const gs={radius:0,cols:0,rows:0,pattern:{},acceptedPatterns:0,emitter:{},program:[],inputParseErrors:[],solutionParseErrors:[],precomputedStates:[]};const api=ctx.makeSimulator({gameState:gs,elements:{}});api.parseHexInput(gs,inputs[bank.case-1]);
 const selected=bank.edges.filter((e,j)=>j%Math.max(1,Math.floor(bank.edges.length/32))===0).slice(0,32);
 for(const e of selected){api.parseHexSolution(gs,e.program.map(row=>row.join(' ')).join('\n'));api.resetEmitterIndices();const L=gs.emitter.perimeter.length;
  if(e.start!=='initial'){gs.emitter.indices=e.start.slice(0,6).map(v=>(L-v)%L);gs.emitter.active=Array.from({length:6},(_,i)=>Boolean((e.start[6]>>i)&1));}
  let prev=0;for(let t=0;t<gs.program.length;t++){prev=gs.acceptedPatterns;api.applyEmitterStep(t);ticks++;}
  assert.equal(gs.acceptedPatterns,e.copies,`case ${bank.case}`);assert.equal(gs.acceptedPatterns-prev,1);assert.equal(JSON.stringify(gs.emitter.indices.map(v=>(L-v)%L)),JSON.stringify(e.end.slice(0,6)));assert.equal(gs.emitter.active.reduce((v,b,i)=>v+(Number(b)<<i),0),e.end[6]);edges++;
 }
}
console.log(JSON.stringify({status:'ORIGINAL_JS_EDGE_SAMPLE_PASS',edges,ticks}));
