"""
Deterministic Grader

Scores agent performance on a scale [0.0, 1.0] across multiple criteria:
- Root cause correctly fixed (0.4)
- System fully recovered (0.2)
- Minimal unnecessary actions (0.2)
- Efficiency (step count) (0.1)
- Correct action sequence (0.1)
"""

from typing import List, Dict, Tuple
from env.models import Action, ActionType, SystemState


class IncidentGrader:
    """Grades agent performance on incident resolution."""
    
    def __init__(self):
        """Initialize grader."""
        pass
    
    def grade(
        self,
        initial_state: SystemState,
        final_state: SystemState,
        actions_taken: List[Action],
        max_steps: int = 50,
    ) -> Tuple[float, Dict]:
        """
        Compute comprehensive grade for incident resolution.
        
        Args:
            initial_state: Starting system state
            final_state: Final system state after actions
            actions_taken: All actions taken by agent
            max_steps: Maximum expected steps (for efficiency scoring)
        
        Returns:
            (score, components_dict)
        """
        components = {
            "root_cause_fixed": self._score_root_cause_fixed(initial_state, final_state),
            "system_recovered": self._score_system_recovered(initial_state, final_state),
            "action_efficiency": self._score_action_efficiency(actions_taken),
            "step_efficiency": self._score_step_efficiency(len(actions_taken), max_steps),
            "action_sequence_correctness": self._score_action_sequence(
                actions_taken, initial_state.root_cause_type
            ),
        }
        
        # Weighted score
        score = (
            0.4 * components["root_cause_fixed"] +
            0.2 * components["system_recovered"] +
            0.2 * components["action_efficiency"] +
            0.1 * components["step_efficiency"] +
            0.1 * components["action_sequence_correctness"]
        )
        
        components["total_score"] = score
        return score, components
    
    def _score_root_cause_fixed(self, initial_state: SystemState, final_state: SystemState) -> float:
        """
        Score: Did the agent fix the root cause?
        
        0.0: Root cause not fixed
        0.5: Root cause partially fixed
        1.0: Root cause fully fixed
        """
        if not initial_state.root_cause_service:
            # No incident - perfect score
            return 1.0
        
        root_service = initial_state.root_cause_service
        
        if root_service not in final_state.services:
            return 0.0
        
        initial_svc = initial_state.services[root_service]
        final_svc = final_state.services[root_service]
        
        # Check if service health improved significantly
        initial_health_score = self._compute_service_health_score(initial_svc)
        final_health_score = self._compute_service_health_score(final_svc)
        
        # If final state has incident resolved, root cause was fixed
        if final_state.incident_resolved:
            svc = final_state.services[root_service]
            if (
                svc.get("error_rate", 1.0) <= 0.05
                and svc.get("latency_ms", 9999) <= 250
                and svc.get("cpu_usage", 100) <= 80
                and svc.get("memory_usage", 100) <= 85
            ):
                return 1.0
            else:
                return 0.6  # partially fixed but not fully stable
        
        # Otherwise compute based on health improvement
        if final_health_score > initial_health_score + 0.5:
            return 0.7  # Good progress
        elif final_health_score > initial_health_score:
            return 0.4  # Some improvement
        else:
            return 0.0  # No improvement
    
    def _score_system_recovered(self, initial_state: SystemState, final_state: SystemState) -> float:
        """
        Score: Is the overall system healthy?
        
        0.0: System still in incident
        1.0: System fully healthy
        """
        if not initial_state.root_cause_service:
            return 1.0
        
        # System recovered if:
        # 1. Incident marked as resolved
        # 2. All services have low error rates
        # 3. All services have acceptable latency
        
        if final_state.incident_resolved:
            score = 1.0
        else:
            score = 0.0
        
        # Bonus: check all services are somewhat healthy
        total_health = 0.0
        for svc_name, svc in final_state.services.items():
            total_health += self._compute_service_health_score(svc)
        
        avg_health = total_health / len(final_state.services)
        
        # If average health > 0.8, give partial credit even without full recovery
        if score == 0.0 and avg_health > 0.8:
            score = 0.5
        elif score == 0.0 and avg_health > 0.6:
            score = 0.2
        
        return min(1.0, score)
    
    def _score_action_efficiency(self, actions_taken: List[Action]) -> float:
        """
        Score: Were the actions taken appropriate and not wasteful?
        
        0.0: Many wrong actions
        1.0: All actions efficient and appropriate
        """
        if len(actions_taken) == 0:
            return 0.0  # No actions taken
        
        # Count action types
        action_counts = {}
        for action in actions_taken:
            action_type = action.action_type.value
            action_counts[action_type] = action_counts.get(action_type, 0) + 1
        
        # Scoring logic:
        # - Restart appropriate service is good
        # - Investigate logs is good (shows reasoning)
        # - Noops are neutral but not ideal
        # - Scaling when not needed is wasteful
        # - Multiple restarts of same service is inefficient
        
        score = 1.0
        
        # Penalize excessive restarts (more than 3)
        restart_count = action_counts.get("restart_service", 0)
        if restart_count > 3:
            score -= 0.15 * (restart_count - 3)
        
        # Penalize excessive noops
        noop_count = action_counts.get("noop", 0)
        if noop_count > 5:
            score -= 0.1 * (noop_count - 5)
        
        # Reward investigation (shows reasoning)
        investigate_count = action_counts.get("investigate_logs", 0)
        if investigate_count >= 2:
            score += 0.1
        
        # Scaling multiple times is slightly wasteful unless needed
        scale_count = action_counts.get("scale_service", 0)
        if scale_count > 2:
            score -= 0.05 * (scale_count - 2)
        
        return max(0.0, min(1.0, score))
    
    def _score_step_efficiency(self, num_steps: int, max_steps: int = 50) -> float:
        """
        Score: How many steps did it take?
        
        1.0: Very efficient (< 5 steps)
        0.5: Moderate (5-15 steps)
        0.0: Too many steps (> max_steps)
        """
        if num_steps <= 5:
            return 1.0
        elif num_steps <= 15:
            return 0.5 + 0.5 * (1 - (num_steps - 5) / 10)
        elif num_steps <= max_steps:
            return max(0.0, 0.5 * (1 - (num_steps - 15) / (max_steps - 15)))
        else:
            return 0.0
    
    def _score_action_sequence_correctness(
        self, actions_taken: List[Action], root_cause_type: str
    ) -> float:
        """
        Score: Was the sequence of actions logical for this incident type?
        
        This checks if the agent's action sequence aligns with the incident type.
        """
        if len(actions_taken) == 0:
            return 0.0
        
        action_types = [a.action_type for a in actions_taken]
        
        # For any incident type, investigating first is good
        if action_types[0] == ActionType.NOOP:
            return 0.2
        elif action_types[0] == ActionType.INVESTIGATE_LOGS:
            score = 0.7
        else:
            score = 0.5
        
        # If restart was eventually attempted, good
        if ActionType.RESTART_SERVICE in action_types:
            score += 0.2
        
        # Rollback is useful for deployment issues
        if ActionType.ROLLBACK_DEPLOYMENT in action_types:
            score += 0.1
        
        return min(1.0, score)
    
    def _score_action_sequence(
        self, actions_taken: List[Action], root_cause_type: str
    ) -> float:
        """Helper: score action sequence correctness."""
        return self._score_action_sequence_correctness(actions_taken, root_cause_type)
    
    def _compute_service_health_score(self, service_state: Dict) -> float:
        """
        Compute a health score for a single service [0.0, 1.0].
        
        Based on:
        - Error rate (lower is better)
        - Latency (lower is better)
        - Memory/CPU usage (lower is better)
        """
        score = 1.0
        
        # Error rate: 0.0 is perfect, 0.1+ is bad
        error_rate = service_state.get("error_rate", 0.0)
        if error_rate > 0.01:
            score -= min(0.6, error_rate)
        
        # Latency: baseline ~50ms, > 1000ms is bad
        latency = service_state.get("latency_ms", 50)
        if latency > 100:
            score -= min(0.2, (latency - 100) / 5000)
        
        # Memory: > 85% is concerning
        memory = service_state.get("memory_usage", 50)
        if memory > 85:
            score -= 0.2
        
        # CPU: > 80% is concerning
        cpu = service_state.get("cpu_usage", 30)
        if cpu > 80:
            score -= 0.1
        
        return max(0.0, score)


def grade_multiple_scenarios(
    scenario_results: Dict[str, Tuple[SystemState, SystemState, List[Action]]]
) -> Dict[str, Tuple[float, Dict]]:
    """
    Grade results from multiple scenarios.
    
    Args:
        scenario_results: mapping of scenario_name -> (initial_state, final_state, actions)
    
    Returns:
        mapping of scenario_name -> (score, components)
    """
    grader = IncidentGrader()
    results = {}
    
    for scenario_name, (initial_state, final_state, actions_taken) in scenario_results.items():
        score, components = grader.grade(initial_state, final_state, actions_taken)
        results[scenario_name] = (score, components)
    
    return results
