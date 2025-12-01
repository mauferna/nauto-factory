"""
Session Manager - Implements Sessions & Memory
Handles session state, context management, and long-term memory
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, field, asdict
import os

logger = logging.getLogger(__name__)


@dataclass
class Session:
    """Represents a session with state and memory"""
    
    session_id: str
    created_at: datetime = field(default_factory=datetime.now)
    context: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, int] = field(default_factory=dict)
    history: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_context(self, key: str, value: Any):
        """Add context information to the session"""
        self.context[key] = value
        self.history.append({
            "timestamp": datetime.now().isoformat(),
            "action": "context_added",
            "key": key
        })
    
    def get_context(self, key: str, default=None) -> Any:
        """Retrieve context information"""
        return self.context.get(key, default)
    
    def increment_metric(self, metric_name: str, amount: int = 1):
        """Increment a metric counter"""
        if metric_name not in self.metrics:
            self.metrics[metric_name] = 0
        self.metrics[metric_name] += amount
    
    def get_metric(self, metric_name: str, default: int = 0) -> int:
        """Get metric value"""
        return self.metrics.get(metric_name, default)
    
    def compact_context(self, keep_recent: int = 5):
        """
        Implement context compaction to manage token usage.
        Keeps only the most recent N context items.
        """
        if len(self.context) > keep_recent:
            # Sort by most recently added (tracked in history)
            recent_keys = []
            for entry in reversed(self.history):
                if entry.get("action") == "context_added":
                    key = entry.get("key")
                    if key not in recent_keys:
                        recent_keys.append(key)
                    if len(recent_keys) >= keep_recent:
                        break
            
            # Keep only recent context
            compacted_context = {
                k: v for k, v in self.context.items()
                if k in recent_keys
            }
            
            # Store compacted items in summary
            removed_items = {
                k: type(v).__name__
                for k, v in self.context.items()
                if k not in recent_keys
            }
            
            self.context = compacted_context
            self.metadata["compacted_items"] = removed_items
            
            logger.info(f"Context compacted: kept {len(recent_keys)} recent items")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary for serialization"""
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat()
        return data


class SessionManager:
    """
    Manages sessions and implements long-term memory.
    
    Features:
    - In-memory session storage
    - Persistent session history (Memory Bank)
    - Session retrieval and analysis
    - Context engineering utilities
    """
    
    def __init__(self, memory_dir: str = "./memory"):
        """Initialize session manager with memory storage"""
        self.sessions: Dict[str, Session] = {}
        self.memory_dir = memory_dir
        os.makedirs(memory_dir, exist_ok=True)
        
        # Memory bank file
        self.memory_bank_path = os.path.join(memory_dir, "memory_bank.json")
        self.memory_bank = self._load_memory_bank()
        
        logger.info(f"Session manager initialized with {len(self.memory_bank)} stored sessions")
    
    def create_session(self, session_id: str, metadata: Dict[str, Any] = None) -> Session:
        """Create a new session"""
        
        session = Session(
            session_id=session_id,
            metadata=metadata or {}
        )
        
        self.sessions[session_id] = session
        logger.info(f"Session created: {session_id}")
        
        return session
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """Retrieve an active session"""
        return self.sessions.get(session_id)
    
    def store_session(self, session: Session):
        """
        Store session to long-term memory (Memory Bank).
        This enables learning from past automations.
        """
        
        # Add to memory bank
        self.memory_bank[session.session_id] = session.to_dict()
        
        # Persist to disk
        self._save_memory_bank()
        
        logger.info(f"Session stored to memory bank: {session.session_id}")
    
    def retrieve_similar_sessions(
        self,
        spec_description: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Retrieve similar past sessions for learning.
        This is a simple keyword-based similarity for now.
        """
        
        similar_sessions = []
        keywords = set(spec_description.lower().split())
        
        for session_id, session_data in self.memory_bank.items():
            # Get spec description from context
            context = session_data.get("context", {})
            parsed_spec = context.get("parsed_spec", {})
            past_description = parsed_spec.get("description", "").lower()
            
            # Calculate simple keyword overlap
            past_keywords = set(past_description.split())
            overlap = len(keywords & past_keywords)
            
            if overlap > 0:
                similar_sessions.append({
                    "session_id": session_id,
                    "similarity": overlap,
                    "data": session_data
                })
        
        # Sort by similarity and return top N
        similar_sessions.sort(key=lambda x: x["similarity"], reverse=True)
        return similar_sessions[:limit]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get overall statistics from memory bank"""
        
        total_sessions = len(self.memory_bank)
        
        if total_sessions == 0:
            return {
                "total_sessions": 0,
                "avg_execution_time": 0,
                "success_rate": 0
            }
        
        execution_times = []
        successes = 0
        
        for session_data in self.memory_bank.values():
            metrics = session_data.get("metrics", {})
            
            # Track execution times (if available in metadata)
            metadata = session_data.get("metadata", {})
            if "execution_time" in metadata:
                execution_times.append(metadata["execution_time"])
            
            # Track successes
            if metadata.get("success", False):
                successes += 1
        
        return {
            "total_sessions": total_sessions,
            "avg_execution_time": sum(execution_times) / len(execution_times) if execution_times else 0,
            "success_rate": (successes / total_sessions * 100) if total_sessions > 0 else 0,
            "total_agent_calls": sum(
                s.get("metrics", {}).get("agent_calls", 0)
                for s in self.memory_bank.values()
            )
        }
    
    def _load_memory_bank(self) -> Dict[str, Any]:
        """Load memory bank from disk"""
        
        if os.path.exists(self.memory_bank_path):
            try:
                with open(self.memory_bank_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load memory bank: {str(e)}")
                return {}
        
        return {}
    
    def _save_memory_bank(self):
        """Persist memory bank to disk"""
        
        try:
            with open(self.memory_bank_path, 'w') as f:
                json.dump(self.memory_bank, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save memory bank: {str(e)}")
    
    def clear_memory_bank(self):
        """Clear all stored sessions (use with caution)"""
        self.memory_bank = {}
        self._save_memory_bank()
        logger.warning("Memory bank cleared")
