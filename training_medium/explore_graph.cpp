#include <iostream>
#include <vector>
#include <string>
#include <array>
#include <unordered_map>
#include <unordered_set>
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

inline uint64_t mix(uint64_t x) {
    x ^= x >> 30; x *= 0xbf58476d1ce4e5b9ULL;
    x ^= x >> 27; x *= 0x94d049bb133111ebULL;
    return x ^ (x >> 31);
}

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

struct Transition {
    uint64_t from_pose;
    uint64_t to_pose;
    int length;
    vector<int> actions;
};

// BFS from a start pose to find all single-copy acceptances within max_depth ticks
vector<Transition> find_transitions(uint64_t start_pose, int max_depth, int beam_width = 500) {
    vector<Transition> found;
    State s0;
    s0.pose = start_pose;
    s0.accepted = 0;

    struct QueueItem {
        State st;
        vector<int> path;
    };

    vector<QueueItem> current_beam;
    current_beam.push_back({s0, {}});

    for (int depth = 1; depth <= max_depth; depth++) {
        vector<QueueItem> next_beam;
        unordered_set<uint64_t> visited;

        for (const auto& item : current_beam) {
            // If already accepted, we don't continue branching from it
            if (item.st.accepted > 0) continue;

            // Generate actions: 64 combinations for first 3 emitters, 64 for next 3
            // To be efficient, evaluate combos
            for (int act = 0; act < 4096; act++) {
                State nxt = apply_step(item.st, act);
                vector<int> new_path = item.path;
                new_path.push_back(act);

                if (nxt.accepted > 0) {
                    found.push_back({start_pose, nxt.pose, depth, new_path});
                } else if (depth < max_depth) {
                    // Score for beam pruning: number of target cells covered minus penalties
                    int good = 0, bad = 0;
                    for (int w = 0; w < W_words; w++) {
                        good += pc(nxt.matter.b[w] & target_mask.b[w]);
                        bad += pc(nxt.matter.b[w] & forbid_mask.b[w]);
                    }
                    int score = good * 10 - bad * 15;
                    uint64_t h = mix(nxt.pose);
                    for (int w = 0; w < W_words; w++) h ^= mix(nxt.matter.b[w] + w);
                    if (visited.insert(h).second) {
                        next_beam.push_back({nxt, new_path});
                    }
                }
            }
        }

        // Prune next_beam
        if ((int)next_beam.size() > beam_width) {
            auto score_fn = [](const QueueItem& q) {
                int good = 0, bad = 0;
                for (int w = 0; w < W_words; w++) {
                    good += pc(q.st.matter.b[w] & target_mask.b[w]);
                    bad += pc(q.st.matter.b[w] & forbid_mask.b[w]);
                }
                return good * 10 - bad * 15;
            };
            sort(next_beam.begin(), next_beam.end(), [&](const QueueItem& a, const QueueItem& b) {
                return score_fn(a) > score_fn(b);
            });
            next_beam.resize(beam_width);
        }

        current_beam = next_beam;
        if (current_beam.empty()) break;
    }

    return found;
}

int main() {
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

    uint64_t incumbent_pose;
    cin >> incumbent_pose;

    cout << "Exploring transitions from incumbent pose " << incumbent_pose << " up to depth 4...\n";
    auto t0 = Clock::now();
    auto transitions = find_transitions(incumbent_pose, 4, 300);
    auto ms = chrono::duration_cast<chrono::milliseconds>(Clock::now() - t0).count();

    cout << "Search finished in " << ms << " ms. Found " << transitions.size() << " transitions!\n";
    for (const auto& tr : transitions) {
        bool is_cycle = (tr.to_pose == tr.from_pose);
        cout << "  Len=" << tr.length << (is_cycle ? " [CYCLE!]" : " -> new pose") << " to_pose=" << tr.to_pose << "\n";
        for (int act : tr.actions) {
            cout << "    ";
            for (int i = 0; i < 6; i++) cout << CHARS[(act >> (2 * i)) & 3] << " ";
            cout << "\n";
        }
    }

    return 0;
}
