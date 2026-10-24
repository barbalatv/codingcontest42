import sys,json,csv,hashlib,subprocess
from collections import Counter
from pathlib import Path
BASE=Path(__file__).resolve().parent
def table(headers,rows):return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+['| '+' | '.join(map(str,row))+' |' for row in rows])
def main():
    gate=json.loads((BASE/'regression.json').read_text());summary=json.loads((BASE/'pilot_measured_summary.json').read_text());old=json.loads((BASE/'pilot_summary.json').read_text());config=json.loads((BASE/'pilot_measured_config.json').read_text());provenance=json.loads((BASE/'provenance.json').read_text())
    witness=[json.loads(l) for l in (BASE/'witness_probe.jsonl').read_text().splitlines()];case_rows=[];allwindows=[];baseline_checks=[]
    sys.path.insert(0,str(BASE));from run import js,verify_protected
    fixtures=json.loads((BASE/'fixtures.json').read_text())
    for f in fixtures[:8]:
        original=js(f,f['program'],f"baseline_js_{f['global_index']}");assert original['pass'] and original['ticks']==f['ticks'];baseline_checks.append(original)
        x=json.loads((BASE/'pilot_measured'/f"case_{f['global_index']}.json").read_text());rr=x['windows'];best=max(r['saved'] for r in rr)
        case_rows.append(dict(dataset=f['dataset'],case=f['case'],K=f['K'],incumbent=f['ticks'],best=f['ticks']-best,saved=best,width=300,window_min=4,window_max=10,expanded=sum(r['expanded'] for r in rr),lookahead_expanded=sum(r['lookahead_expanded'] for r in rr),terminal_transitions=sum(r['terminal_transitions'] for r in rr),reconstructed=sum(r['reconstructed'] for r in rr),timeout_windows=sum(r['timeout'] for r in rr),cpu_seconds=x['case_cpu_seconds'],wall_seconds=sum(r['wall_seconds'] for r in rr),baseline_js='PASS',candidate_js='NOT_RUN_NO_CANDIDATE' if not any(r['program'] for r in rr) else 'PASS'))
        for r in rr:
            r['timeout_phase']='ONE_STEP_LOOKAHEAD' if r['timeout'] and r['depth']==r['W']-2 and r['lookahead_expanded'] else 'BEAM_EXPANSION' if r['timeout'] else 'NONE';r['expanded_parent_visits']=(r['expanded']+4095)//4096;allwindows.append(r)
    def writecsv(name,rows,fields):
        with (BASE/name).open('w',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f,fields,extrasaction='ignore');w.writeheader();w.writerows(rows)
    fields=['dataset','case','K','incumbent','best','saved','width','window_min','window_max','expanded','lookahead_expanded','terminal_transitions','reconstructed','timeout_windows','cpu_seconds','wall_seconds','baseline_js','candidate_js'];writecsv('pilot_cases.csv',case_rows,fields)
    fields=['dataset','official_case','K','incumbent','W','width','expanded','expanded_parent_visits','lookahead_expanded','pruned_early','pruned_excess','pruned_no_final_accept','pruned_lb','duplicates','beam_truncated','depth','terminal_transitions','terminal_depth','reconstructed','timeout','timeout_phase','invalid_start','reported_clock_seconds','wall_seconds','outcome','saved'];writecsv('pilot_windows.csv',allwindows,fields)
    outcomes=Counter(r['outcome'] for r in allwindows);counts={k:sum(r[k] for r in allwindows) for k in ['expanded','lookahead_expanded','pruned_early','pruned_excess','pruned_no_final_accept','pruned_lb','duplicates','beam_truncated']}
    outcome_counts={k:outcomes[k] for k in ['NO_TERMINAL_FOUND','RESOURCE_LIMIT_BEFORE_TERMINAL','INVALID_START_COPY_COUNT','TERMINAL_WITHOUT_RECONSTRUCTION','RECONSTRUCTION_REPLAY_REJECTED','REJECTED_JS','VALID_NOT_SHORTER','INDEPENDENTLY_VALID_SHORTER']}
    assert not any(r['terminal_transitions'] and not r['reconstructed'] for r in allwindows)
    assert summary['cases']==8 and summary['incumbent']==324 and summary['saved']==sum(r['saved'] for r in case_rows)
    protected=verify_protected();text=f'''# P0 Endgame Correctness Repair + Honest Optimization Pilot

## ROOT CAUSE

**The old optimization-negative result is invalid evidence.** The unchanged transition accepts a pattern and removes target matter. Both `canFinishInOne()` and the final branch of `endgameSearch()` then demanded that the cleared target still be covered. For a nonempty target that post-pickup test rejects every genuine acceptance. Even removing that test alone would leave accepted states exposed to ordinary missing-target scoring and pruning for a fresh copy.

The old code was reproduced, not merely inspected: **12/12 known-valid final-tick controls return false/no result in the old search; 12/12 pass after repair**. Historical `endgame_results.csv` and original source files remain unchanged in `p0/original/`. The withdrawn geometry results are not used as optimization evidence.

## CHECKOUT AND SCOPE

Actual starting HEAD: `{provenance['checkout_head']}` (main, 15629 current submission ticks). The requested research directory did not exist there; it was imported alone from `origin/arena/e75111bd-codingcontest42`, whose fetched tip was exactly `{provenance['research_source']}`. Work is on `Vladimir/endgame-correctness-repair`, based on current main, with no merge into main.

The primary benchmark deliberately freezes the old reference answer bank (15657 ticks), and selects the same historical eight cases totaling 324 ticks. It is not the current stronger submission baseline and is not a claimed global score gain. All {protected} protected Level-6 files, including inputs, sandbox and all answer banks, remain byte-identical. No official answer or dataset was changed. Only research code/evidence and a byte-preservation Git attribute were added.

## FIXED BUGS

* `endgame.cpp`, `finalTransition`: before count must be goalв€’1, after count goal. `canFinishInOne` refuses a state already at the goal. The exact transition is the sole authority for painting/skirting acceptance; `apply()` was not changed.
* `endgameSearch`: final success and reconstruction occur before score and lower-bound pruning. Nonfinal acceptance is rejected. Nonterminal admissible pruning is retained. `remainingLowerBound` returns zero for accepted states; tests also verify the ordinary bound along all known final-copy incumbent paths.
* `allActions`: exactly 4096 unique codes 0..4095, including all-NOOP. Both search and lookahead use this one generator. F/B/T encoding and transition implementation remain unchanged.
* `deduplicate`: full-state sorting clusters equal states before unique, with the lowest-key representative first. Then score/state sorting and beam truncation occur. Parent indices refer to the previous immutable layer and travel with each Node. Reconstruction uses checked layer indexing.
* `rtds.cpp`, `beamWindow`: full goal state replaces goal matter alone. For a window with an unchanged suffix, the caller passes `requireExact=(b<T)`, requiring count, relevant matter, all six positions and active mask. Free pose remains allowed only at the program end, including the last interval of K>1. RTDS action generation/scoring was not redesigned; its pre-existing full-state dedup was already correct.
* `validate_case.cjs`: strict accepted==K AND lastAcceptTick==ticks retained. Added acceptance tick list and explicit PASS/INSUFFICIENT_COPIES/EXCESS_COPIES/TRAILING_COMMANDS reasons. An explicit optional mock input path supports the forbidden-cell negative fixture, using the same original sandbox parser and physics.
* `portable.hpp`: C++20 standard headers and equivalent bit-count intrinsics allow the existing C++ algorithm to compile under MSVC; no simulator rule changed.

Key code locations in this feature commit:

| Repair | Location |
|---|---|
| Complete actions | [endgame.cpp:120](endgame.cpp#L120) |
| Terminal transition / accepted LB | [endgame.cpp:133](endgame.cpp#L133) |
| Full-state dedup / parent recovery | [endgame.cpp:173](endgame.cpp#L173) |
| Success before pruning | [endgame.cpp:208](endgame.cpp#L208) |
| RTDS exact suffix endpoint | [rtds.cpp:219](rtds.cpp#L219) |
| RTDS caller chooses internal-window policy | [rtds.cpp:296](rtds.cpp#L296) |

## POSITIVE CONTROLS

{len(gate['positive_controls'])} final-tick controls: eight historical pilot incumbents plus four current incumbents, covering K=1 and K>1. Every control simulates S[Tв€’1], checks the known final count increment, calls canFinishInOne and search(ticks=1), replays the reconstructed full program in Python and checks it with original JS. Exactly K pickups and final pickup at the final command are required. All original eight benchmark incumbents were separately checked through JS too.

{table(['Dataset','Case','K','Ticks','Finish/Search/JS'],[[r['dataset'],r['case'],r['K'],r['ticks'],'PASS'] for r in gate['positive_controls']])}

## NEGATIVE CONTROLS AND AUDIT

Six JS fixtures check concrete counts/reasons: early final acceptance, extra commands after K, incomplete target, insufficient copies, excess copies, and a full target blocked by two dirty skirting cells. C++ separately checks forbidden prevention, count transition guards, all-NOOP acceptance, and missing/extra/early acceptance. Tests assert actual expected values rather than treating arbitrary process failure as success.

The custom forbidden mock initially used CRLF and failed the original sandbox parser before simulation. That setup failure and its input are retained in `fixture_setup_failure.json` and `forbidden_input_crlf.txt`. The actual semantic negative uses normalized LF, as the ordinary dataset loader already does. It has a full target, two dirty skirting cells, zero pickups, and the expected rejection.

The targeted dedup test interleaves duplicate states with a different state and retains the minimum-key representative and its parent. Multi-depth searches replay the reconstructed path and check the exact final acceptance tick. RTDS tests accept a reachable exact endpoint, reject an unreachable pose despite a free-pose solution, distinguish all four required state components, and confirm identical immutable-suffix transitions from equal endpoints. These are local tests, not claims of platform acceptance.

## PILOT RESULTS

Configuration: WMIN=4, WMAX=10, WIDTH=300, full 4096-action space, deterministic state tie-breaks, no RNG. The old environment variables were not recorded; only source defaults are recoverable. The new **5000 ms deadline per window is an explicit difference**, so no claim is made of a fully identical resource budget. Only the requested eight cases were optimized, starting with enormous #133 and #126. No 540-case optimization run or CP-SAT was performed.

The initial bounded rerun: {old['windows']} windows, {old['timeouts']} timeouts, {old['saved']} saved ticks. Its MSVC `clock()` values are elapsed-clock readings, not actual CPU. Original raw records are preserved and their corrected interpretation is in `metric_notes.json`.

The measured repeat uses Windows GetProcessTimes for true CPU per case process, including process startup/serialization; per-window chrono wall time remains separate. It produced **{summary['incumbent']} в†’ {summary['best_ticks']} ticks**, **{summary['saved']} saved**, {summary['timeouts']}/{summary['windows']} resource-limited windows, {summary['terminal_transitions']} valid terminal transitions and {summary['reconstructed']} reconstructed solutions. Search CPU: {summary['cpu_seconds']:.3f} s; window wall total: {summary['wall_seconds']:.3f} s. The CPU totals are not derived from MSVC clock.

{table(['Dataset','Case','K','Incumbent','Best','Timeouts / 7','CPU s','Wall s','Candidate JS'],[[r['dataset'],r['case'],r['K'],r['incumbent'],r['best'],r['timeout_windows'],round(r['cpu_seconds'],3),round(r['wall_seconds'],3),r['candidate_js']] for r in case_rows])}

Outcome counts (separate failure classes):

{table(['Outcome','Windows'],[[k,v] for k,v in outcome_counts.items()])}

`TERMINAL_WITHOUT_RECONSTRUCTION` is zero because no terminal was discovered; this is not an unexecuted validator pass. Candidate JS is NOT_RUN_NO_CANDIDATE where no program exists. The original incumbents and all positive controls did pass JS. If an improvement is found on reproduction, the runner replays it in Python and C++, runs original JS twice and saves it only under `p0/programs/`.

Detailed machine-readable per-window pruning, depth, expansion, CPU/wall and outcome records: `pilot_measured/`, `pilot_windows.csv`, `pilot_cases.csv`, `pilot_measured_summary.json`. Aggregate counts: `{json.dumps(counts)}`. A beam with missing candidates or a resource cutoff cannot establish global infeasibility.

The `expanded` counter measures joint-action successor attempts; `expanded_parent_visits` counts visited parents, and `lookahead_expanded` counts extra one-step action attempts. Resource cutoffs can include the action that checked the deadline before simulation. These are distinct from unique surviving states and should not be conflated.

## WHERE STATES ARE LOST

The independent witness diagnostic searches at the **original**, known-feasible horizon, not the shortened horizon, and tracks the exact incumbent state rank before width truncation (zero-based ranks; width 300 keeps 0..299). Its programs are not counted as improvements:

{table(['Case','Original horizon','Width','Known-state ranks by depth','Depth','Timeout'],[[r['case'],r['original_horizon'],r['width'],r['known_state_rank_before_width_cut'],r['depth'],r['timeout']] for r in witness])}

For #133, original W=8, the known valid state ranks 540 at depth one and is removed by width 300. This demonstrates scoring/width loss of a feasible incumbent path at that horizon, not loss of a proven shorter solution. For original W=4, width 300, the known trajectory survives the first two layers at rank 1; the search then times out during expensive one-step lookahead before completing the layer. Increasing width to 600 under the same 5 s budget reaches less depth. Thus both width pressure and lookahead cost are observed; a larger beam alone does not remove the resource problem.

## NEXT DECISION

Terminal correctness is established by the positive/negative controls. The former `0 savings` claim must be replaced by this bounded, explicitly incomplete result. There is no measured optimization-positive signal here and no reason to launch 540 searches.

Next limited hypothesis: on #133 only, compare score-ordered lookahead against the present full-state order at W=4 (original feasible horizon 4 and shortened horizon 3), widths 300/600, matched deterministic expansion limits and wall budgets. Require the known original-horizon witness to be found first; measure terminal discovery separately from reconstruction/JS. Also inspect W=8 rank-540 preservation under a carefully bounded wider beam. This directly tests the observed loss/cost mechanisms before widening windows or adding an algorithm.

A subsequent 12вЂ“16-tick CP-SAT window with 2вЂ“3 incumbent emitter trajectories frozen could test whether joint beam ranking is the limiting factor, but the current evidence does not yet establish that CP-SAT is necessary. It is proposed only; **no CP-SAT implementation or window expansion was added**.

## REPRODUCTION

From repository root, with Python, Node and either g++ or the installed MSVC C++20 toolchain:

```powershell
python -B research/2026-10-24-gap-analysis/p0/run.py
python -B research/2026-10-24-gap-analysis/p0/run.py --pilot --measured --budget-ms 5000
# Fresh isolated search rather than resume cached evidence:
python -B research/2026-10-24-gap-analysis/p0/run.py --pilot --run-name reproduction1 --budget-ms 5000
cd research/2026-10-24-gap-analysis/p0
./witness_probe.exe > witness_probe.jsonl
cd ../../..
python -B research/2026-10-24-gap-analysis/p0/report.py
```

On Linux the compiled program is `./witness_probe` (without .exe). Frozen cases, reference answer files, fixtures, build hashes/logs, raw and normalized results are included. Completed pilot cases are resumed, not silently rerun; the configuration must match. Use a new --run-name for a fresh isolated search without overwriting recorded evidence. `primary_engine.cpp` preserves the exact source used by the first bounded run; the final engine adds an optional observational witness-rank field which is unused in ordinary searches. Physics body equality is asserted against both archived engines.

## GIT STATE

Feature branch: `Vladimir/endgame-correctness-repair`; base `{provenance['checkout_head']}`. The imported research directory comes from the independent arena branch; the parent main branch is not changed or merged. The feature commit contains the repaired research files, archived sources and new evidence; `.gitattributes` preserves these bytes. Official input/sandbox/answer hashes are in `p0/protected.json` and checked at the end. Exact final commit SHA and push verification are reported in the delivery message; this report is itself part of that commit.
'''
    (BASE.parent/'P0_CORRECTNESS_REPORT.md').write_text(text,encoding='utf-8')
    result=dict(status='CORRECTNESS_PASS_BOUNDED_PILOT_NO_GAIN',regression='PASS',positive_controls=12,negative_js=6,reference_negative_result='INVALIDATED',pilot=summary,outcomes=outcome_counts,witness=witness,protected_files=protected,official_answers_changed=False,next_decision='Single-case lookahead-order/width diagnostic; no CP-SAT and no 540 search')
    (BASE/'final_evidence.json').write_text(json.dumps(result,indent=2),encoding='utf-8');(BASE/'baseline_js.json').write_text(json.dumps(baseline_checks,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
