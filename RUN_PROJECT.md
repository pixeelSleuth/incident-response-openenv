# Incident Response OpenEnv - Run Guide

This guide explains how to run the project and what output to expect.

## 1) Activate Environment

Open PowerShell in project root:

```powershell
cd D:\META_HACKATHON
.\.venv\Scripts\Activate.ps1
python -c "import sys; print(sys.executable)"
```

Expected:
- Python path should point to `.venv\Scripts\python.exe`

If activation is blocked:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## 2) Validate Setup

```powershell
python validate.py
```

Expected output pattern:
- `Environment Setup Validation`
- `[1/5] Testing model imports... ✓`
- `[2/5] Testing dynamics engine... ✓`
- `[3/5] Testing scenarios... ✓`
- `[4/5] Creating environment... ✓`
- `[5/5] Running episode... ✓`
- `✓ ALL VALIDATION CHECKS PASSED`

## 3) Run Demo (No API Key Required)

```powershell
python example_demo.py
```

Expected output pattern:
- Section headers for EASY, MEDIUM, HARD scenarios
- Each scenario shows steps, reward, and final score
- Summary block with averages:
  - `EASY Average: ...`
  - `MEDIUM Average: ...`
  - `HARD Average: ...`
  - `OVERALL AVERAGE: ...`
- Final success line similar to `Demo completed successfully`

## 4) Run Interactive UI

```powershell
python app.py
```

Expected terminal output pattern:
- `Running on local URL:`
- Usually `http://0.0.0.0:7860`

Open in browser:
- http://localhost:7860

Expected UI behavior:
- Scenario dropdown (easy/medium/hard variants)
- Initialize Scenario button calls env reset
- Execute Action button calls env step
- Auto Step (Agent) and Run Full Episode (Agent) available
- Live display of alerts, metrics, logs, reward, steps, resolved status, final score

## 5) Run OpenAI Baseline Agent

Set API key first:

```powershell
$env:OPENAI_API_KEY="your_openai_key"
python baseline/run_baseline.py
```

Expected output pattern:
- EASY SCENARIOS section with per-scenario results
- MEDIUM SCENARIOS section with per-scenario results
- HARD SCENARIOS section with per-scenario results
- Final summary lines:
  - `Easy Average Score: ...`
  - `Medium Average Score: ...`
  - `Hard Average Score: ...`
  - `Overall Average: ...`
- Output file generated: `baseline_results.json`

## 6) Docker Run

Build image:

```powershell
docker build -t incident-response-env .
```

Run UI mode:

```powershell
docker run -p 7860:7860 -e APP_MODE=ui incident-response-env
```

Expected:
- App starts and serves UI on port 7860

Run baseline mode:

```powershell
docker run --rm -e APP_MODE=baseline -e OPENAI_API_KEY="your_openai_key" incident-response-env
```

Expected:
- Baseline evaluation logs and summary scores

## 7) Common Checks

If UI is not visible:
- Confirm app process is running
- Confirm port 7860 is listening
- Open http://localhost:7860 (not 0.0.0.0)

If package import fails:
- Re-activate venv
- Reinstall deps:

```powershell
python -m pip install -r requirements.txt
```

---

## Quick Success Criteria

Project is considered running correctly when:
1. `python validate.py` passes all 5 checks
2. `python example_demo.py` finishes with scenario summaries
3. `python app.py` opens UI at localhost:7860
4. `python baseline/run_baseline.py` prints difficulty averages (with API key)
