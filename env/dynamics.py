"""
System Dynamics Engine

Implements deterministic rule-based transitions for the incident response system.
Simulates cascading failures and recovery.
"""

import random
from typing import Tuple, List
from env.models import SystemState, Alert, AlertSeverity, LogEntry


class DynamicsEngine:
    """Simulates system state transitions based on incident type and agent actions."""
    
    def __init__(self, seed: int = 42):
        """Initialize dynamics engine with deterministic seed."""
        self.random = random.Random(seed)
    
    def initialize_healthy_state(self) -> SystemState:
        """Create a healthy baseline system state."""
        return SystemState(
            timestamp=0,
            services={
                "database": {
                    "healthy": True,
                    "replicas": 3,
                    "memory_usage": 45.0,
                    "cpu_usage": 20.0,
                    "error_rate": 0.001,
                    "latency_ms": 50,
                    "deployed_version": "2.1.0"
                },
                "auth_service": {
                    "healthy": True,
                    "replicas": 2,
                    "memory_usage": 35.0,
                    "cpu_usage": 15.0,
                    "error_rate": 0.0005,
                    "latency_ms": 30,
                    "deployed_version": "1.5.0"
                },
                "api_gateway": {
                    "healthy": True,
                    "replicas": 4,
                    "memory_usage": 40.0,
                    "cpu_usage": 25.0,
                    "error_rate": 0.0,
                    "latency_ms": 20,
                    "deployed_version": "3.2.1"
                },
                "cache_service": {
                    "healthy": True,
                    "replicas": 2,
                    "memory_usage": 60.0,
                    "cpu_usage": 10.0,
                    "error_rate": 0.0,
                    "latency_ms": 5,
                    "deployed_version": "1.0.2"
                }
            },
            root_cause_service=None,
            root_cause_type=None,
            incident_step=0,
            incident_resolved=False,
            actions_taken=[]
        )
    
    def apply_incident(self, state: SystemState, incident_type: str) -> SystemState:
        """
        Apply an incident to the system.
        
        incident_type: "database_outage", "memory_leak", "cascading_failure"
        """
        if incident_type == "database_outage":
            state.services["database"]["healthy"] = False
            state.services["database"]["error_rate"] = 0.95
            state.services["database"]["latency_ms"] = 5000
            state.root_cause_service = "database"
            state.root_cause_type = "outage"
            state.memory_leak_active = False
            
        elif incident_type == "auth_dependency_failure":
            # Auth failure due to DB latency/issues
            state.services["database"]["healthy"] = True
            state.services["database"]["latency_ms"] = 2000
            state.services["database"]["error_rate"] = 0.3
            state.services["auth_service"]["error_rate"] = 0.7
            state.services["auth_service"]["latency_ms"] = 1500
            state.root_cause_service = "database"
            state.root_cause_type = "latency"
            state.memory_leak_active = False
            
        elif incident_type == "cascading_failure":
            # Memory leak triggers cascading failure
            state.services["database"]["healthy"] = False
            state.services["database"]["memory_usage"] = 92.0
            state.services["database"]["cpu_usage"] = 88.0
            state.services["database"]["latency_ms"] = 3000
            state.services["database"]["error_rate"] = 0.4
            state.services["database"]["stabilization_steps_remaining"] = 0
            state.services["auth_service"]["error_rate"] = 0.6
            state.services["auth_service"]["latency_ms"] = 2000
            state.services["api_gateway"]["error_rate"] = 0.3
            state.root_cause_service = "database"
            state.root_cause_type = "memory_leak"
            state.memory_leak_active = True
            state.timeout_storm_active = True
            state.retry_storm_active = True
        
        return state
    
    def step(self, state: SystemState, action_applied: str, 
             action_service: str = None) -> Tuple[SystemState, bool]:
        """
        Apply one step of dynamics.
        
        Returns:
            (updated_state, incident_fixed)
        """
        state.timestamp += 1
        state.incident_step += 1
        
        incident_fixed = False
        
        # Apply action effects
        if action_applied == "restart_service" and action_service:
            state = self._apply_restart_service(state, action_service)
            
        elif action_applied == "investigate_logs":
            state = self._apply_investigate_logs(state, action_service)
            
        elif action_applied == "scale_service" and action_service:
            state = self._apply_scale_service(state, action_service)
            
        elif action_applied == "rollback_deployment" and action_service:
            state = self._apply_rollback(state, action_service)
        
        # Update dynamics (cascading effects, recovery)
        state = self._update_cascading_effects(state)
        
        # Check if incident resolved
        if state.root_cause_service and not state.incident_resolved:
            root_svc = state.services[state.root_cause_service]
            if (
                root_svc.get("healthy", False)
                and root_svc.get("error_rate", 1.0) <= 0.05
                and root_svc.get("latency_ms", 9999) <= 300
                and not state.timeout_storm_active
                and not state.retry_storm_active
            ):
                state.incident_resolved = True
                incident_fixed = True
        
        return state, incident_fixed
    
    def _apply_restart_service(self, state: SystemState, service: str) -> SystemState:
        """Restart a service - clears errors and recovers health."""
        if service in state.services:
            svc = state.services[service]
            svc["error_rate"] = max(0.0, svc["error_rate"] - 0.7)
            svc["latency_ms"] = max(50, svc["latency_ms"] - 2000)
            svc["memory_usage"] = max(30.0, svc["memory_usage"] - 30.0)
            
            # If this is the root cause service and memory leak, restart fixes it
            if state.root_cause_service == service and state.root_cause_type == "memory_leak":
                # Hard-task realism: full recovery requires prior investigation.
                if service in state.investigated_services:
                    # Staged recovery: restart mitigates root issue, full stabilization
                    # completes on a later step.
                    svc["healthy"] = True
                    svc["memory_usage"] = 70.0
                    svc["cpu_usage"] = 65.0
                    svc["error_rate"] = 0.08
                    svc["latency_ms"] = 650
                    svc["stabilization_steps_remaining"] = 2
                    state.memory_leak_active = False
                    state.timeout_storm_active = True
                    state.retry_storm_active = True
                else:
                    # Restart without diagnosis gives temporary relief only.
                    svc["healthy"] = False
                    svc["memory_usage"] = max(80.0, svc["memory_usage"] - 8.0)
                    svc["cpu_usage"] = max(70.0, svc["cpu_usage"] - 10.0)
                    svc["error_rate"] = max(0.18, svc["error_rate"] - 0.15)
                    svc["latency_ms"] = max(900, svc["latency_ms"] - 700)
            
            # If database outage, restart can fix it
            if state.root_cause_service == service and state.root_cause_type == "outage":
                svc["healthy"] = True
                svc["error_rate"] = 0.001
                svc["latency_ms"] = 50

            # Medium case: DB latency is root cause for auth failures.
            if state.root_cause_service == service and state.root_cause_type == "latency":
                required_investigations = {"auth_service", "database"}
                if required_investigations.issubset(set(state.investigated_services)):
                    svc["healthy"] = True
                    svc["error_rate"] = 0.005
                    svc["latency_ms"] = 80
                    state.timeout_storm_active = False
                    state.retry_storm_active = False
                else:
                    # Partial and unstable recovery when dependency chain was not
                    # investigated end-to-end.
                    svc["healthy"] = False
                    svc["error_rate"] = max(0.12, svc["error_rate"] - 0.08)
                    svc["latency_ms"] = max(650, svc["latency_ms"] - 450)
                    state.timeout_storm_active = True
                    state.retry_storm_active = True
        
        return state
    
    def _apply_investigate_logs(self, state: SystemState, service: str) -> SystemState:
        """Investigating logs provides no direct fix but can validate diagnosis."""
        if service and service in state.services and service not in state.investigated_services:
            state.investigated_services.append(service)

        # Hard scenario: investigation provides slight short-term mitigation while
        # revealing signal, but does not resolve incident.
        if state.root_cause_type == "memory_leak" and service == "database":
            db = state.services.get("database", {})
            db["cpu_usage"] = max(60.0, db.get("cpu_usage", 0) - 8.0)
            db["latency_ms"] = max(900, db.get("latency_ms", 50) - 350)
        return state
    
    def _apply_scale_service(self, state: SystemState, service: str) -> SystemState:
        """Scale service - increases replicas, helps with load."""
        if service in state.services:
            svc = state.services[service]
            # Scaling adds replicas (max 10)
            svc["replicas"] = min(10, svc["replicas"] + 2)
            # Slightly improves performance
            svc["error_rate"] = max(0.0, svc["error_rate"] - 0.1)
            svc["latency_ms"] = max(svc["latency_ms"] - 100, 5)
        
        return state
    
    def _apply_rollback(self, state: SystemState, service: str) -> SystemState:
        """Rollback deployment - reverts to previous version."""
        if service in state.services:
            svc = state.services[service]
            
            # Check if rollback might fix a recent issue
            if svc["deployed_version"] == "2.1.0" and service == "database":
                # Rollback can fix issues introduced in recent deploy
                svc["healthy"] = True
                svc["error_rate"] = 0.001
                svc["latency_ms"] = 50
                svc["deployed_version"] = "2.0.5"
            else:
                # Generic rollback effect
                svc["error_rate"] = max(0.0, svc["error_rate"] - 0.4)
                svc["latency_ms"] = max(svc["latency_ms"] - 800, 5)
        
        return state
    
    def _update_cascading_effects(self, state: SystemState) -> SystemState:
        """
        Update system based on cascading failure dynamics.
        
        Rules:
        - If database is unhealthy → auth service errors increase
        - If latency high → retry storm increases error rates
        - If memory/CPU high → latency increases
        - Recovery happens gradually
        """
        # Database health affects downstream services
        db = state.services.get("database", {})

        # Staged stabilization path for hard incidents after corrective restart.
        stabilization_remaining = int(db.get("stabilization_steps_remaining", 0))
        if stabilization_remaining > 0:
            db["stabilization_steps_remaining"] = stabilization_remaining - 1
            db["error_rate"] = max(0.03, db.get("error_rate", 0.0) - 0.04)
            db["latency_ms"] = max(260, db.get("latency_ms", 50) - 180)
            db["cpu_usage"] = max(35.0, db.get("cpu_usage", 0) - 10.0)
            db["memory_usage"] = max(52.0, db.get("memory_usage", 0) - 6.0)

            if db["stabilization_steps_remaining"] <= 0:
                # HARD: do NOT fully recover instantly
                if state.root_cause_type == "memory_leak":
                    db["healthy"] = False  # ❌ keep unstable
                    db["error_rate"] = max(0.03, db.get("error_rate", 0.0))
                    db["latency_ms"] = max(300, db.get("latency_ms", 50))
                    db["cpu_usage"] = max(40.0, db.get("cpu_usage", 20))
                    db["memory_usage"] = max(60.0, db.get("memory_usage", 45))
                    
                    # storms persist longer
                    state.timeout_storm_active = True
                    state.retry_storm_active = True
                else:
                    # normal recovery (easy/medium)
                    db["healthy"] = True
                    db["error_rate"] = min(db.get("error_rate", 0.0), 0.005)
                    db["latency_ms"] = min(db.get("latency_ms", 50), 80)
                    db["cpu_usage"] = min(db.get("cpu_usage", 20), 22.0)
                    db["memory_usage"] = min(db.get("memory_usage", 45), 48.0)
                    state.timeout_storm_active = False
                    state.retry_storm_active = False

        if not db.get("healthy", False):
            # Database issues cascade to auth
            auth = state.services.get("auth_service", {})
            auth["error_rate"] = min(0.9, auth["error_rate"] + 0.05)
            auth["latency_ms"] += 100
        
        # Memory leak chain:
        # memory leak -> CPU spike -> timeout storm -> retry storm
        if state.memory_leak_active and not state.incident_resolved:
            db["memory_usage"] = min(99.0, db.get("memory_usage", 0) + 2.5)
            if db["memory_usage"] > 90:
                db["cpu_usage"] = min(99.0, db.get("cpu_usage", 0) + 3.0)

            if db["cpu_usage"] > 85:
                state.timeout_storm_active = True

            if state.timeout_storm_active:
                db["latency_ms"] = min(6000, db.get("latency_ms", 50) + 250)
                db["error_rate"] = min(0.9, db.get("error_rate", 0.0) + 0.08)

            if db["latency_ms"] > 1200:
                state.retry_storm_active = True

        # Retry storm amplifies downstream errors.
        if state.retry_storm_active:
            for svc_name in ["auth_service", "api_gateway"]:
                svc = state.services.get(svc_name, {})
                svc["error_rate"] = min(0.95, svc.get("error_rate", 0.0) + 0.08)
                svc["latency_ms"] = min(5000, svc.get("latency_ms", 50) + 180)

        # General pressure effects from high CPU/memory.
        for svc in state.services.values():
            if svc.get("cpu_usage", 0) > 80:
                svc["latency_ms"] += 200
                svc["error_rate"] = min(0.8, svc["error_rate"] + 0.1)
            
            if svc.get("memory_usage", 0) > 85:
                svc["error_rate"] = min(0.7, svc["error_rate"] + 0.05)
                svc["latency_ms"] += 150
        
        # Recovery: gradual improvement if root cause is mitigated.
        recovering = (
            not state.memory_leak_active
            and db.get("latency_ms", 0) <= 250
            and int(db.get("stabilization_steps_remaining", 0)) <= 0
        )
        if recovering:
            state.timeout_storm_active = False
            state.retry_storm_active = False

        for svc in state.services.values():
            if svc.get("healthy", False) and (state.incident_resolved or recovering):
                svc["error_rate"] = max(0.0, svc["error_rate"] - 0.05)
                svc["latency_ms"] = max(svc["latency_ms"] - 30, 5)
                svc["cpu_usage"] = max(svc["cpu_usage"] - 2, 10)
                svc["memory_usage"] = max(svc["memory_usage"] - 3, 30)
        
        return state
    
    def add_noise_and_logs(self, state: SystemState, task_name: str) -> Tuple[List[Alert], List[LogEntry]]:
        """
        Generate noisy alerts and logs for observation.
        
        Returns:
            (alerts, logs)
        """
        alerts = []
        logs = []
        
        # Root cause alerts (always present)
        if state.root_cause_service:
            if state.root_cause_type == "outage":
                alerts.append(Alert(
                    timestamp=state.timestamp,
                    service=state.root_cause_service,
                    severity=AlertSeverity.CRITICAL,
                    message=f"{state.root_cause_service} is throwing errors (95% error rate)",
                    is_root_cause=True
                ))
            elif state.root_cause_type == "memory_leak":
                alerts.append(Alert(
                    timestamp=state.timestamp,
                    service=state.root_cause_service,
                    severity=AlertSeverity.CRITICAL,
                    message=f"{state.root_cause_service} memory usage critically high ({state.services[state.root_cause_service]['memory_usage']:.1f}%)",
                    is_root_cause=True
                ))
            elif state.root_cause_type == "latency":
                alerts.append(Alert(
                    timestamp=state.timestamp,
                    service=state.root_cause_service,
                    severity=AlertSeverity.WARNING,
                    message=f"{state.root_cause_service} latency high ({state.services[state.root_cause_service]['latency_ms']}ms)",
                    is_root_cause=True
                ))

        # Medium mode intentionally shows a misleading auth alert.
        if "medium" in task_name and "auth_dependency" in task_name:
            alerts.append(Alert(
                timestamp=state.timestamp,
                service="auth_service",
                severity=AlertSeverity.CRITICAL,
                message=f"auth_service login failures ({state.services['auth_service']['error_rate']:.2%})",
                is_root_cause=False
            ))
        
        # Misleading alerts (to increase difficulty)
        if "cascading" in task_name or "hard" in task_name:
            # Add misleading alerts about downstream services
            for svc_name in ["auth_service", "api_gateway", "cache_service"]:
                if self.random.random() < 0.6:
                    alerts.append(Alert(
                        timestamp=state.timestamp,
                        service=svc_name,
                        severity=AlertSeverity.WARNING,
                        message=f"{svc_name} error rate elevated ({state.services[svc_name]['error_rate']:.2%})",
                        is_root_cause=False
                    ))
        
        # Logs
        if state.root_cause_service:
            root_svc_name = state.root_cause_service
            for _ in range(5):
                logs.append(LogEntry(
                    timestamp=state.timestamp,
                    service=root_svc_name,
                    level="ERROR",
                    message=f"Request failed: connection refused or timeout",
                    is_relevant=self.random.random() < 0.7
                ))

        if state.root_cause_type == "memory_leak":
            if "database" in state.investigated_services:
                logs.append(LogEntry(
                    timestamp=state.timestamp,
                    service="database",
                    level="CRITICAL",
                    message="CRITICAL: memory leak detected in database process",
                    is_relevant=True
                ))
            else:
                logs.append(LogEntry(
                    timestamp=state.timestamp,
                    service="database",
                    level="ERROR",
                    message="database worker instability observed under sustained load",
                    is_relevant=False
                ))

        if state.root_cause_type == "latency":
            if "auth_service" in state.investigated_services:
                logs.append(LogEntry(
                    timestamp=state.timestamp,
                    service="auth_service",
                    level="ERROR",
                    message="ERROR: downstream timeout from database",
                    is_relevant=True
                ))
            if "database" in state.investigated_services:
                logs.append(LogEntry(
                    timestamp=state.timestamp,
                    service="database",
                    level="WARN",
                    message="WARNING: high latency detected in database",
                    is_relevant=True
                ))
            if state.timeout_storm_active:
                logs.append(LogEntry(
                    timestamp=state.timestamp,
                    service="database",
                    level="ERROR",
                    message="timeout storm detected: upstream requests exceeding deadline",
                    is_relevant=True
                ))
            if state.retry_storm_active:
                logs.append(LogEntry(
                    timestamp=state.timestamp,
                    service="api_gateway",
                    level="WARN",
                    message="retry storm detected: aggressive retries amplifying load",
                    is_relevant=True
                ))
        
        # Noisy logs
        for _ in range(10):
            random_svc = self.random.choice(list(state.services.keys()))
            log_levels = ["DEBUG", "INFO", "WARN"]
            messages = [
                "cache miss",
                "slow query detected",
                "connection pool low",
                "disk io spike",
                "network latency detected",
            ]
            logs.append(LogEntry(
                timestamp=state.timestamp,
                service=random_svc,
                level=self.random.choice(log_levels),
                message=self.random.choice(messages),
                is_relevant=False
            ))
        
        return alerts, logs