#!/usr/bin/env python3
"""
Incident Response OpenEnv - Main Entry Point

This script provides a simple way to launch the environment or UI.
"""

from dotenv import load_dotenv
load_dotenv()

import sys
import argparse


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Incident Response OpenEnv - Autonomous SRE Agent Simulator"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Validate command
    subparsers.add_parser("validate", help="Validate environment setup")
    
    # Demo command
    subparsers.add_parser("demo", help="Run demo with rule-based agent")
    
    # UI command
    subparsers.add_parser("ui", help="Launch interactive Gradio UI")
    
    # Baseline command
    subparsers.add_parser("baseline", help="Run OpenAI baseline agent")
    
    args = parser.parse_args()
    
    if args.command == "validate":
        import validate
        validate.main()
    elif args.command == "demo":
        import example_demo
        example_demo.main()
    elif args.command == "ui":
        import app
        app.main()
    elif args.command == "baseline":
        from baseline import run_baseline
        run_baseline.main()
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
