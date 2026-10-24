const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const root=path.join(__dirname,'..','level-6');
const html=fs.readFileSync(path.join(root,'sandbox-level-6.html'),'utf8');
// Original parser, geometry and physics are unchanged. Only the UI call is replaced.
let source=html.slice(html.indexOf('const INSTR_NOOP '),html.indexOf('\nconst globalState ='));
assert(source.includes('    init(gameState, elements);'));
source=source.replace('    init(gameState, elements);','    return { parseHexInput, parseHexSolution, resetEmitterIndices, applyEmitterStep };');
source+='\nglobalThis.makeSimulator = nanofabricator;';
const context=vm.createContext({});vm.runInContext(source,context,{timeout:10000});
const datasets={medium:'2-medium',large:'3-large',enormous:'4-enormous'};
function inputs(ds){
 const lines=fs.readFileSync(path.join(root,`in_level-6_${datasets[ds]}.txt`),'utf8').trim().split(/\r?\n/);let k=1,out=[];
 for(let i=0;i<Number(lines[0]);i++){while(!lines[k].trim())k++;const h=lines[k].trim().split(/\s+/).map(Number);out.push(lines.slice(k,k+1+h[1]).join('\n'));k+=1+h[1];}
 assert(lines.slice(k).every(x=>!x.trim()));return out;
}
function check(input,program,label){
 assert(program.trim().split(/\r?\n/).every(row=>/^[FBT-](\s+[FBT-]){5}$/.test(row.trim())),'invalid six-command format');
 const st={radius:0,cols:0,rows:0,pattern:{},acceptedPatterns:0,emitter:{},program:[],inputParseErrors:[],solutionParseErrors:[],precomputedStates:[]};
 const api=context.makeSimulator({gameState:st,elements:{}});api.parseHexInput(st,input);api.parseHexSolution(st,program);
 assert.equal(st.inputParseErrors.length,0,JSON.stringify(st.inputParseErrors));assert.equal(st.solutionParseErrors.length,0,JSON.stringify(st.solutionParseErrors));api.resetEmitterIndices();
 const acceptances=[];
 for(let t=0;t<st.program.length;t++){let old=st.acceptedPatterns;api.applyEmitterStep(t);if(st.acceptedPatterns>old)acceptances.push(t+1);}
 assert.equal(st.acceptedPatterns,st.pattern.count,label);assert.equal(acceptances.at(-1),st.program.length,`${label}: trailing commands`);
 return {validation:'SANDBOX_LOCAL_PASS',ticks:st.program.length,acceptances};
}
if(process.argv[2]==='--single'){
 const r=JSON.parse(fs.readFileSync(0,'utf8'));console.log(JSON.stringify(check(inputs(r.dataset)[r.case-1],r.program.join('\n'),`${r.dataset} ${r.case}`)));
}else{
 const folder=process.argv[2]||'best';
 for(const ds of Object.keys(datasets)){
  const ii=inputs(ds),pp=fs.readFileSync(path.join(__dirname,folder,`answer_level-6_${datasets[ds]}.txt`),'utf8').trim().split(/\r?\n\s*\r?\n/);assert.equal(pp.length,ii.length);
  let ticks=0;for(let i=0;i<pp.length;i++)ticks+=check(ii[i],pp[i],`${ds} ${i+1}`).ticks;
  console.log(`${ds}: SANDBOX_LOCAL_PASS ${ii.length} cases ${ticks} ticks`);
 }
}
