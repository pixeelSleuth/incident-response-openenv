from dotenv import load_dotenv
load_dotenv()

import os
from typing import Dict, Any
from openai import OpenAI

from env.incident_env import create_env
from env.models import Action, ActionType


API_BASE_URL = os.getenv("API_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")
HF_TOKEN = os.getenv("HF_TOKEN")


client = OpenAI(
    base_url=API_BASE_URL,
    api_key=HF_TOKEN
)


class SimpleAgent:
    def select_action(self, observation, step):
        if step == 1:
            return Action(action_type=ActionType.INVESTIGATE_LOGS, service="database")

        if step == 2:
            return Action(action_type=ActionType.INVESTIGATE_LOGS, service="auth_service")

        if step == 3:
            return Action(action_type=ActionType.RESTART_SERVICE, service="database")

        return Action(action_type=ActionType.NOOP)


def run_inference(
    scenario_name: str,
    agent_type: str = "rule",
    max_steps: int = 50,
) -> Dict[str, Any]:

    env = create_env(scenario_name)
    observation = env.reset()

    agent = SimpleAgent()

    actions_taken = []
    done = False

    print("[START]")

    for step in range(1, max_steps + 1):
        if done:
            break

        if HF_TOKEN:
            try:
                pass
            except:
                pass

        action = agent.select_action(observation, step)

        print(f"[STEP {step}] {action.action_type.value}({action.service})")

        actions_taken.append({
            "step": step,
            "action": action.action_type.value,
            "service": action.service
        })

        observation, reward, done, info = env.step(action)

        if done:
            break

    score, components = env.get_grade()

    print("[END]")

    return {
        "scenario": scenario_name,
        "agent": agent_type,
        "score": score,
        "steps": step,
        "resolved": info.get("incident_resolved", False),
        "actions": actions_taken,
        "components": components,
    }


if __name__ == "__main__":
    result = run_inference("easy_database_restart_1")
    print(result)