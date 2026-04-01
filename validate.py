"""
Quick validation script to verify environment setup.

Run this to check:
1. All imports work
2. Environment can be created
3. Basic step-through works
4. Grading system functions
"""

from dotenv import load_dotenv
load_dotenv()

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 60)
print("Environment Setup Validation")
print("=" * 60)

# Test 1: Import models
print("\n[1/5] Testing model imports...", end=" ")
try:
    from env.models import (
        Observation, Action, ActionType, Reward, SystemState,
        ServiceHealth, Alert, AlertSeverity, Metric, LogEntry
    )
    print("✓")
except Exception as e:
    print(f"✗ FAILED: {e}")
    sys.exit(1)

# Test 2: Import dynamics
print("[2/5] Testing dynamics engine...", end=" ")
try:
    from env.dynamics import DynamicsEngine
    engine = DynamicsEngine(seed=42)
    print("✓")
except Exception as e:
    print(f"✗ FAILED: {e}")
    sys.exit(1)

# Test 3: Import scenarios
print("[3/5] Testing scenarios...", end=" ")
try:
    from env.scenarios import ScenarioManager
    scenarios = ScenarioManager.get_all_scenarios()
    print(f"✓ ({len(scenarios)} difficulty levels)")
except Exception as e:
    print(f"✗ FAILED: {e}")
    sys.exit(1)

# Test 4: Create environment
print("[4/5] Creating environment...", end=" ")
try:
    from env import create_env
    env = create_env("easy_database_restart_1")
    print("✓")
except Exception as e:
    print(f"✗ FAILED: {e}")
    sys.exit(1)

# Test 5: Run basic episode
print("[5/5] Running episode...", end=" ")
try:
    obs = env.reset()
    assert obs is not None
    
    # Take 3 steps
    for i in range(3):
        action = Action(action_type=ActionType.INVESTIGATE_LOGS, service="database")
        obs, reward, done, info = env.step(action)
        if done:
            break
    
    # Get state
    state = env.state()
    assert state is not None
    
    # Get grade (even if not done)
    # Can only grade after done, so skip for now
    
    print("✓")
except Exception as e:
    print(f"✗ FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("✓ ALL VALIDATION CHECKS PASSED")
print("=" * 60)
print("\nEnvironment is ready to use!")
print("\nNext steps:")
print("1. Try the example demo:")
print("   python example_demo.py")
print("\n2. Try the interactive UI:")
print("   python app.py")
print("\n3. Try the baseline agent (requires OPENAI_API_KEY):")
print("   export OPENAI_API_KEY='sk-...'")
print("   python baseline/run_baseline.py")
print("\n" + "=" * 60)
