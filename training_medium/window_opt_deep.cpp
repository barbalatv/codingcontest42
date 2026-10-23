#include <iostream>
#include <vector>
#include <string>
#include <array>
#include <algorithm>
#include <chrono>
#include <cstdint>
#include <intrin.h>

using namespace std;
using Clock = chrono::steady_clock;

constexpr int MW = 8;
struct Bits {
    array<uint64_t, MW> b{};
    bool operator==(const Bits& o) const { return b == o.b; }
    bool operator!=(const Bits& o) const { return b != o.b; }
};

struct State {
    uint64_t pose = 0; // 8 bits per emitter: bit 7 = active, bits 0..6 = pos
    Bits matter;
    int accepted = 0;
};

int R, L_perim, W_words, NT, Required;
Bits target_mask, forbid_mask;
vector<array<Bits, 6>> rays;

inline int pc(uint64_t x) { return (int)__popcnt64(x); }

inline State apply_step(const State& s, int action) {
    State next;
    uint64_t pose = 0;
    Bits one{}, two{}, three{};

    for (int i = 0; i < 6; i++) {
        int act = (action >> (2 * i)) & 3;
        int p = (s.pose >> (8 * i)) & 127;
        int a = (s.pose >> (8 * i + 7)) & 1;

        if (act == 1) p = (p + L_perim - 1) % L_perim;
        else if (act == 2) p = (p + 1) % L_perim;
        else if (act == 3) a ^= 1;

        pose |= (uint64_t(p) | (uint64_t(a) << 7)) << (8 * i);

        if (a) {
            for (int w = 0; w < W_words; w++) {
                uint64_t ray = rays[p][i].b[w];
                three.b[w] |= two.b[w] & ray;
                two.b[w] |= one.b[w] & ray;
                one.b[w] |= ray;
            }
        }
    }
    next.pose = pose;
    next.accepted = s.accepted;

    int good = 0, bad = 0;
    for (int w = 0; w < W_words; w++) {
        uint64_t m = (s.matter.b[w] | two.b[w]) & ~three.b[w];
        next.matter.b[w] = m;
        good += pc(m & target_mask.b[w]);
        bad += pc(m & forbid_mask.b[w]);
    }

    if (good == NT && bad == 0) {
        next.accepted++;
        for (int w = 0; w < W_words; w++) {
            next.matter.b[w] &= ~target_mask.b[w];
        }
    }

    return next;
}

const char CHARS[4] = {'-', 'F', 'B', 'T'};

int token_to_act(char ch) {
    if (ch == 'F') return 1;
    if (ch == 'B') return 2;
    if (ch == 'T') return 3;
    return 0;
}

// Check if running suffix from state `st` achieves Required count
inline bool test_suffix(State st, const vector<int>& prog, int suffix_start) {
    int n = (int)prog.size();
    for (int t = suffix_start; t < n; t++) {
        st = apply_step(st, prog[t]);
        if (st.accepted >= Required) return true;
    }
    return st.accepted >= Required;
}

void get_single_emitter_paths(int p0, int a0, int gp, int ga, int L, vector<vector<int>>& out_paths, int max_paths = 40) {
    out_paths.clear();
    vector<int> cur(L);

    auto dfs = [&](auto& self, int step, int cp, int ca) -> void {
        if ((int)out_paths.size() >= max_paths) return;
        if (step == L) {
            if (cp == gp && ca == ga) {
                out_paths.push_back(cur);
            }
            return;
        }
        for (int op = 0; op < 4; op++) {
            int np = cp, na = ca;
            if (op == 1) np = (np + L_perim - 1) % L_perim;
            else if (op == 2) np = (np + 1) % L_perim;
            else if (op == 3) na ^= 1;
            cur[step] = op;
            self(self, step + 1, np, na);
        }
    };

    dfs(dfs, 0, p0, a0);
}

bool search_window_relaxed(const State& s0, const State& s1, int target_L,
                           const vector<int>& full_prog, int suffix_start,
                           vector<int>& best_plan, int max_combos = 250000) {
    bool is_end_of_program = (suffix_start == (int)full_prog.size());
    vector<vector<int>> cand_paths[6];
    uint64_t total_combos = 1;

    for (int i = 0; i < 6; i++) {
        int cp = (s0.pose >> (8 * i)) & 127;
        int ca = (s0.pose >> (8 * i + 7)) & 1;
        int gp = (s1.pose >> (8 * i)) & 127;
        int ga = (s1.pose >> (8 * i + 7)) & 1;

        get_single_emitter_paths(cp, ca, gp, ga, target_L, cand_paths[i], 30);
        if (cand_paths[i].empty()) return false;

        total_combos *= cand_paths[i].size();
        if (total_combos > (uint64_t)max_combos) return false;
    }

    vector<int> chosen(6, 0);
    uint64_t tested = 0;

    auto explore = [&](auto& self, int em_idx) -> bool {
        if (em_idx == 6) {
            tested++;
            State st = s0;
            vector<int> actions(target_L, 0);
            for (int step = 0; step < target_L; step++) {
                int act = 0;
                for (int i = 0; i < 6; i++) {
                    act |= cand_paths[i][chosen[i]][step] << (2 * i);
                }
                actions[step] = act;
                st = apply_step(st, act);
                if (st.accepted >= Required) {
                    best_plan = vector<int>(actions.begin(), actions.begin() + step + 1);
                    return true;
                }
            }

            if (st.matter == s1.matter && st.accepted == s1.accepted) {
                best_plan = actions;
                return true;
            }

            if (is_end_of_program) {
                if (st.accepted >= Required) {
                    best_plan = actions;
                    return true;
                }
                return false;
            }

            // Quick pruning before expensive suffix simulation
            bool target_match = true;
            for (int w = 0; w < W_words; w++) {
                if (st.matter.b[w] & forbid_mask.b[w]) { target_match = false; break; }
                if ((st.matter.b[w] & target_mask.b[w]) != (s1.matter.b[w] & target_mask.b[w])) { target_match = false; break; }
            }
            if (!target_match) return false;

            // Relaxed verification: test whether rest of program succeeds with this new matter
            if (test_suffix(st, full_prog, suffix_start)) {
                best_plan = actions;
                return true;
            }
            return false;
        }

        for (int p_idx = 0; p_idx < (int)cand_paths[em_idx].size(); p_idx++) {
            chosen[em_idx] = p_idx;
            if (self(self, em_idx + 1)) return true;
        }
        return false;
    };

    return explore(explore, 0);
}

int main(int argc, char** argv) {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int incumbent;
    while (cin >> R >> Required >> incumbent) {
        L_perim = 6 * R;
        vector<string> rows(2 * R + 1);
        for (string& s : rows) cin >> s;

        vector<pair<int, int>> cells;
        vector<vector<int>> index(2 * R + 1, vector<int>(4 * R + 1, -1));
        for (int y = 1; y < 2 * R; y++) {
            for (int x = 0; x <= 4 * R; x++) {
                if (rows[y][x] == 'O' || rows[y][x] == 'M') {
                    index[y][x] = (int)cells.size();
                    cells.push_back({y, x});
                }
            }
        }
        W_words = ((int)cells.size() + 63) / 64;
        target_mask = Bits();
        forbid_mask = Bits();
        NT = 0;

        int dy[6] = {0, 1, 1, 0, -1, -1};
        int dx[6] = {2, 1, -1, -2, -1, 1};

        for (int k = 0; k < (int)cells.size(); k++) {
            auto [y, x] = cells[k];
            if (rows[y][x] == 'M') {
                target_mask.b[k / 64] |= 1ULL << (k % 64);
                NT++;
            } else {
                for (int i = 0; i < 6; i++) {
                    int yy = y + dy[i], xx = x + dx[i];
                    if (yy >= 0 && yy <= 2 * R && xx >= 0 && xx <= 4 * R && rows[yy][xx] == 'M') {
                        forbid_mask.b[k / 64] |= 1ULL << (k % 64);
                    }
                }
            }
        }

        rays.assign(L_perim, {});
        pair<int, int> corners[6] = {{R, 0}, {2 * R, R}, {2 * R, 3 * R}, {R, 4 * R}, {0, 3 * R}, {0, R}};
        for (int side = 0; side < 6; side++) {
            for (int j = 0; j < R; j++) {
                auto [y, x] = corners[side];
                auto [yy, xx] = corners[(side + 1) % 6];
                y += j * (yy - y) / R;
                x += j * (xx - x) / R;
                int p = side * R + j;
                for (int i = 0; i < 6; i++) {
                    int ny = y + dy[i], nx = x + dx[i];
                    while (ny >= 0 && ny <= 2 * R && nx >= 0 && nx <= 4 * R) {
                        int k = index[ny][nx];
                        if (k >= 0) {
                            rays[p][i].b[k / 64] |= (1ULL << (k % 64)) & (target_mask.b[k / 64] | forbid_mask.b[k / 64]);
                        }
                        ny += dy[i];
                        nx += dx[i];
                    }
                }
            }
        }

        int prog_len;
        cin >> prog_len;
        vector<int> program(prog_len);
        for (int t = 0; t < prog_len; t++) {
            int act = 0;
            for (int i = 0; i < 6; i++) {
                char ch;
                cin >> ch;
                act |= token_to_act(ch) << (2 * i);
            }
            program[t] = act;
        }

        // Initial state
        int initial[6] = {0, 5 * R, 4 * R, 3 * R, 2 * R, R};
        State start_state;
        for (int i = 0; i < 6; i++) {
            start_state.pose |= uint64_t(initial[i]) << (8 * i);
        }

        bool improved = true;
        int total_saved = 0;
        int passes = 0;

        while (improved && passes < 3) {
            improved = false;
            passes++;
            int n = (int)program.size();
            vector<State> trace(n + 1);
            trace[0] = start_state;
            for (int t = 0; t < n; t++) {
                trace[t + 1] = apply_step(trace[t], program[t]);
            }

            // Test window sizes 2 to 10
            for (int W = 2; W <= 10 && !improved; W++) {
                for (int t0 = 0; t0 + W <= n; t0++) {
                    const State& s0 = trace[t0];
                    const State& s1 = trace[t0 + W];

                    for (int target_L = 1; target_L < W; target_L++) {
                        vector<int> best_plan;
                        if (search_window_relaxed(s0, s1, target_L, program, t0 + W, best_plan, 300000)) {
                            vector<int> new_prog;
                            new_prog.insert(new_prog.end(), program.begin(), program.begin() + t0);
                            new_prog.insert(new_prog.end(), best_plan.begin(), best_plan.end());
                            if (t0 + (int)best_plan.size() < t0 + W) {
                                new_prog.insert(new_prog.end(), program.begin() + t0 + W, program.end());
                            }

                            // Trim suffix if finished early
                            State check_st = start_state;
                            int final_len = (int)new_prog.size();
                            for (int st_i = 0; st_i < (int)new_prog.size(); st_i++) {
                                check_st = apply_step(check_st, new_prog[st_i]);
                                if (check_st.accepted >= Required) {
                                    final_len = st_i + 1;
                                    break;
                                }
                            }
                            new_prog.resize(final_len);

                            total_saved += (n - (int)new_prog.size());
                            program = new_prog;
                            improved = true;
                            break;
                        }
                    }
                    if (improved) break;
                }
            }
        }

        // Output result
        cout << program.size() << " " << total_saved;
        for (int act : program) {
            cout << " ";
            for (int i = 0; i < 6; i++) {
                cout << CHARS[(act >> (2 * i)) & 3];
            }
        }
        cout << "\n" << flush;
    }
    return 0;
}
