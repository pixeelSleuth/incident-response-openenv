"""
Incident Response Environment

OpenEnv-compliant environment for autonomous SRE incident response training.

Implements:
- step(action) -> observation, reward, done, info
- reset() -> initial observation
- state() -> full internal state
"""

import json
from typing import Dict, List, Tuple, Optional
from env.models import (
    Observation, Action, ActionType, Reward, SystemState,
    ServiceHealth, Alert, AlertSeverity, Metric, LogEntry
)
from env.dynamics import DynamicsEngine
from env.scenarios import ScenarioManager
from env.grader import IncidentGrader


class IncidentResponseEnv:
    """
    OpenEnv environment for incident response simulation.
    
    The agent receives observations (alerts, metrics, logs) and takes actions
    (restart services, investigate logs, scale, rollback) to resolve incidents.
    
    Incidents have hidden root causes that must be diagnosed and fixed.
    """
    
    def __init__(self, scenario_name: str = "easy_database_restart_1", max_steps: int = 50):
        """
        Initialize environment.
        
        Args:
            scenario_name: Name of scenario to load (from ScenarioManager)
            max_steps: Maximum steps before environment terminates
        """
        self.scenario_name = scenario_name
        self.max_steps = max_steps
        self.current_step = 0
        
        # Load scenario
        self.scenario = ScenarioManager.get_scenario_by_name(scenario_name)
        
        # Initialize dynamics engine with scenario seed
        self.dynamics = DynamicsEngine(seed=self.scenario.seed)
        
        # Initialize grader
        self.grader = IncidentGrader()
        
        # State variables
        self._state: Optional[SystemState] = None
        self._initial_state: Optional[SystemState] = None
        self._actions_taken: List[Action] = []
        self._done = False
        
        # Observation history for grader
        self._observations: List[Observation] = []
    
    def reset(self) -> Observation:
        """
        Reset environment to initial state.
        
        Returns:
            Initial observation
        """
        self.current_step = 0
        self._actions_taken = []
        self._done = False
        self._observations = []
        
        # Create healthy baseline
        self._state = self.dynamics.initialize_healthy_state()
        
        # Apply incident
        self._state = self.dynamics.apply_incident(self._state, self.scenario.incident_type)
        
        # Store initial state
        self._initial_state = self._state.model_copy(deep=True)
        
        # Generate observation
        observation = self._get_observation()
        self._observations.append(observation)
        
        return observation
    
    def step(self, action: Action) -> Tuple[Observation, Reward, bool, Dict]:
        """
        Execute one step in the environment.
        
        Args:
            action: Action to take
        
        Returns:
            (observation, reward, done, info)
        """
        if self._state is None:
            raise RuntimeError("Environment not initialized. Call reset() first.")
        
        if self._done:
            raise RuntimeError("Episode is done. Call reset() to start a new episode.")
        
        self.current_step += 1
        self._actions_taken.append(action)
        
        # Apply action to state
        action_service = action.service if action.service else None
        action_type = action.action_type.value
        
        # Update state dynamics
        self._state, incident_fixed = self.dynamics.step(
            self._state, action_type, action_service
        )
        
        # Generate observation
        observation = self._get_observation()
        self._observations.append(observation)
        
        # Compute reward
        reward = self._compute_reward(action, incident_fixed)
        
        # Check if done
        done = False
        if incident_fixed and self.current_step > 5:
            done = True
        elif self.current_step >= self.max_steps:
            done = True
        
        self._done = done
        
        # Info dict
        info = {
            "step": self.current_step,
            "incident_resolved": self._state.incident_resolved,
            "root_cause_service": self._state.root_cause_service,
            "root_cause_type": self._state.root_cause_type,
        }
        
        return observation, reward, done, info
    
    def state(self) -> SystemState:
        """
        Get the full internal system state (ground truth).
        
        This is NOT visible to the agent during normal operation but is
        available for analysis and grading.
        """
        if self._state is None:
            raise RuntimeError("Environment not initialized. Call reset() first.")
        
        return self._state.model_copy(deep=True)
    
    def _get_observation(self) -> Observation:
        """Generate observation visible to agent."""
        if self._state is None:
            raise RuntimeError("Environment not initialized.")
        
        # Generate metrics
        metrics = []
        for svc_name, svc_state in self._state.services.items():
            metrics.extend([
                Metric(
                    name="cpu_usage",
                    service=svc_name,
                    value=svc_state.get("cpu_usage", 0),
                    threshold=80.0,
                    timestamp=self._state.timestamp
                ),
                Metric(
                    name="memory_usage",
                    service=svc_name,
                    value=svc_state.get("memory_usage", 0),
                    threshold=85.0,
                    timestamp=self._state.timestamp
                ),
                Metric(
                    name="error_rate",
                    service=svc_name,
                    value=svc_state.get("error_rate", 0),
                    threshold=0.05,
                    timestamp=self._state.timestamp
                ),
                Metric(
                    name="latency_ms",
                    service=svc_name,
                    value=svc_state.get("latency_ms", 50),
                    threshold=500.0,
                    timestamp=self._state.timestamp
                ),
            ])
        
        # Generate service health summary
        service_health = {}
        for svc_name, svc_state in self._state.services.items():
            if svc_state.get("healthy", False):
                service_health[svc_name] = ServiceHealth.HEALTHY
            elif svc_state.get("error_rate", 0) > 0.1 or svc_state.get("latency_ms", 0) > 1000:
                service_health[svc_name] = ServiceHealth.UNHEALTHY
            else:
                service_health[svc_name] = ServiceHealth.DEGRADED
        
        # Generate alerts and logs with noise
        alerts, logs = self.dynamics.add_noise_and_logs(self._state, self.scenario.task_name)
        
        observation = Observation(
            timestamp=self._state.timestamp,
            alerts=alerts,
            metrics=metrics,
            logs=logs,
            service_health=service_health,
        )
        
        return observation
    
    def _compute_reward(self, action: Action, incident_fixed: bool) -> Reward:
        """
        Compute reward for this step.
        
        Components:
        - +0.4 for fixing root cause
        - +0.2 for system recovery
        - +0.1 for investigation
        - -0.2 for wrong action
        - -0.05 penalty per step
        """
        reward = Reward(total=0.0)
        
        # Step penalty
        reward.step_penalty = -0.05
        
        # Root cause fix bonus
        if incident_fixed:
            reward.root_cause_fix = 0.4

        # System recovery bonus
        if self._state.incident_resolved and self._is_system_recovered():
            reward.system_recovery = 0.2
        
        # Action bonuses/penalties
        if action.action_type == ActionType.INVESTIGATE_LOGS:
            # Investigation receives consistent positive signal.
            reward.investigation_reward = 0.02
        
        elif action.action_type == ActionType.RESTART_SERVICE:
            if action.service != self._state.root_cause_service:
                reward.action_penalty = -0.25
            elif (
                self._state.root_cause_type == "memory_leak"
                and action.service not in self._state.investigated_services
            ):
                # Penalize blind restart for hard scenarios.
                reward.action_penalty = -0.25
            elif (
                self._state.root_cause_type == "latency"
                and not {"auth_service", "database"}.issubset(set(self._state.investigated_services))
            ):
                # Medium scenarios require dependency investigation.
                reward.action_penalty = -0.25
        
        elif action.action_type == ActionType.SCALE_SERVICE:
            if action.service != self._state.root_cause_service:
                reward.action_penalty = -0.25
        
        elif action.action_type == ActionType.ROLLBACK_DEPLOYMENT:
            if action.service != self._state.root_cause_service:
                reward.action_penalty = -0.25
        
        elif action.action_type == ActionType.NOOP:
            reward.action_penalty = -0.25
        
        # Compute total
        reward.total = (
            reward.root_cause_fix +
            reward.system_recovery +
            reward.action_efficiency +
            reward.investigation_reward +
            reward.step_penalty +
            reward.action_penalty
        )
        
        return reward

    def _is_system_recovered(self) -> bool:
        """Return True when all services are back to healthy operating ranges."""
        if self._state is None:
            return False

        for svc_state in self._state.services.values():
            if svc_state.get("error_rate", 1.0) > 0.05:
                return False
            if svc_state.get("latency_ms", 9999) > 300:
                return False
            if svc_state.get("cpu_usage", 100.0) > 85:
                return False
            if svc_state.get("memory_usage", 100.0) > 90:
                return False

        return True
    
    def get_grade(self) -> Tuple[float, Dict]:
        """
        Get final grade for episode (after done=True).
        
        Returns:
            (score, components_dict)
        """
        if not self._done or self._initial_state is None:
            raise RuntimeError("Can only grade after episode is done.")
        
        return self.grader.grade(
            self._initial_state,
            self._state,
            self._actions_taken,
            self.max_steps
        )
    
    def render(self) -> str:
        """
        Render current environment state as string.
        
        Useful for debugging and visualization.
        """
        if self._state is None:
            return "Environment not initialized"
        
        output = []
        output.append(f"=== Incident Response Environment ===")
        output.append(f"Step: {self.current_step}/{self.max_steps}")
        output.append(f"Scenario: {self.scenario_name}")
        output.append(f"Incident Resolved: {self._state.incident_resolved}")
        output.append(f"Root Cause: {self._state.root_cause_service} ({self._state.root_cause_type})")
        output.append(f"")
        
        output.append(f"Service Status:")
        for svc_name, svc_state in self._state.services.items():
            output.append(
                f"  {svc_name}: "
                f"err={svc_state.get('error_rate', 0):.2%}, "
                f"lat={svc_state.get('latency_ms', 0)}ms, "
                f"cpu={svc_state.get('cpu_usage', 0):.0f}%, "
                f"mem={svc_state.get('memory_usage', 0):.0f}%"
            )
        
        output.append(f"")
        output.append(f"Actions Taken: {len(self._actions_taken)}")
        for i, action in enumerate(self._actions_taken[-5:]):  # Show last 5
            output.append(f"  {i+1}. {action.action_type.value}({action.service})")
        
        return "\n".join(output)


def create_env(scenario_name: str = "easy_database_restart_1") -> IncidentResponseEnv:
    """Factory function to create an environment."""
    return IncidentResponseEnv(scenario_name=scenario_name, max_steps=50)


class IncidentEnv(IncidentResponseEnv):
    """Backward-compatible alias that matches requested class naming."""

