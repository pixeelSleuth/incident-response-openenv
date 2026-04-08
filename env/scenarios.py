"""
Task Scenarios

Defines 3 tasks with increasing difficulty:
- Easy: Single database outage
- Medium: Dependency failure (auth fails due to DB issues)
- Hard: Cascading failure (memory leak → CPU spike → cascading errors)
"""

from typing import Dict, List
from dataclasses import dataclass
import random


@dataclass
class ScenarioVariant:
    """A specific variant of a scenario."""
    scenario_id: str
    task_name: str
    incident_type: str
    seed: int
    description: str
    expected_root_cause: str
    difficulty: str


class ScenarioManager:
    """Manages task scenarios and variants."""
    
    @staticmethod
    def get_easy_scenarios() -> List[ScenarioVariant]:
        """
        EASY TASK: Database outage
        
        Clear signals:
        - Critical alert about database unavailability
        - 95% error rate
        - Minimal cascading effects
        - Solution: Restart database
        """
        base_variants = [
            ScenarioVariant(
                scenario_id="easy_1",
                task_name="easy_database_restart_1",
                incident_type="database_outage",
                seed=42,
                description="Database suddenly becomes unavailable",
                expected_root_cause="database",
                difficulty="easy"
            ),
            ScenarioVariant(
                scenario_id="easy_2",
                task_name="easy_database_restart_2",
                incident_type="database_outage",
                seed=123,
                description="Database service crashes",
                expected_root_cause="database",
                difficulty="easy"
            ),
            ScenarioVariant(
                scenario_id="easy_3",
                task_name="easy_database_restart_3",
                incident_type="database_outage",
                seed=456,
                description="Database returns 503 errors",
                expected_root_cause="database",
                difficulty="easy"
            ),
        ]
        return base_variants
    
    @staticmethod
    def get_medium_scenarios() -> List[ScenarioVariant]:
        """
        MEDIUM TASK: Dependency failure
        
        Misleading signals:
        - Auth service appears to be the problem (high error rate)
        - But root cause is database latency/partial outage
        - Misleading alerts about auth service
        - Solution: Fix database, which fixes auth
        """
        base_variants = [
            ScenarioVariant(
                scenario_id="medium_1",
                task_name="medium_auth_dependency_1",
                incident_type="auth_dependency_failure",
                seed=789,
                description="Auth service fails due to database latency",
                expected_root_cause="database",
                difficulty="medium"
            ),
            ScenarioVariant(
                scenario_id="medium_2",
                task_name="medium_auth_dependency_2",
                incident_type="auth_dependency_failure",
                seed=101,
                description="Authentication requests timeout due to DB slowness",
                expected_root_cause="database",
                difficulty="medium"
            ),
            ScenarioVariant(
                scenario_id="medium_3",
                task_name="medium_auth_dependency_3",
                incident_type="auth_dependency_failure",
                seed=202,
                description="Cascading failures starting from database latency",
                expected_root_cause="database",
                difficulty="medium"
            ),
        ]
        return base_variants
    
    @staticmethod
    def get_hard_scenarios() -> List[ScenarioVariant]:
        """
        HARD TASK: Cascading failure (memory leak)
        
        Complex signals:
        - Multiple services show errors
        - Noisy logs with misleading information
        - Root cause is memory leak in database
        - High CPU and memory usage
        - Cascading affecting auth and API gateway
        - Multiple possible diagnosis paths
        - Solution: Restart database (fixes memory leak) AND possibly scale services
        """
        base_variants = [
            ScenarioVariant(
                scenario_id="hard_1",
                task_name="hard_cascading_failure_1",
                incident_type="cascading_failure",
                seed=303,
                description="Memory leak causes cascading system failure",
                expected_root_cause="database",
                difficulty="hard"
            ),
            ScenarioVariant(
                scenario_id="hard_2",
                task_name="hard_cascading_failure_2",
                incident_type="cascading_failure",
                seed=404,
                description="Progressive degradation from memory leak",
                expected_root_cause="database",
                difficulty="hard"
            ),
            ScenarioVariant(
                scenario_id="hard_3",
                task_name="hard_cascading_failure_3",
                incident_type="cascading_failure",
                seed=505,
                description="Multiple services in failure mode due to memory pressure",
                expected_root_cause="database",
                difficulty="hard"
            ),
        ]
        return base_variants
    
    @staticmethod
    def get_scenario_by_name(scenario_name: str) -> ScenarioVariant:
        """Retrieve a scenario by name."""
        all_scenarios = (
            ScenarioManager.get_easy_scenarios() +
            ScenarioManager.get_medium_scenarios() +
            ScenarioManager.get_hard_scenarios()
        )
        
        for scenario in all_scenarios:
            if scenario.task_name == scenario_name or scenario.scenario_id == scenario_name:
                return scenario
        
        raise ValueError(f"Unknown scenario: {scenario_name}")
    
    @staticmethod
    def get_all_scenarios() -> Dict[str, List[ScenarioVariant]]:
        """Get all scenarios organized by difficulty."""
        return {
            "easy": ScenarioManager.get_easy_scenarios(),
            "medium": ScenarioManager.get_medium_scenarios(),
            "hard": ScenarioManager.get_hard_scenarios(),
        }
    
    @staticmethod
    def get_scenario_names_by_difficulty(difficulty: str) -> List[str]:
        """Get scenario names for a difficulty level."""
        scenarios = {
            "easy": ScenarioManager.get_easy_scenarios(),
            "medium": ScenarioManager.get_medium_scenarios(),
            "hard": ScenarioManager.get_hard_scenarios(),
        }
        
        if difficulty not in scenarios:
            raise ValueError(f"Unknown difficulty: {difficulty}")
        
        return [s.task_name for s in scenarios[difficulty]]


# Example usage for testing
if __name__ == "__main__":
    scenarios = ScenarioManager.get_all_scenarios()
    for difficulty, variants in scenarios.items():
        print(f"\n{difficulty.upper()} SCENARIOS:")
        for variant in variants:
            print(f"  - {variant.scenario_id}: {variant.description}")
