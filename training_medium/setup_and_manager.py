import os
import sys
import shutil
import csv
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from solve_l6 import parse
from solve_l5 import verify
from optimize_l6 import load_programs, save_programs
MEDIUM_IN = ROOT_DIR / 'level-6' / 'in_level-6_2-medium.txt'
ORIGINAL_ANS = ROOT_DIR / 'level-6' / 'answer_level-6_2-medium.txt'

BASELINE_DIR = BASE_DIR / 'baseline'
BEST_DIR = BASE_DIR / 'best'
CANDIDATES_DIR = BASE_DIR / 'candidates'
LOGS_DIR = BASE_DIR / 'logs'
RESULTS_CSV = BASE_DIR / 'results.csv'
REPORT_MD = BASE_DIR / 'REPORT.md'

BASELINE_ANS = BASELINE_DIR / 'answer_level-6_2-medium.txt'
BEST_ANS = BEST_DIR / 'answer_level-6_2-medium.txt'


class MediumManager:
    def __init__(self):
        self._ensure_dirs()
        self.cases = parse(MEDIUM_IN)
        assert len(self.cases) == 210, f"Expected 210 cases, got {len(self.cases)}"
        
        # Initialize baseline if not present
        if not BASELINE_ANS.exists():
            shutil.copy2(ORIGINAL_ANS, BASELINE_ANS)
            print(f"Copied baseline from {ORIGINAL_ANS} to {BASELINE_ANS}")
            
        # Initialize best if not present
        if not BEST_ANS.exists():
            shutil.copy2(BASELINE_ANS, BEST_ANS)
            print(f"Copied best from {BASELINE_ANS} to {BEST_ANS}")
            
        self.baseline_progs = load_programs(BASELINE_ANS)
        self.best_progs = load_programs(BEST_ANS)
        
        assert len(self.baseline_progs) == 210
        assert len(self.best_progs) == 210
        
        base_ticks = sum(map(len, self.baseline_progs))
        assert base_ticks == 5946, f"Baseline ticks mismatch: {base_ticks} != 5946"
        
        if not RESULTS_CSV.exists():
            self._init_csv()

    def _ensure_dirs(self):
        for d in [BASELINE_DIR, BEST_DIR, CANDIDATES_DIR, LOGS_DIR]:
            d.mkdir(parents=True, exist_ok=True)

    def _init_csv(self):
        with open(RESULTS_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['case', 'r', 'count', 'cells', 'baseline', 'best', 'saved', 'method', 'timestamp'])
            for i, (r, pat, count) in enumerate(self.cases):
                b_len = len(self.baseline_progs[i])
                cur_len = len(self.best_progs[i])
                writer.writerow([i + 1, r, count, len(pat), b_len, cur_len, b_len - cur_len, 'baseline', int(time.time())])

    def current_total(self):
        return sum(map(len, self.best_progs))

    def update_case(self, case_idx_0based, new_program, method_name):
        """
        Atomically update a case if new_program is strictly shorter and valid.
        Returns (improved: bool, old_len, new_len).
        """
        r, pat, count = self.cases[case_idx_0based]
        old_len = len(self.best_progs[case_idx_0based])
        new_len = len(new_program)

        if new_len >= old_len:
            return False, old_len, new_len

        # Strict independent verification
        verified_count = verify(r, pat, new_program)
        if verified_count != count:
            raise ValueError(f"Verification failed for case {case_idx_0based + 1}: required {count}, got {verified_count}")

        # Save candidate to candidate directory
        cand_file = CANDIDATES_DIR / f"case_{case_idx_0based + 1:03d}_{new_len}_{method_name}.txt"
        with open(cand_file, 'w', encoding='utf-8') as f:
            for line in new_program:
                f.write(' '.join(line) + '\n')

        # Atomic in-memory update
        self.best_progs[case_idx_0based] = [tuple(line) for line in new_program]

        # Atomic disk save of best set
        tmp_target = BEST_ANS.with_suffix('.tmp')
        save_programs(tmp_target, self.best_progs)
        tmp_target.replace(BEST_ANS)

        # Update CSV
        self._update_csv(case_idx_0based + 1, new_len, method_name)

        return True, old_len, new_len

    def _update_csv(self, case_1based, new_len, method_name):
        rows = []
        with open(RESULTS_CSV, 'r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader)
            rows.append(header)
            for row in reader:
                if int(row[0]) == case_1based:
                    base_len = int(row[4])
                    row[5] = str(new_len)
                    row[6] = str(base_len - new_len)
                    row[7] = method_name
                    row[8] = str(int(time.time()))
                rows.append(row)
        with open(RESULTS_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerows(rows)


if __name__ == '__main__':
    mgr = MediumManager()
    print(f"MediumManager initialized successfully.")
    print(f"Baseline score: {sum(map(len, mgr.baseline_progs))}")
    print(f"Current best score: {mgr.current_total()}")
