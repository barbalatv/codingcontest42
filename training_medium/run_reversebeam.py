import sys
import time
from pathlib import Path
from subprocess import run

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from training_medium.setup_and_manager import MediumManager

CHAR_TO_OP = {'-': 0, 'B': 1, 'F': 2, 'T': 3}
OP_TO_CHAR = {0: '-', 1: 'B', 2: 'F', 3: 'T'}

def run_reversebeam_on_cases(case_indices, manager, budget_ms=3000):
    base_dir = Path(__file__).resolve().parent
    in_file = base_dir / 'reversebeam_in.tmp'
    out_file = base_dir / 'reversebeam_out.tmp'
    
    # Prepare input payload
    lines = [str(len(case_indices))]
    for idx in case_indices:
        r, pat, count = manager.cases[idx]
        prog = manager.best_progs[idx]
        lines.append(f"{r} {count} {len(pat)} {len(prog)}")
        for y, x in sorted(pat):
            lines.append(f"{y} {x}")
        for row in prog:
            ops = [str(CHAR_TO_OP[ch]) for ch in row]
            lines.append(" ".join(ops))
            
    in_file.write_text("\n".join(lines) + "\n", encoding='ascii')
    
    exe_path = base_dir.parent / 'archive_engines' / 'reversebeam.exe'
    t0 = time.time()
    res = run([str(exe_path), str(in_file), str(out_file), '0', str(budget_ms)], capture_output=True, text=True)
    if res.returncode != 0:
        print("reversebeam error:", res.stderr)
        return 0
        
    out_tokens = iter(out_file.read_text().split())
    num_cases = int(next(out_tokens))
    assert num_cases == len(case_indices)
    
    total_saved = 0
    for idx in case_indices:
        cand_len = int(next(out_tokens))
        cand_prog = []
        for _ in range(cand_len):
            row = tuple(OP_TO_CHAR[int(next(out_tokens))] for _ in range(6))
            cand_prog.append(row)
            
        old_len = len(manager.best_progs[idx])
        if cand_len < old_len:
            improved, old_len, new_len = manager.update_case(idx, cand_prog, 'reversebeam')
            if improved:
                saved = old_len - new_len
                total_saved += saved
                print(f"CASE {idx + 1:3d}: {old_len} -> {new_len} (SAVED {saved} TICKS!) [Total: {manager.current_total()}]")
                
    print(f"ReverseBeam batch ({len(case_indices)} cases) completed in {time.time() - t0:.2f}s. Saved: {total_saved} ticks.")
    return total_saved

if __name__ == '__main__':
    mgr = MediumManager()
    batch = [167] # Case 168
    if len(sys.argv) > 1:
        if sys.argv[1] == 'all':
            batch = list(range(210))
        else:
            batch = [int(x) - 1 for x in sys.argv[1:]]
            
    run_reversebeam_on_cases(batch, mgr)
