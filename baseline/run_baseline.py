"""
Baseline Agent Runner

Runs the LLM-based agent on the three task difficulties and reports scores.
"""

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

import sys
import os
import json
from typing import Dict, Tuple

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from env import IncidentResponseEnv, ScenarioManager
from baseline.agent_openai import OpenAIAgent


def run_scenario(env: IncidentResponseEnv, agent: OpenAIAgent, verbose: bool = False) -> Tuple[float, Dict]:
    """
    Run a single scenario with the agent.
    
    Returns:
        (score, grade_components)
    """
    observation = env.reset()
    agent.reset()
    
    if verbose:
        print(f"\n{'='*60}")
        print(f"Scenario: {env.scenario_name}")
        print(f"Incident Type: {env.scenario.incident_type}")
        print(f"Description: {env.scenario.description}")
        print(f"{'='*60}")
    
    done = False
    step_count = 0
    
    while not done and step_count < 100:
        step_count += 1
        
        # Agent selects action
        action = agent.select_action(observation, step_count)
        
        if verbose:
            print(f"\nStep {step_count}: {action.action_type.value}({action.service})")
        
        # Environment step
        observation, reward, done, info = env.step(action)
        
        if verbose:
            print(f"  Reward: {reward.total:.2f}")
            print(f"  Status: {info}")
        
        if done:
            if verbose:
                print(f"\nIncident {'RESOLVED' if info['incident_resolved'] else 'NOT RESOLVED'}")
    
    # Compute final grade
    score, components = env.get_grade()
    
    if verbose:
        print(f"\nFinal Grade: {score:.3f}")
        print(f"Components:")
        for key, value in components.items():
            if key != "total_score":
                print(f"  {key}: {value:.3f}")
    
    return score, components


def main():
    """Run baseline agent on all three difficulty levels."""
    
    print("Incident Response Baseline Agent")
    print("="*60)
    
    # Check for API key (Groq, OpenAI, or Grok)
    if (
        not os.getenv("GROQ_API_KEY")
        and not os.getenv("OPENAI_API_KEY")
        and not os.getenv("GROK_API_KEY")
    ):
        print("ERROR: GROQ_API_KEY or OPENAI_API_KEY or GROK_API_KEY environment variable not set")
        print("Set one of them in your .env file")
        sys.exit(1)
    
    try:
        agent = OpenAIAgent(model=os.getenv("OPENAI_MODEL"))
    except Exception as e:
        print(f"ERROR: Could not initialize OpenAI agent: {e}")
        sys.exit(1)
    
    results = {}
    
    # Run easy scenarios
    print("\n" + "="*60)
    print("EASY SCENARIOS")
    print("="*60)
    easy_scenarios = ScenarioManager.get_easy_scenarios()
    easy_scores = []
    
    for scenario in easy_scenarios:
        try:
            env = IncidentResponseEnv(scenario_name=scenario.task_name)
            score, components = run_scenario(env, agent, verbose=True)
            easy_scores.append(score)
            results[scenario.task_name] = {
                "score": score,
                "components": components
            }
        except Exception as e:
            print(f"ERROR in scenario {scenario.task_name}: {e}")
            results[scenario.task_name] = {"score": 0.0, "error": str(e)}
    
    easy_avg = sum(easy_scores) / len(easy_scores) if easy_scores else 0.0
    
    # Run medium scenarios
    print("\n" + "="*60)
    print("MEDIUM SCENARIOS")
    print("="*60)
    medium_scenarios = ScenarioManager.get_medium_scenarios()
    medium_scores = []
    
    for scenario in medium_scenarios:
        try:
            env = IncidentResponseEnv(scenario_name=scenario.task_name)
            score, components = run_scenario(env, agent, verbose=True)
            medium_scores.append(score)
            results[scenario.task_name] = {
                "score": score,
                "components": components
            }
        except Exception as e:
            print(f"ERROR in scenario {scenario.task_name}: {e}")
            results[scenario.task_name] = {"score": 0.0, "error": str(e)}
    
    medium_avg = sum(medium_scores) / len(medium_scores) if medium_scores else 0.0
    
    # Run hard scenarios
    print("\n" + "="*60)
    print("HARD SCENARIOS")
    print("="*60)
    hard_scenarios = ScenarioManager.get_hard_scenarios()
    hard_scores = []
    
    for scenario in hard_scenarios:
        try:
            env = IncidentResponseEnv(scenario_name=scenario.task_name)
            score, components = run_scenario(env, agent, verbose=True)
            hard_scores.append(score)
            results[scenario.task_name] = {
                "score": score,
                "components": components
            }
        except Exception as e:
            print(f"ERROR in scenario {scenario.task_name}: {e}")
            results[scenario.task_name] = {"score": 0.0, "error": str(e)}
    
    hard_avg = sum(hard_scores) / len(hard_scores) if hard_scores else 0.0
    
    # Print summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Easy Average Score:   {easy_avg:.3f}")
    print(f"Medium Average Score: {medium_avg:.3f}")
    print(f"Hard Average Score:   {hard_avg:.3f}")
    print(f"Overall Average:      {(easy_avg + medium_avg + hard_avg) / 3:.3f}")
    
    # Save results
    output_file = "baseline_results.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\nDetailed results saved to: {output_file}")
    
    return (easy_avg + medium_avg + hard_avg) / 3


if __name__ == "__main__":
    overall_score = main()
    sys.exit(0)
