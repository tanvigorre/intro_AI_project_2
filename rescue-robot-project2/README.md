# Project 2: Rescue Robot Adversarial Search

RescueBot is back, but this time the disaster environment gets a turn.
After each RescueBot action, environmental hazard agents may shift: a
wind-driven fire/smoke front can move through open areas, and a secondary
collapse wavefront can threaten corridors. Your job is to write agents that
make good rescue decisions when the world responds.

Important framing: in games, minimax is often described as playing against
an optimal opponent. In this rescue project, the "opponent" is not
intelligent. The opponent is uncertainty. Minimax means RescueBot is
planning against the worst plausible environmental change. Alpha-beta
computes the same conservative decision more efficiently. Expectimax
relaxes that assumption and treats hazard changes as chance events.

This project uses Python 3.13 for the course commands. The autograder code
is also compatible with Python 3.10+ so Gradescope can fall back to
`python3` if its base image does not provide `python3.13`. The graphical
display uses pygame, but the autograder runs without graphics.

## Files

Edit and submit only:

```text
agents.py
evaluation.py
```

You should read these support files, but do not submit modified versions:

- `rescue.py`: command-line entry point.
- `rescue_core/game.py`: game state and successor generation.
- `rescue_core/layout.py`: map loading, terrain costs, and hazard rules.
- `rescue_core/runner.py`: episode loop and hazard policies.
- `maps/`: mission layouts.

## Install

```bash
python3.13 -m pip install pygame
```

## Run the GUI

Manual mode is useful before your agents are implemented:

```bash
python3.13 rescue.py --map training_corner --manual
python3.13 rescue.py --map two_fronts_station --manual
```

Q2-Q4 are mostly about recursive search logic. With the default
`score_evaluation_function`, minimax and alpha-beta do not have a distance
gradient toward survivors, so full mission rollouts may lose even when the
search recursion is correct. That is expected, and it is why Q5 asks you to
design `better_evaluation_function`.

After Q5, use `--eval better_evaluation_function` for full rescue demos:

```bash
python3.13 rescue.py --map training_corner --agent reflex
python3.13 rescue.py --map fireline_rescue --agent minimax --depth 2 --eval better_evaluation_function
python3.13 rescue.py --map collapse_corridor --agent alphabeta --depth 2 --eval better_evaluation_function
python3.13 rescue.py --map pruning_showcase --agent alphabeta --depth 3 --eval better_evaluation_function
python3.13 rescue.py --map stochastic_smoke --agent expectimax --depth 2 --eval better_evaluation_function --hazards random --seed 3
python3.13 rescue.py --map evaluation_gauntlet --agent expectimax --depth 2 --eval better_evaluation_function --hazards random --seed 2
```

The command-line summary prints `Planning successor calls`. Minimax and
alpha-beta should usually choose the same rescue actions, but alpha-beta
should need fewer successor calls on maps with enough branching, such as
`pruning_showcase`.

For expectimax, a seed gives a reproducible visual demo. Changing the seed
changes the sampled hazard motion; some seeds can lose because expectimax
maximizes expected value, not guaranteed success in every possible rollout.

## Manual GUI preview

Controls:

- Arrow keys or WASD move RescueBot.
- Space waits for one turn.
- R resets the mission.
- Q or Escape quits.

## Run without graphics

```bash
python3.13 rescue.py --map training_corner --agent reflex --no-graphics
```

## World Rules

RescueBot wins when all survivor markers are secured and the robot returns
to the triage base. A survivor marker represents a protected beacon cell:
RescueBot tags and stabilizes the survivor by entering the cell, then
returns to base to transmit the triage manifest. Active survivor markers
project a one-tile shield radius while they are waiting to be secured. The
triage base projects the same protected perimeter on the return leg after
all survivor markers are secured. Hazards cannot enter those protected
cells, but they can threaten nearby corridors.

| Symbol | Meaning | Cost or behavior |
|---|---|---|
| `R` | RescueBot start | starting position |
| `B` | triage base | return here after all survivors are secured |
| `S` | survivor marker | +30 when secured |
| `F` | fire/smoke front | hazard agent |
| `C` | secondary-collapse wavefront | hazard agent |
| `#` | wall or collapsed structure | blocked |
| `.` | clear floor | cost 1 |
| `m` | sand | cost 2 |
| `g` | smoke haze | cost 2 |
| `r` | rubble | cost 3 |
| `w` | standing water | cost 4 |
| `c` | charging pad | cost 1, restores battery to full, reusable |

The raw game score contains objective terms only: movement cost is
subtracted each RescueBot move, securing a survivor gives +30, entering a
charging pad restores battery but does not add score, returning to base
after all survivors are secured gives +100, and
losing applies one -500 penalty using the first specific loss cause. The
engine does not secretly add survivor-distance,
base-distance, or hazard-adjacency shaping; those are features you should
design in Q1 and Q5.

The `--hazards` flag controls how environmental agents move:

- `stationary`: hazards wait in the episode and in planning rollouts.
- `adversarial`: hazards press toward the nearest un-secured survivor
  marker, then toward the triage base once all survivor markers are secured.
  They respect the one-tile shield radius and normally avoid starting a
  directly upwind move. A front may continue its current drift direction or
  drift out of a dead end, then uses wind and terrain tie-breaks instead of
  freezing in place. A front never chooses to wait when any legal move is
  available, although waiting remains legal in the game model so search
  agents still consider it.
- `random`: after each RescueBot move, each hazard chooses uniformly from
  legal moving actions if any are available. It waits only when no movement
  is possible.
- `auto`: uses random hazards for expectimax and adversarial hazards for
  reflex, minimax, and alpha-beta.

If you run `--hazards random` without `--seed`, each run can use a different
random hazard path; pin `--seed` when comparing agents.

## RescueGameState API

You will mostly use these methods:

- `get_legal_actions(agent_index)`: legal actions for RescueBot (`0`) or a hazard (`1`, `2`, ...).
- `generate_successor(agent_index, action)`: next state after that agent acts.
- `get_num_agents()`: RescueBot plus all hazard agents.
- `is_win()` and `is_loss()`: terminal checks.
- `get_score()`: current raw score.
- `get_robot_position()`, `get_survivor_positions()`, `get_hazard_positions()`, `get_base_position()`.
- `get_hazard_kinds()`, `get_hazard_last_actions()`, `get_hazard_model()`: hazard type, recent drift direction, and hazard policy model. `get_hazard_model()` returns `"stationary"` or `"adversarial"`; the random policy uses the adversarial model because hazards are still mobile.
- `get_battery()`, `get_turns()`, `get_tile_cost(location)`.

## Depth Semantics

In this project, depth counts RescueBot moves, not individual agent moves.
At `--depth 2`, RescueBot plans two of its own actions ahead. After each
RescueBot action, every hazard agent gets a turn before RescueBot acts
again.

```text
depth 2:
RescueBot move 1 -> hazard 1 -> hazard 2 -> RescueBot move 2 -> hazard 1 -> hazard 2 -> evaluate
```

Very large depths such as `--depth 100` are not practical. The game tree
grows exponentially, and a depth bug can hang your program. Use depth 1-3
for visual exploration unless your implementation is carefully optimized.

## Run the local autograder

```bash
python3.13 autograder.py
```

Run one question at a time:

```bash
python3.13 autograder.py -q q3
```

The project is graded out of 30 points: 25 points for code behavior and
5 points for self-reflection.

## Questions

### Q1 Reflex Rescue Agent, 5 points

Implement `ReflexRescueAgent.evaluation_function(self, current_game_state, action)`
in `agents.py`. This function scores one immediate RescueBot action. It
should prefer moving toward survivor markers, avoid nearby hazards, prefer
rescue progress over small detours, and once all survivors are secured,
prefer returning to base. Do not rely only on `successor.get_score()`; the
Q1 tests include equal-score states where distance features matter.

Useful visual checks:

```bash
python3.13 rescue.py --map training_corner --agent reflex
python3.13 rescue.py --map fireline_rescue --agent reflex
python3.13 autograder.py -q q1
```

### Q2 Minimax Search, 7 points

Implement `MinimaxAgent.get_action(self, game_state)` in `agents.py`.
RescueBot is the max agent. Hazards are min agents. Cycle through every
hazard agent before returning to RescueBot and decrement depth only when
the turn returns to RescueBot. Stop recursion at wins, losses, or depth 0.

Useful visual checks:

```bash
python3.13 autograder.py -q q2
python3.13 rescue.py --map fireline_rescue --agent minimax --depth 2 --eval better_evaluation_function
python3.13 rescue.py --map two_fronts_station --agent minimax --depth 2 --eval better_evaluation_function --hazards stationary
```

Q2's correctness tests check the minimax recursion and depth handling. For
full mission rollouts, use `--eval better_evaluation_function` after Q5;
the default score function has no survivor-distance gradient and is not
meant to guide long rescues by itself.

### Q3 Alpha-Beta Pruning, 6 points

Implement `AlphaBetaAgent.get_action(self, game_state)` in `agents.py`.
It must return the same minimax action as Q2 while pruning branches that
cannot affect the final decision. Carry alpha and beta through the recursive
search. Root-level alpha propagation across RescueBot's candidate actions is
expected by the pruning-count test.

Useful visual checks:

```bash
python3.13 rescue.py --map pruning_showcase --agent minimax --depth 3 --eval better_evaluation_function
python3.13 rescue.py --map pruning_showcase --agent alphabeta --depth 3 --eval better_evaluation_function
python3.13 rescue.py --map collapse_corridor --agent alphabeta --depth 2 --eval better_evaluation_function
python3.13 autograder.py -q q3
```

Compare the `Planning successor calls` line for minimax and alpha-beta on
`pruning_showcase`; the action and score should match, but alpha-beta should
expand fewer successors.

### Q4 Expectimax Search, 6 points

Implement `ExpectimaxAgent.get_action(self, game_state)` in `agents.py`.
RescueBot is still the max agent, but hazards are chance agents. At a hazard
node, average the values of all legal hazard actions instead of taking the
minimum or maximum. Your implementation must cycle through multiple hazards
the same way minimax does.

Useful visual checks:

```bash
python3.13 autograder.py -q q4
python3.13 rescue.py --map stochastic_smoke --agent expectimax --depth 2 --eval better_evaluation_function --hazards random --seed 3
python3.13 rescue.py --map stochastic_smoke --agent expectimax --depth 2 --eval better_evaluation_function --hazards random --seed 11
```

Different seeds can produce different outcomes because the visual rollout
samples one random hazard path after expectimax has chosen an action.

### Q5 Evaluation Functions, 6 points

In `evaluation.py`, `score_evaluation_function(current_game_state)` is
already provided for you and should remain a direct
`current_game_state.get_score()` return. Implement
`better_evaluation_function(current_game_state)`. The better function should
combine raw score with meaningful rescue features:
remaining survivors, distance to survivors, return distance to base, hazard
distance, terrain cost, battery, and turn pressure. The tests include
equal-score comparisons and harder stochastic episodes on
`two_fronts_station` and `evaluation_gauntlet`, so a monotone transform of
`get_score()` is not enough.

Useful visual checks:

```bash
python3.13 rescue.py --map evaluation_gauntlet --agent expectimax --depth 2 --eval better_evaluation_function --hazards random --seed 2
python3.13 rescue.py --map two_fronts_station --agent expectimax --depth 2 --eval better_evaluation_function --hazards random --seed 3
python3.13 autograder.py -q q5
```

## Self-reflection blocks

Each question includes a plain-comment self-reflection block in one of the
student-editable files. Do not use JSON, YAML, dictionaries, or any special
syntax. Write normal comment sentences after `YOUR RESPONSE:`.

This project must be completed without generative AI or coding-assistant
tools. Do not use ChatGPT, Copilot, Cursor, Claude, Gemini, Perplexity, or
similar tools to write, revise, debug, explain, or generate code or
reflection responses.

You may use the course materials, lecture notes, project handout, provided
code, Python documentation, Pygame documentation, and local debugging tools.
You may also search for general Python or environment setup information.

You may not use online solution repositories, posted implementations,
code-sharing sites, forum answers, tutorial code, or any resource that
directly solves this project or its algorithms for you. All submitted code
and reflections must be your own work.

Each reflection is worth 1 point. To receive the point, your response must
be non-placeholder, at least 25 words total, explicitly state that you did
not use GenAI, AI tools, coding assistants, posted solutions, or online
project-solving resources for that question, explain how you checked your
answer, include at least one concrete project detail such as a function name,
file name, map name, test id, or command you ran, and include one sentence
about what the question taught you.

The concept sentence can use plain language. Examples include "minimax
assumes the worst plausible hazard response," "alpha-beta skips branches
that cannot change the minimax choice," or "expectimax averages random
hazard outcomes."

Generic filler such as "I did not use GenAI or posted solutions because I
understand the concept" will not receive credit unless it includes concrete
project details and verification. Natural phrasings such as "I did not rely
on any artificial intelligence tool or project-solving online resource" are
acceptable when the rest of the reflection is complete.

| Question | Complete the block in |
|---|---|
| Q1 | `agents.py` |
| Q2 | `agents.py` |
| Q3 | `agents.py` |
| Q4 | `agents.py` |
| Q5 | `evaluation.py` |

Example:

```python
# YOUR RESPONSE:
# I did not use GenAI, AI tools, coding assistants, posted solutions, or
# online project-solving resources for Q4. I worked from the lecture notes
# and the provided RescueBot files.
# I checked my answer by running python3.13 autograder.py -q q4 and testing
# stochastic_smoke in rescue.py. Q4 helped me understand that chance nodes
# average outcomes rather than choosing the worst hazard action.
```

## Understanding autograder failures

When a public test fails, the autograder prints the expected behavior and a
likely place to look.

| Failed test | Expected behavior | Start checking |
|---|---|---|
| Q1.1 | Reflex prefers moving toward the survivor on `training_corner` over stopping | `ReflexRescueAgent.evaluation_function` |
| Q1.2 | Reflex scores safer nonfatal actions above ending next to a hazard | hazard-distance features |
| Q1.3 | Reflex prioritizes the survivor route over a charging-pad detour | survivor-distance and rescue-priority features |
| Q1.4 | Reflex values returning to base after survivors are secured | base-distance feature |
| Q1.5 | Reflex secures an adjacent survivor on `evaluation_gauntlet` | secured-survivor feature |
| Q1.6 | Reflex returns a legal opening action | `ReflexRescueAgent.get_action` |
| Q2.1 | Minimax chooses the best worst-case branch | recursive min/max values |
| Q2.2 | Minimax cycles through every hazard agent before reducing depth | agent-index and depth logic |
| Q2.3 | Minimax respects depth; depth 1 and depth 2 can choose different actions | depth decrement and terminal checks |
| Q2.4 | Minimax returns a legal layout action on `fireline_rescue` | legal actions and terminal checks |
| Q3.1 | Alpha-beta matches minimax | max/min backup logic |
| Q3.2 | Alpha-beta prunes unnecessary branches | alpha and beta updates |
| Q3.3 | Alpha-beta returns a legal layout action on `collapse_corridor` | terminal checks and legal actions |
| Q3.4 | Alpha-beta matches minimax on `pruning_showcase` | pruning should not change minimax value |
| Q4.1 | Expectimax chooses higher expected value | chance-node averaging |
| Q4.2 | Expectimax is not maximax | average all hazard outcomes |
| Q4.3 | Expectimax cycles through multiple hazards | chance-node agent cycling |
| Q4.4 | Expectimax returns a legal layout action on `stochastic_smoke` | legal actions and terminal checks |
| Q5.1 | Provided score evaluation remains the game score | leave `score_evaluation_function` unchanged |
| Q5.2 | Better evaluation prefers equal-score rescue progress | survivor-progress features |
| Q5.3 | Better evaluation uses survivor distance beyond score | survivor-distance feature |
| Q5.4 | Better evaluation penalizes nearby hazards | hazard-distance feature |
| Q5.5 | Better evaluation guides harder stochastic rescues | route, hazard, turn, and terrain features |
| Q1.R-Q5.R | Plain-comment self-reflection block has 25+ words, explicit no-GenAI/no-prohibited-resource attestation, verification, a concrete project detail, and one sentence about what you learned | the file listed in the self-reflection table |

## Questions

- Q1 Reflex Rescue Agent: 4 code + 1 reflection = 5 points
- Q2 Minimax Search: 6 code + 1 reflection = 7 points
- Q3 Alpha-Beta Pruning: 5 code + 1 reflection = 6 points
- Q4 Expectimax Search: 5 code + 1 reflection = 6 points
- Q5 Evaluation Functions: 5 code + 1 reflection = 6 points

## Submission

Submit exactly these files:

```text
agents.py
evaluation.py
```
