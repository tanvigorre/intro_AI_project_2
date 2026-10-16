from __future__ import annotations
import argparse
import json
import re
import signal
import traceback
from collections import Counter as WordCounter
from pathlib import Path

TOTAL_POINTS = 30
TEST_TIMEOUT_SECONDS = 20
REFLECTION_POINTS = 1
REFLECTION_MIN_WORDS = 25

REFLECTION_LOCATIONS = {
    "q1": "agents.py",
    "q2": "agents.py",
    "q3": "agents.py",
    "q4": "agents.py",
    "q5": "evaluation.py",
}

CONCRETE_REFLECTION_TERMS = {
    "agents.py", "evaluation.py", "autograder.py", "rescue.py",
    "rescue_core/game.py", "rescue_core/runner.py", "rescue_core/layout.py",
    "ReflexRescueAgent", "MinimaxAgent", "AlphaBetaAgent", "ExpectimaxAgent",
    "MultiAgentSearchAgent", "evaluation_function", "score_evaluation_function",
    "better_evaluation_function", "generate_successor", "get_legal_actions",
    "get_num_agents", "alpha", "beta", "minimax", "alpha-beta", "alphabeta",
    "expectimax", "reflex", "successor", "hazard", "training_corner",
    "fireline_rescue", "collapse_corridor", "pruning_showcase",
    "stochastic_smoke", "evaluation_gauntlet", "Planning successor calls",
    "two_fronts_station", "wind",
}

AI_RESOURCE_TERMS = (
    r"gen[- ]?ai|generative ai|artificial intelligence|ai tools?|ai assistance|"
    r"machine learning|large language models?|llms?|llm|chatgpt|openai|"
    r"copilot|claude|gemini|cursor|perplexity|deepseek|grok|bard|"
    r"windsurf|mistral|llama|codewhisperer|amazon q|tabnine|codeium|"
    r"qodo|meta ai|coding assistants?|code assistants?|programming assistants?|"
    r"chatbots?|autocomplete"
)

PROHIBITED_RESOURCE_TERMS = (
    r"posted solutions?|online solutions?|project solutions?|solution repositories?|"
    r"solution code|posted implementations?|public implementations?|github solutions?|"
    r"code-sharing sites?|forum answers?|tutorial code|outside code|external code|"
    r"online code help|project-specific help|answers? for this project|"
    r"online resources?[^.?!\n;]{0,80}(?:solve|solves|solving)"
)

NO_AI_ASSISTANCE_PATTERNS = [
    rf"\b(?:i\s+)?(?:did not|didn't|do not|don't|never)\s+(?:use|consult|access|rely on|ask|search|look up|visit)\b[^.?!\n;]{{0,140}}\b(?:{AI_RESOURCE_TERMS})\b",
    rf"\bwithout\s+(?:using|consulting|accessing|relying on|asking)\b[^.?!\n;]{{0,140}}\b(?:{AI_RESOURCE_TERMS})\b",
    rf"\bno\s+(?:{AI_RESOURCE_TERMS})\b",
    rf"\bavoided\b[^.?!\n;]{{0,120}}\b(?:{AI_RESOURCE_TERMS})\b",
]

NO_PROHIBITED_RESOURCE_PATTERNS = [
    rf"\b(?:i\s+)?(?:did not|didn't|do not|don't|never)\s+(?:use|consult|access|rely on|ask|search for|look up|visit|copy)\b[^.?!\n;]{{0,160}}\b(?:{PROHIBITED_RESOURCE_TERMS})\b",
    rf"\bwithout\s+(?:using|consulting|accessing|relying on|asking|copying)\b[^.?!\n;]{{0,160}}\b(?:{PROHIBITED_RESOURCE_TERMS})\b",
    rf"\bno\s+(?:{PROHIBITED_RESOURCE_TERMS})\b",
    rf"\bavoided\b[^.?!\n;]{{0,120}}\b(?:{PROHIBITED_RESOURCE_TERMS})\b",
]

VERIFICATION_PATTERNS = [
    r"\b(?:ran|run|running|tested|checked|verified|compared|debugged|inspected|traced|visualized)\b",
    r"\bautograder\.py\b",
    r"\brescue\.py\b",
    r"\b--no-graphics\b",
]

REFLECTION_STOPWORDS = {
    "i", "me", "my", "this", "that", "the", "a", "an", "and", "or", "to",
    "for", "of", "in", "on", "with", "by", "it", "is", "was", "were",
    "be", "because", "did", "not", "use", "used", "answer", "question",
}

CONCEPT_TERMS_BY_QID = {
    "q1": {
        "reflex agent", "one-step", "one step", "successor state",
        "survivor distance", "base distance", "hazard distance",
        "immediate action", "nearby hazard", "closest survivor",
        "return to base", "score an action", "legal action",
        "rescue progress", "look at the next state", "one move",
        "action evaluation", "reflex", "next state", "immediate",
    },
    "q2": {
        "minimax", "worst-case", "worst case", "min node", "max node",
        "search depth", "depth limit", "depth counting", "agent index",
        "backup value", "hazard agent", "recursion", "recursive search",
        "opponent", "assume the worst", "worst plausible", "turn order",
        "two players", "multi-agent", "game tree", "look ahead", "search ply",
        "minimize", "maximize", "adversarial search", "depth", "decrement",
        "minimum", "min", "backup", "layer",
    },
    "q3": {
        "alpha-beta", "alpha beta", "alpha bound", "beta bound",
        "pruning", "search bounds", "minimax value", "successor calls",
        "same action", "search branch", "skip branch", "cut off",
        "avoid expanding", "fewer nodes", "same minimax", "lower bound",
        "upper bound", "search efficiency", "prune branch", "expanded fewer",
        "unnecessary branch", "prune", "pruned", "bound", "bounds",
        "window", "node count", "skip",
    },
    "q4": {
        "expectimax", "expected value", "average value", "chance node",
        "chance agent", "hazard outcomes", "probability", "uncertainty",
        "random hazard", "stochastic hazard", "mean value", "not worst case",
        "sampled outcome", "possible outcomes", "average outcomes",
        "random motion", "chance events", "average", "averages",
        "expected", "chance", "randomness",
    },
    "q5": {
        "evaluation function", "state evaluation", "score function",
        "weighted feature", "survivor distance", "base distance",
        "hazard distance", "battery level", "terrain cost", "turn pressure",
        "state estimate", "non-terminal", "remaining survivors", "return to base",
        "route estimate", "weighted heuristic", "heuristic value",
        "state value", "closer survivor", "safer state", "stochastic maps",
        "feature tradeoff", "estimate", "guess", "weighted", "non-final",
        "heuristic",
    },
}

CASE_HINTS = {
    "Q1.1 Reflex prefers survivor progress": (
        "Moving East toward the survivor on training_corner should score above Stop.",
        "Check ReflexRescueAgent.evaluation_function in agents.py; score immediate successors, survivor distance, and Stop penalties.",
    ),
    "Q1.2 Reflex avoids nearby hazards": (
        "A safe nonfatal action should score above ending next to an active hazard.",
        "Check hazard-distance features in ReflexRescueAgent.evaluation_function, not only loss states.",
    ),
    "Q1.3 Reflex prioritizes survivor route": (
        "A move toward the survivor route should score above a small charging-pad detour.",
        "Check survivor-distance and rescue-priority features in the reflex evaluation.",
    ),
    "Q1.4 Reflex values returning to base": (
        "After all survivors are secured, moving toward triage base should score higher than moving away.",
        "Check get_base_position() and the no-survivors branch of ReflexRescueAgent.evaluation_function.",
    ),
    "Q1.5 Reflex secures adjacent survivor on evaluation_gauntlet": (
        "When a survivor marker is adjacent on evaluation_gauntlet, stepping onto it should score above waiting.",
        "Check that ReflexRescueAgent.evaluation_function rewards secured survivors even when another survivor remains farther away.",
    ),
    "Q1.6 Reflex returns a legal action": (
        "The reflex agent should return one legal RescueBot action and should not Stop at the opening of training_corner.",
        "Check get_action in ReflexRescueAgent and make sure evaluation_function returns comparable numbers.",
    ),
    "Q2.1 Minimax chooses best worst case": (
        "Minimax should choose the action with the best worst-case hazard response.",
        "Check MinimaxAgent.get_action and recursive min/max backups in agents.py.",
    ),
    "Q2.2 Minimax cycles through multiple hazards": (
        "Minimax must advance through all hazard agents before reducing the RescueBot depth.",
        "Check get_num_agents(), agent_index updates, and depth counting in MinimaxAgent.",
    ),
    "Q2.3 Minimax respects search depth": (
        "Depth 1 and depth 2 should be able to choose different actions on a deeper tree.",
        "Check that self.depth is used and that depth decreases only after all hazard agents move.",
    ),
    "Q2.4 Minimax returns a legal layout action": (
        "Minimax should return a legal non-losing opening action on fireline_rescue.",
        "Check legal actions, terminal tests, and evaluation_function use in MinimaxAgent.",
    ),
    "Q3.1 Alpha-beta matches minimax": (
        "Alpha-beta should return the same action as minimax on the test tree.",
        "Check AlphaBetaAgent's max/min logic before looking at pruning.",
    ),
    "Q3.2 Alpha-beta prunes": (
        "Alpha-beta should avoid expanding the late branch once the bound proves it cannot matter.",
        "Check alpha and beta updates and the pruning conditions in AlphaBetaAgent.",
    ),
    "Q3.3 Alpha-beta returns a legal layout action": (
        "Alpha-beta should return a legal non-losing opening action on collapse_corridor.",
        "Check AlphaBetaAgent.get_action and terminal-state handling.",
    ),
    "Q3.4 Alpha-beta matches minimax on pruning_showcase": (
        "Alpha-beta should return the same action as minimax on a real layout at depth 2.",
        "Check that pruning never changes the backed-up minimax value.",
    ),
    "Q4.1 Expectimax uses expected value": (
        "Expectimax should choose the higher-average action, even when its worst case is lower.",
        "Check that hazard nodes average successor values instead of taking min.",
    ),
    "Q4.2 Expectimax is not maximax": (
        "Expectimax should average all chance outcomes, not choose the best hazard outcome.",
        "Check the chance-node backup rule in ExpectimaxAgent.",
    ),
    "Q4.3 Expectimax cycles through multiple hazards": (
        "Expectimax must advance through all hazard agents before returning to RescueBot.",
        "Check get_num_agents(), agent-index updates, and chance-node averaging in ExpectimaxAgent.",
    ),
    "Q4.4 Expectimax returns a legal layout action": (
        "Expectimax should return a legal non-losing opening action on stochastic_smoke.",
        "Check ExpectimaxAgent.get_action and terminal-state handling.",
    ),
    "Q5.1 Provided score evaluation remains state score": (
        "The provided score_evaluation_function should still return current_game_state.get_score().",
        "Leave score_evaluation_function in evaluation.py unchanged while implementing better_evaluation_function.",
    ),
    "Q5.2 Better evaluation prefers equal-score rescue progress": (
        "With equal raw score, better_evaluation_function should prefer a state that has secured a survivor.",
        "Check survivor count and rescue-progress features in evaluation.py, not only get_score().",
    ),
    "Q5.3 Better evaluation uses survivor distance beyond score": (
        "With equal raw score, being closer to a remaining survivor should rank higher.",
        "Check survivor-distance features in better_evaluation_function.",
    ),
    "Q5.4 Better evaluation penalizes nearby hazards": (
        "Being farther from an active hazard should rank higher than standing next to one.",
        "Check hazard-distance penalties in better_evaluation_function.",
    ),
    "Q5.5 Better evaluation guides harder stochastic rescues": (
        "Expectimax with better_evaluation_function should win most harder random-hazard episodes and maintain a reasonable average score.",
        "Check survivor distance, return-to-base, hazard distance, turn pressure, and terrain-cost features.",
    ),
}


def result(name, score, max_score, output=""):
    score = round(float(score), 4)
    max_score = round(float(max_score), 4)
    status = "passed" if abs(score - max_score) < 1e-9 else "failed"
    return {"name": name, "score": score, "max_score": max_score, "status": status, "output": output}


def format_points(value):
    value = float(value)
    if value.is_integer():
        return str(int(value))
    return f"{value:.2f}".rstrip("0").rstrip(".")


def make_case(name, max_score, fn):
    return {"name": name, "max_score": max_score, "fn": fn}


class ReflectionError(AssertionError):
    """Raised when a required plain-comment self-reflection is missing."""


def _clean_comment_line(line):
    text = line.strip()
    if text.startswith("#"):
        text = text[1:].strip()
    return text


def _reflection_message(qid, filename, issue, found=None):
    qlabel = qid.upper()
    found_text = f"\n\nFound:\n{found}" if found else ""
    return (
        f"Expected behavior:\n"
        f"Complete the plain-comment self-reflection block for {qlabel}.\n\n"
        f"Where to complete it:\n"
        f"{filename}, inside the block labeled:\n"
        f"=== {qlabel} SELF-REFLECTION (1 point) ===\n\n"
        f"What to write:\n"
        f"Write 3-5 sentences, at least {REFLECTION_MIN_WORDS} words total. This is a no-GenAI/coding-assistant assignment.\n"
        f"Explicitly state that you did not use GenAI, AI tools, coding assistants, or autocomplete assistants for {qlabel}.\n"
        f"Also explicitly state that you did not use posted solutions, solution repositories, tutorial code, forum answers, online code-help resources, or other resources that directly solve this project.\n"
        f"Say how you checked your answer using the provided project files, local commands, lecture material, or course resources.\n"
        f"Also include one sentence about the concept you worked on in your own words.\n"
        f"Plain-language concept wording is fine, such as minimax assumes the worst plausible hazard response, alpha-beta skips branches that cannot change the choice, or expectimax averages random hazard outcomes.\n"
        f"Include at least one concrete project detail, such as a function name, file name, map name, test id, or command.\n\n"
        f"Issue found:\n"
        f"{issue}{found_text}\n\n"
        f"Concrete detail examples:\n"
        f"ExpectimaxAgent, better_evaluation_function, stochastic_smoke, Planning successor calls, autograder.py -q {qid}\n\n"
        f"Example:\n"
        f"# I did not use GenAI, AI tools, coding assistants, posted solutions, or online project-solving resources for {qlabel}.\n"
        f"# I worked from the lecture notes and the provided RescueBot files.\n"
        f"# I checked my answer by running python3.13 autograder.py -q {qid} and testing stochastic_smoke in rescue.py.\n"
        f"# This question helped me explain the search backup rule in my own words."
    )


def has_no_ai_assistance_attestation(response):
    lowered = response.lower()
    return any(re.search(pattern, lowered) for pattern in NO_AI_ASSISTANCE_PATTERNS)


def has_no_prohibited_resource_attestation(response):
    lowered = response.lower()
    return any(re.search(pattern, lowered) for pattern in NO_PROHIBITED_RESOURCE_PATTERNS)


def has_verification_evidence(response):
    lowered = response.lower()
    return any(re.search(pattern, lowered) for pattern in VERIFICATION_PATTERNS)


def has_repetition_problem(response):
    tokens = [
        token.lower()
        for token in re.findall(r"[A-Za-z0-9_./-]+", response)
        if token.lower() not in REFLECTION_STOPWORDS
    ]
    if len(tokens) < 12:
        return False
    token, count = WordCounter(tokens).most_common(1)[0]
    return count >= 5 and count / len(tokens) > 0.25


def has_concrete_project_detail(response):
    lowered = response.lower()
    for term in CONCRETE_REFLECTION_TERMS:
        pattern = r"(?<![A-Za-z0-9_])" + re.escape(term.lower()) + r"(?![A-Za-z0-9_])"
        if re.search(pattern, lowered):
            return True
    if re.search(r"\bq[1-5](?:\.(?:[1-9]|r))?\b", lowered):
        return True
    if re.search(r"\b(?:python3(?:\.13)?|py -3\.13)\b", lowered) and (
        "autograder.py" in lowered or "rescue.py" in lowered
    ):
        return True
    return False


def has_concept_evidence(qid, response):
    lowered = response.lower()
    for term in CONCEPT_TERMS_BY_QID.get(qid, set()):
        pattern = r"(?<![A-Za-z0-9_])" + re.escape(term.lower()) + r"(?![A-Za-z0-9_])"
        if re.search(pattern, lowered):
            return True
    return False


def check_reflection(qid, filename):
    qlabel = qid.upper()
    path = Path(filename)
    if not path.exists():
        raise ReflectionError(_reflection_message(qid, filename, f"{filename} was not found."))

    lines = path.read_text(encoding="utf-8").splitlines()
    start_text = f"=== {qlabel} SELF-REFLECTION"
    end_text = f"=== END {qlabel} SELF-REFLECTION ==="

    start_idx = next((i for i, line in enumerate(lines) if start_text in line), None)
    if start_idx is None:
        raise ReflectionError(_reflection_message(
            qid, filename, f"The {qlabel} self-reflection block is missing."
        ))

    end_idx = next((i for i in range(start_idx + 1, len(lines)) if end_text in lines[i]), None)
    if end_idx is None:
        raise ReflectionError(_reflection_message(
            qid, filename, f"The {qlabel} self-reflection block has no END marker."
        ))

    response_idx = next((i for i in range(start_idx + 1, end_idx) if "YOUR RESPONSE:" in lines[i]), None)
    if response_idx is None:
        raise ReflectionError(_reflection_message(
            qid, filename, "The block is present, but the YOUR RESPONSE marker is missing."
        ))

    marker_line = _clean_comment_line(lines[response_idx])
    marker_match = re.search(r"YOUR RESPONSE:\s*(.*)$", marker_line, flags=re.IGNORECASE)
    marker_response = marker_match.group(1).strip() if marker_match else ""
    response_lines = [marker_response] if marker_response else []
    response_lines.extend(_clean_comment_line(line) for line in lines[response_idx + 1:end_idx])
    response_lines = [
        line for line in response_lines
        if line and not line.startswith("===") and "YOUR RESPONSE:" not in line
    ]
    response = " ".join(response_lines)
    response = re.sub(r"\s+", " ", response).strip()

    placeholders = {
        "todo", "tbd", "n/a", "na", "none", "no", "...", ".", "placeholder",
        "your response", "write your response here", "replace this text",
    }
    normalized = response.lower().strip()
    normalized = re.sub(r"[^a-z0-9\s/.-]", "", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()

    if not response:
        raise ReflectionError(_reflection_message(
            qid, filename, "The block is present, but YOUR RESPONSE is blank."
        ))
    if normalized in placeholders:
        raise ReflectionError(_reflection_message(
            qid, filename, "The response appears to be placeholder text.", found=response
        ))

    words = re.findall(r"[A-Za-z0-9']+", response)
    if len(words) < REFLECTION_MIN_WORDS:
        raise ReflectionError(_reflection_message(
            qid, filename,
            f"The response is too short to count as a complete reflection. It has {len(words)} words; expected at least {REFLECTION_MIN_WORDS}.",
            found=response,
        ))
    if not has_no_ai_assistance_attestation(response):
        raise ReflectionError(_reflection_message(
            qid, filename,
            "The response must explicitly state that you did not use GenAI, AI tools, coding assistants, or autocomplete assistants for this question.",
            found=response,
        ))
    if not has_no_prohibited_resource_attestation(response):
        raise ReflectionError(_reflection_message(
            qid, filename,
            "The response must explicitly state that you did not use posted solutions, solution repositories, tutorial code, forum answers, online code-help resources, or other resources that directly solve this project.",
            found=response,
        ))
    if not has_verification_evidence(response):
        raise ReflectionError(_reflection_message(
            qid, filename,
            "The response does not explain how you checked, tested, verified, debugged, or inspected your answer.",
            found=response,
        ))
    if not has_concrete_project_detail(response):
        raise ReflectionError(_reflection_message(
            qid, filename,
            "The response is too generic. Include at least one concrete project detail such as a function name, file name, map name, test id, or command.",
            found=response,
        ))
    if not has_concept_evidence(qid, response):
        raise ReflectionError(_reflection_message(
            qid, filename,
            "The response does not explain the question's AI concept in your own words.",
            found=response,
        ))
    if has_repetition_problem(response):
        raise ReflectionError(_reflection_message(
            qid, filename,
            "The response repeats the same nontrivial word too many times and appears to be filler rather than a reflection.",
            found=response,
        ))

    return f"Completed self-reflection in {filename} ({len(words)} words)."


def reflection_case(qid):
    filename = REFLECTION_LOCATIONS[qid]
    return make_case(f"{qid.upper()}.R Self-reflection for {qid.upper()}", REFLECTION_POINTS,
                     lambda qid=qid, filename=filename: check_reflection(qid, filename))


def run_case(case):
    old_handler = signal.getsignal(signal.SIGALRM)

    def _timeout(signum, frame):
        raise TimeoutError(
            f"Test exceeded {TEST_TIMEOUT_SECONDS}s. Check recursion depth, terminal conditions, and agent-index wraparound."
        )

    try:
        signal.signal(signal.SIGALRM, _timeout)
        signal.alarm(TEST_TIMEOUT_SECONDS)
        output = case["fn"]()
        return result(case["name"], case["max_score"], case["max_score"], output or "Passed.")
    except TimeoutError as exc:
        return result(
            case["name"],
            0,
            case["max_score"],
            f"TimeoutError: {exc}\nLikely place to check: depth counting, terminal checks, and recursive agent cycling in agents.py.",
        )
    except ReflectionError as exc:
        return result(case["name"], 0, case["max_score"], str(exc))
    except Exception as exc:
        expected, check = CASE_HINTS.get(case["name"], ("See the test name for the expected behavior.", "Check the function named by this question."))
        output = f"{type(exc).__name__}: {exc}\n" + traceback.format_exc(limit=5)
        output = f"Expected behavior: {expected}\nLikely place to check: {check}\n\n{output}"
        return result(case["name"], 0, case["max_score"], output)
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)


class Counter:
    def __init__(self):
        self.count = 0


class TreeState:
    def __init__(self, transitions, scores, node="root", num_agents=2, counter=None):
        self.transitions = transitions
        self.scores = scores
        self.node = node
        self.num_agents = num_agents
        self.counter = counter if counter is not None else Counter()

    def get_num_agents(self):
        return self.num_agents

    def get_legal_actions(self, agent_index=0):
        if self.node in self.scores:
            return []
        return list(self.transitions.get(self.node, {}).get(agent_index, {}).keys())

    def generate_successor(self, agent_index, action):
        legal = self.transitions.get(self.node, {}).get(agent_index, {})
        if action not in legal:
            raise ValueError(f"Illegal action {action!r} at node {self.node!r} for agent {agent_index}.")
        self.counter.count += 1
        return TreeState(self.transitions, self.scores, legal[action], self.num_agents, self.counter)

    def is_win(self):
        return self.node in self.scores and self.scores[self.node] >= 0

    def is_loss(self):
        return self.node in self.scores and self.scores[self.node] < 0

    def get_score(self):
        return self.scores.get(self.node, 0)

    def get_robot_position(self):
        from rescue_core.location import GridLocation
        return GridLocation(0, 0)

    def get_hazard_positions(self):
        return ()

    def get_survivor_positions(self):
        return ()

    def get_base_position(self):
        from rescue_core.location import GridLocation
        return GridLocation(0, 0)

    def get_battery(self):
        return 0

    def get_turns(self):
        return 0

    def get_tile_cost(self, loc):
        return 1


def load_state(name):
    from rescue_core.game import RescueGameState
    from rescue_core.layout import load_layout
    from rescue_core.parser import resolve_map_path
    return RescueGameState.initial_state(load_layout(resolve_map_path(name)))


def q1_cases():
    def reflex_rescue_move_scores_higher():
        from agents import ReflexRescueAgent
        state = load_state("training_corner")
        agent = ReflexRescueAgent()
        east_score = agent.evaluation_function(state, "East")
        stop_score = agent.evaluation_function(state, "Stop")
        assert east_score > stop_score, f"Moving toward the survivor should score above stopping; got East={east_score}, Stop={stop_score}."
        return "The reflex evaluation prefers progress toward the survivor over stopping."

    def reflex_avoids_nearby_hazard():
        from dataclasses import replace
        from agents import ReflexRescueAgent
        from rescue_core.location import GridLocation
        state = load_state("training_corner")
        state = replace(state, robot=GridLocation(1, 3), hazards=(GridLocation(1, 5),), remaining_survivors=frozenset({GridLocation(3, 3)}))
        agent = ReflexRescueAgent()
        next_to_hazard = agent.evaluation_function(state, "East")
        safer = agent.evaluation_function(state, "West")
        assert safer > next_to_hazard, (
            f"A safer action should score above ending next to a hazard; "
            f"West={safer}, East={next_to_hazard}."
        )
        return "The reflex evaluation penalizes nonfatal hazard proximity."

    def reflex_prioritizes_survivor_route():
        from dataclasses import replace
        from agents import ReflexRescueAgent
        from rescue_core.location import GridLocation
        state = load_state("two_fronts_station")
        state = replace(state, robot=GridLocation(1, 3), hazards=(GridLocation(1, 9), GridLocation(4, 5)), remaining_survivors=frozenset({GridLocation(3, 3)}))
        agent = ReflexRescueAgent()
        toward_survivor = agent.evaluation_function(state, "South")
        charger_detour = agent.evaluation_function(state, "East")
        assert toward_survivor > charger_detour, (
            f"Moving toward the survivor route should score above a charging-pad detour; "
            f"South={toward_survivor}, East={charger_detour}."
        )
        return "The reflex evaluation prioritizes survivor progress over a charging-pad detour."

    def reflex_values_return_base():
        from dataclasses import replace
        from agents import ReflexRescueAgent
        from rescue_core.location import GridLocation
        state = load_state("training_corner")
        state = replace(state, robot=GridLocation(1, 3), hazards=(GridLocation(1, 6),), remaining_survivors=frozenset())
        agent = ReflexRescueAgent()
        toward_base = agent.evaluation_function(state, "West")
        away = agent.evaluation_function(state, "East")
        assert toward_base > away, f"After all survivors are secured, moving toward base should score higher; got West={toward_base}, East={away}."
        return "The reflex evaluation recognizes the return-to-base objective."

    def reflex_secures_adjacent_survivor_on_evaluation_gauntlet():
        from dataclasses import replace
        from agents import ReflexRescueAgent
        from rescue_core.location import GridLocation
        state = load_state("evaluation_gauntlet")
        state = replace(
            state,
            robot=GridLocation(3, 2),
            hazards=(GridLocation(1, 10), GridLocation(4, 6)),
            remaining_survivors=frozenset({GridLocation(3, 3), GridLocation(3, 9)}),
        )
        agent = ReflexRescueAgent()
        rescue_now = agent.evaluation_function(state, "East")
        wait = agent.evaluation_function(state, "Stop")
        assert rescue_now > wait, (
            f"On evaluation_gauntlet, stepping onto an adjacent survivor should score above waiting; "
            f"East={rescue_now}, Stop={wait}."
        )
        return "The reflex evaluation does not idle when a survivor marker is adjacent."

    def reflex_get_action_legal():
        from agents import ReflexRescueAgent
        state = load_state("training_corner")
        action = ReflexRescueAgent().get_action(state)
        assert action in state.get_legal_actions(0), f"ReflexRescueAgent returned illegal action {action!r}."
        assert action != "Stop", "The opening move should not be Stop on training_corner."
        return f"ReflexRescueAgent returned a legal opening action: {action}."

    return [
        make_case("Q1.1 Reflex prefers survivor progress", 0.5, reflex_rescue_move_scores_higher),
        make_case("Q1.2 Reflex avoids nearby hazards", 0.5, reflex_avoids_nearby_hazard),
        make_case("Q1.3 Reflex prioritizes survivor route", 0.75, reflex_prioritizes_survivor_route),
        make_case("Q1.4 Reflex values returning to base", 0.75, reflex_values_return_base),
        make_case("Q1.5 Reflex secures adjacent survivor on evaluation_gauntlet", 0.75, reflex_secures_adjacent_survivor_on_evaluation_gauntlet),
        make_case("Q1.6 Reflex returns a legal action", 0.75, reflex_get_action_legal),
        reflection_case("q1"),
    ]


def q2_cases():
    def minimax_worst_case_choice():
        from agents import MinimaxAgent
        transitions = {
            "root": {0: {"quick": "quick_h", "secure": "secure_h"}},
            "quick_h": {1: {"flare": "quick_bad", "clear": "quick_good"}},
            "secure_h": {1: {"flare": "secure_bad", "clear": "secure_good"}},
        }
        scores = {"quick_bad": -5, "quick_good": 20, "secure_bad": 4, "secure_good": 6}
        action = MinimaxAgent(depth=1).get_action(TreeState(transitions, scores))
        assert action == "secure", f"Minimax should choose the best worst-case action 'secure'; got {action!r}."
        return "Minimax selected the action with the stronger worst-case outcome."

    def minimax_cycles_through_two_hazards():
        from agents import MinimaxAgent
        transitions = {
            "root": {0: {"left": "left_f", "right": "right_f"}},
            "left_f": {1: {"north": "left_calm", "south": "left_collapse"}},
            "left_calm": {2: {"hold": "left_good", "shift": "left_bad"}},
            "left_collapse": {2: {"hold": "left_mid", "shift": "left_worst"}},
            "right_f": {1: {"north": "right_calm", "south": "right_collapse"}},
            "right_calm": {2: {"hold": "right_good", "shift": "right_mid"}},
            "right_collapse": {2: {"hold": "right_ok", "shift": "right_ok2"}},
        }
        scores = {
            "left_good": 12, "left_bad": 2, "left_mid": 3, "left_worst": -8,
            "right_good": 8, "right_mid": 5, "right_ok": 4, "right_ok2": 4,
        }
        action = MinimaxAgent(depth=1).get_action(TreeState(transitions, scores, num_agents=3))
        assert action == "right", f"Minimax must include both hazard agents before returning to RescueBot; got {action!r}."
        return "Minimax handled two hazard agents in the turn order."

    def minimax_respects_depth():
        from agents import MinimaxAgent

        class DeepTreeState(TreeState):
            def __init__(self, transitions, scores, terminal_nodes, node="root", counter=None):
                super().__init__(transitions, scores, node=node, num_agents=2, counter=counter)
                self.terminal_nodes = set(terminal_nodes)

            def generate_successor(self, agent_index, action):
                legal = self.transitions.get(self.node, {}).get(agent_index, {})
                if action not in legal:
                    raise ValueError(f"Illegal action {action!r} at node {self.node!r} for agent {agent_index}.")
                self.counter.count += 1
                return DeepTreeState(self.transitions, self.scores, self.terminal_nodes, legal[action], self.counter)

            def get_legal_actions(self, agent_index=0):
                if self.node in self.terminal_nodes:
                    return []
                return list(self.transitions.get(self.node, {}).get(agent_index, {}).keys())

            def is_win(self):
                return self.node in self.terminal_nodes and self.get_score() >= 0

            def is_loss(self):
                return self.node in self.terminal_nodes and self.get_score() < 0

        transitions = {
            "root": {0: {"near": "near_h", "detour": "detour_h"}},
            "near_h": {1: {"clear": "near_mid"}},
            "detour_h": {1: {"clear": "detour_mid"}},
            "near_mid": {0: {"finish": "near_finish_h"}},
            "detour_mid": {0: {"finish": "detour_finish_h"}},
            "near_finish_h": {1: {"hold": "near_good"}},
            "detour_finish_h": {1: {"hold": "detour_bad"}},
        }
        scores = {
            "near_mid": 5,
            "detour_mid": 6,
            "near_good": 20,
            "detour_bad": -1,
        }
        terminal_nodes = {"near_good", "detour_bad"}
        depth1 = MinimaxAgent(depth=1).get_action(DeepTreeState(transitions, scores, terminal_nodes))
        depth2 = MinimaxAgent(depth=2).get_action(DeepTreeState(transitions, scores, terminal_nodes))
        assert depth1 == "detour", f"At depth 1, minimax should prefer the better immediate evaluation 'detour'; got {depth1!r}."
        assert depth2 == "near", f"At depth 2, minimax should see the delayed outcome and prefer 'near'; got {depth2!r}."
        return "Minimax used self.depth; depth 1 and depth 2 selected different actions as expected."

    def minimax_real_layout_legal():
        from agents import MinimaxAgent
        state = load_state("fireline_rescue")
        action = MinimaxAgent(depth=1).get_action(state)
        assert action in state.get_legal_actions(0), f"Minimax returned illegal action {action!r}."
        successor = state.generate_successor(0, action)
        assert not successor.is_loss(), f"Minimax chose an immediate losing action {action!r}."
        return f"Minimax returned a legal non-losing action on fireline_rescue: {action}."

    return [
        make_case("Q2.1 Minimax chooses best worst case", 2, minimax_worst_case_choice),
        make_case("Q2.2 Minimax cycles through multiple hazards", 1.5, minimax_cycles_through_two_hazards),
        make_case("Q2.3 Minimax respects search depth", 1.5, minimax_respects_depth),
        make_case("Q2.4 Minimax returns a legal layout action", 1, minimax_real_layout_legal),
        reflection_case("q2"),
    ]


def q3_cases():
    def alphabeta_matches_minimax():
        from agents import AlphaBetaAgent, MinimaxAgent
        transitions = {
            "root": {0: {"quick": "quick_h", "secure": "secure_h"}},
            "quick_h": {1: {"flare": "quick_bad", "clear": "quick_good"}},
            "secure_h": {1: {"flare": "secure_bad", "clear": "secure_good"}},
        }
        scores = {"quick_bad": -5, "quick_good": 20, "secure_bad": 4, "secure_good": 6}
        tree = TreeState(transitions, scores)
        expected = MinimaxAgent(depth=1).get_action(tree)
        actual = AlphaBetaAgent(depth=1).get_action(TreeState(transitions, scores))
        assert actual == expected == "secure", f"Alpha-beta should match minimax; expected {expected!r}, got {actual!r}."
        return "Alpha-beta selected the same minimax action."

    def alphabeta_prunes_branch():
        from agents import AlphaBetaAgent
        counter = Counter()
        transitions = {
            "root": {0: {"first": "first_h", "second": "second_h"}},
            "first_h": {1: {"low": "first_low", "high": "first_high"}},
            "second_h": {1: {"prune": "second_low", "late": "second_late"}},
        }
        scores = {"first_low": 3, "first_high": 5, "second_low": 2, "second_late": 100}
        action = AlphaBetaAgent(depth=1).get_action(TreeState(transitions, scores, counter=counter))
        assert action == "first", f"Alpha-beta should choose 'first'; got {action!r}."
        assert counter.count <= 5, f"Alpha-beta should prune the late branch; generate_successor was called {counter.count} times."
        return f"Alpha-beta pruned the late branch with {counter.count} successor calls."

    def alphabeta_real_layout_legal():
        from agents import AlphaBetaAgent
        state = load_state("collapse_corridor")
        action = AlphaBetaAgent(depth=1).get_action(state)
        assert action in state.get_legal_actions(0), f"AlphaBetaAgent returned illegal action {action!r}."
        successor = state.generate_successor(0, action)
        assert not successor.is_loss(), f"AlphaBetaAgent chose an immediate losing action {action!r}."
        return f"Alpha-beta returned a legal non-losing action on collapse_corridor: {action}."

    def alphabeta_matches_minimax_real_layout():
        from agents import AlphaBetaAgent, MinimaxAgent
        state = load_state("pruning_showcase")
        minimax_action = MinimaxAgent(depth=2).get_action(state)
        alphabeta_action = AlphaBetaAgent(depth=2).get_action(state)
        assert alphabeta_action == minimax_action, (
            f"Alpha-beta should match minimax on pruning_showcase at depth 2; "
            f"minimax={minimax_action!r}, alpha-beta={alphabeta_action!r}."
        )
        return f"Alpha-beta matched minimax on pruning_showcase at depth 2: {alphabeta_action}."

    return [
        make_case("Q3.1 Alpha-beta matches minimax", 1.5, alphabeta_matches_minimax),
        make_case("Q3.2 Alpha-beta prunes", 1.5, alphabeta_prunes_branch),
        make_case("Q3.3 Alpha-beta returns a legal layout action", 1, alphabeta_real_layout_legal),
        make_case("Q3.4 Alpha-beta matches minimax on pruning_showcase", 1, alphabeta_matches_minimax_real_layout),
        reflection_case("q3"),
    ]


def q4_cases():
    def expectimax_uses_average_not_worst_case():
        from agents import ExpectimaxAgent
        transitions = {
            "root": {0: {"safe": "safe_h", "risk": "risk_h"}},
            "safe_h": {1: {"a": "safe_a", "b": "safe_b"}},
            "risk_h": {1: {"a": "risk_a", "b": "risk_b"}},
        }
        scores = {"safe_a": 5, "safe_b": 5, "risk_a": 0, "risk_b": 12}
        action = ExpectimaxAgent(depth=1).get_action(TreeState(transitions, scores))
        assert action == "risk", f"Expectimax should choose the higher average action 'risk'; got {action!r}."
        return "Expectimax chose the higher expected value instead of the safer worst case."

    def expectimax_not_maximax():
        from agents import ExpectimaxAgent
        transitions = {
            "root": {0: {"steady": "steady_h", "lure": "lure_h"}},
            "steady_h": {1: {"a": "steady_a", "b": "steady_b", "c": "steady_c"}},
            "lure_h": {1: {"a": "lure_a", "b": "lure_b", "c": "lure_c"}},
        }
        scores = {
            "steady_a": 40, "steady_b": 40, "steady_c": 40,
            "lure_a": 0, "lure_b": 0, "lure_c": 100,
        }
        action = ExpectimaxAgent(depth=1).get_action(TreeState(transitions, scores))
        assert action == "steady", f"Expectimax should use the average value and choose 'steady'; got {action!r}."
        return "Expectimax averaged chance outcomes rather than taking the maximum hazard outcome."

    def expectimax_cycles_through_two_hazards():
        from agents import ExpectimaxAgent
        transitions = {
            "root": {0: {"north": "north_f", "south": "south_f"}},
            "north_f": {1: {"calm": "north_calm_c", "flare": "north_flare_c"}},
            "north_calm_c": {2: {"hold": "n1", "shift": "n2"}},
            "north_flare_c": {2: {"hold": "n3", "shift": "n4"}},
            "south_f": {1: {"calm": "south_calm_c", "flare": "south_flare_c"}},
            "south_calm_c": {2: {"hold": "s1", "shift": "s2"}},
            "south_flare_c": {2: {"hold": "s3", "shift": "s4"}},
        }
        scores = {
            "n1": 8, "n2": 8, "n3": 0, "n4": 0,
            "s1": 5, "s2": 5, "s3": 5, "s4": 5,
        }
        action = ExpectimaxAgent(depth=1).get_action(TreeState(transitions, scores, num_agents=3))
        assert action == "south", f"Expectimax must average through both hazard agents; expected 'south', got {action!r}."
        return "Expectimax handled two hazard agents in the turn order."

    def expectimax_real_layout_legal():
        from agents import ExpectimaxAgent
        state = load_state("stochastic_smoke")
        action = ExpectimaxAgent(depth=1).get_action(state)
        assert action in state.get_legal_actions(0), f"Expectimax returned illegal action {action!r}."
        successor = state.generate_successor(0, action)
        assert not successor.is_loss(), f"Expectimax chose an immediate losing action {action!r}."
        return f"Expectimax returned a legal non-losing action on stochastic_smoke: {action}."

    return [
        make_case("Q4.1 Expectimax uses expected value", 1.5, expectimax_uses_average_not_worst_case),
        make_case("Q4.2 Expectimax is not maximax", 1.25, expectimax_not_maximax),
        make_case("Q4.3 Expectimax cycles through multiple hazards", 1.25, expectimax_cycles_through_two_hazards),
        make_case("Q4.4 Expectimax returns a legal layout action", 1, expectimax_real_layout_legal),
        reflection_case("q4"),
    ]


def q5_cases():
    def score_eval_returns_score():
        import evaluation
        state = load_state("training_corner")
        assert evaluation.score_evaluation_function(state) == state.get_score(), "Provided score_evaluation_function should still return game_state.get_score()."
        return "Provided score_evaluation_function still returned the game score."

    def better_eval_prefers_rescued_state():
        import evaluation
        from dataclasses import replace
        state = load_state("training_corner")
        after_east = state.generate_successor(0, "East")
        after_rescue = after_east.generate_successor(0, "East")
        after_rescue = replace(after_rescue, score=state.get_score())
        start_value = evaluation.better_evaluation_function(state)
        rescue_value = evaluation.better_evaluation_function(after_rescue)
        assert rescue_value > start_value, (
            f"With equal raw score, a state that has secured a survivor should rank higher; "
            f"start={start_value}, rescued={rescue_value}."
        )
        return "better_evaluation_function ranks rescue progress above an equal-score start state."

    def better_eval_prefers_closer_survivor_with_equal_score():
        import evaluation
        from dataclasses import replace
        from rescue_core.location import GridLocation
        state = load_state("training_corner")
        far = replace(state, robot=GridLocation(1, 2), hazards=(GridLocation(1, 6),), score=0)
        near = replace(state, robot=GridLocation(3, 4), hazards=(GridLocation(1, 6),), score=0)
        far_value = evaluation.better_evaluation_function(far)
        near_value = evaluation.better_evaluation_function(near)
        assert near_value > far_value, (
            f"With equal raw score, being closer to the remaining survivor should rank higher; "
            f"far={far_value}, near={near_value}."
        )
        return "better_evaluation_function uses state features beyond get_score()."

    def better_eval_penalizes_near_hazard():
        import evaluation
        from dataclasses import replace
        from rescue_core.location import GridLocation
        state = load_state("training_corner")
        far = replace(state, robot=GridLocation(3, 2), hazards=(GridLocation(1, 6),))
        near = replace(state, robot=GridLocation(1, 5), hazards=(GridLocation(1, 6),))
        far_value = evaluation.better_evaluation_function(far)
        near_value = evaluation.better_evaluation_function(near)
        assert far_value > near_value, f"Being far from a hazard should rank higher; far={far_value}, near={near_value}."
        return "better_evaluation_function penalizes operating next to hazards."

    def better_eval_guides_random_field_tests():
        from agents import ExpectimaxAgent
        from rescue_core.layout import load_layout
        from rescue_core.parser import resolve_map_path
        from rescue_core.runner import run_episode
        agent = ExpectimaxAgent(eval_fn="better_evaluation_function", depth=2)
        seeds_by_map = {
            "two_fronts_station": [2, 3, 5, 15, 18],
            "evaluation_gauntlet": [2, 4, 5, 15, 20],
        }
        wins = 0
        scores = []
        details = []
        for map_name, seeds in seeds_by_map.items():
            layout = load_layout(resolve_map_path(map_name))
            for seed in seeds:
                result = run_episode(layout, agent, hazard_policy="random", seed=seed)
                final = result.final_state
                wins += int(final.is_win())
                scores.append(final.get_score())
                details.append(f"{map_name}/seed{seed}:{'W' if final.is_win() else 'L'}:{final.get_score():.1f}")
        average_score = sum(scores) / len(scores)
        assert wins >= 7 and average_score >= -150, (
            "better_evaluation_function should guide robust play on harder stochastic maps. "
            f"Expected at least 7 wins out of 10 and average score >= -150; got wins={wins}, "
            f"average={average_score:.1f}. Details: {', '.join(details)}"
        )
        return f"better_evaluation_function won {wins}/10 harder stochastic episodes with average score {average_score:.1f}."

    return [
        make_case("Q5.1 Provided score evaluation remains state score", 0.5, score_eval_returns_score),
        make_case("Q5.2 Better evaluation prefers equal-score rescue progress", 1, better_eval_prefers_rescued_state),
        make_case("Q5.3 Better evaluation uses survivor distance beyond score", 1, better_eval_prefers_closer_survivor_with_equal_score),
        make_case("Q5.4 Better evaluation penalizes nearby hazards", 1, better_eval_penalizes_near_hazard),
        make_case("Q5.5 Better evaluation guides harder stochastic rescues", 1.5, better_eval_guides_random_field_tests),
        reflection_case("q5"),
    ]


QUESTION_CASES = [
    ("q1", "Q1 Reflex Rescue Agent", 5, q1_cases),
    ("q2", "Q2 Minimax Search", 7, q2_cases),
    ("q3", "Q3 Alpha-Beta Pruning", 6, q3_cases),
    ("q4", "Q4 Expectimax Search", 6, q4_cases),
    ("q5", "Q5 Evaluation Functions", 6, q5_cases),
]


def _assert_total_points():
    computed = 0
    for _, _, _, cases_fn in QUESTION_CASES:
        computed += sum(case["max_score"] for case in cases_fn())
    if abs(computed - TOTAL_POINTS) > 1e-9:
        raise AssertionError(f"Autograder point total drifted: computed {computed}, expected {TOTAL_POINTS}.")


def _select_questions(question_id):
    if question_id is None:
        return QUESTION_CASES
    q = question_id.lower().strip()
    lookup = {qid: (qid, title, max_score, cases_fn) for qid, title, max_score, cases_fn in QUESTION_CASES}
    if q not in lookup:
        valid = ", ".join(qid for qid, *_ in QUESTION_CASES)
        raise SystemExit(f"Unknown question {question_id!r}. Valid choices: {valid}")
    return [lookup[q]]


def main(argv=None):
    parser = argparse.ArgumentParser(description="Rescue Robot Project 2 autograder")
    parser.add_argument("-q", "--question", dest="question", default=None,
                        help="Run only one question, for example: -q q2")
    parser.add_argument("--no-graphics", action="store_true",
                        help="Accepted for compatibility; the autograder never opens graphics.")
    args = parser.parse_args(argv)

    _assert_total_points()
    if args.question and Path("/autograder/results").exists():
        print("Ignoring -q on Gradescope so the submitted run receives a full-project results.json.")
        args.question = None

    selected = _select_questions(args.question)
    all_results = []
    total = 0
    max_total = 0

    for _, title, _, cases_fn in selected:
        print(f"\n{title}")
        print("-" * len(title))
        q_results = []
        for case in cases_fn():
            r = run_case(case)
            q_results.append(r)
            all_results.append(r)
            print(f"{r['name']}: {format_points(r['score'])}/{format_points(r['max_score'])} {'PASS' if r['status'] == 'passed' else 'FAIL'}")
            if r["status"] != "passed":
                print(r["output"].rstrip())
        q_score = sum(r["score"] for r in q_results)
        q_max = sum(r["max_score"] for r in q_results)
        total += q_score
        max_total += q_max
        print(f"{title} subtotal: {format_points(q_score)}/{format_points(q_max)}")

    total = round(float(total), 4)
    max_total = round(float(max_total), 4)
    print(f"\nTotal: {format_points(total)}/{format_points(max_total)}")
    payload = {
        "score": total,
        "max_score": max_total,
        "tests": all_results,
        "stdout_visibility": "visible",
    }
    out_dir = Path("/autograder/results")
    if out_dir.exists():
        (out_dir / "results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    else:
        Path("results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return 0 if abs(total - max_total) < 1e-9 else 1


if __name__ == "__main__":
    raise SystemExit(main())
