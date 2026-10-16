from __future__ import annotations
import argparse

from agents import ReflexRescueAgent, MinimaxAgent, AlphaBetaAgent, ExpectimaxAgent
from rescue_core.parser import available_maps, resolve_map_path
from rescue_core.layout import load_layout
from rescue_core.runner import run_episode


def build_agent(name: str, depth: int, eval_fn: str):
    if name == "reflex":
        return ReflexRescueAgent()
    if name == "minimax":
        return MinimaxAgent(depth=depth, eval_fn=eval_fn)
    if name == "alphabeta":
        return AlphaBetaAgent(depth=depth, eval_fn=eval_fn)
    if name == "expectimax":
        return ExpectimaxAgent(depth=depth, eval_fn=eval_fn)
    raise ValueError(f"Unknown agent {name!r}.")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Rescue Robot Project 2: adversarial search")
    parser.add_argument("--map", "--layout", dest="map_name", default="training_corner")
    parser.add_argument("--agent", choices=["reflex", "minimax", "alphabeta", "expectimax"], default="reflex")
    parser.add_argument("--depth", type=int, default=2)
    parser.add_argument("--eval", choices=["score_evaluation_function", "better_evaluation_function"],
                        default="score_evaluation_function",
                        help="Evaluation function for minimax, alpha-beta, and expectimax.")
    parser.add_argument("--hazards", choices=["auto", "adversarial", "random", "stationary"], default="auto",
                        help="Hazard policy. auto uses random hazards for expectimax and adversarial hazards otherwise; stationary freezes hazards in the episode and planning rollouts.")
    parser.add_argument("--seed", type=int, default=None,
                        help="Random seed for hazard motion. Omit it for a fresh random run; set it to reproduce a run.")
    parser.add_argument("--no-graphics", action="store_true")
    parser.add_argument("--manual", action="store_true",
                        help="Keyboard-control RescueBot while hazards respond after each move.")
    parser.add_argument("--frame-time", type=float, default=0.12)
    parser.add_argument("--list-maps", action="store_true")
    args = parser.parse_args(argv)

    if args.list_maps:
        print("Available rescue layouts:")
        for name in available_maps():
            print(f"  {name}")
        return 0

    layout = load_layout(resolve_map_path(args.map_name))
    hazard_policy = args.hazards
    if hazard_policy == "auto":
        hazard_policy = "random" if args.agent == "expectimax" else "adversarial"

    if args.manual:
        if args.no_graphics:
            raise ValueError("--manual requires graphics; remove --no-graphics.")
        from rescue_graphics.display import manual_play
        manual_play(layout, hazard_policy=hazard_policy, seed=args.seed)
        return 0

    agent = build_agent(args.agent, args.depth, args.eval)
    result = run_episode(layout, agent, hazard_policy=hazard_policy, seed=args.seed)
    final = result.final_state

    print(f"Map: {layout.name}")
    print(f"Agent: {args.agent}, depth: {args.depth}, eval: {args.eval}, hazards: {hazard_policy}")
    if hazard_policy == "random":
        seed_label = "fresh random run" if args.seed is None else args.seed
        print(f"Random seed: {seed_label}")
    print(f"Robot actions: {' '.join(result.robot_actions)}")
    if result.planning_expansions:
        total_expansions = sum(result.planning_expansions)
        avg_expansions = total_expansions / len(result.planning_expansions)
        max_expansions = max(result.planning_expansions)
        print(
            "Planning successor calls: "
            f"total={total_expansions}, avg={avg_expansions:.1f}, max={max_expansions}"
        )
    print(f"Turns used: {final.get_turns()}/{layout.max_turns}")
    print(f"Battery remaining: {final.get_battery()}/{layout.initial_battery}")
    print(f"Survivors remaining: {len(final.get_survivor_positions())}/{len(layout.survivors)}")
    print(f"Score: {final.get_score():.1f}")
    print(f"Outcome: {'WIN' if final.is_win() else 'LOSS' if final.is_loss() else 'IN PROGRESS'}")
    print(f"Last event: {final.last_event}")

    if not args.no_graphics:
        from rescue_graphics.display import animate
        animate(result.frames, delay=args.frame_time)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
