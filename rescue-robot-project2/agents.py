from __future__ import annotations
import math

import evaluation
from evaluation import manhattan_distance
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
# I did not use generative AI, posted solutions, AI tools, online resources or a coding-assistant for this assignemnt as well as any online resources outside of allowed resources. I checked my answer using the autograder command (autograder.py -q q1), since it was able to provide useful information to help me identify how to interact with the data structures within each positions for the successors. I ran the manhattan distance function from evaluation so I could identify how far the agent was to pertinent landmarks within the game. The concept for the function was fairly simple in that the agent tries to seek out survivors and if there aren't any it will return to base. We also account for proximity to hazards and use this to reduce scores and subsequently add back battery for the player to make its next move.
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
        
        distance_list = []
        
        if surviving:
            for survivor in surviving:
                #survivor_distances = abs(new_position.row - survivor.row) + abs(new_position.col - survivor.col)
                survivor_distances = manhattan_distance(new_position,survivor)
                distance_list.append(survivor_distances)
            
            survivor_distance = min(distance_list)
            score -= 2.0 * survivor_distances

        else:
            #base_distance = abs(new_position.row - base.row) + abs(new_position.col - base.col)
            base_distance = manhattan_distance(new_position,base)
            score -= 2.0 * base_distance

        for hazard in hazards:
            #distance = abs(new_position.row - hazard.row) + abs(new_position.col - hazard.col)
            distance = manhattan_distance(new_position,hazard)

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
# I did not use generative AI, online or posted solutions, AI tools, or a coding-assistant for this assignemnt as well as any online resources outside of allowed resources (particularly for the , _ statement since I realized I only really needed the value from each time I recursively ran through the function). I checked my answer using the autograder (autograder.py -q q2) for question 2 as well as lecture notes on minimax which were very fruitful for figuring out the intial values for the min and max agents (sometimes I get them mixed up). For this function, I leveraged the evaluation function from question 1 so when the robot was done with its moves so it can be scored accordingly. As for how this process works, in essence you have the robot use the max agent while the rest use the min agent, which means we assume that the hazards will choose worse than the robot. 
# === END Q2 SELF-REFLECTION ===

class MinimaxAgent(MultiAgentSearchAgent):
    """Worst-case planner.

    RescueBot is agent 0 and maximizes value. Each hazard agent minimizes
    value. Cycle agent indices 0, 1, ..., get_num_agents() - 1; decrement
    depth only when the next turn returns to RescueBot.
    """

    def get_action(self, game_state):
    
        def minimax(robot, depth, agent_index):
            if depth >= self.depth:
                return self.evaluation_function(robot), None
            
            legal = robot.get_legal_actions(agent_index)
            if not legal:
                return self.evaluation_function(robot), None
            
            next_agent = (agent_index + 1) 
            if next_agent == robot.get_num_agents():
                next_agent = 0
                next_depth = depth + 1
            else:
                next_depth = depth

            if agent_index == 0:
                best_value = -math.inf
                best_action = None

                for action in legal:
                    successor = robot.generate_successor(agent_index, action)
                    value, _ = minimax(successor, next_depth, next_agent)

                    if value > best_value:
                        best_value = value
                        best_action = action

                return best_value, best_action

            else:
                best_value = math.inf

                for action in legal:
                    successor = robot.generate_successor(agent_index, action)
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
# I did not use GenAI, online or posted solutions, AI tools,  or any coding assistants to solve this problem. I checked my answer using the course materials, specifically the lecture slides on aplha-beta pruning. The pseduo-code provided in the slides was extremely helpful for implementing Q3, especially in thinking about the parameters needed for the alphabeta function. For this question, I followed the code structure from MinimaxAgent, but just extended it so the remianing leaves of a node would be skipped when beta becomes less than or equal to alpha.
# === END Q3 SELF-REFLECTION ===

class AlphaBetaAgent(MultiAgentSearchAgent):
    """Minimax with alpha-beta pruning.

    Return the same action as MinimaxAgent while pruning branches that
    cannot change the decision. Carry alpha across RescueBot's root actions
    as well as through recursive max nodes.
    """

    def get_action(self, game_state):
        # TODO: Question 3
        def alphabeta(state, depth, agent_index, alpha, beta):
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
                    value, _ = alphabeta(successor, next_depth, next_agent, alpha, beta)
            
                    if value > best_value:
                        best_value = value
                        best_action = action
            
                    alpha = max(alpha, best_value)
                    if beta <= alpha:
                        break
            
                return best_value, best_action
        
            else:
                best_value = math.inf
        
                for action in legal:
                    successor = state.generate_successor(agent_index, action)
                    value, _ = alphabeta(successor, next_depth, next_agent, alpha, beta)
        
                    if value < best_value:
                        best_value = value
        
                    beta = min(beta, best_value)
                    if beta <= alpha:
                        break
        
                return best_value, None
        
        value, action = alphabeta(game_state, 0, 0, -math.inf, math.inf)
        return action if action is not None else "Stop"


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
# I did not use GenAI, AI tools, coding assistants, posted solutions, or online resources that solve this project. I checked my answer using the expectimax lecture as well as the autograder (autograder.py -q q4) which helped me realize that I needed to re-initialize next_agent to zero so we can continue to loop through the function. With this question, it has a very similar premise to the minimax, only difference being it takes the average of the options and sees how its value compares. While the robot will have the max agent, the hazards will pick randomly in a sense. As for functions used, I had to use the generate_successor function to check for the next step so then we could identify which action would be selected.
# === END Q4 SELF-REFLECTION ===

class ExpectimaxAgent(MultiAgentSearchAgent):
    """Expected-value planner.

    RescueBot is still a max agent. Hazard nodes are chance nodes: average
    all legal successor values, including when there are multiple hazards.
    """

    def get_action(self, game_state):
        num_agents = game_state.get_num_agents()

        def expectimax(robot, depth, agent_index):
            if depth == self.depth or robot.is_win() or robot.is_loss():
                return self.evaluation_function(robot)

            actions = robot.get_legal_actions(agent_index)

            if not actions:
                return self.evaluation_function(robot)

            next_agent = (agent_index + 1) 
            if next_agent == robot.get_num_agents():
                next_agent = 0
                next_depth = depth + 1
            else:
                next_depth = depth

            if agent_index == 0:
                best_value = -math.inf

                for action in actions:
                    successor = robot.generate_successor(agent_index, action)
                    value = expectimax(successor, next_depth, next_agent)
                    best_value = max(best_value, value)

                return best_value

            total_value = 0

            for action in actions:
                successor = robot.generate_successor(agent_index, action)
                value = expectimax(successor, next_depth, next_agent)
                total_value += value

            return total_value / len(actions)

        
        actions = game_state.get_legal_actions(0)

        if not actions:
            return None

        best_action = None
        best_value = -math.inf

        for action in actions:
            successor = game_state.generate_successor(0, action)
            value = expectimax(successor, 0 if num_agents == 1 else 0, 1 if num_agents > 1 else 0)

            if num_agents == 1:
                value = expectimax(successor, 1, 0)

            if value > best_value:
                best_value = value
                best_action = action

        return best_action
