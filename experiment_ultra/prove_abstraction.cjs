const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path'),assert=require('node:assert/strict');
const html=fs.readFileSync(path.join(__dirname,'../level-6/sandbox-level-6.html'),'utf8');
let code=html.slice(html.indexOf('const INSTR_NOOP '),html.indexOf('\nconst globalState =')).replace('    init(gameState, elements);','    return {parseHexInput,resetEmitterIndices,applyEmitterStep};');
const ctx=vm.createContext({});vm.runInContext(code+'\nglobalThis.make=nanofabricator;',ctx);
const r=3,rows=[];for(let y=0;y<=6;y++){const pad=Math.abs(r-y),n=2*r-pad+1,c=Array(n).fill('O');if(y===0||y===6)c.fill('*');else c[0]=c[n-1]='*';rows.push('-'.repeat(pad)+c.join('-')+'-'.repeat(pad));}rows[3]=rows[3].slice(0,6)+'M'+rows[3].slice(7);
function history(extra){
 const s={radius:0,cols:0,rows:0,pattern:{},acceptedPatterns:0,emitter:{},program:[],inputParseErrors:[],solutionParseErrors:[],precomputedStates:[]};const api=ctx.make({gameState:s,elements:{}});api.parseHexInput(s,'3 7 13 50\n'+rows.join('\n'));assert.equal(s.inputParseErrors.length,0);
 const emit=line=>{s.program.push(line);api.applyEmitterStep(s.program.length-1);};
 const origins=cell=>[0,1].map(i=>s.emitter.rayCells.findIndex(rr=>rr[i].some(c=>c.r===cell[0]&&c.c===cell[1])));
 function move(cell){const goals=origins(cell),L=s.emitter.perimeter.length;while(goals.some((p,i)=>s.emitter.indices[i]!==p)){let line=Array(6).fill('-');for(let i=0;i<2;i++){let d=(goals[i]-s.emitter.indices[i]+L)%L;if(d)line[i]=d<=L/2?'F':'B';}emit(line);}}
 const toggle=['T','T','-','-','-','-'];
 if(extra){move([1,4]);emit(toggle);assert.equal(s.acceptedPatterns,0);emit(toggle);}
 move([3,6]);emit(toggle);assert.equal(s.acceptedPatterns,1);return {s,emit};
}
const a=history(false),b=history(true);assert.deepEqual(a.s.emitter.indices,b.s.emitter.indices);assert.deepEqual(a.s.emitter.active,b.s.emitter.active);
assert.notDeepEqual(a.s.emitter.grid,b.s.emitter.grid);
const relevant=[[3,6],[3,8],[4,7],[4,5],[3,4],[2,5],[2,7]];const material=s=>relevant.map(([r,c])=>['M','m'].includes(s.emitter.grid[r][c]));
const acceptance=[];let random=12345;
for(let t=0;t<120;t++){random=(Math.imul(random,1664525)+1013904223)>>>0;const line=t<10?Array(6).fill('-'):Array.from({length:6},(_,i)=>'-FBT'[(random>>>(i*2))&3]);a.emit(line);b.emit(line);assert.equal(a.s.acceptedPatterns,b.s.acceptedPatterns);assert.deepEqual(material(a.s),material(b.s));acceptance.push(a.s.acceptedPatterns);}
const result={status:'ORIGINAL_SANDBOX_EQUIVALENCE_PASS',histories_from_empty:true,initial_emitter_states_identical:true,initial_irrelevant_matter_differs:true,continuation_ticks:120,accepted:a.s.acceptedPatterns,acceptance};fs.writeFileSync(path.join(__dirname,'abstraction_proof.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result));
