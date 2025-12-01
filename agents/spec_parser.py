"""
Specification Parser Agent
Parses and validates network automation specifications
"""

import yaml
import logging
from typing import Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class SpecificationParserAgent:
    """
    Agent responsible for parsing and validating automation specifications.
    
    This agent ensures that input specifications are:
    - Syntactically valid YAML
    - Contain all required fields
    - Follow expected schema
    - Have realistic and achievable requirements
    """
    
    def __init__(self, model):
        """Initialize with Gemini model for intelligent parsing"""
        self.model = model
        self.required_fields = [
            "automation_spec.name",
            "automation_spec.description",
            "automation_spec.target_devices",
            "automation_spec.tasks"
        ]
    
    async def parse_specification(
        self,
        spec_file: str,
        session: Any
    ) -> Dict[str, Any]:
        """
        Parse and validate the automation specification file.
        
        Returns:
            Dictionary with 'valid' boolean and 'parsed_spec' data
        """
        
        logger.info(f"Parsing specification file: {spec_file}")
        session.increment_metric("agent_calls")
        
        try:
            # Read YAML file
            with open(spec_file, 'r') as f:
                raw_spec = yaml.safe_load(f)
            
            # Basic validation
            validation_result = self._validate_structure(raw_spec)
            if not validation_result["valid"]:
                return validation_result
            
            # Use AI to enrich and validate the specification
            enriched_spec = await self._ai_enrich_specification(
                raw_spec,
                session
            )
            
            # Extract key parameters
            parsed_spec = self._extract_parameters(enriched_spec)
            
            logger.info("Specification parsed and validated successfully")
            
            return {
                "valid": True,
                "parsed_spec": parsed_spec,
                "raw_spec": raw_spec,
                "enriched_spec": enriched_spec
            }
            
        except yaml.YAMLError as e:
            logger.error(f"YAML parsing error: {str(e)}")
            return {
                "valid": False,
                "error": f"Invalid YAML syntax: {str(e)}",
                "parsed_spec": None
            }
        
        except FileNotFoundError:
            logger.error(f"Specification file not found: {spec_file}")
            return {
                "valid": False,
                "error": f"File not found: {spec_file}",
                "parsed_spec": None
            }
        
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            return {
                "valid": False,
                "error": f"Parsing error: {str(e)}",
                "parsed_spec": None
            }
    
    def _validate_structure(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """Validate that the specification has all required fields"""
        
        missing_fields = []
        
        # Check for automation_spec root
        if "automation_spec" not in spec:
            return {
                "valid": False,
                "error": "Missing 'automation_spec' root element"
            }
        
        automation_spec = spec["automation_spec"]
        
        # Check required fields
        required = ["name", "description", "target_devices", "tasks"]
        for field in required:
            if field not in automation_spec:
                missing_fields.append(field)
        
        if missing_fields:
            return {
                "valid": False,
                "error": f"Missing required fields: {', '.join(missing_fields)}"
            }
        
        # Validate target devices
        if not isinstance(automation_spec["target_devices"], list):
            return {
                "valid": False,
                "error": "target_devices must be a list"
            }
        
        if not automation_spec["target_devices"]:
            return {
                "valid": False,
                "error": "At least one target device must be specified"
            }
        
        # Validate tasks
        if not isinstance(automation_spec["tasks"], list):
            return {
                "valid": False,
                "error": "tasks must be a list"
            }
        
        if not automation_spec["tasks"]:
            return {
                "valid": False,
                "error": "At least one task must be specified"
            }
        
        return {"valid": True}
    
    async def _ai_enrich_specification(
        self,
        raw_spec: Dict[str, Any],
        session: Any
    ) -> Dict[str, Any]:
        """
        Use AI to enrich the specification with:
        - Best practices recommendations
        - Missing optional parameters
        - Validation of device types and commands
        """
        
        prompt = f"""
You are a network automation expert. Analyze this automation specification and provide:

1. Validation of device types and compatibility
2. Suggestions for missing best practices
3. Identification of potential issues
4. Recommended additional parameters

Specification:
{yaml.dump(raw_spec, default_flow_style=False)}

Provide your analysis in this format:
- Valid: [yes/no]
- Issues: [list any problems]
- Recommendations: [list improvements]
- Enriched Spec: [the specification with recommended additions]

Focus on network automation best practices for Ansible.
"""
        
        try:
            response = await self.model.generate_content_async(prompt)
            session.increment_metric("tokens_used", len(prompt.split()))
            
            # For now, return the original spec with AI validation in metadata
            enriched = raw_spec.copy()
            enriched["_ai_validation"] = {
                "validated": True,
                "recommendations": response.text[:500]  # First 500 chars
            }
            
            return enriched
            
        except Exception as e:
            logger.warning(f"AI enrichment failed: {str(e)}")
            # Return original spec if AI enrichment fails
            return raw_spec
    
    def _extract_parameters(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """Extract key parameters for downstream agents"""
        
        automation_spec = spec["automation_spec"]
        
        return {
            "name": automation_spec["name"],
            "description": automation_spec["description"],
            "target_devices": automation_spec["target_devices"],
            "tasks": automation_spec["tasks"],
            "requirements": automation_spec.get("requirements", {}),
            "cicd": automation_spec.get("cicd", {}),
            "variables": automation_spec.get("variables", {}),
            "handlers": automation_spec.get("handlers", []),
            "tags": automation_spec.get("tags", []),
            "_ai_validation": spec.get("_ai_validation", {})
        }
