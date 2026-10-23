from symmetry_graph import *
import csv,hashlib,re
started=time.perf_counter();baseline=load_programs(BASE/'baseline'/NAME);best=load_programs(BASE/'best'/NAME)
assert len(baseline)==210 and sum(map(len,baseline))==5926
# Recover per-case minima even if independent searches happened to checkpoint simultaneously.
for f in sorted((BASE/'experiments').glob('case*.txt')):
 match=re.match(r'case(\d+)_',f.name)
 if not match:continue
 i=int(match[1])-1;p=load_programs(f)[0]
 if len(p)<len(best[i]):
  c=CASES[i];assert verify(c[0],c[1],p)==c[2];best[i]=p
pending=BASE/'best'/NAME;temp=pending.with_suffix('.pending');save_programs(temp,best);subprocess.run(['node',str(BASE/'validate_sandbox_medium.cjs'),str(temp)],check=True);temp.replace(pending)
paths={};nodes=edges=0
for idx in range(1,211):
 if not (BASE/'edges'/f'case{idx}.json').exists():continue
 g=restore(idx);nodes+=len(g.nodes);edges+=len(g.E);p,path=g.dp(frontier=4096)
 if p:
  assert verify(CASES[idx-1][0],CASES[idx-1][1],p)==CASES[idx-1][2];update(idx-1,p,'final_graph_dp',0)
  paths[idx]=path
(BASE/'experiments/selected_paths.json').write_text(json.dumps(paths,separators=(',',':')))
best=load_programs(BASE/'best'/NAME);changes=[]
for i,(a,b) in enumerate(zip(baseline,best)):
 c=CASES[i];assert verify(c[0],c[1],b)==c[2]
 if len(b)<len(a):
  sim=Sim(c);sa=sim.prefix(a);sb=sim.prefix(b);aa=[t for t in range(1,len(sa)) if sa[t][3]>sa[t-1][3]];ba=[t for t in range(1,len(sb)) if sb[t][3]>sb[t-1][3]]
  changes.append(dict(case=i+1,before=len(a),after=len(b),gain=len(a)-len(b),setup_before=aa[0],setup_after=ba[0],acceptances_before=aa,acceptances_after=ba))
logs={}
for name in ['pilot','all','focused','partial_cp']:
 f=BASE/'experiments'/f'{name}.jsonl'
 if f.exists():
  rr=[json.loads(l) for l in f.read_text().splitlines() if l.strip()];logs[name]=dict(queries=len(rr),seconds=sum(x['seconds'] for x in rr),statuses=dict(Counter(x.get('status','completed') for x in rr)))
attribution=Counter()
for row in csv.reader((BASE/'results.csv').open()):attribution[row[1]]+=int(row[4])
score=sum(map(len,best));gain=5926-score
assert gain==sum(attribution.values()),(gain,attribution)
summary=dict(baseline=5926,best=score,gain=gain,improved_cases=len(changes),changes=changes,additive_attribution=dict(attribution),timings=logs,nodes=nodes,edges=edges,finalization_seconds=time.perf_counter()-started)
(BASE/'experiments/summary.json').write_text(json.dumps(summary,indent=2))
# Verify that all protected tracked input/answer bytes still match the control commit (EOL-normalized).
for root in ['level-6','training_medium_codex']:
 diff=subprocess.run(['git','diff','1238079e3020a364eac0485e14265bbe5fcad940','--',root],capture_output=True,check=True)
 assert not diff.stdout,root
manifest={str(f.relative_to(REPO)):hashlib.sha256(f.read_bytes()).hexdigest() for f in [REPO/'level-6/in_level-6_2-medium.txt',REPO/'level-6'/NAME,REPO/'training_medium_codex/best'/NAME,BASE/'baseline'/NAME,BASE/'best'/NAME,BASE/'engines/edge_search.cpp']}
(BASE/'experiments/sha256.json').write_text(json.dumps(manifest,indent=2))
lines=['# Acceptance-cycle graph optimization v2','',f'Baseline **5926**, best **{score}**, saved **{gain}**, improved **{len(changes)}/210**. Full independent Python and original JS validation PASS.','', '## Non-overlapping attribution','', '| Stage | Saved ticks |','|---|---:|']
for method,n in attribution.items():lines.append(f'| {method} | {n} |')
lines+=['','Generalized Bounce is an edge-generation step; DP is the optimizer combining those edges. Their savings are attributed only at the checkpoint that first improved the full program, never added again. `new_edges_dp` includes any downstream bounce/symmetry expansions enabled by a synthesized edge. No repeat-period breakthrough is claimed without a reduced interval trace.','','## Improved cases','', '| Case | Before | After | Saved | First acceptance before/after |','|---|---:|---:|---:|---|']
for c in changes:lines.append(f'| {c["case"]} | {c["before"]} | {c["after"]} | {c["gain"]} | {c["setup_before"]}/{c["setup_after"]} |')
lines+=['','Exact acceptance times and selected paths are stored in `experiments/summary.json` and `experiments/selected_paths.json`. They distinguish setup savings from terminal or interior savings. Case 50 retains its verified 82-tick, 5-tick-per-copy strategy; no further reduction found.','','## Implementation and correctness','', 'Every library edge stores case (bank file), start/end physical pose, copy count 1-4, ticks, complete program, provenance and verification flag. All edges are replayed by independent Python simulation before insertion. The initial state is a separate vertex. DP tracks exact copy count, keeps one cheapest path per pose/count, bounds its frontier, and permits any final pose. Macros preserve intermediate pickup semantics. Library expansion includes physical reversals with endpoint holds, phase shifts, trajectories from nearby donor poses, all 8 opposed-pair permutations, endpoint-relaxed partial-emitter mutations and separately tested return bridges. Opposed symmetries are validated against every ray mask and each resulting edge is simulated.','','C++ runs persistently and receives actual starting pose with clean relevant matter. Fixed-pose bridges use an explicit endpoint cost. Python validates every improving complete program with solve_l5.verify and original sandbox on a temporary full output before atomic replacement. Historical trajectories are independently verified before extraction. Generalized Bounce never assumes that physical reversal reverses matter.','','## Experiments and limitations','', f'Library: {nodes} vertices, {edges} minimum-cost edges across available case banks. Search timings below are wall time summed within each stage; independent overlapping stages must not be summed as total elapsed time.','']
for name,v in logs.items():lines.append(f'- {name}: {v}')
lines+=['','Pilot: ten specified cases, then all-210 bounded search. A subsequent targeted run prioritizes actual DP path edges, allows longer macros and uses a new seed/budget. The first broad run used the earlier short-edge selector; its exact parameters are in logs and source-history patch scripts. Partial CP freezes 3-4 emitter trajectories and removes a tick from the others; results and UNKNOWN/INFEASIBLE statuses are retained. It does not repeat the previous unrestricted closed-cycle queries. No global CP-SAT search or exhaustive optimality proof is claimed. Deep target-case search stalled: new physical poses were generated, but their outgoing transitions were not cheap enough to improve the full route.','','JS edge sampling results: `experiments/edge_js_validation.json`. Complete best-set validation: `validate_sandbox_medium.cjs`. Input, old best, baseline and new best SHA256 provenance: `experiments/sha256.json`. All original competition files, v1 results and Antigravity files remain unchanged. No commit or push performed for this experiment.','','## Reproduction','', 'Compile `engines/edge_search.cpp` once with MSVC `/O2 /EHsc /std:c++17`. The complete source is included. From the repository root:','', '```powershell','python training_medium_codex_v2/graph_cycles.py --mode pilot --ms 600 --queries 8 --seed 20000','python training_medium_codex_v2/symmetry_graph.py','python training_medium_codex_v2/graph_cycles.py --mode all --ms 180 --queries 3 --seed 40000','python training_medium_codex_v2/graph_cycles.py --mode focused --ms 1100 --queries 6 --seed 90000','python training_medium_codex_v2/partial_replan.py','python training_medium_codex_v2/finalize.py','node training_medium_codex_v2/validate_edges.cjs','```','','For a fresh experiment use a new copy of this directory with its baseline as the initial best. Never reset an existing stronger best. The historical source bank depends on available local files; every retained edge records its actual origin. Replaying stored edge banks and selected paths does not require the historical files. Deterministic seeds are recorded; time-limited annealing may vary with hardware.','']
(BASE/'REPORT.md').write_text('\n'.join(lines),encoding='utf8');print(json.dumps(summary,indent=2))

with (BASE/'REPORT.md').open('a',encoding='utf8') as f:f.write('\n## Outcome interpretation\n\nEight saved ticks come from earlier first acceptance. Case 204 contributes one tick from a different transient route after the first acceptance; its setup remains 7 ticks and its steady 4-tick interval is unchanged. Terminal-only gain: 0. No faster sustained repeating cycle was found. Thus the minimum score goal is met, but the intended substantial repeating-cycle breakthrough is not achieved.\n\nHistorical DP contributes 3 already-known per-case programs from the read-only Antigravity best (cases 143, 166, 204); these are reuse gains, not newly synthesized improvements. The remaining 6 saved ticks are new: symmetry graph DP 1, synthesized-edge DP 5. See experiments/donor_attribution.json. Generalized Bounce alone: 0 verified ticks; partial CP: 0 verified ticks.\n\nElapsed session time: about 10 minutes. Broad pass: 361.47 seconds for 210 cases. Focused pass: 95.48 seconds for ten cases. Pilot: 62.77 seconds. These overlap with independent analyses and must not be added to infer elapsed time. Original JS independently checked 6626 sampled library edges / 89972 ticks; all 210 complete best programs also passed original JS and solve_l5.verify.\n')
