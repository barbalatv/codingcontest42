const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');

const root = path.join(__dirname, 'level-6');
const html = fs.readFileSync(path.join(root, 'sandbox-level-6.html'), 'utf8');
// Keep supplied parsing, geometry, beam, detection and deletion code unchanged.
// Expose the simulation functions instead of initializing the browser UI.
let source = html.slice(html.indexOf('const INSTR_NOOP '), html.indexOf('\nconst globalState ='));
assert(source.includes('    init(gameState, elements);'));
source = source.replace('    init(gameState, elements);',
  '    return { parseHexInput, parseHexSolution, resetEmitterIndices, applyEmitterStep };');
source += '\nglobalThis.makeSimulator = nanofabricator;';
const context = vm.createContext({});
vm.runInContext(source, context, {timeout: 10000});

for (const name of fs.readdirSync(root).filter(n => /^in_.*\.txt$/.test(n)).sort()) {
  const input = fs.readFileSync(path.join(root,name),'utf8').trim().split(/\r?\n/);
  const count = Number(input.shift());
  const inputs = [];
  let k = 0;
  for (let i=0;i<count;i++) {
    while (!input[k].trim()) k++;
    const header = input[k].trim().split(/\s+/).map(Number);
    inputs.push(input.slice(k,k+1+header[1]).join('\n'));
    k += 1+header[1];
  }
  assert(input.slice(k).every(line => !line.trim()));
  const outputName = name.replace(/^in_/,'answer_');
  const programs = fs.readFileSync(path.join(root,outputName),'utf8').trim().split(/\r?\n\s*\r?\n/);
  assert.equal(programs.length,count);
  let ticks = 0;
  for (let i=0;i<count;i++) {
    const gameState = {radius:0,cols:0,rows:0,pattern:{},acceptedPatterns:0,
      emitter:{},program:[],inputParseErrors:[],solutionParseErrors:[],precomputedStates:[]};
    const api = context.makeSimulator({gameState,elements:{}});
    api.parseHexInput(gameState,inputs[i]);
    api.parseHexSolution(gameState,programs[i]);
    assert.equal(gameState.inputParseErrors.length,0,JSON.stringify(gameState.inputParseErrors));
    assert.equal(gameState.solutionParseErrors.length,0,JSON.stringify(gameState.solutionParseErrors));
    api.resetEmitterIndices();
    for(let tick=0;tick<gameState.program.length;tick++) api.applyEmitterStep(tick);
    assert.equal(gameState.acceptedPatterns,gameState.pattern.count,`${name}, case ${i+1}`);
    ticks += gameState.program.length;
  }
  console.log(`${outputName}: SANDBOX_LOCAL_PASS, ${count} cases, ${ticks} ticks`);
}
