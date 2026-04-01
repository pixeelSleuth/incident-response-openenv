"""
LLM-based Baseline Agent

Uses OpenAI-compatible chat completions APIs (OpenAI, xAI/Grok, Groq) to
perform reasoning over observations and select actions.
"""

import os
import json
from typing import Tuple, Optional
from env.models import Action, ActionType, Observation
from env.incident_env import IncidentResponseEnv

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


class OpenAIAgent:
    """Agent that uses an OpenAI-compatible API for reasoning."""
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize agent.
        
        Args:
            api_key: API key (GROQ_API_KEY, OPENAI_API_KEY, or GROK_API_KEY)
            model: Model name. If not set, uses OPENAI_MODEL or provider default.
        """
        if OpenAI is None:
            raise ImportError("openai package not installed")
        
        self.api_key = (
            api_key
            or os.getenv("GROQ_API_KEY")
            or os.getenv("OPENAI_API_KEY")
            or os.getenv("GROK_API_KEY")
        )
        if not self.api_key:
            raise ValueError("Set GROQ_API_KEY or OPENAI_API_KEY or GROK_API_KEY in environment")

        self.base_url = os.getenv("OPENAI_BASE_URL")
        if not self.base_url:
            if os.getenv("GROQ_API_KEY"):
                self.base_url = "https://api.groq.com/openai/v1"
            elif os.getenv("GROK_API_KEY"):
                self.base_url = "https://api.x.ai/v1"

        self.model = model or os.getenv("OPENAI_MODEL")
        if not self.model:
            if self.base_url == "https://api.groq.com/openai/v1":
                self.model = "llama-3.3-70b-versatile"
            elif self.base_url == "https://api.x.ai/v1":
                self.model = "grok-2-latest"
            else:
                self.model = "gpt-4o-mini"
        
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        self.conversation_history = []
        self.last_error: Optional[str] = None
        self._last_logged_error: Optional[str] = None
        self.last_reasoning: str = ""
    
    def select_action(self, observation: Observation, step: int) -> Action:
        """
        Select action based on observation using OpenAI reasoning.
        
        Args:
            observation: Current environment observation
            step: Current step number
        
        Returns:
            Action to take
        """
        # Format observation for prompt
        obs_text = self._format_observation(observation)
        
        # Construct prompt
        system_prompt = self._get_system_prompt()
        
        user_message = f"""
Current step: {step}

{obs_text}

Based on this observation, what action should we take to resolve this incident?

Please respond in this exact JSON format:
{{
    "reasoning": "Brief explanation of your reasoning",
    "action_type": "restart_service|investigate_logs|scale_service|rollback_deployment|noop",
    "service": "database|auth_service|api_gateway|cache_service|null"
}}

ACTION DEFINITIONS:
- restart_service: Restart a failing service to clear errors
- investigate_logs: Analyze logs from a service to gather information
- scale_service: Add more replicas to distribute load
- rollback_deployment: Revert to previous version
- noop: Take no action (think and wait)
"""
        
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })
        
        # Call OpenAI-compatible API
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": system_prompt}] + self.conversation_history,
                temperature=0.0,
                max_tokens=500,
            )
            self.last_error = None
            
            assistant_response = response.choices[0].message.content
            self.conversation_history.append({
                "role": "assistant",
                "content": assistant_response
            })
            
            # Parse response
            action = self._parse_action_response(assistant_response)
            if not self.last_reasoning:
                self.last_reasoning = "Model selected this action based on current alerts, metrics, and logs."
            
        except Exception as e:
            self.last_error = str(e)
            if self.last_error != self._last_logged_error:
                print(f"LLM API error: {self.last_error}")
                self._last_logged_error = self.last_error
            raise RuntimeError(f"LLM request failed: {self.last_error}") from e
        
        return action
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the agent."""
        return """
You are an expert Site Reliability Engineer (SRE) tasked with diagnosing and resolving
production incidents in a distributed system. 

Your goal is to return the system to a healthy state as quickly as possible using the
fewest actions possible.

Key principles:
1. First, understand the root cause of the incident by analyzing alerts and logs
2. Prefer targeted fixes (restart the right service) over broad actions
3. Use investigation and logs to guide your diagnosis
4. Prioritize critical alerts (CRITICAL > WARNING > INFO)
5. When uncertain, investigate before taking action
6. Track which services are actually failing vs. affected downstream

Common incident patterns:
- Database outage: restart the database service
- Auth failures due to DB issues: restart database (fixes auth)
- Memory leaks: restart affected service
- Cascading failures: start with root cause, not symptoms
"""
    
    def _format_observation(self, observation: Observation) -> str:
        """Format observation into readable text."""
        lines = []
        
        lines.append("ALERTS:")
        for alert in observation.alerts:
            severity_emoji = "🔴" if alert.severity == "critical" else "🟡" if alert.severity == "warning" else "ℹ️"
            lines.append(f"  {severity_emoji} [{alert.service}] {alert.message}")
        
        lines.append("\nMETRICS (Summary):")
        # Group metrics by service
        metrics_by_service = {}
        for metric in observation.metrics:
            if metric.service not in metrics_by_service:
                metrics_by_service[metric.service] = {}
            metrics_by_service[metric.service][metric.name] = metric.value
        
        for service, metrics in sorted(metrics_by_service.items()):
            lines.append(f"  {service}:")
            if "error_rate" in metrics:
                lines.append(f"    Error Rate: {metrics['error_rate']:.2%}")
            if "latency_ms" in metrics:
                lines.append(f"    Latency: {metrics['latency_ms']:.0f}ms")
            if "cpu_usage" in metrics:
                lines.append(f"    CPU: {metrics['cpu_usage']:.0f}%")
            if "memory_usage" in metrics:
                lines.append(f"    Memory: {metrics['memory_usage']:.0f}%")
        
        lines.append("\nSERVICE HEALTH:")
        for service, health in sorted(observation.service_health.items()):
            status = "✅" if health == "healthy" else "⚠️" if health == "degraded" else "❌"
            lines.append(f"  {status} {service}: {health}")
        
        lines.append("\nRECENT LOGS:")
        error_logs = [log for log in observation.logs if log.level in ["ERROR", "WARN"]]
        for log in error_logs[:5]:  # Show first 5 error logs
            lines.append(f"  [{log.service}] {log.message}")
        
        return "\n".join(lines)
    
    def _parse_action_response(self, response_text: str) -> Action:
        """Parse JSON action response from OpenAI."""
        try:
            # Find JSON in response
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            
            if json_start == -1 or json_end == 0:
                # No JSON found, parse text
                return self._fallback_parse(response_text)
            
            json_str = response_text[json_start:json_end]
            data = json.loads(json_str)
            
            action_type_str = data.get("action_type", "noop").lower()
            service = data.get("service")
            self.last_reasoning = (data.get("reasoning") or "").strip()
            
            # Convert to ActionType
            action_type_map = {
                "restart_service": ActionType.RESTART_SERVICE,
                "investigate_logs": ActionType.INVESTIGATE_LOGS,
                "scale_service": ActionType.SCALE_SERVICE,
                "rollback_deployment": ActionType.ROLLBACK_DEPLOYMENT,
                "noop": ActionType.NOOP,
            }
            
            action_type = action_type_map.get(action_type_str, ActionType.NOOP)
            
            return Action(action_type=action_type, service=service)
        
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Could not parse action response: {e}")
            # Fallback
            self.last_reasoning = "Response parsing failed; using investigation fallback."
            return Action(action_type=ActionType.INVESTIGATE_LOGS)
    
    def _fallback_parse(self, text: str) -> Action:
        """Fallback parsing if JSON parsing fails."""
        text_lower = text.lower()
        
        if "restart" in text_lower:
            self.last_reasoning = "Text indicated restart remediation."
            return Action(action_type=ActionType.RESTART_SERVICE, service="database")
        elif "investigate" in text_lower or "log" in text_lower:
            self.last_reasoning = "Text indicated further investigation."
            return Action(action_type=ActionType.INVESTIGATE_LOGS)
        elif "scale" in text_lower:
            self.last_reasoning = "Text indicated scaling for pressure relief."
            return Action(action_type=ActionType.SCALE_SERVICE, service="api_gateway")
        elif "rollback" in text_lower:
            self.last_reasoning = "Text indicated rollback as remediation."
            return Action(action_type=ActionType.ROLLBACK_DEPLOYMENT, service="database")
        else:
            self.last_reasoning = "No clear action parsed; defaulting to noop."
            return Action(action_type=ActionType.NOOP)

    def reset(self):
        """Reset conversation history for new episode."""
        self.conversation_history = []
