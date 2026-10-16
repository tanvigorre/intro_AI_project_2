from __future__ import annotations
from dataclasses import dataclass

from .actions import ACTIONS, ACTION_ORDER
from .layout import RescueLayout, HAZARD_NAMES
from .location import GridLocation


RESCUE_BONUS = 30
WIN_BONUS = 100
LOSS_PENALTY = -500
SUCCESSOR_CALLS = 0
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


def reset_successor_counter() -> None:
    global SUCCESSOR_CALLS
    SUCCESSOR_CALLS = 0


def get_successor_counter() -> int:
    return SUCCESSOR_CALLS


@dataclass(frozen=True)
class RescueGameState:
    layout: RescueLayout
    robot: GridLocation
    hazards: tuple[GridLocation, ...]
    remaining_survivors: frozenset[GridLocation]
    battery: int
    score: float = 0.0
    turns: int = 0
    lost: bool = False
    last_event: str = "Mission started."
    hazard_last_actions: tuple[str, ...] = ()
    hazard_model: str = "adversarial"

    @classmethod
    def initial_state(cls, layout: RescueLayout, hazard_model: str = "adversarial") -> "RescueGameState":
        return cls(
            layout=layout,
            robot=layout.start,
            hazards=layout.hazards,
            remaining_survivors=frozenset(layout.survivors),
            battery=layout.initial_battery,
            hazard_last_actions=tuple("Stop" for _ in layout.hazards),
            hazard_model=hazard_model,
        )

    def get_num_agents(self) -> int:
        return 1 + len(self.hazards)

    def get_agent_name(self, agent_index: int) -> str:
        if agent_index == 0:
            return "RescueBot"
        kind = self.layout.hazard_kinds[agent_index - 1]
        return HAZARD_NAMES.get(kind, "hazard")

    def is_win(self) -> bool:
        return not self.lost and not self.remaining_survivors and self.robot == self.layout.base

    def is_loss(self) -> bool:
        if self.is_win():
            return False
        return self.lost or self.battery <= 0 or self.turns >= self.layout.max_turns

    def get_score(self) -> float:
        return self.score

    def get_robot_position(self) -> GridLocation:
        return self.robot

    def get_base_position(self) -> GridLocation:
        return self.layout.base

    def get_hazard_positions(self) -> tuple[GridLocation, ...]:
        return self.hazards

    def get_hazard_kinds(self) -> tuple[str, ...]:
        return self.layout.hazard_kinds

    def get_hazard_last_actions(self) -> tuple[str, ...]:
        if len(self.hazard_last_actions) == len(self.hazards):
            return self.hazard_last_actions
        return tuple("Stop" for _ in self.hazards)

    def get_hazard_model(self) -> str:
        return self.hazard_model

    def get_survivor_positions(self) -> tuple[GridLocation, ...]:
        return tuple(sorted(self.remaining_survivors))

    def get_battery(self) -> int:
        return self.battery

    def get_turns(self) -> int:
        return self.turns

    def get_layout(self) -> RescueLayout:
        return self.layout

    def get_tile_cost(self, loc: GridLocation) -> int:
        return self.layout.movement_cost(loc)

    def get_legal_actions(self, agent_index: int = 0) -> list[str]:
        if self.is_win() or self.is_loss():
            return []
        if agent_index < 0 or agent_index >= self.get_num_agents():
            raise IndexError(f"Unknown agent index {agent_index}.")

        origin = self.robot if agent_index == 0 else self.hazards[agent_index - 1]
        hazard_index = agent_index - 1 if agent_index > 0 else None

        def hazard_respects_protected_perimeter(loc: GridLocation) -> bool:
            if any(loc.manhattan_distance(sv) <= 1 for sv in self.remaining_survivors):
                return False
            if not self.remaining_survivors and loc.manhattan_distance(self.layout.base) <= 1:
                return False
            return True

        if (
            agent_index > 0
            and self.hazard_model == "stationary"
            and hazard_respects_protected_perimeter(origin)
        ):
            return ["Stop"]

        legal: list[str] = []
        upwind_fallback: list[str] = []
        for action in ACTION_ORDER:
            is_upwind_fallback = False
            if agent_index > 0:
                wind_action = WIND_TO_ACTION.get(self.layout.wind, "East")
                last_action = self.get_hazard_last_actions()[hazard_index]
                if action == OPPOSITE_ACTION[wind_action] and action != last_action:
                    is_upwind_fallback = True
            dr, dc = ACTIONS[action]
            nxt = origin.moved(dr, dc)
            if action == "Stop":
                nxt = origin
            if not self.layout.in_bounds(nxt) or self.layout.is_wall(nxt):
                continue
            if agent_index > 0 and not self.layout.hazard_can_enter(nxt):
                continue
            if agent_index == 0:
                cost = 1 if action == "Stop" else self.layout.movement_cost(nxt)
                if cost > self.battery:
                    continue
            if agent_index > 0:
                if not hazard_respects_protected_perimeter(nxt):
                    continue
                if any(nxt == hazard for i, hazard in enumerate(self.hazards) if i != hazard_index):
                    continue
            if is_upwind_fallback:
                upwind_fallback.append(action)
            else:
                legal.append(action)
        if agent_index > 0 and not any(action != "Stop" for action in legal):
            legal.extend(action for action in upwind_fallback if action not in legal)
        return legal

    def generate_successor(self, agent_index: int, action: str) -> "RescueGameState":
        global SUCCESSOR_CALLS
        SUCCESSOR_CALLS += 1
        legal = self.get_legal_actions(agent_index)
        if action not in legal:
            raise ValueError(f"Illegal action {action!r} for agent {agent_index}; legal actions are {legal}.")

        if agent_index == 0:
            return self._robot_successor(action)
        return self._hazard_successor(agent_index, action)

    def _robot_successor(self, action: str) -> "RescueGameState":
        dr, dc = ACTIONS[action]
        nxt = self.robot if action == "Stop" else self.robot.moved(dr, dc)
        cost = 1 if action == "Stop" else self.layout.movement_cost(nxt)
        battery = self.battery - cost
        score = self.score - cost

        event = f"RescueBot moved {action}."
        remaining = set(self.remaining_survivors)
        if nxt in remaining:
            remaining.remove(nxt)
            score += RESCUE_BONUS
            event = "RescueBot reached a survivor marker."

        if self.layout.is_charger(nxt):
            battery = self.layout.initial_battery
            event = "RescueBot recharged at a field charging pad."

        lost = self.lost
        turns = self.turns + 1
        survived_at_base = not remaining and nxt == self.layout.base
        if nxt in self.hazards:
            lost = True
            event = "RescueBot entered an active hazard front."
        elif any(nxt.manhattan_distance(h) == 1 for h in self.hazards):
            event = "RescueBot is operating next to an active hazard."
        if not lost and battery <= 0 and not survived_at_base:
            lost = True
            event = "RescueBot depleted its battery."
        elif not lost and turns >= self.layout.max_turns and not survived_at_base:
            lost = True
            event = "The rescue window closed before evacuation."
        if lost and not self.lost:
            score += LOSS_PENALTY
        if not lost and not remaining and nxt == self.layout.base:
            score += WIN_BONUS
            event = "All survivor markers are secured and RescueBot returned to base."

        return RescueGameState(
            layout=self.layout,
            robot=nxt,
            hazards=self.hazards,
            remaining_survivors=frozenset(remaining),
            battery=battery,
            score=score,
            turns=turns,
            lost=lost,
            last_event=event,
            hazard_last_actions=self.get_hazard_last_actions(),
            hazard_model=self.hazard_model,
        )

    def _hazard_successor(self, agent_index: int, action: str) -> "RescueGameState":
        hazard_index = agent_index - 1
        dr, dc = ACTIONS[action]
        old = self.hazards[hazard_index]
        nxt = old if action == "Stop" else old.moved(dr, dc)
        hazards = list(self.hazards)
        hazards[hazard_index] = nxt
        score = self.score
        event = f"{self.get_agent_name(agent_index)} shifted {action}."
        lost = self.lost

        if nxt == self.robot:
            lost = True
            event = f"{self.get_agent_name(agent_index)} overtook RescueBot."
        elif nxt.manhattan_distance(self.robot) == 1:
            event = f"{self.get_agent_name(agent_index)} pressed close to RescueBot."
        if lost and not self.lost:
            score += LOSS_PENALTY

        last_actions = list(self.get_hazard_last_actions())
        if action != "Stop":
            last_actions[hazard_index] = action

        return RescueGameState(
            layout=self.layout,
            robot=self.robot,
            hazards=tuple(hazards),
            remaining_survivors=self.remaining_survivors,
            battery=self.battery,
            score=score,
            turns=self.turns,
            lost=lost,
            last_event=event,
            hazard_last_actions=tuple(last_actions),
            hazard_model=self.hazard_model,
        )
