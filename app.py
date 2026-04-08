"""
Incident Response Environment - Interactive Gradio UI

A beautiful, interactive interface for the incident response environment.
Allows users to manually step through incidents, see the system state, and understand SRE workflows.

Deployable to Hugging Face Spaces.
"""
from fastapi import FastAPI
from pydantic import BaseModel
from env.incident_env import create_env

app = FastAPI()

env = create_env()

@app.post("/reset")
def reset():
    obs = env.reset()
    return obs.model_dump()

@app.post("/step")
def step(action: dict):
    from env.models import Action, ActionType

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
    
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

import gradio as gr
import json
from typing import Dict, List, Tuple
from env import IncidentResponseEnv, ScenarioManager, ActionType, Action
from env.models import Observation
from baseline.agent_openai import OpenAIAgent

class EnvironmentUI:
    """Manages environment instances for the UI."""
    
    def __init__(self):
        """Initialize UI."""
        self.env: IncidentResponseEnv = None
        self.scenario_name: str = "easy_database_restart_1"
        self.current_observation: Observation = None
        self.total_reward: float = 0.0
        self.final_score: float = 0.0
        self.done: bool = False
        self.agent = None
        self.agent_error_message: str = ""
        self.decision_trace: List[str] = []
    
    def init_environment(self, scenario_name: str) -> Tuple[str, str, str, float, int, float, str, str, str, str]:
        """Initialize a new environment for the selected scenario."""
        self.scenario_name = scenario_name
        self.env = IncidentResponseEnv(scenario_name=scenario_name, max_steps=50)
        self.current_observation = self.env.reset()
        self.total_reward = 0.0
        self.final_score = 0.0
        self.done = False
        self.agent = None
        self.decision_trace = []
        
        status = f"✅ Environment initialized: {scenario_name}"
        
        # Render initial state
        state_text = self._render_state()
        logs_text = self._render_logs()
        
        return status, state_text, logs_text, 0.0, 0, 0.0, "No", "Running", self._render_root_cause_analysis(), self._render_decision_trace()
    
    def step_with_action(
        self, action_type: str, service: str, reason: str = "", actor: str = "User"
    ) -> Tuple[str, str, str, float, int, float, str, str, str, str]:
        """Execute one step with the selected action."""
        if self.env is None:
            return (
                "❌ Environment not initialized. Select a scenario first.",
                "", "", 0.0, 0, 0.0, "No", "Not started", self._render_root_cause_analysis(), self._render_decision_trace()
            )
        
        if self.done:
            return (
                "⏸️ Episode finished. Reset to continue.",
                self._render_state(),
                self._render_logs(),
                self.total_reward,
                self.env.current_step,
                self.final_score,
                "Yes" if self.env.state().incident_resolved else "No",
                "Done",
                self._render_root_cause_analysis(),
                self._render_decision_trace(),
            )
        
        # Accept both UI labels and enum values from agent actions.
        normalized_action = action_type.strip().lower().replace(" ", "_")
        action_type_map = {
            "noop": ActionType.NOOP,
            "investigate_logs": ActionType.INVESTIGATE_LOGS,
            "restart_service": ActionType.RESTART_SERVICE,
            "scale_service": ActionType.SCALE_SERVICE,
            "rollback_deployment": ActionType.ROLLBACK_DEPLOYMENT,
        }

        action_enum = action_type_map.get(normalized_action, ActionType.NOOP)
        service_param = service if action_enum != ActionType.NOOP else None
        
        action = Action(action_type=action_enum, service=service_param)
        
        # Step environment
        self.current_observation, reward, done, info = self.env.step(action)
        
        self.total_reward += reward.total
        self.done = done
        
        # Generate feedback
        action_text = f"Executed: {action_type}"
        if service_param:
            action_text += f" on {service_param}"
        
        step_info = self.env.current_step

        action_label = action_enum.value
        target_label = service_param if service_param else "none"
        reason_text = reason.strip() if reason else "No explicit reasoning provided."
        self.decision_trace.append(
            f"Step {step_info}:\n"
            f"  Actor: {actor}\n"
            f"  Action: {action_label}({target_label})\n"
            f"  Reason: {reason_text}"
        )
        
        if done:
            if info["incident_resolved"]:
                status = f"✅ Incident RESOLVED in {step_info} steps!"
                score, components = self.env.get_grade()
                self.final_score = score
                grade_text = f"Final Score: {score:.3f}\n"
                grade_text += f"Root Cause Fix: {components['root_cause_fixed']:.3f}\n"
                grade_text += f"System Recovery: {components['system_recovered']:.3f}\n"
                grade_text += f"Action Efficiency: {components['action_efficiency']:.3f}"
                status += f"\n\n{grade_text}"
            else:
                status = f"❌ Max steps reached without resolution."
                self.final_score = 0.0
        else:
            status = f"ℹ️ Step {step_info}: {action_text}\nReward: {reward.total:.3f}"
        
        state_text = self._render_state()
        logs_text = self._render_logs()
        
        status_badge = "Done" if done else "Running"
        resolved_text = "Yes" if info.get("incident_resolved", False) else "No"
        
        return (
            status,
            state_text,
            logs_text,
            self.total_reward,
            self.env.current_step,
            self.final_score,
            resolved_text,
            status_badge,
            self._render_root_cause_analysis(),
            self._render_decision_trace(),
        )

    def _ensure_openai_agent(self):
        if self.agent is not None:
            return
        self.agent = OpenAIAgent(model=os.getenv("OPENAI_MODEL"))
    
    def auto_step(self) -> Tuple[str, str, str, float, int, float, str, str, str, str]:
        """Take one OpenAI-agent action step."""
        if self.env is None:
            return (
                "❌ Environment not initialized. Select a scenario first.",
                "", "", 0.0, 0, 0.0, "No", "Not started", self._render_root_cause_analysis(), self._render_decision_trace()
            )

        try:
            self._ensure_openai_agent()
            action = self.agent.select_action(self.current_observation, self.env.current_step + 1)
            self.agent_error_message = getattr(self.agent, "last_error", "") or ""
            reason = getattr(self.agent, "last_reasoning", "") or "Model-selected action from observed telemetry."
        except Exception as e:
            return (
                f"❌ Auto Step failed: {e}",
                self._render_state(),
                self._render_logs(),
                self.total_reward,
                self.env.current_step,
                self.final_score,
                "Yes" if self.env.state().incident_resolved else "No",
                "Running" if not self.done else "Done",
                self._render_root_cause_analysis(),
                self._render_decision_trace(),
            )

        result = self.step_with_action(
            action.action_type.value,
            action.service or "",
            reason=reason,
            actor="Agent",
        )
        return result

    def run_full_episode_agent(self) -> Tuple[str, str, str, float, int, float, str, str, str, str]:
        """Run a full episode using OpenAI agent until done."""
        if self.env is None:
            return (
                "❌ Environment not initialized. Select a scenario first.",
                "", "", 0.0, 0, 0.0, "No", "Not started", self._render_root_cause_analysis(), self._render_decision_trace()
            )

        if self.done:
            return (
                "⏸️ Episode already finished. Reset or initialize another scenario.",
                self._render_state(),
                self._render_logs(),
                self.total_reward,
                self.env.current_step,
                self.final_score,
                "Yes" if self.env.state().incident_resolved else "No",
                "Done",
                self._render_root_cause_analysis(),
                self._render_decision_trace(),
            )

        trace_lines = []
        max_agent_steps = max(1, self.env.max_steps - self.env.current_step)

        for _ in range(max_agent_steps):
            if self.env is None:
                trace_lines.append("⏹️ Environment reset while episode was running.")
                break
            step_result = self.auto_step()
            trace_lines.append(step_result[0].split("\n")[0])
            if step_result[0].startswith("❌"):
                break
            if self.done:
                break

        final_status = "\n".join(trace_lines[-15:])
        if self.env is None:
            return (
                f"{final_status}\n⏹️ Episode stopped because environment is not initialized.",
                "Waiting for scenario selection...",
                "",
                self.total_reward,
                0,
                self.final_score,
                "No",
                "Not started",
                self._render_root_cause_analysis(),
                self._render_decision_trace(),
            )
        if self.done:
            final_status += "\n✅ Agent episode complete."
        else:
            final_status += "\n⏸️ Agent stopped before completion."

        return (
            final_status,
            self._render_state(),
            self._render_logs(),
            self.total_reward,
            self.env.current_step,
            self.final_score,
            "Yes" if self.env.state().incident_resolved else "No",
            "Done" if self.done else "Running",
            self._render_root_cause_analysis(),
            self._render_decision_trace(),
        )

    def _render_root_cause_analysis(self) -> str:
        """Render root cause analysis details after episode completion."""
        if self.env is None or not self.done:
            return "Root cause analysis appears after episode completion."

        state = self.env.state()
        root_service = state.root_cause_service or "unknown"
        root_type = state.root_cause_type or "unknown"

        identified = any(
            a.service == root_service and a.action_type in {
                ActionType.INVESTIGATE_LOGS,
                ActionType.RESTART_SERVICE,
                ActionType.SCALE_SERVICE,
                ActionType.ROLLBACK_DEPLOYMENT,
            }
            for a in self.env._actions_taken
        )

        return (
            "### Root Cause Analysis\n"
            f"- Root Cause Service: **{root_service}**\n"
            f"- Root Cause Type: **{root_type}**\n"
            f"- Identified by Agent: **{'✅' if identified else '❌'}**"
        )

    def _render_decision_trace(self) -> str:
        """Render agent/user decision trace."""
        if not self.decision_trace:
            return "No decisions yet."
        return "\n\n".join(self.decision_trace[-20:])
    
    def _render_state(self) -> str:
        """Render current system state."""
        if self.current_observation is None:
            return "No observation yet"
        
        lines = []
        
        # Alerts
        lines.append("🚨 **ALERTS**")
        if self.current_observation.alerts:
            for alert in self.current_observation.alerts:
                severity_icon = "🔴" if alert.severity.value == "critical" else "🟡" if alert.severity.value == "warning" else "ℹ️"
                marker = "⭐" if alert.is_root_cause else ""
                lines.append(f"{severity_icon} {alert.service}: {alert.message} {marker}")
        else:
            lines.append("✅ No alerts")
        
        # Service Health
        lines.append("\n📊 **SERVICE HEALTH**")
        for service, health in sorted(self.current_observation.service_health.items()):
            status_icon = "✅" if health.value == "healthy" else "⚠️" if health.value == "degraded" else "❌"
            lines.append(f"{status_icon} {service}: {health.value}")
        
        # Key Metrics
        lines.append("\n📈 **KEY METRICS**")
        
        metrics_by_service = {}
        for metric in self.current_observation.metrics:
            if metric.service not in metrics_by_service:
                metrics_by_service[metric.service] = {}
            metrics_by_service[metric.service][metric.name] = metric.value
        
        for service in sorted(metrics_by_service.keys()):
            metrics = metrics_by_service[service]
            lines.append(f"\n**{service}**")
            for metric_name in ["cpu_usage", "memory_usage", "error_rate", "latency_ms"]:
                if metric_name in metrics:
                    value = metrics[metric_name]
                    if metric_name.endswith("_rate"):
                        lines.append(f"  • {metric_name}: {value:.2%}")
                    elif metric_name.endswith("_usage") or metric_name == "cpu_usage":
                        lines.append(f"  • {metric_name}: {value:.1f}%")
                    else:
                        lines.append(f"  • {metric_name}: {value:.0f}ms")
        
        return "\n".join(lines)
    
    def _render_logs(self) -> str:
        """Render recent logs."""
        if not self.current_observation or not self.current_observation.logs:
            return "No logs yet"
        
        lines = []
        lines.append("📝 **RECENT LOGS**")
        
        # Show error/warning logs first
        error_logs = [l for l in self.current_observation.logs if l.level in ["ERROR", "WARN"]]
        for log in error_logs[:10]:
            icon = "🔴" if log.level == "ERROR" else "🟡"
            relevant = "⭐" if log.is_relevant else ""
            lines.append(f"{icon} [{log.service}] {log.message} {relevant}")
        
        return "\n".join(lines)
    
    def reset_ui(self) -> Tuple[str, str, str, float, int, float, str, str, str, str]:
        """Reset to initial state."""
        self.env = None
        self.current_observation = None
        self.total_reward = 0.0
        self.final_score = 0.0
        self.done = False
        self.agent = None
        self.decision_trace = []
        
        return (
            "Ready to select scenario",
            "Waiting for scenario selection...",
            "",
            0.0,
            0,
            0.0,
            "No",
            "Not started",
            self._render_root_cause_analysis(),
            self._render_decision_trace(),
        )


# Initialize UI
ui = EnvironmentUI()


def create_interface() -> gr.Blocks:
    """Create Gradio interface."""
    
    scenarios_by_difficulty = ScenarioManager.get_all_scenarios()
    
    # Flatten scenarios for dropdown
    scenario_choices = []
    for difficulty, scenarios in scenarios_by_difficulty.items():
        for scenario in scenarios:
            scenario_choices.append((f"[{difficulty.upper()}] {scenario.task_name}", scenario.task_name))
    
    with gr.Blocks(title="SRE Incident Response Simulator") as interface:
        
        # Header
        gr.Markdown("""
# 🚨 Incident Response OpenEnv Simulator

An interactive environment for training autonomous SRE agents to diagnose and resolve production incidents.

**Objective**: Use strategic actions to identify the root cause and restore system health.
        """)
        
        # Main layout
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("## Controls")
                
                # Scenario selector
                scenario_select = gr.Dropdown(
                    label="Select Scenario",
                    choices=scenario_choices,
                    value=scenario_choices[0][1] if scenario_choices else None
                )
                
                init_button = gr.Button("Initialize Scenario", variant="primary", size="lg")
                
                gr.Markdown("### Actions")
                action_select = gr.Dropdown(
                    label="Action Type",
                    choices=[
                        "NOOP",
                        "Investigate Logs",
                        "Restart Service",
                        "Scale Service",
                        "Rollback Deployment",
                    ],
                    value="Investigate Logs"
                )
                
                service_select = gr.Dropdown(
                    label="Target Service",
                    choices=["database", "auth_service", "api_gateway", "cache_service"],
                    value="database"
                )
                
                with gr.Row():
                    step_button = gr.Button("Execute Action", variant="primary")
                    auto_button = gr.Button("Auto Step (Agent)")

                full_episode_button = gr.Button("Run Full Episode (Agent)", variant="secondary")
                
                reset_button = gr.Button("Reset", variant="stop")
            
            with gr.Column(scale=2):
                gr.Markdown("## System State")
                
                status_box = gr.Textbox(
                    label="Status",
                    value="Ready",
                    interactive=False,
                    lines=3
                )
                
                with gr.Tabs():
                    with gr.TabItem("Alerts & Health"):
                        state_output = gr.Markdown("Waiting for scenario initialization...")
                    
                    with gr.TabItem("Logs"):
                        logs_output = gr.Markdown("No logs yet...")
                
                reward_box = gr.Number(
                    label="Total Reward (Training Signal)",
                    value=0.0,
                    interactive=False
                )

                steps_box = gr.Number(
                    label="Steps Taken",
                    value=0,
                    interactive=False
                )

                score_box = gr.Number(
                    label="Final Score (Evaluation)",
                    value=0.0,
                    interactive=False
                )

                gr.Markdown("Reward is step-by-step feedback. Final Score is evaluation metric.")

                resolved_box = gr.Textbox(
                    label="Incident Resolved",
                    value="No",
                    interactive=False
                )
                
                status_badge = gr.Textbox(
                    label="Episode Status",
                    value="Not started",
                    interactive=False
                )

                root_cause_output = gr.Markdown("Root cause analysis appears after episode completion.")
                trace_output = gr.Markdown("No decisions yet.")
        
        # Event handlers
        def init_scenario(scenario_name: str):
            return ui.init_environment(scenario_name)
        
        def exec_action(action_type: str, service: str):
            return ui.step_with_action(action_type, service)
        
        def auto():
            return ui.auto_step()

        def run_full_episode():
            return ui.run_full_episode_agent()
        
        def reset():
            return ui.reset_ui()
        
        init_button.click(
            fn=init_scenario,
            inputs=[scenario_select],
            outputs=[status_box, state_output, logs_output, reward_box, steps_box, score_box, resolved_box, status_badge, root_cause_output, trace_output]
        )
        
        step_button.click(
            fn=exec_action,
            inputs=[action_select, service_select],
            outputs=[status_box, state_output, logs_output, reward_box, steps_box, score_box, resolved_box, status_badge, root_cause_output, trace_output]
        )
        
        auto_button.click(
            fn=auto,
            inputs=[],
            outputs=[status_box, state_output, logs_output, reward_box, steps_box, score_box, resolved_box, status_badge, root_cause_output, trace_output]
        )

        full_episode_button.click(
            fn=run_full_episode,
            inputs=[],
            outputs=[status_box, state_output, logs_output, reward_box, steps_box, score_box, resolved_box, status_badge, root_cause_output, trace_output]
        )
        
        reset_button.click(
            fn=reset,
            inputs=[],
            outputs=[status_box, state_output, logs_output, reward_box, steps_box, score_box, resolved_box, status_badge, root_cause_output, trace_output]
        )
    
    return interface


def main():
    """Launch the Gradio app."""
    interface = create_interface()
    interface.launch(share=False, server_name="0.0.0.0", server_port=7860, theme=gr.themes.Soft())


if __name__ == "__main__":
    main()
