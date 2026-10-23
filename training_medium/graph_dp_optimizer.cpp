#include <iostream>
#include <vector>
#include <string>
#include <array>
#include <unordered_map>
#include <unordered_set>
#include <algorithm>
#include <chrono>
#include <cstdint>
#include <cassert>
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

int token_to_act(char ch) {
    if (ch == 'F') return 1;
    if (ch == 'B') return 2;
    if (ch == 'T') return 3;
    return 0;
}

struct Edge {
    int from_idx;
    int to_idx;
    int cost;
    vector<int> actions;
};

// Beam search from start_pose to find single-copy acceptance paths
void search_edges_from(uint64_t start_pose, int from_idx, int max_depth, int beam_width,
                       unordered_map<uint64_t, int>& pose_to_idx, vector<uint64_t>& idx_to_pose,
                       vector<vector<Edge>>& adj, bool allow_new_nodes = true) {
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
            if (item.st.accepted > 0) continue;

            for (int act = 0; act < 4096; act++) {
                State nxt = apply_step(item.st, act);
                vector<int> new_path = item.path;
                new_path.push_back(act);

                if (nxt.accepted > 0) {
                    uint64_t target_pose = nxt.pose;
                    int to_idx = -1;
                    auto it = pose_to_idx.find(target_pose);
                    if (it != pose_to_idx.end()) {
                        to_idx = it->second;
                    } else if (allow_new_nodes && (int)idx_to_pose.size() < 120) {
                        to_idx = (int)idx_to_pose.size();
                        pose_to_idx[target_pose] = to_idx;
                        idx_to_pose.push_back(target_pose);
                        adj.emplace_back();
                    }

                    if (to_idx != -1) {
                        adj[from_idx].push_back({from_idx, to_idx, depth, new_path});
                    }
                } else if (depth < max_depth) {
                    int good = 0, bad = 0;
                    for (int w = 0; w < W_words; w++) {
                        good += pc(nxt.matter.b[w] & target_mask.b[w]);
                        bad += pc(nxt.matter.b[w] & forbid_mask.b[w]);
                    }
                    int score = good * 16 - bad * 24;
                    uint64_t h = mix(nxt.pose);
                    for (int w = 0; w < W_words; w++) h ^= mix(nxt.matter.b[w] + w);
                    if (visited.insert(h).second) {
                        next_beam.push_back({nxt, new_path});
                    }
                }
            }
        }

        if ((int)next_beam.size() > beam_width) {
            auto score_fn = [](const QueueItem& q) {
                int good = 0, bad = 0;
                for (int w = 0; w < W_words; w++) {
                    good += pc(q.st.matter.b[w] & target_mask.b[w]);
                    bad += pc(q.st.matter.b[w] & forbid_mask.b[w]);
                }
                return good * 16 - bad * 24;
            };
            sort(next_beam.begin(), next_beam.end(), [&](const QueueItem& a, const QueueItem& b) {
                return score_fn(a) > score_fn(b);
            });
            next_beam.resize(beam_width);
        }

        current_beam = next_beam;
        if (current_beam.empty()) break;
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

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

    // Read seed poses and first copy setup
    int num_seeds;
    cin >> num_seeds;
    vector<uint64_t> idx_to_pose;
    unordered_map<uint64_t, int> pose_to_idx;

    for (int i = 0; i < num_seeds; i++) {
        uint64_t p;
        cin >> p;
        if (pose_to_idx.find(p) == pose_to_idx.end()) {
            pose_to_idx[p] = (int)idx_to_pose.size();
            idx_to_pose.push_back(p);
        }
    }

    int setup_len;
    cin >> setup_len;
    vector<int> setup_prog(setup_len);
    for (int t = 0; t < setup_len; t++) {
        int act = 0;
        for (int i = 0; i < 6; i++) {
            char ch; cin >> ch;
            act |= token_to_act(ch) << (2 * i);
        }
        setup_prog[t] = act;
    }

    // Determine setup target pose
    int initial[6] = {0, 5 * R, 4 * R, 3 * R, 2 * R, R};
    State init_state;
    for (int i = 0; i < 6; i++) init_state.pose |= uint64_t(initial[i]) << (8 * i);

    State setup_end = init_state;
    for (int act : setup_prog) {
        setup_end = apply_step(setup_end, act);
    }
    assert(setup_end.accepted == 1);
    uint64_t setup_end_pose = setup_end.pose;

    int setup_pose_idx = -1;
    if (pose_to_idx.find(setup_end_pose) == pose_to_idx.end()) {
        setup_pose_idx = (int)idx_to_pose.size();
        pose_to_idx[setup_end_pose] = setup_pose_idx;
        idx_to_pose.push_back(setup_end_pose);
    } else {
        setup_pose_idx = pose_to_idx[setup_end_pose];
    }

    vector<vector<Edge>> adj(idx_to_pose.size());

    // Expand edges from all nodes in pool
    int max_depth = 6;
    int beam_width = 400;

    for (size_t u = 0; u < idx_to_pose.size() && u < 8; u++) {
        cerr << "Expanding node " << u + 1 << "/" << min(idx_to_pose.size(), size_t(8)) << "..." << endl;
        search_edges_from(idx_to_pose[u], (int)u, max_depth, beam_width, pose_to_idx, idx_to_pose, adj, true);
        cerr << "Node " << u + 1 << " generated " << adj[u].size() << " edges." << endl;
    }

    // DP on copies: DP[k][v] = min cost to achieve k copies ending at pose v
    constexpr int INF = 1e9;
    int V = (int)idx_to_pose.size();
    vector<vector<int>> dp(required + 1, vector<int>(V, INF));
    vector<vector<pair<int, int>>> parent(required + 1, vector<pair<int, int>>(V, {-1, -1})); // (prev_u, edge_idx)

    // Base case: copy 1 achieved at setup_end_pose with cost setup_len
    dp[1][setup_pose_idx] = setup_len;

    // Fill DP
    for (int k = 2; k <= required; k++) {
        for (int u = 0; u < V; u++) {
            if (dp[k - 1][u] == INF) continue;
            for (size_t e_idx = 0; e_idx < adj[u].size(); e_idx++) {
                const auto& edge = adj[u][e_idx];
                int v = edge.to_idx;
                int new_cost = dp[k - 1][u] + edge.cost;
                if (new_cost < dp[k][v]) {
                    dp[k][v] = new_cost;
                    parent[k][v] = {u, (int)e_idx};
                }
            }
        }
    }

    // Find best final pose
    int best_final_cost = INF;
    int best_final_v = -1;
    for (int v = 0; v < V; v++) {
        if (dp[required][v] < best_final_cost) {
            best_final_cost = dp[required][v];
            best_final_v = v;
        }
    }

    if (best_final_cost < incumbent) {
        // Reconstruct program
        vector<vector<int>> edge_seq;
        int curr_v = best_final_v;
        for (int k = required; k >= 2; k--) {
            auto [prev_u, e_idx] = parent[k][curr_v];
            assert(prev_u != -1);
            edge_seq.push_back(adj[prev_u][e_idx].actions);
            curr_v = prev_u;
        }
        reverse(edge_seq.begin(), edge_seq.end());

        vector<int> full_prog = setup_prog;
        for (const auto& acts : edge_seq) {
            full_prog.insert(full_prog.end(), acts.begin(), acts.end());
        }

        cout << full_prog.size() << " " << (incumbent - (int)full_prog.size());
        for (int act : full_prog) {
            cout << " ";
            for (int i = 0; i < 6; i++) cout << CHARS[(act >> (2 * i)) & 3];
        }
        cout << "\n" << flush;
    } else {
        cout << incumbent << " 0\n" << flush;
    }

    return 0;
}
