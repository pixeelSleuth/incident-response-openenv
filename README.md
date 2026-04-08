# Incident Response OpenEnv

## Overview

This project implements a custom **OpenEnv environment** simulating real-world incident response scenarios handled by Site Reliability Engineers (SREs).

The objective is to enable agents to **diagnose and resolve system failures** using structured signals such as logs, metrics, and alerts.

The environment models realistic production issues including:

* database outages
* service dependency failures
* cascading system failures

---

## Environment Design

The environment follows the OpenEnv specification:

* `reset()` initializes a new scenario
* `step(action)` returns:

  * observation
  * reward
  * done
  * info
* `state()` exposes full internal state (for evaluation)

The system is deterministic and reproducible.

---

## Observation Space

Each step provides:

* Alerts (severity + messages)
* Metrics (CPU, memory, latency, error rate)
* Logs (relevant + noisy entries)
* Service health status

Observations may contain noise and indirect signals.

---

## Action Space

Available actions:

* `restart_service(service)`
* `investigate_logs(service)`
* `scale_service(service)`
* `rollback_deployment(service)`
* `noop`

---

## Tasks

Three difficulty levels are implemented:

### Easy

* Single service failure
* Clear signals

### Medium

* Dependency failures
* Root cause not directly visible

### Hard

* Cascading failures across multiple services
* Noisy and misleading signals

---

## Reward & Evaluation

The environment provides dense rewards:

* Reward for fixing root cause
* Bonus for full recovery
* Reward for investigation
* Penalty for inefficient or incorrect actions

Final evaluation score is in the range **[0.0, 1.0]**.

---

## Running the Project

### Install dependencies

```bash
pip install -r requirements.txt
```

### Validate environment

```bash
python validate.py
```

### Run inference

```bash
python inference.py
```

---

## Baseline Agent

The project includes a baseline inference script using the OpenAI-compatible client with configurable API endpoint and model.

---

## Deployment

### Docker

```bash
docker build -t incident-env .
docker run incident-env
```

### Hugging Face Spaces

The project is compatible with Docker-based Spaces deployment.

---

## Summary

* Real-world incident simulation
* Multi-step reasoning environment
* Deterministic grading system
* OpenEnv compliant design

---

## Author

Developed as part of a hackathon submission.
