// Independent verification of a single candidate program against the ORIGINAL
// JavaScript sandbox (level-6/sandbox-level-6.html), not the Python/C++ models.
//
//   node validate_case.cjs <dataset> <caseNumber1based> <programFile>
//
// Enforces BOTH contest conditions:
//   accepted == K                     (exactly the required number of copies)
//   lastAcceptTick == programLength   (no commands after the K-th pickup)
//
// prints JSON: {dataset, case, ticks, accepted, required, lastAcceptTick, pass}
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');

const REPO = path.join(__dirname, '..', '..');
const root = path.join(REPO, 'level-6');
const html = fs.readFileSync(path.join(root, 'sandbox-level-6.html'), 'utf8');
let source = html.slice(html.indexOf('const INSTR_NOOP '), html.indexOf('\nconst globalState ='));
assert(source.includes('    init(gameState, elements);'));
source = source.replace('    init(gameState, elements);',
  '    return { parseHexInput, parseHexSolution, resetEmitterIndices, applyEmitterStep };');
source += '\nglobalThis.makeSimulator = nanofabricator;';
const context = vm.createContext({});
vm.runInContext(source, context, { timeout: 10000 });

const DATASETS = { medium: '2-medium', large: '3-large', enormous: '4-enormous' };

function loadInput(dataset, caseNumber) {
  const name = `in_level-6_${DATASETS[dataset]}.txt`;
  const lines = fs.readFileSync(path.join(root, name), 'utf8').trim().split(/\r?\n/);
  const count = Number(lines.shift());
  let k = 0;
  const inputs = [];
  for (let i = 0; i < count; i++) {
    while (!lines[k].trim()) k++;
    const header = lines[k].trim().split(/\s+/).map(Number);
    inputs.push(lines.slice(k, k + 1 + header[1]).join('\n'));
    k += 1 + header[1];
  }
  assert(caseNumber >= 1 && caseNumber <= inputs.length, 'case out of range');
  return inputs[caseNumber - 1];
}

const [dataset, caseNumber, programFile, explicitInputFile] = process.argv.slice(2);
const input = explicitInputFile ? fs.readFileSync(explicitInputFile, "utf8") : loadInput(dataset, Number(caseNumber));
const program = fs.readFileSync(programFile, 'utf8').trim();
const gameState = {
  radius: 0, cols: 0, rows: 0, pattern: {}, acceptedPatterns: 0,
  emitter: {}, program: [], inputParseErrors: [], solutionParseErrors: [], precomputedStates: [],
};
const api = context.makeSimulator({ gameState, elements: {} });
api.parseHexInput(gameState, input);
api.parseHexSolution(gameState, program);
assert.equal(gameState.inputParseErrors.length, 0, JSON.stringify(gameState.inputParseErrors));
assert.equal(gameState.solutionParseErrors.length, 0, JSON.stringify(gameState.solutionParseErrors));
api.resetEmitterIndices();

// Track the accepted count AFTER EVERY tick - the previous version declared
// lastAccept but never computed it, so a program that reached K early and then
// kept running would still pass.
let lastAcceptTick = -1;
let prevAccepted = 0;
const acceptances = [];
for (let tick = 0; tick < gameState.program.length; tick++) {
  api.applyEmitterStep(tick);
  if (gameState.acceptedPatterns > prevAccepted) {
    acceptances.push(tick + 1);
    lastAcceptTick = tick + 1;                 // 1-based tick of the K-th pickup
    prevAccepted = gameState.acceptedPatterns;
  }
}
const accepted = gameState.acceptedPatterns;
const required = gameState.pattern.count;
const ticks = gameState.program.length;
const reason = accepted < required ? "INSUFFICIENT_COPIES" : accepted > required ? "EXCESS_COPIES" : lastAcceptTick !== ticks ? "TRAILING_COMMANDS" : "PASS";
const pass = reason === "PASS";
console.log(JSON.stringify({
  dataset, case: Number(caseNumber), ticks, accepted, required, lastAcceptTick, acceptances, reason, pass,
}));
process.exit(pass ? 0 : 1);
