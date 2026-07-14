"""DQN dynamic-pricing agent skeleton (illustrative blueprint).

Demonstrates the state/action/reward contract of the production agent.
Network weights, training data, and the historical simulator are proprietary
and omitted.
"""
from dataclasses import dataclass

import torch
import torch.nn as nn

# Bounded action space: continuous rate moves discretized to 1% steps across
# -15% .. +35% of baseline rack rate. The bounds exist to prevent a
# race-to-the-bottom feedback loop with competitor pricing algorithms.
ACTION_LOWER_PCT = -0.15
ACTION_UPPER_PCT = +0.35
N_ACTIONS = 51


@dataclass
class PricingState:
    """State vector S — assembled from the Feast online store in <15 ms."""

    otb_velocity: float          # on-the-book booking velocity vs capacity
    days_to_arrival: int         # DTA window
    competitor_delta: float      # scraped hourly, normalized vs own rate
    demand_q10: float            # TFT quantile forecasts (tau = 0.1 / 0.5 / 0.9)
    demand_q50: float
    demand_q90: float
    # ... calendar encodings, property static embedding (24 dims total)


class QNetwork(nn.Module):
    def __init__(self, state_dim: int = 24, n_actions: int = N_ACTIONS):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(state_dim, 128),
            nn.ReLU(),
            nn.Linear(128, 128),
            nn.ReLU(),
            nn.Linear(128, n_actions),
        )

    def forward(self, state: torch.Tensor) -> torch.Tensor:
        return self.net(state)


def reward(occupancy: torch.Tensor, adr: torch.Tensor, overprice_vacancy_penalty: torch.Tensor) -> torch.Tensor:
    """R = sum(Occupancy * ADR) - Penalty(overprice-vacancy).

    Maximizes yield over a rolling 30-day booking window while heavily
    penalizing rooms priced into vacancy — an unsold room-night expires
    worthless at midnight.
    """
    return (occupancy * adr).sum() - overprice_vacancy_penalty.sum()


def select_action(q_net: QNetwork, state: torch.Tensor, epsilon: float = 0.0) -> int:
    """epsilon-greedy: exploration only during offline historical simulation;
    production inference is pure argmax served via ONNX on Triton
    (p99 < 150 ms SLA)."""
    if epsilon > 0 and torch.rand(1).item() < epsilon:
        return int(torch.randint(N_ACTIONS, (1,)).item())
    with torch.no_grad():
        return int(q_net(state).argmax().item())


def action_to_rate_multiplier(action_index: int) -> float:
    """Map discretized action index back to a bounded rate multiplier."""
    step = (ACTION_UPPER_PCT - ACTION_LOWER_PCT) / (N_ACTIONS - 1)
    return 1.0 + ACTION_LOWER_PCT + action_index * step
