from fastapi import FastAPI
from env.incident_env import create_env
from env.models import Action, ActionType

app = FastAPI()

env = create_env()

@app.get("/")
def root():
    return {"status": "ok"}

@app.post("/reset")
def reset():
    obs = env.reset()
    return obs.model_dump()

@app.post("/step")
def step(action: dict):
    act = Action(
        action_type=ActionType(action["action"]),
        service=action.get("service")
    )

    obs, reward, done, info = env.step(act)

    return {
        "observation": obs.model_dump(),
        "reward": reward.total,
        "done": done,
        "info": info
    }