#include <iostream>
#include <vector>
#include <string>
#include <array>
#include <algorithm>
#include <cstdint>
#include <intrin.h>

using namespace std;

constexpr int MW = 8;
struct Bits {
    array<uint64_t, MW> b{};
    bool operator==(const Bits& o) const { return b == o.b; }
};

struct State {
    uint64_t pose = 0;
    Bits matter;
    int accepted = 0;
};

int R, L_perim, W_words, NT;
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

// Generate closed paths of length P for one emitter
void get_closed_paths(int p0, int a0, int P, vector<vector<int>>& out_paths) {
    out_paths.clear();
    vector<int> cur(P);
    auto dfs = [&](auto& self, int step, int cp, int ca) -> void {
        if (step == P) {
            if (cp == p0 && ca == a0) out_paths.push_back(cur);
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

int main() {
    // Test Case 51: R=5
    R = 5;
    L_perim = 30;
    
    // Read input from stdin
    int required, incumbent;
    if (!(cin >> R >> required >> incumbent)) return 0;
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

    uint64_t start_pose;
    cin >> start_pose;

    State s0;
    s0.pose = start_pose;
    s0.accepted = 0;

    cout << "Testing closed cycles of length P=3 from pose " << start_pose << "...\n";
    vector<vector<int>> cand_paths[6];
    uint64_t total_combos = 1;
    for (int i = 0; i < 6; i++) {
        int cp = (start_pose >> (8 * i)) & 127;
        int ca = (start_pose >> (8 * i + 7)) & 1;
        get_closed_paths(cp, ca, 3, cand_paths[i]);
        cout << "  Emitter " << i << ": " << cand_paths[i].size() << " closed paths of len 3\n";
        total_combos *= cand_paths[i].size();
    }
    cout << "Total 3-tick combinations to test: " << total_combos << "\n";

    vector<int> chosen(6, 0);
    int found_cycles = 0;

    auto explore = [&](auto& self, int em_idx) -> void {
        if (em_idx == 6) {
            State st = s0;
            for (int step = 0; step < 3; step++) {
                int act = 0;
                for (int i = 0; i < 6; i++) {
                    act |= cand_paths[i][chosen[i]][step] << (2 * i);
                }
                st = apply_step(st, act);
            }
            if (st.accepted >= 1 && st.pose == s0.pose) {
                found_cycles++;
                cout << "FOUND 3-TICK CYCLE! Accepted=" << st.accepted << "\n";
                for (int step = 0; step < 3; step++) {
                    for (int i = 0; i < 6; i++) {
                        cout << CHARS[cand_paths[i][chosen[i]][step]] << " ";
                    }
                    cout << "\n";
                }
            }
            return;
        }
        for (int p_idx = 0; p_idx < (int)cand_paths[em_idx].size(); p_idx++) {
            chosen[em_idx] = p_idx;
            self(self, em_idx + 1);
            if (found_cycles >= 5) return;
        }
    };

    explore(explore, 0);
    cout << "Done testing 3-tick cycles. Found: " << found_cycles << "\n";
    return 0;
}
