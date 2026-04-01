# Project Structure & Architecture

## Directory Layout

```
incident-response-env/
├── env/                        # Core Environment Module
│   ├── __init__.py            # Package initialization, exports main classes
│   ├── models.py              # Pydantic data models
│   ├── incident_env.py        # Main OpenEnv environment class
│   ├── dynamics.py            # System state transitions & cascading logic
│   ├── scenarios.py           # Task definitions (9 scenarios, 3 difficulties)
│   └── grader.py              # Deterministic multi-component grading
│
├── baseline/                   # Baseline Agent Implementation
│   ├── __init__.py            # Package initialization
│   ├── agent_openai.py        # OpenAI-based reasoning agent
│   └── run_baseline.py        # Script to run baseline on all scenarios
│
├── app.py                      # Gradio UI for interactive demos
├── validate.py                # Validation & environment check script
├── example_demo.py            # Example runner with rule-based agent
│
├── openenv.yaml               # OpenEnv specification
├── Dockerfile                 # Container image definition
├── .dockerignore              # Docker build exclusions
├── requirements.txt           # Python dependencies
├── .env.example               # Environment variable template
├── Makefile                   # Development task automation
│
├── README.md                  # Main documentation (comprehensive)
├── PROJECT_SUMMARY.md         # This project's executive summary
├── STRUCTURE.md               # This file
└── ARCHITECTURE.md            # (Optional) Detailed architecture document
```

## Module Descriptions

### `env/models.py` (Data Models)
**Purpose**: Define all data structures using Pydantic for type safety

**Key Classes**:
- `ServiceHealth`, `AlertSeverity` (Enums)
- `Alert` - Structured alert message
- `Metric` - Performance metric with thresholds
- `LogEntry` - Service log with relevance flag
- `Observation` - What agent sees (alerts, metrics, logs, health)
- `Action` - What agent can do (action_type, target service)
- `Reward` - Multi-component reward for interpretability
- `SystemState` - Complete ground truth state (hidden from agent)

**Lines**: ~250  
**Dependencies**: pydantic (only external dep for models)

---

### `env/incident_env.py` (Main Environment)
**Purpose**: Implement OpenEnv specification

**Key Classes**:
- `IncidentResponseEnv` - Main environment class
  - `reset()` - Initialize new episode
  - `step(action)` - Execute one step, return (obs, reward, done, info)
  - `state()` - Get full hidden state
  - `get_grade()` - Compute final grade after done
  - `render()` - String representation for debugging

**Design**:
```
┌──────────────────────────────────────────────┐
│ agent.select_action(observation)             │
└──────────────────────────────────────────────┘
              ↓            ↑
        (action)    (observation, reward, done)
              ↓            ↑
┌──────────────────────────────────────────────┐
│ IncidentResponseEnv.step(action)             │
├──────────────────────────────────────────────┤
│ 1. Apply action to system state              │
│ 2. Run dynamics transitions                  │
│ 3. Generate noisy observation                │
│ 4. Compute dense reward                      │
│ 5. Check if done (resolved or max_steps)     │
└──────────────────────────────────────────────┘
```

**Lines**: ~400  
**Dependencies**: models, dynamics, scenarios, grader

---

### `env/dynamics.py` (System Dynamics)
**Purpose**: Simulate realistic incident progression and cascading failures

**Key Classes**:
- `DynamicsEngine` - Manages state transitions
  - `initialize_healthy_state()` - Create baseline state
  - `apply_incident()` - Initialize incident (outage/dependency/cascading)
  - `step()` - Execute one timestep
  - `_apply_*()` - Individual action effects
  - `_update_cascading_effects()` - Rules for cascading failures
  - `add_noise_and_logs()` - Inject realistic noise

**Cascading Failure Logic**:
```
Database unhealthy (latency > 1s, errors > 0.1)
  ↓
Auth service error_rate increases (depends on DB)
  ↓
API gateway sees auth failures, cascades
  ↓
Retry storms amplify errors system-wide
  ↓
High CPU/memory causes more failures
  ↓
Restart database → cascades reverse
```

**Noise Injection**:
- Misleading alerts about downstream services
- Noisy logs with irrelevant entries
- Partial error rates (not binary healthy/unhealthy)

**Lines**: ~350  
**Dependencies**: models, random

---

### `env/scenarios.py` (Task Definitions)
**Purpose**: Define 3 task difficulties with variants

**Tasks**:

1. **Easy (3 variants)**
   - `easy_database_restart_1/2/3`
   - Incident: `database_outage`
   - Clear signals, direct solution

2. **Medium (3 variants)**
   - `medium_auth_dependency_1/2/3`
   - Incident: `auth_dependency_failure`
   - Misleading alerts, root cause hidden

3. **Hard (3 variants)**
   - `hard_cascading_failure_1/2/3`
   - Incident: `cascading_failure`
   - Noisy logs, multiple cascading effects

**Structure**:
```python
ScenarioVariant(
    scenario_id="easy_1",
    task_name="easy_database_restart_1",
    incident_type="database_outage",
    seed=42,  # Deterministic!
    description="...",
    expected_root_cause="database",
    difficulty="easy"
)
```

**Lines**: ~200  
**Dependencies**: dataclasses, random

---

### `env/grader.py` (Scoring System)
**Purpose**: Deterministic, multi-component grading

**Grading Formula**:
```
Score = (
    0.4 * root_cause_fixed +
    0.2 * system_recovered +
    0.2 * action_efficiency +
    0.1 * step_efficiency +
    0.1 * action_sequence_correctness
)
```

**Components**:

| Component | Weight | Range | Notes |
|-----------|--------|-------|-------|
| Root Cause Fixed | 40% | [0.0-1.0] | Did agent fix underlying issue? |
| System Recovered | 20% | [0.0-1.0] | Are all services healthy? |
| Action Efficiency | 20% | [0.0-1.0] | Minimal, appropriate actions? |
| Step Efficiency | 10% | [0.0-1.0] | How many steps to solution? |
| Action Sequence | 10% | [0.0-1.0] | Logical action order? |

**Example Scores**:
- Perfect fix in 3 steps: 0.92-0.98
- Good fix in 7 steps: 0.75-0.85
- Partial recovery: 0.40-0.50
- Failed diagnosis: 0.00-0.20

**Lines**: ~280  
**Dependencies**: models

---

### `baseline/agent_openai.py` (OpenAI Agent)
**Purpose**: Baseline agent using OpenAI API for reasoning

**Design**:
```
Observation (text-formatted)
    ↓
OpenAI GPT ("expert SRE" prompt)
    ↓
JSON action response
    ↓
Extract: action_type, service
    ↓
Execute in environment
```

**System Prompt**:
- Expert SRE with incident response knowledge
- Pattern recognition (DB outage → restart DB)
- Importance of diagnosis before action
- Understanding of cascading failures

**Features**:
- Conversation history for multi-turn reasoning
- Temperature=0.3 for reproducible behavior
- Structured JSON output format
- Fallback to noop on parsing errors
- Graceful handling of API failures

**Lines**: ~300  
**Dependencies**: openai, models

---

### `baseline/run_baseline.py` (Baseline Runner)
**Purpose**: Evaluate agent on all 9 scenarios

**Workflow**:
1. Initialize OpenAI agent
2. For each difficulty level (easy/medium/hard):
   - For each scenario variant:
     - Create environment
     - Reset environment
     - Run episode (up to 50 steps)
     - Collect final grade
3. Compute averages by difficulty
4. Save results to `baseline_results.json`

**Output**:
```
SUMMARY
============================================================
Easy Average Score:   0.895
Medium Average Score: 0.734
Hard Average Score:   0.612
Overall Average:      0.747
```

**Lines**: ~250  
**Dependencies**: models, agent_openai, incident_env

---

### `app.py` (Gradio UI)
**Purpose**: Interactive interface for manual exploration and visualization

**Features**:
- 📋 Scenario selector (all 9 tasks)
- 🚨 Real-time alerts with severity
- 📊 Metrics display (CPU, memory, latency, errors)
- 💬 Log viewer with filtering
- ⚙️ Action executor (select action + service)
- 🤖 Auto-step (smart heuristic)
- 🏆 Final grading with component breakdown

**Layout**:
```
┌─────────────────┬──────────────────────────────┐
│  CONTROLS       │  SYSTEM STATE                │
│  ┌───────────┐  │  ┌──────────────────────┐    │
│  │ Scenario  │  │  │ Alerts & Health      │    │
│  │ selector  │  │  ├──────────────────────┤    │
│  └───────────┘  │  │ Logs | Metrics       │    │
│  ┌───────────┐  │  │                      │    │
│  │ Action    │  │  │ Reward tracking      │    │
│  │ selector  │  │  │ Status badge         │    │
│  └───────────┘  │  └──────────────────────┘    │
│  [Execute]      │                              │
│  [Auto Step]    │                              │
│  [Reset]        │                              │
└─────────────────┴──────────────────────────────┘
```

**Lines**: ~400  
**Dependencies**: gradio, models, incident_env

---

### `validate.py` (Validation Script)
**Purpose**: Quick checks that everything is working

**Checks**:
1. Import all modules
2. Initialize DynamicsEngine
3. Load all scenarios
4. Create environment
5. Run basic 3-step episode

**Output**: ✓ or ✗ for each check

**Lines**: ~70  
**Dependencies**: env modules

---

### `example_demo.py` (Example Runner)
**Purpose**: Demonstrate environment without OpenAI

**Implementation**:
- Simple rule-based agent
- Falls back to investigate when uncertain
- Runs all 9 scenarios (easy/medium/hard)
- Prints scores by difficulty

**Lines**: ~180  
**Dependencies**: env modules

---

## Data Flow Diagrams

### Reset Flow
```
env.reset()
  ↓
initialize_healthy_state()  [all metrics normal]
  ↓
apply_incident(incident_type)  [introduce problem]
  ↓
_get_observation()  [format for agent]
  ├─ format metrics
  ├─ generate noisy alerts
  ├─ generate noisy logs
  └─ compute service_health
  ↓
return Observation
```

### Step Flow
```
env.step(action)
  ↓
Apply action effects:
  - restart_service: clear errors
  - investigate_logs: no state change
  - scale_service: add replicas
  - rollback_deployment: revert version
  - noop: no change
  ↓
Update cascading effects:
  - Database down → auth errors ↑
  - High CPU → latency ↑
  - Recovery: gradual improvement
  ↓
Generate observation
  ├─ compute metrics from state
  ├─ inject noise
  └─ format for agent
  ↓
Compute reward:
  - +0.4 root cause fixed
  - +0.1-0.3 partial improvements
  - -0.05 per step
  - +0.1 investigation
  ↓
Check done: incident_resolved? or max_steps?
  ↓
return (observation, reward, done, info)
```

### Grading Flow
```
env.get_grade()  [after done]
  ↓
Compare initial_state vs final_state
  ├─ root_cause_fixed: service health improved?
  ├─ system_recovered: all services healthy?
  ├─ action_efficiency: appropriate actions?
  ├─ step_efficiency: few steps?
  └─ action_sequence: logical order?
  ↓
Weight components: 0.4 + 0.2 + 0.2 + 0.1 + 0.1
  ↓
return (score: float, components: Dict)
```

## Design Patterns

### 1. Deterministic Seeding
**Pattern**: `Random(seed)` in DynamicsEngine
**Benefit**: Same scenario + seed → identical results
**Example**: `easy_database_restart_1` with seed=42 always produces identical state progression

### 2. Pydantic Models
**Pattern**: All data structures inherit from BaseModel
**Benefit**: Type safety, validation, serialization
**Example**: `observation.model_dump()` for JSON

### 3. Factory Pattern
**Pattern**: `create_env(scenario_name)` creates environment
**Benefit**: Simple API, hides complexity
**Example**: `env = create_env("hard_cascading_failure_1")`

### 4. Hidden State
**Pattern**: Full state in `system_state`, partial in `observation`
**Benefit**: Agents can't cheat, must reason
**Example**: `root_cause` is hidden but used by grader

### 5. Composition
**Pattern**: IncidentEnv uses DynamicsEngine, Grader, etc.
**Benefit**: Testable, modular, reusable
**Example**: DynamicsEngine can be tested independently

## Dependency Graph

```
app.py
  ├─ env.incident_env
  │   ├─ env.models
  │   ├─ env.dynamics
  │   │   ├─ env.models
  │   │   └─ random
  │   ├─ env.scenarios
  │   │   ├─ dataclasses
  │   │   └─ random
  │   └─ env.grader
  │       └─ env.models
  └─ gradio

baseline/run_baseline.py
  ├─ baseline.agent_openai
  │   ├─ openai
  │   └─ env.models
  └─ env (complete)

validate.py
  └─ env (complete)

example_demo.py
  └─ env (complete)
```

## Extension Points

### Add New Scenario
Edit `env/scenarios.py`:
```python
ScenarioVariant(
    scenario_id="medium_4",
    task_name="medium_deployment_issue",
    incident_type="bad_deployment",
    seed=707,
    description="New service version broke auth",
    expected_root_cause="auth_service",
    difficulty="medium"
)
```

### Add New Incident Type
Edit `env/dynamics.py`:
```python
def apply_incident(self, state, incident_type):
    if incident_type == "connection_pool_exhaustion":
        # Create appropriate state for this incident
        state.services["database"]["error_rate"] = 0.6
        state.root_cause_type = "connection_pool"
```

### Add New Action
Edit `env/models.py`:
```python
class ActionType(str, Enum):
    # ... existing actions ...
    DRAIN_CONNECTIONS = "drain_connections"
```

Then implement in `env/dynamics.py`:
```python
elif action_applied == "drain_connections":
    state = self._apply_drain_connections(state, action_service)
```

### Custom Agent
Implement interface matching `OpenAIAgent`:
```python
class CustomAgent:
    def select_action(self, observation, step) -> Action:
        # Your reasoning here
        return Action(...)
```

---

## Testing Strategy

### Unit Tests (Can Add)
- Test individual dynamics rules
- Test grading with known inputs
- Test scenario loading

### Integration Tests
- `validate.py` checks end-to-end
- `example_demo.py` demonstrates full episode flow
- `baseline/run_baseline.py` tests all 9 scenarios

### Manual Testing
- `app.py` for interactive exploration
- Verify UI updates in real-time
- Check final grades match expectations

---

## Performance Considerations

### Scalability
- **Episode length**: Up to 50 steps (configurable)
- **Scenarios**: 9 tasks (extensible to 100+)
- **State size**: ~1-2 KB per observation
- **Memory**: <100 MB for full environment

### Speed
- **Step time**: ~10ms (without OpenAI)
- **With OpenAI**: ~1-2s per step (API latency)
- **Episode**: 1-2 minutes typical

### Optimization
- Deterministic state transitions (no simulation loops)
- Minimal observation generation
- Optional gym/gymnasium integration

---

This architecture provides a solid foundation for production use while remaining extensible for future enhancements.
