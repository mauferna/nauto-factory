"""
Test Suite for Network Automation Factory
Tests all agents and core functionality
"""

import pytest
import asyncio
import os
import yaml
from pathlib import Path

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.spec_parser import SpecificationParserAgent
from agents.ansible_generator import AnsibleGeneratorAgent
from agents.code_reviewer import CodeReviewAgent
from memory.session_manager import SessionManager, Session
from observability.logger import MetricsCollector


class TestSpecificationParser:
    """Test the specification parser agent"""
    
    @pytest.fixture
    def parser(self):
        """Create parser instance"""
        # Mock model for testing
        class MockModel:
            async def generate_content_async(self, prompt):
                class Response:
                    text = "Valid: yes\nIssues: none\nRecommendations: none"
                return Response()
        
        return SpecificationParserAgent(MockModel())
    
    @pytest.fixture
    def valid_spec_file(self, tmp_path):
        """Create a valid specification file"""
        spec = {
            "automation_spec": {
                "name": "test_automation",
                "description": "Test automation",
                "target_devices": [
                    {"type": "cisco_ios", "count": 1}
                ],
                "tasks": [
                    {"name": "test_task", "action": "ios_facts"}
                ]
            }
        }
        
        spec_file = tmp_path / "test_spec.yaml"
        with open(spec_file, 'w') as f:
            yaml.dump(spec, f)
        
        return str(spec_file)
    
    @pytest.mark.asyncio
    async def test_parse_valid_specification(self, parser, valid_spec_file):
        """Test parsing a valid specification"""
        session = Session(session_id="test_session")
        result = await parser.parse_specification(valid_spec_file, session)
        
        assert result["valid"] is True
        assert "parsed_spec" in result
        assert result["parsed_spec"]["name"] == "test_automation"
    
    @pytest.mark.asyncio
    async def test_parse_missing_file(self, parser):
        """Test parsing a non-existent file"""
        session = Session(session_id="test_session")
        result = await parser.parse_specification("nonexistent.yaml", session)
        
        assert result["valid"] is False
        assert "error" in result
    
    def test_validate_structure_missing_fields(self, parser):
        """Test validation with missing fields"""
        spec = {"automation_spec": {"name": "test"}}
        result = parser._validate_structure(spec)
        
        assert result["valid"] is False
        assert "missing required fields" in result["error"].lower()


class TestSessionManager:
    """Test session management and memory"""
    
    @pytest.fixture
    def session_manager(self, tmp_path):
        """Create session manager with temp directory"""
        return SessionManager(memory_dir=str(tmp_path))
    
    def test_create_session(self, session_manager):
        """Test session creation"""
        session = session_manager.create_session("test_session_1")
        
        assert session.session_id == "test_session_1"
        assert session.session_id in session_manager.sessions
    
    def test_session_context_management(self, session_manager):
        """Test adding and retrieving context"""
        session = session_manager.create_session("test_session_2")
        
        session.add_context("key1", "value1")
        session.add_context("key2", {"nested": "data"})
        
        assert session.get_context("key1") == "value1"
        assert session.get_context("key2") == {"nested": "data"}
        assert session.get_context("missing", "default") == "default"
    
    def test_session_metrics(self, session_manager):
        """Test metric tracking"""
        session = session_manager.create_session("test_session_3")
        
        session.increment_metric("agent_calls")
        session.increment_metric("agent_calls")
        session.increment_metric("tokens_used", 100)
        
        assert session.get_metric("agent_calls") == 2
        assert session.get_metric("tokens_used") == 100
        assert session.get_metric("missing") == 0
    
    def test_context_compaction(self, session_manager):
        """Test context compaction"""
        session = session_manager.create_session("test_session_4")
        
        # Add many context items
        for i in range(10):
            session.add_context(f"key_{i}", f"value_{i}")
        
        # Compact to keep only 3 recent
        session.compact_context(keep_recent=3)
        
        # Should only have 3 items left
        assert len(session.context) == 3
        assert "compacted_items" in session.metadata
    
    def test_memory_bank_persistence(self, session_manager):
        """Test memory bank storage and retrieval"""
        session = session_manager.create_session("test_session_5")
        session.add_context("test", "data")
        session.increment_metric("agent_calls", 5)
        
        # Store to memory bank
        session_manager.store_session(session)
        
        # Should be in memory bank
        assert "test_session_5" in session_manager.memory_bank
        
        # Get statistics
        stats = session_manager.get_statistics()
        assert stats["total_sessions"] >= 1


class TestMetricsCollector:
    """Test metrics collection"""
    
    @pytest.fixture
    def metrics(self, tmp_path):
        """Create metrics collector with temp file"""
        metrics_file = tmp_path / "test_metrics.json"
        return MetricsCollector(metrics_file=str(metrics_file))
    
    def test_record_request_lifecycle(self, metrics):
        """Test complete request lifecycle"""
        session_id = "test_request_1"
        
        # Start request
        metrics.record_request_started(session_id)
        
        # Complete request
        metrics.record_request_completed(session_id, 10.5, 5)
        
        # Check summary
        summary = metrics.get_summary()
        assert summary["total_requests"] == 1
        assert summary["completed_requests"] == 1
        assert summary["success_rate"] == 100.0
    
    def test_record_failed_request(self, metrics):
        """Test failed request recording"""
        session_id = "test_request_2"
        
        metrics.record_request_started(session_id)
        metrics.record_request_failed(session_id, "Test error")
        
        summary = metrics.get_summary()
        assert summary["failed_requests"] == 1
        assert summary["total_errors"] == 1
    
    def test_agent_call_tracking(self, metrics):
        """Test agent call metrics"""
        metrics.record_agent_call("test_agent", "session_1", 1.5, True)
        metrics.record_agent_call("test_agent", "session_1", 2.0, True)
        metrics.record_agent_call("test_agent", "session_1", 1.0, False)
        
        summary = metrics.get_summary()
        agent_stats = summary["agent_statistics"]["test_agent"]
        
        assert agent_stats["total_calls"] == 3
        assert agent_stats["successful_calls"] == 2
        assert agent_stats["success_rate"] == pytest.approx(66.67, 0.1)


class TestAnsibleGenerator:
    """Test Ansible playbook generation"""
    
    @pytest.fixture
    def generator(self, tmp_path):
        """Create generator instance"""
        class MockModel:
            async def generate_content_async(self, prompt):
                class Response:
                    text = """---
- name: Test Playbook
  hosts: all
  tasks:
    - name: Test task
      ping:
"""
                return Response()
        
        gen = AnsibleGeneratorAgent(MockModel())
        gen.output_dir = str(tmp_path / "playbooks")
        return gen
    
    @pytest.mark.asyncio
    async def test_generate_playbook(self, generator):
        """Test playbook generation"""
        session = Session(session_id="test_session")
        parsed_spec = {
            "name": "test_playbook",
            "description": "Test",
            "target_devices": [{"type": "cisco_ios", "count": 1}],
            "tasks": [{"name": "test", "action": "ping"}]
        }
        
        result = await generator.generate_playbook(parsed_spec, session)
        
        assert result["success"] is True
        assert "file_path" in result
        assert os.path.exists(result["file_path"])
        
        # Verify playbook content
        with open(result["file_path"], 'r') as f:
            content = f.read()
            assert "name:" in content
            assert "hosts:" in content
    
    def test_generate_inventory(self, generator):
        """Test inventory generation"""
        parsed_spec = {
            "target_devices": [
                {"type": "cisco_ios", "count": 2, "connection": "network_cli"}
            ]
        }
        
        inventory = generator._generate_inventory(parsed_spec)
        
        assert "cisco_ios" in inventory
        assert "ansible_network_os" in inventory


class TestCodeReviewer:
    """Test code review functionality"""
    
    @pytest.fixture
    def reviewer(self):
        """Create reviewer instance"""
        class MockModel:
            async def generate_content_async(self, prompt):
                class Response:
                    text = """ISSUES:
- [SEVERITY: low] Minor formatting issue

RECOMMENDATIONS:
- Add more comments

SCORE: 4.5/5.0
"""
                return Response()
        
        return CodeReviewAgent(MockModel())
    
    @pytest.mark.asyncio
    async def test_security_scan(self, reviewer, tmp_path):
        """Test security scanning"""
        # Create a test playbook with security issue
        playbook = tmp_path / "test.yml"
        playbook.write_text("""---
- name: Test
  hosts: all
  vars:
    password: "hardcoded_password"
  tasks:
    - name: Test
      ping:
""")
        
        session = Session(session_id="test")
        result = await reviewer._security_scan(str(playbook), session)
        
        # Should detect hardcoded password
        assert len(result["issues"]) > 0
        assert any("password" in issue["message"].lower() 
                  for issue in result["issues"])
    
    def test_calculate_quality_score(self, reviewer):
        """Test quality score calculation"""
        # Perfect score
        score = reviewer._calculate_quality_score(0, 0, 0, 0)
        assert score == 5.0
        
        # With issues
        score = reviewer._calculate_quality_score(1, 2, 3, 4)
        assert score < 5.0
        assert score >= 0.0


# Integration Tests
class TestIntegration:
    """Integration tests for complete workflow"""
    
    @pytest.mark.asyncio
    async def test_session_workflow(self):
        """Test complete session workflow"""
        session_manager = SessionManager()
        session = session_manager.create_session("integration_test")
        
        # Simulate agent workflow
        session.add_context("step1", "parsed_spec")
        session.increment_metric("agent_calls")
        
        session.add_context("step2", "generated_playbook")
        session.increment_metric("agent_calls")
        
        session.add_context("step3", "review_complete")
        session.increment_metric("agent_calls")
        
        # Verify state
        assert len(session.context) == 3
        assert session.get_metric("agent_calls") == 3
        
        # Store session
        session_manager.store_session(session)
        assert "integration_test" in session_manager.memory_bank


# Run tests with pytest
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
