# Incident Response OpenEnv: Autonomous SRE Agent Simulator

A production-quality **OpenEnv environment** for training autonomous Site Reliability Engineer (SRE) agents to diagnose and resolve distributed system incidents.

## 🎯 Problem Motivation

Modern distributed systems fail in complex ways. Site Reliability Engineers must rapidly diagnose root causes and take corrective actions across dozens of services. This environment simulates realistic incident scenarios where:

- **Root causes are hidden** behind multiple layers of cascading failures
- **Signals are noisy** with misleading alerts and logs
- **Decisions are consequential** – wrong actions waste time and worsen situations
- **Domain expertise is crucial** – understanding service dependencies and failure modes is essential

Traditional RL benchmarks don't capture these nuances. **Incident Response OpenEnv** provides a realistic, deterministic, reproducible environment for training agents to reason about and resolve production incidents.

## 🏆 Key Features

### 1. **Realistic Incident Simulation**
- **Database outages**: Complete service unavailability
- **Dependency failures**: Cascading errors from upstream services
- **Memory leaks + cascading failures**: Progressive degradation with retry storms
- **Hidden root causes**: Agents must diagnose without ground truth

### 2. **OpenEnv Compliance**
Strict adherence to OpenEnv specification:
- `step(action) → observation, reward, done, info`
- `reset() → initial observation`
- `state() → full internal state`
- Pydantic-typed observations and actions
- Deterministic, reproducible behavior

### 3. **Multi-Task Difficulty Progression**
- **Easy (1-2 steps)**: Single database outage with clear signals
- **Medium (2-3 steps)**: Dependency failure requiring investigation of auth and database
- **Hard (3-5 steps)**: Cascading memory leak requiring investigation, corrective action, and stabilization

### 4. **Deterministic Grading System**
Production-quality grader with 5 weighted components:
- **Root cause fixed (0.4)**: Was the underlying issue resolved?
- **System recovery (0.2)**: Did all services return to healthy state?
- **Action efficiency (0.2)**: Were actions minimal and appropriate?
- **Step efficiency (0.1)**: How many steps to resolution?
- **Action sequence correctness (0.1)**: Was the sequence logical?

**Score range**: [0.0, 1.0] – NO binary grading, continuous scoring.

### 5. **Dense Reward Function**
```
- +0.4: Root cause fix (after required investigation in medium/hard)
- +0.2: Full system recovery
- +0.1: Investigation action
- -0.2: Incorrect/harmful actions
- -0.05: Per-step penalty (incentivizes efficiency)
```

## 🏗️ Architecture

### Environment Design

```
┌─────────────────────────────────────────────────────┐
│  Agent (OpenAI, Rule-based, RL algorithm, etc.)    │
│                                                     │
│  Observation: alerts, metrics, logs, health        │
│  Action: restart, investigate, scale, rollback     │
└─────────────────────────────────────────────────────┘
                          ↓↑
┌─────────────────────────────────────────────────────┐
│            Incident Response Environment           │
│                                                     │
│  ┌─────────────────────────────────────────────┐  │
│  │  Hidden System State (Root Cause)           │  │
│  │  - Database (healthy/unhealthy)             │  │
│  │  - Auth Service (error rate, latency)       │  │
│  │  - API Gateway (cascading effects)          │  │
│  │  - Cache Service (dependent on DB)          │  │
│  └─────────────────────────────────────────────┘  │
│                      ↓                             │
│  ┌─────────────────────────────────────────────┐  │
│  │  Dynamics Engine (Rule-based Transitions)   │  │
│  │  - Cascading failure logic                  │  │
│  │  - Recovery behavior                        │  │
│  │  - Action effects                           │  │
│  └─────────────────────────────────────────────┘  │
│                      ↓                             │
│  ┌─────────────────────────────────────────────┐  │
│  │  Observation Generator (Noise Injection)    │  │
│  │  - Realistic alerts (some misleading)       │  │
│  │  - Noisy logs                               │  │
│  │  - Aggregated metrics                       │  │
│  └─────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
                          ↓
                    Grader Evaluation
```

### Project Structure

```
incident-response-env/
├── env/                        # Core environment
│   ├── __init__.py
│   ├── models.py              # Pydantic models (Observation, Action, etc.)
│   ├── incident_env.py        # Main OpenEnv class
│   ├── dynamics.py            # System state transitions
│   ├── scenarios.py           # Task definitions (easy/medium/hard)
│   └── grader.py              # Deterministic scoring
│
├── baseline/                   # Baseline agent
│   ├── __init__.py
│   ├── agent_openai.py        # OpenAI reasoning agent
│   └── run_baseline.py        # Run baseline on all tasks
│
├── app.py                      # Gradio UI (Hugging Face Spaces)
├── openenv.yaml               # OpenEnv specification
├── requirements.txt           # Python dependencies
├── Dockerfile                 # Container image
├── .dockerignore
└── README.md
```

## 🚀 Quick Start

### Installation

```bash
# Clone repository
git clone <repo_url>
cd incident-response-env

# Install dependencies
pip install -r requirements.txt

# Set provider config in .env (OpenAI-compatible API)
# Groq example (recommended):
# GROQ_API_KEY=gsk-...
# OPENAI_BASE_URL=https://api.groq.com/openai/v1
# OPENAI_MODEL=llama-3.3-70b-versatile

# OpenAI example:
# OPENAI_API_KEY=sk-...
# OPENAI_MODEL=gpt-4o-mini

# xAI Grok example:
# GROK_API_KEY=xai-...
# OPENAI_BASE_URL=https://api.x.ai/v1
# OPENAI_MODEL=grok-2-latest
```

### Run Baseline Agent

```bash
# Run baseline on all tasks (easy, medium, hard)
python baseline/run_baseline.py

# Output: baseline_results.json with scores for each scenario
```

Example output:
```
SUMMARY
============================================================
Easy Average Score:   0.895
Medium Average Score: 0.734
Hard Average Score:   0.612
Overall Average:      0.747
```

### Interactive UI

```bash
# Launch Gradio interface
python app.py

# Opens at http://localhost:7860
```

Features:
- Select any scenario (easy/medium/hard)
- Manually step through incidents
- See real-time system state, alerts, metrics
- View Total Reward (Training Signal) and Final Score (Evaluation)
- Root Cause Analysis panel after episode completion
- Agent Decision Trace panel for interpretability

### Docker Deployment

```bash
# Build image
docker build -t incident-response-env .

# Run UI on port 7860
docker run -p 7860:7860 \
  -e GROQ_API_KEY="gsk-..." \
  -e OPENAI_BASE_URL="https://api.groq.com/openai/v1" \
  -e OPENAI_MODEL="llama-3.3-70b-versatile" \
  incident-response-env

# Run baseline
docker run --rm \
  -e GROQ_API_KEY="gsk-..." \
  -e OPENAI_BASE_URL="https://api.groq.com/openai/v1" \
  -e OPENAI_MODEL="llama-3.3-70b-versatile" \
  -v $(pwd)/results:/app/results \
  incident-response-env \
  python baseline/run_baseline.py
```

### Hugging Face Spaces Deployment

1. Create repository on Hugging Face
2. Link to this project
3. Set one provider key secret in repository settings (`GROQ_API_KEY` recommended)
4. Gradio app automatically deploys at `https://huggingface.co/spaces/<user>/<repo>`

## 📊 Observation Space

**Observation** (presented to agent):

```python
{
  "timestamp": 42,
  "alerts": [
    {
      "timestamp": 42,
      "service": "database",
      "severity": "critical",
      "message": "database error rate 95%",
      "is_root_cause": True,  # For grader evaluation only
    }
  ],
  "metrics": [
    {
      "name": "error_rate",
      "service": "database",
      "value": 0.95,
      "threshold": 0.05,
      "timestamp": 42
    },
    # ... more metrics for all services
  ],
  "logs": [
    {
      "timestamp": 42,
      "service": "database",
      "level": "ERROR",
      "message": "Connection refused: database unavailable",
      "is_relevant": True
    },
    # ... noisy logs
  ],
  "service_health": {
    "database": "unhealthy",
    "auth_service": "degraded",
    "api_gateway": "degraded",
    "cache_service": "healthy"
  }
}
```

### Metrics Available

Per service:
- `cpu_usage` (0–100%)
- `memory_usage` (0–100%)
- `error_rate` (0-1)
- `latency_ms` (milliseconds)

### Alerts

Three severity levels:
- **CRITICAL**: Service down, high error rate
- **WARNING**: Degraded performance, elevated latency
- **INFO**: Status updates

## ⚙️ Action Space

```python
{
  "action_type": "restart_service" | "investigate_logs" | "scale_service" | "rollback_deployment" | "noop",
  "service": "database" | "auth_service" | "api_gateway" | "cache_service",
  "target_replicas": Optional[int]
}
```

### Actions Explained

| Action | Effect | Good For |
|--------|--------|----------|
| **restart_service** | Clear errors, reset service state | Fixing outages, memory leaks |
| **investigate_logs** | Reveals high-signal evidence; can provide slight mitigation in hard tasks | Diagnosis, dependency reasoning, root-cause confirmation |
| **scale_service** | Add replicas, reduce per-instance load | Load balancing, reducing error rates |
| **rollback_deployment** | Revert to previous version | Recovery from bad deployments |
| **noop** | No action | Thinking/waiting |

## 🏅 Tasks

### Easy: Database Restart

**Scenario**: Database becomes completely unavailable

**Signals**:
- CRITICAL: "database: error rate 95%"
- All metrics show failure
- No cascading effects yet

**Solution**: `restart_service(database)`

**Expected Duration**: 1–2 steps

**Difficulty**: ⭐

---

### Medium: Auth Dependency Failure

**Scenario**: Database latency causes auth service to fail

**Signals**:
- Database: Elevated latency, partial errors
- Auth service: High error rate (symptom, not root cause)
- Misleading alerts about auth service
- Multiple services showing cascading effects

**Key Challenge**: Distinguish root cause (database) from symptoms (auth, api_gateway)

**Solution**:
1. `investigate_logs(auth_service)` → reveals downstream DB timeout
2. `investigate_logs(database)` → confirms DB latency root cause
3. `restart_service(database)` → resolves dependency chain

**Expected Duration**: 2–3 steps

**Difficulty**: ⭐⭐

---

### Hard: Cascading Memory Leak

**Scenario**: Memory leak in database → CPU spike → timeouts → retry storm

**Signals**:
- All services show errors
- Noisy logs with misleading messages
- Multiple possible diagnosis paths
- Cascading failures confuse diagnosis

**State Progression**:
1. Database memory 92% → 99%
2. Database CPU 88% → near max
3. Database latency spike (3000ms+)
4. Auth service timeouts
5. API gateway and cache degradation
6. Retry storms

**Key Challenge**: Identify database as root cause amid cascading signals

**Solution**:
1. `investigate_logs(database)` → reveals critical memory leak signal
2. `restart_service(database)` → mitigates root cause
3. stabilization step(s) as downstream services recover

**Expected Duration**: 3–5 steps

**Difficulty**: ⭐⭐⭐

## 🎯 Reward Function

Step reward (training signal) and final score (evaluation) are different by design.

Per-step reward components:

```python
step_reward = (
  +0.4 * root_cause_fix_if_resolved
  +0.2 * full_recovery_bonus
  +0.1 * investigate_logs_bonus
  -0.05 * step_penalty
  -0.2 * wrong_or_premature_action_penalty
)
```

Key behavior:
- Medium/hard penalize premature restart before required investigations.
- Correct investigate -> fix sequence yields higher cumulative reward.
- UI shows this as Total Reward (Training Signal).

Final evaluation score is computed by the deterministic grader (0.0-1.0) and shown as Final Score (Evaluation).

### Component Breakdown

**Root Cause Fix (0.4)**:
- 1.0: Root cause service fully restored
- 0.7: Good progress toward fixing root cause
- 0.4: Some improvement
- 0.0: No improvement

**System Recovery (0.2)**:
- 1.0: All services healthy, incident marked resolved
- 0.5: Significant recovery but not complete
- 0.2: Partial improvement
- 0.0: Still in incident state

**Action Efficiency (0.2)**:
- Penalizes redundant actions
- Rewards investigation
- Deducts for unnecessary scaling/rollbacks

**Step Efficiency (0.1)**:
- 1.0: ≤5 steps
- 0.5: 5–15 steps
- 0.0: >50 steps

**Action Sequence Correctness (0.1)**:
- Validates logical order
- Rewards investigation before action
- Deducts for random action sequences

## 🔍 Grader Details

**Deterministic Scoring System** – NO binary pass/fail, continuous [0.0, 1.0]

```python
score = grader.grade(
    initial_state,
    final_state,
    actions_taken,
    max_steps=50
)
# Returns: (score: float, components: Dict)
```

### Scoring Components

```python
{
  "root_cause_fixed": 0.4–1.0,
  "system_recovered": 0.0–1.0,
  "action_efficiency": 0.0–1.0,
  "step_efficiency": 0.0–1.0,
  "action_sequence_correctness": 0.0–1.0,
  "total_score": 0.0–1.0
}
```

### Example Grading

**Scenario**: Hard cascading failure

**Agent Actions**:
1. investigate_logs(database)
2. investigate_logs(auth_service)
3. restart_service(database)
4. noop
5. noop

**Grading**:
- Root cause fixed: 1.0 (database restarted)
- System recovered: 0.9 (cascading effects reversed)
- Action efficiency: 0.8 (2 noops are wasteful)
- Step efficiency: 0.6 (5 steps for hard task)
- Action sequence: 0.9 (investigated then acted)

**Total Score**: 0.4(1.0) + 0.2(0.9) + 0.2(0.8) + 0.1(0.6) + 0.1(0.9) = **0.85**

## 🤖 Baseline Agent Implementation

### LLM-Based Agent

**Architecture**:
- Uses OpenAI-compatible APIs (Groq/OpenAI/xAI)
- Converts observations to natural language prompts
- Extracts JSON action responses
- Maintains conversation history for multi-turn reasoning

**Reasoning Flow**:

```
Observation (alerts, metrics, logs)
    → Natural language formatting
  → LLM prompt with SRE expertise
    → JSON action extraction
    → Execute action
    → Repeat
```

**Prompt Design**:
- Expert SRE system prompt with incident patterns
- Clear action definitions
- Structured output format (JSON)
- Low temperature (0.0) for deterministic behavior

**Setup**:

```bash
# Groq (recommended)
export GROQ_API_KEY="gsk-..."
export OPENAI_BASE_URL="https://api.groq.com/openai/v1"
export OPENAI_MODEL="llama-3.3-70b-versatile"

# Alternative providers are also supported:
# OPENAI_API_KEY=sk-...
# GROK_API_KEY=xai-...
python baseline/run_baseline.py
```

**Example Output**:
```
EASY SCENARIOS
==============================================================
Scenario: easy_database_restart_1
Scenario Type: database_outage
Actions Taken:
  1. investigate_logs(database)
  2. restart_service(database)
Incident RESOLVED in 2 steps!
Final Score: 0.92

MEDIUM SCENARIOS
==============================================================
...

HARD SCENARIOS
==============================================================
...

SUMMARY
==============================================================
Easy Average Score:   0.895
Medium Average Score: 0.734
Hard Average Score:   0.612
Overall Average:      0.747
```

## 🎨 Interactive UI (Gradio)

Beautiful, intuitive interface for:
- **Scenario Selection**: Easy → Medium → Hard progression
- **Manual Stepping**: Control actions and observe consequences
- **Real-time State**: Alerts, metrics, logs, health status
- **Reward Tracking**: Cumulative reward and scoring components
- **Outcome Visualization**: Success/failure with detailed grading

**Launch**:
```bash
python app.py
# Opens http://localhost:7860
```

**Features**:
- 🚨 Live alerts with severity indicators
- 📊 Service health with real-time metrics
- 📝 Log viewer with error highlighting
- ⚙️ Action executor with service selector
- 🤖 Auto-step and full-episode agent execution
- 🧭 Agent Decision Trace (action + reasoning)
- 🔍 Root Cause Analysis panel after completion
- 🏆 Clear split: training reward vs evaluation score

## 📈 Evaluation Criteria

Judging Framework (Hackathon):

| Criterion | Weight | Rubric |
|-----------|--------|--------|
| **Real-world Utility** | 30% | Reflects actual SRE workflows, solves genuine problems |
| **Task & Grader Quality** | 25% | Non-trivial progression, deterministic grading, meaningful differentiation |
| **Environment Design** | 20% | Realistic dynamics, hidden state, cascading effects |
| **Code Quality & OpenEnv Compliance** | 15% | Clean architecture, spec compliance, reproducibility |
| **Creativity & Novelty** | 10% | Novel problem formulation, unique incident patterns |

## 🔒 Implementation Quality

✅ **Deterministic**: Fixed seeds ensure reproducible results  
✅ **Realistic**: Simulates actual SRE incidents (DB outages, cascading failures)  
✅ **Modular**: Clean separation of concerns (models, dynamics, grader, env)  
✅ **Spec-Compliant**: Strict OpenEnv adherence  
✅ **Production-Ready**: Type hints, error handling, documentation  
✅ **Scalable**: Easy to add new scenarios, incidents, actions  
✅ **Containerized**: Docker support for reproducible deployment  
✅ **Cloud-Ready**: Hugging Face Spaces deployment-ready  

## 🧪 Testing & Reproducibility

```bash
# Run all scenarios deterministically
python baseline/run_baseline.py

# Check grading consistency
python -c "from env import create_env; env = create_env('easy_database_restart_1'); env.reset(); ..."

# Expected output: Identical scores across runs (same seed)
```

## 📚 API Reference

### Create Environment

```python
from env import create_env

env = create_env(scenario_name="easy_database_restart_1")
```

### Episode Loop

```python
observation = env.reset()

done = False
while not done:
    action = agent.select_action(observation)
    observation, reward, done, info = env.step(action)

# Get final grade
score, components = env.get_grade()
```

### Inspection

```python
# Access full hidden state
state = env.state()

# Get current observation
obs = env.current_observation

# Render for debugging
print(env.render())
```

## 🤝 Contributing

Extend the environment:

1. **Add new scenario**: Edit `env/scenarios.py`
2. **Modify dynamics**: Edit `env/dynamics.py`
3. **Implement new agent**: Implement similar interface to `OpenAIAgent`
4. **Add tasks**: Follow task structure in `env/scenarios.py`

## 📜 License

MIT License – see LICENSE file

## 📞 Support

- **Questions**: Open issue on GitHub
- **Bugs**: Report with reproduction steps
- **Contributions**: Submit pull requests

## 🏆 Citation

```bibtex
@software{incident_response_openenv_2024,
  title={Incident Response OpenEnv: Autonomous SRE Agent Simulator},
  author={Your Name},
  year={2024},
  url={https://github.com/...}
}
```

---

**Built for the [META Hackathon](hackathon_link)**

🔴 **STATUS**: Production-Ready | 📊 **SPEC**: OpenEnv v1.0 | 🚀 **DEPLOYMENT**: Docker + Hugging Face Spaces
