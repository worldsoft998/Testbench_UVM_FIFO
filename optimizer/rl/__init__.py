"""Local RL / ANN engine for AId-UVO-RT.

Algorithms: Q-learning (tabular), DQN (pure-numpy ANN), PPO.
All training/inference runs locally. No external AI APIs.
"""

__all__ = [
    "base_agent",
    "q_learning",
    "dqn",
    "ppo",
    "replay_buffer",
    "reward",
    "state_encoder",
    "action_space",
]
