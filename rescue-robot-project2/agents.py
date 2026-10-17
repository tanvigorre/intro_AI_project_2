from __future__ import annotations
import math

import evaluation
from rescue_core.actions import ACTION_ORDER


class Agent:
    def get_action(self, game_state):
        raise NotImplementedError


# === Q1 SELF-REFLECTION (1 point) ===
# Write 3-5 sentences below, at least 25 words total.
# This is a no-GenAI/coding-assistant assignment.
# State that you did not use GenAI, AI tools, coding assistants,
# posted solutions, or online resources that solve this project.
# Say how you checked your answer using course/local project resources.
# Include at least one concrete project detail, such as a function name,
# file name, map name, test id, or command you ran.
# Include one sentence explaining the Q1 reflex-agent concept in your own words.
#
# YOUR RESPONSE:
# Write your response here.
# === END Q1 SELF-REFLECTION ===

class ReflexRescueAgent(Agent):
    """A reflex agent chooses one action by scoring immediate successors."""

    def get_action(self, game_state):
        legal = game_state.get_legal_actions(0)
        if not legal:
            return "Stop"
        scores = [(self.evaluation_function(game_state, action), action) for action in legal]
        return max(scores, key=lambda item: (item[0], -ACTION_ORDER.index(item[1])))[1]

    def evaluation_function(self, current_game_state, action):
        """Return a number describing how desirable this immediate action is.
        
        Useful features include:
        - successor score,
        - distance to the nearest remaining survivor,
        - distance back to triage base after all survivors are secured,
        - distance to the nearest hazard,
        - remaining battery.
        """
        # TODO: Question 1
        successor = current_game_state.generate_successor(0, action)
        score = successor.get_score()
        new_position = successor.get_robot_position()
        
        surviving = successor.get_survivor_positions()
        hazards = successor.get_hazard_positions()
        base = successor.get_base_position()
        
        if surviving:
            survivor_distances = [abs(new_position.row - survivor.row)
            + abs(new_position.col - survivor.col)
            for survivor in surviving
            ]
            score -= 2.0 * min(survivor_distances)

        else:
            base_distance = abs(new_position.row - base.row) + abs(new_position.col - base.col)
            score -= 2.0 * base_distance

        for hazard in hazards:
            distance = abs(new_position.row - hazard.row) + abs(new_position.col - hazard.col)

            if distance == 0:
                score -= 100
            elif distance == 1:
                score -= 50
            elif distance == 2:
                score -= 5

        battery = successor.get_battery()
        score += 0.1 * battery
        
        return score


class MultiAgentSearchAgent(Agent):
    """Common settings for minimax, alpha-beta, and expectimax agents.

    depth counts RescueBot moves. A depth of 2 means RescueBot plans two of
    its own actions ahead, with every hazard agent moving after each one.
    """

    def __init__(self, eval_fn="score_evaluation_function", depth=2):
        if isinstance(eval_fn, str):
            self.evaluation_function = getattr(evaluation, eval_fn)
        else:
            self.evaluation_function = eval_fn
        self.depth = int(depth)


# === Q2 SELF-REFLECTION (1 point) ===
# Write 3-5 sentences below, at least 25 words total.
# This is a no-GenAI/coding-assistant assignment.
# State that you did not use GenAI, AI tools, coding assistants,
# posted solutions, or online resources that solve this project.
# Say how you checked your answer using course/local project resources.
# Include at least one concrete project detail, such as a function name,
# file name, map name, test id, or command you ran.
# Include one sentence explaining the Q2 minimax concept in your own words.
#
# YOUR RESPONSE:
# Write your response here.
# === END Q2 SELF-REFLECTION ===

class MinimaxAgent(MultiAgentSearchAgent):
    """Worst-case planner.

    RescueBot is agent 0 and maximizes value. Each hazard agent minimizes
    value. Cycle agent indices 0, 1, ..., get_num_agents() - 1; decrement
    depth only when the next turn returns to RescueBot.
    """

    def get_action(self, game_state):
    
    
        def minimax(state, depth, agent_index):
            if depth >= self.depth:
                return self.evaluation_function(state), None
            
            legal = state.get_legal_actions(agent_index)
            if not legal:
                return self.evaluation_function(state), None
            
            next_agent = (agent_index + 1) % state.get_num_agents()
            next_depth = depth + 1 if next_agent == 0 else depth

            if agent_index == 0:
                best_value = -math.inf
                best_action = None

                for action in legal:
                    successor = state.generate_successor(agent_index, action)
                    value, _ = minimax(successor, next_depth, next_agent)

                    if value > best_value:
                        best_value = value
                        best_action = action

                return best_value, best_action

            else:
                best_value = math.inf

                for action in legal:
                    successor = state.generate_successor(agent_index, action)
                    value, _ = minimax(successor, next_depth, next_agent)

                    if value < best_value:
                        best_value = value

                return best_value, None
        value, action = minimax(game_state, 0, 0)
        return action if action is not None else "Stop"
        
        


# === Q3 SELF-REFLECTION (1 point) ===
# Write 3-5 sentences below, at least 25 words total.
# This is a no-GenAI/coding-assistant assignment.
# State that you did not use GenAI, AI tools, coding assistants,
# posted solutions, or online resources that solve this project.
# Say how you checked your answer using course/local project resources.
# Include at least one concrete project detail, such as a function name,
# file name, map name, test id, or command you ran.
# Include one sentence explaining the Q3 alpha-beta concept in your own words.
#
# YOUR RESPONSE:
# Write your response here.
# === END Q3 SELF-REFLECTION ===

class AlphaBetaAgent(MultiAgentSearchAgent):
    """Minimax with alpha-beta pruning.

    Return the same action as MinimaxAgent while pruning branches that
    cannot change the decision. Carry alpha across RescueBot's root actions
    as well as through recursive max nodes.
    """

    def get_action(self, game_state):
        # TODO: Question 3
        raise NotImplementedError


# === Q4 SELF-REFLECTION (1 point) ===
# Write 3-5 sentences below, at least 25 words total.
# This is a no-GenAI/coding-assistant assignment.
# State that you did not use GenAI, AI tools, coding assistants,
# posted solutions, or online resources that solve this project.
# Say how you checked your answer using course/local project resources.
# Include at least one concrete project detail, such as a function name,
# file name, map name, test id, or command you ran.
# Include one sentence explaining the Q4 expectimax concept in your own words.
#
# YOUR RESPONSE:
# Write your response here.
# === END Q4 SELF-REFLECTION ===

class ExpectimaxAgent(MultiAgentSearchAgent):
    """Expected-value planner.

    RescueBot is still a max agent. Hazard nodes are chance nodes: average
    all legal successor values, including when there are multiple hazards.
    """

    def get_action(self, game_state):
        # TODO: Question 4
        raise NotImplementedError
