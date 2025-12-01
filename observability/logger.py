"""
Observability Module
Implements logging, tracing, and metrics collection
"""

import logging
import sys
from datetime import datetime
from typing import Dict, Any, List
import json
import os

# Setup logging configuration
def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Setup structured logging with comprehensive output.
    
    Implements:
    - Console and file logging
    - Structured log format
    - Different log levels per module
    """
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Prevent duplicate handlers
    if logger.handlers:
        return logger
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    
    # File handler
    os.makedirs("./logs", exist_ok=True)
    file_handler = logging.FileHandler(
        f"./logs/automation_factory_{datetime.now().strftime('%Y%m%d')}.log"
    )
    file_handler.setLevel(logging.DEBUG)
    
    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger


class MetricsCollector:
    """
    Collects and tracks performance metrics.
    
    Tracks:
    - Request counts
    - Execution times
    - Success/failure rates
    - Agent performance
    - Resource usage
    """
    
    def __init__(self, metrics_file: str = "./logs/metrics.json"):
        """Initialize metrics collector"""
        self.metrics_file = metrics_file
        self.metrics: Dict[str, List[Dict[str, Any]]] = {
            "requests": [],
            "agent_calls": [],
            "errors": []
        }
        
        # Load existing metrics
        self._load_metrics()
        
        logger = logging.getLogger(__name__)
        logger.info(f"Metrics collector initialized")
    
    def record_request_started(self, session_id: str):
        """Record when a request starts"""
        self.metrics["requests"].append({
            "session_id": session_id,
            "status": "started",
            "timestamp": datetime.now().isoformat()
        })
        self._save_metrics()
    
    def record_request_completed(
        self,
        session_id: str,
        execution_time: float,
        artifacts_count: int
    ):
        """Record successful request completion"""
        
        # Find and update the request
        for request in self.metrics["requests"]:
            if request["session_id"] == session_id and request["status"] == "started":
                request["status"] = "completed"
                request["execution_time"] = execution_time
                request["artifacts_count"] = artifacts_count
                request["completed_at"] = datetime.now().isoformat()
                break
        
        self._save_metrics()
    
    def record_request_failed(self, session_id: str, error: str):
        """Record failed request"""
        
        # Find and update the request
        for request in self.metrics["requests"]:
            if request["session_id"] == session_id and request["status"] == "started":
                request["status"] = "failed"
                request["error"] = error
                request["failed_at"] = datetime.now().isoformat()
                break
        
        # Record error
        self.metrics["errors"].append({
            "session_id": session_id,
            "error": error,
            "timestamp": datetime.now().isoformat()
        })
        
        self._save_metrics()
    
    def record_agent_call(
        self,
        agent_name: str,
        session_id: str,
        duration: float,
        success: bool
    ):
        """Record individual agent call"""
        
        self.metrics["agent_calls"].append({
            "agent": agent_name,
            "session_id": session_id,
            "duration": duration,
            "success": success,
            "timestamp": datetime.now().isoformat()
        })
        
        self._save_metrics()
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics"""
        
        total_requests = len(self.metrics["requests"])
        completed_requests = len([
            r for r in self.metrics["requests"]
            if r["status"] == "completed"
        ])
        failed_requests = len([
            r for r in self.metrics["requests"]
            if r["status"] == "failed"
        ])
        
        # Calculate average execution time
        execution_times = [
            r["execution_time"]
            for r in self.metrics["requests"]
            if r["status"] == "completed" and "execution_time" in r
        ]
        avg_execution_time = (
            sum(execution_times) / len(execution_times)
            if execution_times else 0
        )
        
        # Agent statistics
        agent_stats = {}
        for call in self.metrics["agent_calls"]:
            agent = call["agent"]
            if agent not in agent_stats:
                agent_stats[agent] = {
                    "total_calls": 0,
                    "successful_calls": 0,
                    "total_duration": 0
                }
            
            agent_stats[agent]["total_calls"] += 1
            if call["success"]:
                agent_stats[agent]["successful_calls"] += 1
            agent_stats[agent]["total_duration"] += call["duration"]
        
        # Calculate averages
        for agent, stats in agent_stats.items():
            stats["avg_duration"] = (
                stats["total_duration"] / stats["total_calls"]
                if stats["total_calls"] > 0 else 0
            )
            stats["success_rate"] = (
                stats["successful_calls"] / stats["total_calls"] * 100
                if stats["total_calls"] > 0 else 0
            )
        
        return {
            "total_requests": total_requests,
            "completed_requests": completed_requests,
            "failed_requests": failed_requests,
            "success_rate": (
                completed_requests / total_requests * 100
                if total_requests > 0 else 0
            ),
            "avg_execution_time": avg_execution_time,
            "total_errors": len(self.metrics["errors"]),
            "agent_statistics": agent_stats
        }
    
    def _load_metrics(self):
        """Load metrics from file"""
        if os.path.exists(self.metrics_file):
            try:
                with open(self.metrics_file, 'r') as f:
                    self.metrics = json.load(f)
            except Exception as e:
                logging.warning(f"Failed to load metrics: {str(e)}")
    
    def _save_metrics(self):
        """Save metrics to file"""
        try:
            os.makedirs(os.path.dirname(self.metrics_file), exist_ok=True)
            with open(self.metrics_file, 'w') as f:
                json.dump(self.metrics, f, indent=2)
        except Exception as e:
            logging.error(f"Failed to save metrics: {str(e)}")


class Tracer:
    """
    Simple distributed tracing for agent workflows.
    
    Tracks:
    - Agent execution flow
    - Call hierarchy
    - Timing information
    """
    
    def __init__(self):
        self.traces: Dict[str, List[Dict[str, Any]]] = {}
    
    def start_trace(self, session_id: str, operation: str):
        """Start a new trace"""
        if session_id not in self.traces:
            self.traces[session_id] = []
        
        self.traces[session_id].append({
            "operation": operation,
            "start_time": datetime.now().isoformat(),
            "status": "running"
        })
    
    def end_trace(self, session_id: str, operation: str, success: bool = True):
        """End a trace"""
        if session_id in self.traces:
            for trace in reversed(self.traces[session_id]):
                if (trace["operation"] == operation and 
                    trace["status"] == "running"):
                    trace["end_time"] = datetime.now().isoformat()
                    trace["status"] = "completed" if success else "failed"
                    break
    
    def get_trace(self, session_id: str) -> List[Dict[str, Any]]:
        """Get trace for a session"""
        return self.traces.get(session_id, [])
