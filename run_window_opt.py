import sys, time
from pathlib import Path
from subprocess import Popen, PIPE
from optimize_l6 import ROOT, load_programs, save_programs
from solve_l6 import parse
from solve_l4 import geometry
from solve_l5 import verify
from phase2_run import atomic_save

def run_optimizer(dataset_name):
    source = ROOT / f'in_level-6_{dataset_name}.txt'
    target = ROOT / f'answer_level-6_{dataset_name}.txt'
    cases = parse(source)
    programs = load_programs(target)

    engine = Popen(['window_opt.exe'], stdin=PIPE, stdout=PIPE, text=True, bufsize=1)
    t0 = time.time()
    old_total = sum(map(len, programs))
    total_saved = 0
    improved_cases = 0

    try:
        for i, (r, pattern, count) in enumerate(cases):
            prog = programs[i]
            rows = list(map(list, geometry(r)[0]))
            for y, x in pattern:
                rows[y][x] = 'M'
            
            header = f'{r} {count} {len(prog)}'
            grid_str = '\n'.join(''.join(row) for row in rows)
            prog_lines = '\n'.join(' '.join(line) for line in prog)
            payload = f'{header}\n{grid_str}\n{len(prog)}\n{prog_lines}\n'

            engine.stdin.write(payload)
            engine.stdin.flush()

            resp = engine.stdout.readline().split()
            if not resp:
                continue

            new_len = int(resp[0])
            saved = int(resp[1])

            if saved > 0 and new_len < len(prog):
                candidate = [tuple(token) for token in resp[2:]]
                assert len(candidate) == new_len
                assert verify(r, pattern, candidate) == count, f'Verification failed for {dataset_name} case {i+1}'

                programs[i] = candidate
                atomic_save(target, programs)
                total_saved += saved
                improved_cases += 1
                print(f'{dataset_name} Case {i+1}: {len(prog)} -> {new_len} (-{saved} ticks)', flush=True)

        new_total = sum(map(len, programs))
        print(f'=== {dataset_name} FINISHED ===')
        print(f'Total ticks: {old_total} -> {new_total} (saved {total_saved} ticks in {improved_cases} cases) [{time.time()-t0:.1f}s]')

    finally:
        engine.stdin.close()
        engine.wait(timeout=5)

if __name__ == '__main__':
    ds = sys.argv[1] if len(sys.argv) > 1 else '4-enormous'
    run_optimizer(ds)
