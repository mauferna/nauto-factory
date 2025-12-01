"""
Code Review Agent
Performs comprehensive code review of generated Ansible playbooks
"""

import os
import logging
import yaml
import subprocess
from typing import Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)


class CodeReviewAgent:
    """
    Agent responsible for reviewing Ansible playbook code quality.
    
    Checks for:
    - Ansible-lint compliance
    - Security vulnerabilities
    - Best practices
    - Performance issues
    - Syntax errors
    """
    
    def __init__(self, model):
        """Initialize with Gemini model"""
        self.model = model
        self.output_dir = "./output/reviews"
        os.makedirs(self.output_dir, exist_ok=True)
    
    async def review_code(
        self,
        playbook_path: str,
        parsed_spec: Dict[str, Any],
        session: Any
    ) -> Dict[str, Any]:
        """
        Perform comprehensive code review of the playbook.
        
        Returns:
            Dictionary with review results and report path
        """
        
        logger.info(f"Reviewing playbook: {playbook_path}")
        session.increment_metric("agent_calls")
        
        try:
            # Run multiple review checks
            lint_results = await self._run_ansible_lint(playbook_path)
            security_results = await self._security_scan(playbook_path, session)
            ai_review = await self._ai_code_review(playbook_path, session)
            
            # Aggregate results
            all_issues = []
            all_issues.extend(lint_results.get("issues", []))
            all_issues.extend(security_results.get("issues", []))
            all_issues.extend(ai_review.get("issues", []))
            
            # Calculate severity counts
            critical_issues = len([i for i in all_issues if i.get("severity") == "critical"])
            high_issues = len([i for i in all_issues if i.get("severity") == "high"])
            medium_issues = len([i for i in all_issues if i.get("severity") == "medium"])
            low_issues = len([i for i in all_issues if i.get("severity") == "low"])
            
            # Calculate quality score
            quality_score = self._calculate_quality_score(
                critical_issues,
                high_issues,
                medium_issues,
                low_issues
            )
            
            # Generate review report
            report_path = await self._generate_review_report(
                playbook_path,
                all_issues,
                quality_score,
                {
                    "lint": lint_results,
                    "security": security_results,
                    "ai_review": ai_review
                }
            )
            
            logger.info(f"Code review complete. Quality score: {quality_score}/5.0")
            session.increment_metric("artifacts")
            
            return {
                "success": True,
                "report_path": report_path,
                "quality_score": quality_score,
                "issues": all_issues,
                "critical_issues": critical_issues,
                "high_issues": high_issues,
                "medium_issues": medium_issues,
                "low_issues": low_issues,
                "total_issues": len(all_issues),
                "passed": critical_issues == 0 and high_issues == 0
            }
            
        except Exception as e:
            logger.error(f"Code review failed: {str(e)}", exc_info=True)
            raise
    
    async def _run_ansible_lint(self, playbook_path: str) -> Dict[str, Any]:
        """Run ansible-lint on the playbook"""
        
        logger.info("Running ansible-lint...")
        
        try:
            result = subprocess.run(
                ["ansible-lint", "--nocolor", playbook_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            issues = []
            
            # Parse lint output
            if result.returncode != 0:
                for line in result.stdout.split("\n"):
                    if line.strip() and not line.startswith("WARNING"):
                        issues.append({
                            "type": "lint",
                            "severity": "medium",
                            "message": line.strip(),
                            "line": None
                        })
            
            return {
                "passed": result.returncode == 0,
                "issues": issues,
                "output": result.stdout
            }
            
        except FileNotFoundError:
            logger.warning("ansible-lint not found, skipping")
            return {
                "passed": True,
                "issues": [],
                "output": "ansible-lint not available"
            }
        except Exception as e:
            logger.warning(f"ansible-lint failed: {str(e)}")
            return {
                "passed": False,
                "issues": [{
                    "type": "lint",
                    "severity": "low",
                    "message": f"Lint check failed: {str(e)}",
                    "line": None
                }],
                "output": str(e)
            }
    
    async def _security_scan(
        self,
        playbook_path: str,
        session: Any
    ) -> Dict[str, Any]:
        """Scan for security vulnerabilities"""
        
        logger.info("Running security scan...")
        
        issues = []
        
        try:
            with open(playbook_path, 'r') as f:
                content = f.read()
            
            # Check for common security issues
            security_checks = [
                {
                    "pattern": "password:",
                    "message": "Hardcoded password detected",
                    "severity": "critical"
                },
                {
                    "pattern": "secret:",
                    "message": "Hardcoded secret detected",
                    "severity": "critical"
                },
                {
                    "pattern": "api_key:",
                    "message": "Hardcoded API key detected",
                    "severity": "critical"
                },
                {
                    "pattern": "no_log: false",
                    "message": "Sensitive data may be logged",
                    "severity": "high"
                },
                {
                    "pattern": "become: true",
                    "message": "Privilege escalation used - ensure necessary",
                    "severity": "medium"
                },
                {
                    "pattern": "shell:",
                    "message": "Shell module used - prefer specific modules",
                    "severity": "medium"
                }
            ]
            
            for check in security_checks:
                if check["pattern"] in content.lower():
                    issues.append({
                        "type": "security",
                        "severity": check["severity"],
                        "message": check["message"],
                        "pattern": check["pattern"]
                    })
            
            return {
                "passed": len([i for i in issues if i["severity"] == "critical"]) == 0,
                "issues": issues
            }
            
        except Exception as e:
            logger.error(f"Security scan failed: {str(e)}")
            return {
                "passed": False,
                "issues": [{
                    "type": "security",
                    "severity": "low",
                    "message": f"Security scan failed: {str(e)}"
                }]
            }
    
    async def _ai_code_review(
        self,
        playbook_path: str,
        session: Any
    ) -> Dict[str, Any]:
        """Use AI to perform intelligent code review"""
        
        logger.info("Running AI code review...")
        
        try:
            with open(playbook_path, 'r') as f:
                playbook_content = f.read()
            
            prompt = f"""
You are an expert Ansible code reviewer. Review this playbook for:

1. Best practices compliance
2. Code quality and maintainability
3. Performance considerations
4. Error handling
5. Idempotency
6. Documentation quality

Playbook:
{playbook_content}

Provide your review in this format:
ISSUES:
- [SEVERITY: critical/high/medium/low] Issue description (line X if applicable)

RECOMMENDATIONS:
- Suggestion for improvement

SCORE: X/5.0 (overall quality score)

Be thorough but concise.
"""
            
            response = await self.model.generate_content_async(prompt)
            session.increment_metric("tokens_used", len(prompt.split()))
            
            # Parse AI response for issues
            issues = self._parse_ai_review_response(response.text)
            
            return {
                "passed": True,
                "issues": issues,
                "full_review": response.text
            }
            
        except Exception as e:
            logger.error(f"AI code review failed: {str(e)}")
            return {
                "passed": True,
                "issues": [],
                "full_review": f"AI review failed: {str(e)}"
            }
    
    def _parse_ai_review_response(self, review_text: str) -> List[Dict[str, Any]]:
        """Parse AI review response to extract issues"""
        
        issues = []
        
        if "ISSUES:" in review_text:
            issues_section = review_text.split("ISSUES:")[1].split("RECOMMENDATIONS:")[0]
            
            for line in issues_section.split("\n"):
                line = line.strip()
                if line.startswith("-") and "SEVERITY:" in line.upper():
                    # Extract severity
                    severity = "medium"  # default
                    for sev in ["critical", "high", "medium", "low"]:
                        if sev in line.lower():
                            severity = sev
                            break
                    
                    # Extract message
                    message = line.split("]", 1)[1].strip() if "]" in line else line[1:].strip()
                    
                    issues.append({
                        "type": "ai_review",
                        "severity": severity,
                        "message": message
                    })
        
        return issues
    
    def _calculate_quality_score(
        self,
        critical: int,
        high: int,
        medium: int,
        low: int
    ) -> float:
        """Calculate overall quality score out of 5.0"""
        
        # Start with perfect score
        score = 5.0
        
        # Deduct points based on severity
        score -= critical * 1.0
        score -= high * 0.5
        score -= medium * 0.25
        score -= low * 0.1
        
        # Ensure score is between 0 and 5
        return max(0.0, min(5.0, score))
    
    async def _generate_review_report(
        self,
        playbook_path: str,
        issues: List[Dict[str, Any]],
        quality_score: float,
        detailed_results: Dict[str, Any]
    ) -> str:
        """Generate comprehensive review report"""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        playbook_name = os.path.basename(playbook_path).replace(".yml", "")
        report_path = os.path.join(
            self.output_dir,
            f"{playbook_name}_review_{timestamp}.md"
        )
        
        # Build report content
        report = f"""# Code Review Report

**Playbook**: `{os.path.basename(playbook_path)}`  
**Review Date**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**Quality Score**: {quality_score:.2f}/5.0

## Summary

- **Total Issues**: {len(issues)}
- **Critical**: {len([i for i in issues if i.get("severity") == "critical"])}
- **High**: {len([i for i in issues if i.get("severity") == "high"])}
- **Medium**: {len([i for i in issues if i.get("severity") == "medium"])}
- **Low**: {len([i for i in issues if i.get("severity") == "low"])}

## Overall Assessment

"""
        
        if quality_score >= 4.5:
            report += "✅ **EXCELLENT** - Playbook meets all best practices\n\n"
        elif quality_score >= 3.5:
            report += "✓ **GOOD** - Playbook is production-ready with minor improvements suggested\n\n"
        elif quality_score >= 2.5:
            report += "⚠️ **NEEDS IMPROVEMENT** - Address issues before production use\n\n"
        else:
            report += "❌ **CRITICAL ISSUES** - Major refactoring required\n\n"
        
        # Issues by severity
        for severity in ["critical", "high", "medium", "low"]:
            severity_issues = [i for i in issues if i.get("severity") == severity]
            if severity_issues:
                report += f"## {severity.upper()} Issues\n\n"
                for issue in severity_issues:
                    report += f"- **[{issue.get('type', 'unknown')}]** {issue.get('message', 'No description')}\n"
                report += "\n"
        
        # Detailed results
        report += "## Detailed Analysis\n\n"
        
        if detailed_results.get("lint"):
            report += "### Ansible Lint\n"
            report += f"Status: {'✅ Passed' if detailed_results['lint']['passed'] else '❌ Failed'}\n\n"
        
        if detailed_results.get("security"):
            report += "### Security Scan\n"
            report += f"Status: {'✅ Passed' if detailed_results['security']['passed'] else '⚠️ Issues Found'}\n\n"
        
        if detailed_results.get("ai_review", {}).get("full_review"):
            report += "### AI Review\n\n"
            report += detailed_results['ai_review']['full_review']
            report += "\n\n"
        
        # Write report
        with open(report_path, 'w') as f:
            f.write(report)
        
        logger.info(f"Review report generated: {report_path}")
        
        return report_path
