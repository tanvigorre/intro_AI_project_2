from __future__ import annotations
import math


def manhattan_distance(a, b) -> int:
    return abs(a.row - b.row) + abs(a.col - b.col)


def score_evaluation_function(current_game_state):
    """Provided default evaluation: return the current game score."""
    return current_game_state.get_score()


# === Q5 SELF-REFLECTION (1 point) ===
# Write 3-5 sentences below, at least 25 words total.
# This is a no-GenAI/coding-assistant assignment.
# State that you did not use GenAI, AI tools, coding assistants,
# posted solutions, or online resources that solve this project.
# Say how you checked your answer using course/local project resources.
# Include at least one concrete project detail, such as a function name,
# file name, map name, test id, or command you ran.
# Include one sentence explaining the Q5 evaluation-function concept in your own words.
#
# YOUR RESPONSE:
# Write your response here.
# === END Q5 SELF-REFLECTION ===

def better_evaluation_function(current_game_state):
    """Design a stronger state evaluation function for Question 5."""
    score = current_game_state.get_score()
    
    robot_position = current_game_state.get_robot_position()
    survivor_positions = current_game_state.get_survivor_positions()
    hazards = current_game_state.get_hazard_positions()
    base = current_game_state.get_base_position()
    battery = current_game_state.get_battery()
    turns = current_game_state.get_turns()
    
    distance_list = []
    
    robot_position = current_game_state.get_robot_position()
    survivor_positions = current_game_state.get_survivor_positions()
    if survivor_positions:
        for survivor in survivor_positions:
            distance = manhattan_distance(robot_position, survivor)
            distance_list.append(distance)
        
        nearest_distance = min(distance_list)
        score -= 2.0 * nearest_distance
        
    else:
        base_distance = manhattan_distance(robot_position, base)
        score -= 2.5 * base_distance
    
    for hazard in hazards:
        hazard_distance = manhattan_distance(robot_position, hazard)

        if hazard_distance == 0:
            score -= 100
        elif hazard_distance == 1:
            score -= 50
        elif hazard_distance == 2:
            score -= 10
        elif hazard_distance == 3:
            score -= 2

    # Reward conserving battery.
    score += 0.1 * battery

    # Penalize expensive terrain at the robot's current position.
    tile_cost = current_game_state.get_tile_cost(robot_position)
    score -= 1.0 * tile_cost

    # Slightly penalize taking too many turns.
    score -= 0.1 * turns

    return score
    
 
