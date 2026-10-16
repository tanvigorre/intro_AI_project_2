from __future__ import annotations
import random
from dataclasses import dataclass

from .game import RescueGameState, get_successor_counter, reset_successor_counter
from .layout import RescueLayout

WIND_TO_ACTION = {
    "N": "North",
    "S": "South",
    "E": "East",
    "W": "West",
}
OPPOSITE_ACTION = {
    "North": "South",
    "South": "North",
    "East": "West",
    "West": "East",
}


@dataclass(frozen=True)
class EpisodeResult:
    final_state: RescueGameState
    robot_actions: list[str]
    frames: list[RescueGameState]
    planning_expansions: list[int]


def choose_hazard_action(state: RescueGameState, agent_index: int, policy: str, rng: random.Random) -> str:
    legal = state.get_legal_actions(agent_index)
    if not legal:
        return "Stop"
    if policy == "stationary":
        return "Stop" if "Stop" in legal else legal[0]
    if any(action != "Stop" for action in legal):
        legal = [action for action in legal if action != "Stop"]
    if policy == "random":
        return rng.choice(legal)
    if policy == "adversarial":
        wind_action = WIND_TO_ACTION.get(state.layout.wind, "East")
        current_loc = state.get_hazard_positions()[agent_index - 1]
        last_action = state.get_hazard_last_actions()[agent_index - 1]
        reverse_action = OPPOSITE_ACTION.get(last_action)
        current_targets = state.get_survivor_positions() or (state.get_base_position(),)
        current_gradient = min(current_loc.manhattan_distance(target) for target in current_targets)

        metrics = []
        for candidate in legal:
            successor = state.generate_successor(agent_index, candidate)
            hazard_loc = successor.get_hazard_positions()[agent_index - 1]
            targets = successor.get_survivor_positions() or (successor.get_base_position(),)
            thermal_gradient = min(hazard_loc.manhattan_distance(target) for target in targets)
            metrics.append((candidate, successor, hazard_loc, thermal_gradient))

        drift_available = any(
            candidate != "Stop" and thermal_gradient <= current_gradient + 1
            for candidate, _, _, thermal_gradient in metrics
        )

        def pressure_key(action: str):
            successor, hazard_loc, thermal_gradient = next(
                (successor, hazard_loc, thermal_gradient)
                for candidate, successor, hazard_loc, thermal_gradient in metrics
                if candidate == action
            )
            terrain = state.layout.tile_at(hazard_loc)
            downwind = 0 if action == wind_action else 1
            terrain_bias = 0 if terrain in {"g", "r", "m"} else 1 if terrain == "." else 2
            waits = 1 if action == "Stop" else 0
            continues = 0 if action == last_action and action != "Stop" else 1
            reverses = 1 if action == reverse_action else 0
            effective_gradient = thermal_gradient
            if action == "Stop" and drift_available:
                effective_gradient = current_gradient + 2
            gradient_key = effective_gradient
            if current_gradient <= 3 and effective_gradient <= current_gradient + 1:
                gradient_key = current_gradient
            # Primary goal: minimize RescueBot score when a legal
            # environmental change is immediately dangerous. Otherwise,
            # pressure the protected survivor/base perimeter. Once a
            # front is near that perimeter, let its last drift direction
            # break near-ties so it looks like a moving physical front.
            return (
                successor.get_score(),
                gradient_key,
                waits,
                continues,
                reverses,
                effective_gradient,
                downwind,
                terrain_bias,
            )

        return min(legal, key=pressure_key)
    raise ValueError(f"Unknown hazard policy {policy!r}.")


def advance_hazards(state: RescueGameState, policy: str = "adversarial",
                    rng: random.Random | None = None) -> RescueGameState:
    rng = rng or random.Random(7)
    current = state
    for agent_index in range(1, current.get_num_agents()):
        if current.is_win() or current.is_loss():
            break
        action = choose_hazard_action(current, agent_index, policy, rng)
        if action not in current.get_legal_actions(agent_index):
            continue
        current = current.generate_successor(agent_index, action)
    return current


def run_episode(layout: RescueLayout, robot_agent, hazard_policy: str = "adversarial",
                max_steps: int | None = None, seed: int = 7) -> EpisodeResult:
    rng = random.Random(seed)
    hazard_model = "stationary" if hazard_policy == "stationary" else "adversarial"
    state = RescueGameState.initial_state(layout, hazard_model=hazard_model)
    frames = [state]
    actions: list[str] = []
    planning_expansions: list[int] = []
    limit = max_steps if max_steps is not None else layout.max_turns

    for _ in range(limit):
        if state.is_win() or state.is_loss():
            break
        reset_successor_counter()
        action = robot_agent.get_action(state)
        planning_expansions.append(get_successor_counter())
        state = state.generate_successor(0, action)
        actions.append(action)
        frames.append(state)
        state = advance_hazards(state, hazard_policy, rng)
        frames.append(state)

    return EpisodeResult(state, actions, frames, planning_expansions)
