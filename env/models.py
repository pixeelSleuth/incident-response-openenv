"""
Incident Response Environment Models

Defines Pydantic models for observation, action, reward, and system state.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from enum import Enum


class ServiceHealth(str, Enum):
    """Service health states."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class Alert(BaseModel):
    """Structured alert message."""
    timestamp: int
    service: str
    severity: AlertSeverity
    message: str
    is_root_cause: bool = False  # If True, this alert points to root cause


class Metric(BaseModel):
    """Performance metric."""
    name: str
    service: str
    value: float
    threshold: Optional[float] = None
    timestamp: int


class LogEntry(BaseModel):
    """Log entry from a service."""
    timestamp: int
    service: str
    level: str  # "DEBUG", "INFO", "WARN", "ERROR"
    message: str
    is_relevant: bool = False  # True if log is relevant to diagnosis


class Observation(BaseModel):
    """
    Complete observation presented to the agent.
    
    Includes:
    - Alerts (structured, with severities)
    - Metrics (CPU, memory, latency, error rates)
    - Recent logs (noisy, partially irrelevant)
    - Service health summary
    """
    timestamp: int
    alerts: List[Alert] = Field(default_factory=list)
    metrics: List[Metric] = Field(default_factory=list)
    logs: List[LogEntry] = Field(default_factory=list)
    service_health: Dict[str, ServiceHealth] = Field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "timestamp": self.timestamp,
            "alerts": [a.model_dump() for a in self.alerts],
            "metrics": [m.model_dump() for m in self.metrics],
            "logs": [l.model_dump() for l in self.logs],
            "service_health": {k: v.value for k, v in self.service_health.items()}
        }


class ActionType(str, Enum):
    """Available action types."""
    RESTART_SERVICE = "restart_service"
    INVESTIGATE_LOGS = "investigate_logs"
    SCALE_SERVICE = "scale_service"
    ROLLBACK_DEPLOYMENT = "rollback_deployment"
    NOOP = "noop"


class Action(BaseModel):
    """Agent action."""
    action_type: ActionType
    service: Optional[str] = None
    target_replicas: Optional[int] = None


class Reward(BaseModel):
    """Reward with components for interpretability."""
    total: float
    root_cause_fix: float = 0.0
    system_recovery: float = 0.0
    action_efficiency: float = 0.0
    investigation_reward: float = 0.0
    step_penalty: float = 0.0
    action_penalty: float = 0.0
    
    def __add__(self, other):
        """Add rewards together."""
        if isinstance(other, (int, float)):
            new_reward = Reward(total=self.total + other)
            new_reward.step_penalty = self.step_penalty
            return new_reward
        return Reward(
            total=self.total + other.total,
            root_cause_fix=self.root_cause_fix + other.root_cause_fix,
            system_recovery=self.system_recovery + other.system_recovery,
            action_efficiency=self.action_efficiency + other.action_efficiency,
            investigation_reward=self.investigation_reward + other.investigation_reward,
            step_penalty=self.step_penalty + other.step_penalty,
            action_penalty=self.action_penalty + other.action_penalty,
        )


class SystemState(BaseModel):
    """Complete internal system state (not visible to agent)."""
    timestamp: int
    
    # Service states
    services: Dict[str, Dict] = Field(default_factory=dict)
    # Example: {
    #     "database": {
    #         "healthy": False,
    #         "replicas": 3,
    #         "memory_usage": 85.0,
    #         "cpu_usage": 45.0,
    #         "error_rate": 0.05,
    #         "latency_ms": 150
    #     }
    # }
    
    # Root cause information (NOT visible to agent)
    root_cause_service: Optional[str] = None
    root_cause_type: Optional[str] = None  # "outage", "memory_leak", "slow_deployment"
    
    # Incident progression
    incident_step: int = 0
    incident_resolved: bool = False

    # Hidden dynamics state (not visible to agent)
    memory_leak_active: bool = False
    timeout_storm_active: bool = False
    retry_storm_active: bool = False
    investigated_services: List[str] = Field(default_factory=list)
    
    # Tracking agent actions
    actions_taken: List[Action] = Field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp,
            "services": self.services,
            "root_cause_service": self.root_cause_service,
            "root_cause_type": self.root_cause_type,
            "incident_step": self.incident_step,
            "incident_resolved": self.incident_resolved,
            "memory_leak_active": self.memory_leak_active,
            "timeout_storm_active": self.timeout_storm_active,
            "retry_storm_active": self.retry_storm_active,
            "investigated_services": self.investigated_services,
            "actions_taken": [a.model_dump() for a in self.actions_taken]
        }
