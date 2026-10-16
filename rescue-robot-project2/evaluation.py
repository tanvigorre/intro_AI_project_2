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
    # TODO: Question 5
    raise NotImplementedError
