"""
Example script demonstrating environment usage without OpenAI dependency.

This script:
1. Creates environments for each difficulty level
2. Runs a simple rule-based agent
3. Demonstrates observation structure
4. Shows grading system
"""

from dotenv import load_dotenv
load_dotenv()

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from env import create_env, ScenarioManager, ActionType, Action


class SimpleAgent:
    """Simple rule-based agent for demonstration."""
    
    def select_action(self, observation, step):
        """
        Select action based on simple heuristics.
        
        Rules:
        1. If critical alert from database → restart database
        2. Otherwise, investigate logs
        """
        if not observation.alerts:
            return Action(action_type=ActionType.NOOP)
        
        # Find critical alerts
        for alert in observation.alerts:
            if alert.severity.value == "critical":
                return Action(
                    action_type=ActionType.RESTART_SERVICE,
                    service=alert.service
                )
        
        # If no critical alerts, investigate
        for service in ["database", "auth_service", "api_gateway"]:
            return Action(
                action_type=ActionType.INVESTIGATE_LOGS,
                service=service
            )
        
        return Action(action_type=ActionType.NOOP)


def run_scenario(scenario_name, agent, verbose=True):
    """Run a single scenario."""
    env = create_env(scenario_name)
    obs = env.reset()
    
    if verbose:
        print(f"\n{'='*80}")
        print(f"Scenario: {scenario_name}")
        print(f"Incident: {env.scenario.description}")
        print(f"{'='*80}")
    
    done = False
    step = 0
    
    while not done and step < 50:
        step += 1
        
        # Agent selects action
        action = agent.select_action(obs, step)
        
        if verbose:
            print(f"\nStep {step}: {action.action_type.value}", end="")
            if action.service:
                print(f"({action.service})", end="")
            print()
        
        # Environment step
        obs, reward, done, info = env.step(action)
        
        if verbose:
            print(f"  Reward: {reward.total:+.3f} | Incident Resolved: {info['incident_resolved']}")
        
        if done:
            break
    
    # Get final grade
    score, components = env.get_grade()
    
    if verbose:
        print(f"\n✓ Final Score: {score:.3f}")
        print(f"  - Root Cause Fixed: {components['root_cause_fixed']:.3f}")
        print(f"  - System Recovered: {components['system_recovered']:.3f}")
        print(f"  - Action Efficiency: {components['action_efficiency']:.3f}")
        print(f"  - Step Efficiency: {components['step_efficiency']:.3f}")
        print(f"  - Action Sequence: {components['action_sequence_correctness']:.3f}")
    
    return score


def main():
    """Run all scenarios with simple agent."""
    print("""
╔═══════════════════════════════════════════════════════════════════════════╗
║         Incident Response Environment - Example Demo                     ║
║                                                                           ║
║  This demonstrates the environment without requiring OpenAI API key      ║
║  Using a simple rule-based agent for illustration                        ║
╚═══════════════════════════════════════════════════════════════════════════╝
    """)
    
    agent = SimpleAgent()
    scenarios = ScenarioManager.get_all_scenarios()
    
    all_scores = {
        "easy": [],
        "medium": [],
        "hard": [],
    }
    
    # Run scenarios
    for difficulty in ["easy", "medium", "hard"]:
        print(f"\n{'#'*80}")
        print(f"# {difficulty.upper()} SCENARIOS")
        print(f"{'#'*80}")
        
        for scenario in scenarios[difficulty]:
            try:
                score = run_scenario(scenario.task_name, agent, verbose=True)
                all_scores[difficulty].append(score)
            except Exception as e:
                print(f"ERROR: {e}")
                import traceback
                traceback.print_exc()
    
    # Print summary
    print(f"\n{'='*80}")
    print(f"SUMMARY")
    print(f"{'='*80}")
    
    for difficulty in ["easy", "medium", "hard"]:
        if all_scores[difficulty]:
            avg = sum(all_scores[difficulty]) / len(all_scores[difficulty])
            print(f"{difficulty.upper():10} Average: {avg:.3f}")
        else:
            print(f"{difficulty.upper():10} Average: N/A (no scenarios run)")
    
    overall_avg = sum(
        sum(scores) for scores in all_scores.values()
    ) / sum(len(scores) for scores in all_scores.values())
    
    print(f"\nOVERALL AVERAGE: {overall_avg:.3f}")
    
    print(f"\n{'='*80}")
    print("✓ Demo completed successfully!")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
