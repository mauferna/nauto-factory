"""
Network Automation Factory - Main Orchestrator Agent
Coordinates multi-agent system for network automation artifact generation
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import json
import os

# Google AI imports
import google.generativeai as genai

# Local imports
from agents.spec_parser import SpecificationParserAgent
from agents.ansible_generator import AnsibleGeneratorAgent
from agents.code_reviewer import CodeReviewAgent
from agents.test_generator import TestGeneratorAgent
from agents.cicd_agent import CICDAgent
from agents.documentation_agent import DocumentationAgent
from memory.session_manager import SessionManager
from observability.logger import setup_logger
from observability.metrics import MetricsCollector

logger = setup_logger(__name__)


@dataclass
class AutomationRequest:
    """Represents a network automation request"""
    spec_file: str
    output_dir: str
    session_id: str
    metadata: Dict[str, Any]


@dataclass
class AutomationResult:
    """Results from the automation factory"""
    success: bool
    artifacts: Dict[str, str]
    metrics: Dict[str, Any]
    errors: List[str]
    execution_time: float


class OrchestratorAgent:
    """
    Main orchestrator agent that coordinates the multi-agent system.
    
    Implements:
    - Multi-agent coordination (sequential and parallel execution)
    - Session management
    - Context engineering
    - Observability
    """
    
    def __init__(self, api_key: str, output_base_dir: str = "./output"):
        """Initialize the orchestrator with all specialized agents"""
        
        # Configure Google AI
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        # Initialize session and memory management
        self.session_manager = SessionManager()
        
        # Initialize metrics collection
        self.metrics = MetricsCollector()
        
        # Output directory setup
        self.output_base_dir = output_base_dir
        os.makedirs(output_base_dir, exist_ok=True)
        
        # Initialize specialized agents
        logger.info("Initializing specialized agents...")
        self.spec_parser = SpecificationParserAgent(self.model)
        self.ansible_generator = AnsibleGeneratorAgent(self.model)
        self.code_reviewer = CodeReviewAgent(self.model)
        self.test_generator = TestGeneratorAgent(self.model)
        self.cicd_agent = CICDAgent(self.model)
        self.documentation_agent = DocumentationAgent(self.model)
        
        logger.info("Orchestrator initialized successfully")
    
    async def process_automation_request(
        self, 
        request: AutomationRequest
    ) -> AutomationResult:
        """
        Main workflow orchestration method.
        
        Implements multi-agent workflow:
        1. Parse specification (Sequential)
        2. Parallel execution: Generate documentation + Ansible playbook
        3. Sequential pipeline: Review → Test → CI/CD
        """
        
        start_time = datetime.now()
        artifacts = {}
        errors = []
        
        try:
            # Create session for this automation request
            session = self.session_manager.create_session(request.session_id)
            logger.info(f"Processing automation request: {request.session_id}")
            self.metrics.record_request_started(request.session_id)
            
            # PHASE 1: Parse and validate specification (Sequential)
            logger.info("Phase 1: Parsing specification...")
            spec_result = await self.spec_parser.parse_specification(
                request.spec_file,
                session
            )
            
            if not spec_result.get("valid", False):
                errors.append("Specification validation failed")
                return self._create_error_result(errors, start_time)
            
            parsed_spec = spec_result["parsed_spec"]
            session.add_context("parsed_spec", parsed_spec)
            
            # PHASE 2: Parallel execution for independent tasks
            logger.info("Phase 2: Parallel generation (Documentation + Ansible)...")
            doc_task = self.documentation_agent.generate_documentation(
                parsed_spec, 
                session
            )
            ansible_task = self.ansible_generator.generate_playbook(
                parsed_spec,
                session
            )
            
            # Execute in parallel
            doc_result, ansible_result = await asyncio.gather(
                doc_task,
                ansible_task,
                return_exceptions=True
            )
            
            # Handle parallel execution results
            if isinstance(doc_result, Exception):
                errors.append(f"Documentation generation failed: {str(doc_result)}")
            else:
                artifacts["documentation"] = doc_result["file_path"]
                session.add_context("documentation", doc_result)
            
            if isinstance(ansible_result, Exception):
                errors.append(f"Ansible generation failed: {str(ansible_result)}")
                return self._create_error_result(errors, start_time)
            else:
                artifacts["ansible_playbook"] = ansible_result["file_path"]
                artifacts["inventory"] = ansible_result.get("inventory_path", "")
                session.add_context("ansible_playbook", ansible_result)
            
            # PHASE 3: Sequential pipeline (Review → Test → CI/CD)
            logger.info("Phase 3: Sequential pipeline (Review → Test → CI/CD)...")
            
            # Step 3a: Code Review
            review_result = await self.code_reviewer.review_code(
                ansible_result["file_path"],
                parsed_spec,
                session
            )
            artifacts["code_review"] = review_result["report_path"]
            session.add_context("code_review", review_result)
            
            # Check if critical issues found
            if review_result.get("critical_issues", 0) > 0:
                logger.warning("Critical issues found in code review")
                
                # LOOP AGENT: Iterative refinement
                logger.info("Initiating iterative refinement loop...")
                refined_result = await self._refinement_loop(
                    ansible_result,
                    review_result,
                    parsed_spec,
                    session,
                    max_iterations=3
                )
                
                if refined_result:
                    artifacts["ansible_playbook"] = refined_result["file_path"]
                    session.add_context("refined_playbook", refined_result)
            
            # Step 3b: Test Generation
            test_result = await self.test_generator.generate_tests(
                artifacts["ansible_playbook"],
                parsed_spec,
                session
            )
            artifacts["tests"] = test_result["test_dir"]
            session.add_context("tests", test_result)
            
            # Step 3c: CI/CD Pipeline Generation
            cicd_result = await self.cicd_agent.generate_pipeline(
                parsed_spec,
                artifacts,
                session
            )
            artifacts["cicd_pipeline"] = cicd_result["pipeline_path"]
            session.add_context("cicd", cicd_result)
            
            # PHASE 4: Final validation and packaging
            logger.info("Phase 4: Final validation and packaging...")
            await self._validate_artifacts(artifacts, session)
            
            # Calculate metrics
            execution_time = (datetime.now() - start_time).total_seconds()
            self.metrics.record_request_completed(
                request.session_id,
                execution_time,
                len(artifacts)
            )
            
            # Store session for learning
            self.session_manager.store_session(session)
            
            logger.info(f"Automation request completed successfully in {execution_time:.2f}s")
            
            return AutomationResult(
                success=True,
                artifacts=artifacts,
                metrics=self._collect_metrics(session, execution_time),
                errors=errors,
                execution_time=execution_time
            )
            
        except Exception as e:
            logger.error(f"Automation request failed: {str(e)}", exc_info=True)
            errors.append(f"Orchestration error: {str(e)}")
            execution_time = (datetime.now() - start_time).total_seconds()
            self.metrics.record_request_failed(request.session_id, str(e))
            
            return self._create_error_result(errors, start_time)
    
    async def _refinement_loop(
        self,
        ansible_result: Dict[str, Any],
        review_result: Dict[str, Any],
        parsed_spec: Dict[str, Any],
        session: Any,
        max_iterations: int = 3
    ) -> Optional[Dict[str, Any]]:
        """
        Implements iterative refinement loop for quality improvement.
        
        This is a LOOP AGENT implementation.
        """
        
        iteration = 0
        current_playbook = ansible_result
        
        while iteration < max_iterations:
            iteration += 1
            logger.info(f"Refinement iteration {iteration}/{max_iterations}")
            
            # Generate refinement instructions from review
            refinement_prompt = self._create_refinement_prompt(
                review_result,
                iteration
            )
            
            # Re-generate with improvements
            refined_result = await self.ansible_generator.refine_playbook(
                current_playbook["file_path"],
                refinement_prompt,
                parsed_spec,
                session
            )
            
            # Re-review
            new_review = await self.code_reviewer.review_code(
                refined_result["file_path"],
                parsed_spec,
                session
            )
            
            # Check if improvement achieved
            if new_review.get("critical_issues", 0) == 0:
                logger.info(f"Refinement successful after {iteration} iteration(s)")
                return refined_result
            
            # Update for next iteration
            current_playbook = refined_result
            review_result = new_review
            
            # Context compaction to manage token usage
            session.compact_context(keep_recent=3)
        
        logger.warning(f"Refinement loop completed without resolving all issues")
        return current_playbook
    
    def _create_refinement_prompt(
        self,
        review_result: Dict[str, Any],
        iteration: int
    ) -> str:
        """Create a targeted refinement prompt based on review findings"""
        
        issues = review_result.get("issues", [])
        critical_issues = [i for i in issues if i.get("severity") == "critical"]
        
        prompt = f"""
Refinement Iteration {iteration}:

Critical Issues to Address:
{json.dumps(critical_issues, indent=2)}

Please refine the Ansible playbook to:
1. Fix all critical security and syntax issues
2. Implement best practices for the identified problems
3. Maintain functionality while improving code quality
4. Add appropriate error handling

Focus on making minimal, targeted changes to resolve the issues.
"""
        return prompt
    
    async def _validate_artifacts(
        self,
        artifacts: Dict[str, str],
        session: Any
    ) -> bool:
        """Validate all generated artifacts"""
        
        logger.info("Validating generated artifacts...")
        
        # Check all expected artifacts exist
        required_artifacts = [
            "ansible_playbook",
            "code_review",
            "tests",
            "cicd_pipeline"
        ]
        
        for artifact_type in required_artifacts:
            if artifact_type not in artifacts:
                logger.warning(f"Missing artifact: {artifact_type}")
                return False
            
            # Verify file exists
            path = artifacts[artifact_type]
            if not os.path.exists(path):
                logger.error(f"Artifact file not found: {path}")
                return False
        
        logger.info("All artifacts validated successfully")
        return True
    
    def _collect_metrics(
        self,
        session: Any,
        execution_time: float
    ) -> Dict[str, Any]:
        """Collect comprehensive metrics from the session"""
        
        return {
            "execution_time_seconds": execution_time,
            "total_agent_calls": session.get_metric("agent_calls", 0),
            "tokens_used": session.get_metric("tokens_used", 0),
            "refinement_iterations": session.get_metric("refinements", 0),
            "artifacts_generated": session.get_metric("artifacts", 0),
            "timestamp": datetime.now().isoformat()
        }
    
    def _create_error_result(
        self,
        errors: List[str],
        start_time: datetime
    ) -> AutomationResult:
        """Create an error result object"""
        
        execution_time = (datetime.now() - start_time).total_seconds()
        
        return AutomationResult(
            success=False,
            artifacts={},
            metrics={"execution_time_seconds": execution_time},
            errors=errors,
            execution_time=execution_time
        )


async def main():
    """Main entry point for testing the orchestrator"""
    
    # Get API key from environment
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY environment variable not set")
    
    # Create orchestrator
    orchestrator = OrchestratorAgent(api_key)
    
    # Create test request
    request = AutomationRequest(
        spec_file="examples/example_spec.yaml",
        output_dir="./output/test_run",
        session_id=f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        metadata={"user": "test_user", "environment": "development"}
    )
    
    # Process request
    result = await orchestrator.process_automation_request(request)
    
    # Print results
    print("\n" + "="*80)
    print("AUTOMATION FACTORY RESULTS")
    print("="*80)
    print(f"\nSuccess: {result.success}")
    print(f"Execution Time: {result.execution_time:.2f}s")
    print(f"\nGenerated Artifacts:")
    for artifact_type, path in result.artifacts.items():
        print(f"  - {artifact_type}: {path}")
    
    if result.errors:
        print(f"\nErrors:")
        for error in result.errors:
            print(f"  - {error}")
    
    print(f"\nMetrics:")
    for metric, value in result.metrics.items():
        print(f"  - {metric}: {value}")
    print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
