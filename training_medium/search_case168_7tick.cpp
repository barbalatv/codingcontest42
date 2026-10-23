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

constexpr int MW = 4;
struct Bits {
    array<uint64_t, MW> b{};
    bool operator==(const Bits& o) const { return b == o.b; }
};

int R, L_perim, W_words, NT;
Bits target_mask, forbid_mask;
vector<array<Bits, 6>> rays;
vector<int> valid_pos[6];

struct Path {
    int ops[7];
    int pos[8];
};

vector<Path> emitter_paths[6];

bool is_valid_pos(int e, int p) {
    for (int vp : valid_pos[e]) if (vp == p) return true;
    return false;
}

void generate_constrained_paths(int e, int p0, int p_target, int L) {
    emitter_paths[e].clear();
    Path cur;
    cur.pos[0] = p0;

    int dir = (p_target - p0 + L_perim) % L_perim;
    if (dir > L_perim / 2) dir -= L_perim; // signed displacement

    auto dfs = [&](auto& self, int step) -> void {
        if (step == L) {
            if (cur.pos[L] == p_target) {
                emitter_paths[e].push_back(cur);
            }
            return;
        }

        int remaining_steps = L - step;
        int cur_p = cur.pos[step];
        int d = (p_target - cur_p + L_perim) % L_perim;
        if (d > L_perim / 2) d -= L_perim;

        if (abs(d) > remaining_steps) return; // cannot reach in time

        for (int op = 0; op < 3; op++) {
            // If dir is strictly non-zero, prefer monotone or at most 1 wobble
            if (dir > 0 && op == 1) continue; // no F if target is B
            if (dir < 0 && op == 2) continue; // no B if target is F
            if (dir == 0 && remaining_steps <= 2 && op != 0) {
                // To return to p0 in remaining steps, op must allow returning
            }

            cur.ops[step] = op;
            int nxt = cur_p;
            if (op == 1) nxt = (nxt + L_perim - 1) % L_perim;
            else if (op == 2) nxt = (nxt + 1) % L_perim;

            if (!is_valid_pos(e, nxt)) continue; // stay in pattern zone

            cur.pos[step + 1] = nxt;
            self(self, step + 1);
        }
    };

    dfs(dfs, 0);
}

int main() {
    R = 5;
    L_perim = 6 * R;
    W_words = 2;

    vector<string> rows(2 * R + 1);
    for (int i = 0; i < 2 * R + 1; i++) cin >> rows[i];

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
                        rays[p][i].b[k / 64] |= (1ULL << (k % 64));
                    }
                    ny += dy[i];
                    nx += dx[i];
                }
            }
        }
    }

    for (int e = 0; e < 6; e++) {
        for (int p = 0; p < L_perim; p++) {
            if ((rays[p][e].b[0] & target_mask.b[0]) != 0) {
                valid_pos[e].push_back(p);
            }
        }
    }

    int pA[6] = {0, 27, 24, 11, 14, 4};
    int pB[6] = {1, 23, 20, 13, 13, 4};

    cerr << "Constrained 7-tick search from State A to State B:" << endl;
    for (int i = 0; i < 6; i++) {
        generate_constrained_paths(i, pA[i], pB[i], 7);
        cerr << "Emitter " << i << ": " << emitter_paths[i].size() << " valid constrained paths" << endl;
    }

    uint64_t evals = 0;
    auto t0 = Clock::now();
    bool found = false;

    int P0 = (int)emitter_paths[0].size();
    int P1 = (int)emitter_paths[1].size();
    int P2 = (int)emitter_paths[2].size();
    int P3 = (int)emitter_paths[3].size();
    int P4 = (int)emitter_paths[4].size();
    int P5 = (int)emitter_paths[5].size();

    const char CHARS[4] = {'-', 'F', 'B', 'T'};

    for (int i0 = 0; i0 < P0 && !found; i0++) {
        const auto& path0 = emitter_paths[0][i0];
        for (int i1 = 0; i1 < P1 && !found; i1++) {
            const auto& path1 = emitter_paths[1][i1];
            for (int i2 = 0; i2 < P2 && !found; i2++) {
                const auto& path2 = emitter_paths[2][i2];
                for (int i3 = 0; i3 < P3 && !found; i3++) {
                    const auto& path3 = emitter_paths[3][i3];
                    for (int i4 = 0; i4 < P4 && !found; i4++) {
                        const auto& path4 = emitter_paths[4][i4];
                        for (int i5 = 0; i5 < P5 && !found; i5++) {
                            const auto& path5 = emitter_paths[5][i5];
                            evals++;

                            // Fast simulate 7 ticks
                            uint64_t matter = 0;
                            int accepted = 0;
                            for (int step = 0; step < 7; step++) {
                                uint64_t one = 0, two = 0, three = 0;
                                int pos[6] = {path0.pos[step + 1], path1.pos[step + 1], path2.pos[step + 1],
                                              path3.pos[step + 1], path4.pos[step + 1], path5.pos[step + 1]};
                                for (int e = 0; e < 6; e++) {
                                    uint64_t ray = rays[pos[e]][e].b[0];
                                    three |= two & ray;
                                    two |= one & ray;
                                    one |= ray;
                                }
                                matter = (matter | two) & ~three;
                                if ((matter & target_mask.b[0]) == target_mask.b[0] &&
                                    (matter & forbid_mask.b[0]) == 0) {
                                    accepted++;
                                    matter &= ~target_mask.b[0];
                                }
                            }

                            if (accepted == 1 && matter == 0) {
                                cerr << "\n*** SUCCESS! FOUND 7-TICK TRANSITION A -> B! ***" << endl;
                                for (int step = 0; step < 7; step++) {
                                    string line = "";
                                    line += CHARS[path0.ops[step]]; line += " ";
                                    line += CHARS[path1.ops[step]]; line += " ";
                                    line += CHARS[path2.ops[step]]; line += " ";
                                    line += CHARS[path3.ops[step]]; line += " ";
                                    line += CHARS[path4.ops[step]]; line += " ";
                                    line += CHARS[path5.ops[step]];
                                    cout << line << endl;
                                }
                                found = true;
                                break;
                            }
                        }
                    }
                }
            }
        }
    }

    auto elapsed = chrono::duration<double>(Clock::now() - t0).count();
    cerr << "Done. Evaluated " << evals << " combinations in " << elapsed << "s" << endl;
    if (!found) cerr << "No monotone 7-tick transition A -> B exists." << endl;
    return 0;
}
