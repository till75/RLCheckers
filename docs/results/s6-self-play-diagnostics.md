# S6 self-play diagnostics

**Date:** 2026-11-06  
**Status:** diagnostic evidence for S6/S7 planning; no production code changed  
**S6 code:** `52580ad` (S6 implementation and docs)  
**Related:** `docs/specs/0006-self-play-snapshots.md`,
`docs/adr/0006-self-play-snapshot-policy.md`, `docs/plan.md` S7

## Why this note exists

Three questions during S6 review led to collecting this evidence:

| Question | Concern | Evidence collected |
|---|---|---|
| Why did the S6 agent win 100% against greedy? | The result looked too good and might indicate a self-play or evaluation bug. | Deterministic-baseline diagnosis, randomized-tie greedy, depth-2 minimax, unique-game accounting. |
| How many unique games does 5x5 checkers have? Why play 1,000 games? Are we repeating the same games? | The 1,000-game diagnostic might be mostly repeated games. | Perft counts, terminal-game counts, reachable-state BFS, unique-game accounting. |
| Are later self-play snapshots stronger than the initial one, for example against random? | We had not shown that self-play actually improves over training. | Snapshot learning curve against random, selected snapshots against other baselines, final agent against its own snapshots. |

## Method

Training config for the diagnostic run:

```toml
seed = 7
episodes = 10000
alpha = 0.1
gamma = 0.9
epsilon_start = 1.0
epsilon_end = 0.05
epsilon_decay_fraction = 0.8
opponent = "self"
max_table_entries = 2000000
snapshot_interval = 1000
```

Snapshots were captured by wrapping `SnapshotPolicy.refresh` in an ad hoc
diagnostic script. The production code was not changed. The final table after
10,000 episodes was also evaluated.

Evaluation used `play_matchup` with `STANDARD_OPENINGS` and seed 7:

- **1,000 games** for stochastic opponents: random and randomized-tie greedy.
  Each game is unique because the opponent is seeded per game.
- **10 games** for deterministic opponents: depth-1 greedy and depth-2 minimax.
  These are 5 openings × 2 colours, so the 1,000-game count would be 100
  repetitions of the same 10 games.

The randomized-tie greedy and depth-2 minimax were diagnostic-only agents:

- **Randomized-tie greedy:** the same depth-1 material score as `GreedyAgent`,
  but chooses uniformly among tied best moves with a seeded RNG.
- **Depth-2 minimax:** two-ply material minimax with terminal scores and a
  deterministic tie-break.

## Question 1: why 100% against greedy?

The S6 diagnostic reported **1,000 W / 0 D / 0 L** against depth-1 greedy. That
is a real result for the games played, but it is not 1,000 independent wins.

Both the Q-agent and `GreedyAgent` are deterministic and ignore the game seed.
The arena therefore replays the same 10 opening/colour games 100 times. The
1,000-game confidence interval is not an independent-sample interval.

| Matchup | Result |
|---|---|
| Q vs deterministic greedy, 1,000 games | 1,000 / 0 / 0, score 1.000, CI 1.000–1.000 |
| Q vs deterministic greedy, 10 unique games | 10 / 0 / 0 |
| Q vs randomized-tie greedy, 1,000 games | 808 / 22 / 170, score 0.819, CI 0.795572–0.842428 |
| Q vs depth-2 minimax, 10 unique games | 4 / 0 / 6, score 0.400, CI 0.079939–0.720061 |
| Greedy vs random, 1,000 games | 488 / 16 / 496, score 0.496 |
| Empty Q-table vs greedy, 1,000 games | 500 / 0 / 500, score 0.500 |
| Empty Q-table vs greedy, 10 unique games | 5 / 0 / 5 |

The randomized-tie result is the honest version of the greedy diagnostic. The
same agent scores **0.819**, not 1.000. The depth-2 result shows the agent is not
generally strong; it has learned a narrow counter to the deterministic depth-1
policy.

Example: in the empty-opening game with Q as White and greedy as Black, greedy
played `6-10`, `0-6`, `2-6`, `8-14`, `4-8` while Q captured repeatedly and won in
10 plies. Those are legal moves; greedy simply does not look at the opponent's
immediate capture. That is the intended depth-1 policy, not a rules bug.

## Question 2: how many unique games, and why 1,000?

The exact number of complete 5x5 games is not known here; it is the size of the
game tree. Perft from the initial position counts legal move sequences:

| Depth | Move sequences |
|---:|---:|
| 1 | 4 |
| 2 | 8 |
| 3 | 18 |
| 4 | 38 |
| 5 | 76 |
| 6 | 140 |
| 7 | 264 |
| 8 | 590 |
| 9 | 1,178 |
| 10 | 2,526 |
| 11 | 4,966 |
| 12 | 10,092 |
| 13 | 20,760 |
| 14 | 46,708 |
| 15 | 105,136 |
| 16 | 252,034 |
| 17 | 596,164 |
| 18 | 1,520,108 |
| 19 | 3,692,626 |
| 20 | 9,675,368 |

Decisive terminal games reachable within a ply limit, ignoring
repetition/no-progress draws:

| Max plies | Decisive terminal games |
|---:|---:|
| 10 | 22 |
| 12 | 402 |
| 14 | 2,338 |
| 16 | 9,714 |
| 18 | 42,072 |
| 20 | 294,200 |

A reachable-board-state BFS found **838,131 distinct board states in 120
seconds** and had not finished. The full state space is larger.

So 5x5 checkers is not a 100-game game. The 1,000-game evaluation is a
statistical sample, not a census. The fixed suite is 5 openings × 2 colours =
10 starting conditions. Against a stochastic opponent, the 1,000 games are
unique. Against a deterministic opponent, they are 10 unique games repeated 100
times.

## Question 3: are later snapshots stronger?

Yes. The initial empty snapshot scores **0.521** against random; the final agent
scores **0.8295**. The confidence intervals do not overlap.

### Learning curve against random

Each row is a frozen snapshot evaluated against the same seeded random opponent,
1,000 games per snapshot.

| Episode | Table size | W / D / L | Score | 95% CI |
|---:|---:|---:|---:|---:|
| 0 | 0 | 512 / 18 / 470 | 0.5210 | 0.490303–0.551697 |
| 1,000 | 1,704 | 724 / 43 / 233 | 0.7455 | 0.719266–0.771734 |
| 2,000 | 3,036 | 716 / 44 / 240 | 0.7380 | 0.711520–0.764480 |
| 3,000 | 4,130 | 738 / 36 / 226 | 0.7560 | 0.730025–0.781975 |
| 4,000 | 4,932 | 733 / 46 / 221 | 0.7560 | 0.730210–0.781790 |
| 5,000 | 5,853 | 758 / 42 / 200 | 0.7790 | 0.754068–0.803932 |
| 6,000 | 6,510 | 815 / 30 / 155 | 0.8300 | 0.807334–0.852666 |
| 7,000 | 6,882 | 820 / 30 / 150 | 0.8350 | 0.812618–0.857382 |
| 8,000 | 7,023 | 798 / 30 / 172 | 0.8130 | 0.789425–0.836575 |
| 9,000 | 7,106 | 819 / 28 / 153 | 0.8330 | 0.810461–0.855539 |
| 10,000 | 7,181 | 818 / 23 / 159 | 0.8295 | 0.806659–0.852341 |

### Selected snapshots against other baselines

| Episode | Random-tie greedy | Deterministic greedy, 10 unique | Depth-2 minimax, 10 unique |
|---:|---:|---:|---:|
| 0 | 0.4995 (492/15/493) | 5 / 0 / 5 | 3 / 0 / 7 |
| 1,000 | 0.7255 (708/35/257) | 9 / 0 / 1 | 3 / 0 / 7 |
| 5,000 | 0.7445 (725/39/236) | 10 / 0 / 0 | 3 / 0 / 7 |
| 9,000 | 0.8185 (801/35/164) | 10 / 0 / 0 | 4 / 0 / 6 |
| 10,000 | 0.8190 (808/22/170) | 10 / 0 / 0 | 4 / 0 / 6 |

Random-tie greedy confidence intervals:

- Initial: score 0.4995, CI 0.468728–0.530272.
- Final: score 0.8190, CI 0.795572–0.842428.

Depth-2 confidence intervals:

- Initial: score 0.300, CI 0.000611–0.599389.
- Final: score 0.400, CI 0.079939–0.720061.

The depth-2 intervals overlap widely, so the 3/10 to 4/10 change is not
meaningful.

### Final agent against its own snapshots

The final agent played 10 unique games against each earlier snapshot:

| Opponent | W / D / L |
|---|---:|
| Empty snapshot | 10 / 0 / 0 |
| Snapshots 1,000–9,000 | 9 / 0 / 1 each |

The final agent is stronger than its past selves, but the margin is one unique
game after early training. This is consistent with the plateau.

## What we learned

1. **Self-play is learning.** The final agent is much stronger than the initial
   empty snapshot against random and randomized-tie greedy.
2. **Most of the gain is early.** The first 1,000 episodes take random from
   0.521 to 0.7455. After that, progress is slower and noisy.
3. **It plateaus.** The best random score is at 7,000 episodes (0.8350); the
   final 10,000 score is 0.8295. The difference is within noise.
4. **Table growth slows.** 1,704 entries at 1,000 episodes, 5,853 at 5,000,
   7,181 at 10,000. The table keeps growing while the score mostly flattens.
5. **The improvement is opponent-specific.** Against depth-2 minimax, the agent
   goes from 3/10 to only 4/10. It learns to beat its own policy, random, and
   greedy, but not general depth-2 play.
6. **The 100% vs deterministic greedy is a narrow exploit.** The randomized-tie
   result (0.819) and depth-2 result (0.400) show that the 100% is not general
   strength.
7. **The 1,000-game greedy interval is not meaningful.** It is 10 unique games
   repeated 100 times. Report unique-game W/D/L for deterministic baselines.

## Implications for S7

The S7 plan was updated to reflect this evidence:

- Use **random** and **stochastic greedy** for the 1,000-game gate, where the
  games are genuinely unique.
- Report deterministic greedy as **10 unique games**, not 1,000 independent
  games.
- Train **10,000 episodes per seed**.
- Include the **per-snapshot learning curve** in the S7 report, showing the
  early gain and the plateau.
- Keep the **depth-2 minimax** as a reported robustness diagnostic, not part of
  the pass/fail gate.

## Caveats

- The random opponent is weak; 0.83 against random is a diagnostic, not a strong
  general-strength claim.
- The depth-2 minimax is a simple diagnostic baseline, not a production agent.
- Perft counts move sequences, not unique complete games. The terminal count
  ignores repetition/no-progress draws.
- The reachable-state BFS did not exhaust the state space.
- The learning curve is one seed. S7 will use three training seeds.
- The randomized-tie greedy and depth-2 agents were ad hoc diagnostic scripts;
  no production code was changed.

## Resolved questions

- **Per-snapshot learning curve:** S7 includes it in the report, not only the
  final three-seed gate.
- **Training budget:** S7 uses 10,000 episodes per seed.
- **Depth-2 robustness check:** S7 reports it as a diagnostic; it is not part of
  the pass/fail gate.
