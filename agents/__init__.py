"""
Remaining Specialized Agents:
- Test Generator Agent
- CI/CD Agent  
- Documentation Agent
"""

import os
import logging
from typing import Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class TestGeneratorAgent:
    """Generate comprehensive tests for Ansible playbooks"""
    
    def __init__(self, model):
        self.model = model
        self.output_dir = "./output/tests"
        os.makedirs(self.output_dir, exist_ok=True)
    
    async def generate_tests(
        self,
        playbook_path: str,
        parsed_spec: Dict[str, Any],
        session: Any
    ) -> Dict[str, Any]:
        """Generate molecule tests and unit tests"""
        
        logger.info(f"Generating tests for: {playbook_path}")
        session.increment_metric("agent_calls")
        
        # Read playbook
        with open(playbook_path, 'r') as f:
            playbook_content = f.read()
        
        # Generate test scenarios
        test_content = await self._generate_test_scenarios(
            playbook_content,
            parsed_spec,
            session
        )
        
        # Create test directory structure
        playbook_name = os.path.basename(playbook_path).replace(".yml", "")
        test_dir = os.path.join(self.output_dir, playbook_name)
        os.makedirs(test_dir, exist_ok=True)
        
        # Write molecule scenario
        molecule_dir = os.path.join(test_dir, "molecule", "default")
        os.makedirs(molecule_dir, exist_ok=True)
        
        # Create molecule.yml
        molecule_config = f"""---
driver:
  name: docker
platforms:
  - name: instance
    image: geerlingguy/docker-ubuntu2004-ansible
    pre_build_image: true
provisioner:
  name: ansible
  playbooks:
    converge: ../../../../{playbook_path}
verifier:
  name: ansible
"""
        
        with open(os.path.join(molecule_dir, "molecule.yml"), 'w') as f:
            f.write(molecule_config)
        
        # Create verify.yml
        with open(os.path.join(molecule_dir, "verify.yml"), 'w') as f:
            f.write(test_content)
        
        # Create pytest test file
        pytest_content = f"""
import pytest
import yaml
import subprocess

def test_playbook_syntax():
    \"\"\"Test playbook has valid syntax\"\"\"
    result = subprocess.run(
        ["ansible-playbook", "--syntax-check", "{playbook_path}"],
        capture_output=True
    )
    assert result.returncode == 0

def test_playbook_structure():
    \"\"\"Test playbook has required structure\"\"\"
    with open("{playbook_path}", 'r') as f:
        playbook = yaml.safe_load(f)
    
    assert isinstance(playbook, list)
    assert len(playbook) > 0
    assert 'name' in playbook[0]
    assert 'tasks' in playbook[0]
"""
        
        with open(os.path.join(test_dir, "test_playbook.py"), 'w') as f:
            f.write(pytest_content)
        
        logger.info(f"Tests generated in: {test_dir}")
        session.increment_metric("artifacts")
        
        return {
            "success": True,
            "test_dir": test_dir,
            "molecule_dir": molecule_dir,
            "test_count": 3
        }
    
    async def _generate_test_scenarios(
        self,
        playbook_content: str,
        parsed_spec: Dict[str, Any],
        session: Any
    ) -> str:
        """Use AI to generate test scenarios"""
        
        prompt = f"""
Generate Ansible verification tasks for testing this playbook:

{playbook_content}

Create a verify.yml file with tasks that:
1. Verify expected changes were made
2. Check service states
3. Validate configuration files
4. Test connectivity
5. Verify idempotency

Output ONLY the YAML content for verify.yml
"""
        
        try:
            response = await self.model.generate_content_async(prompt)
            session.increment_metric("tokens_used", len(prompt.split()))
            
            content = response.text.strip()
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1])
            
            return content if content.startswith("---") else "---\n" + content
            
        except Exception as e:
            logger.warning(f"AI test generation failed: {str(e)}")
            return """---
- name: Verify playbook execution
  hosts: all
  tasks:
    - name: Check connectivity
      ping:
"""


class CICDAgent:
    """Generate CI/CD pipeline configurations"""
    
    def __init__(self, model):
        self.model = model
        self.output_dir = "./output/cicd"
        os.makedirs(self.output_dir, exist_ok=True)
    
    async def generate_pipeline(
        self,
        parsed_spec: Dict[str, Any],
        artifacts: Dict[str, str],
        session: Any
    ) -> Dict[str, Any]:
        """Generate CI/CD pipeline configuration"""
        
        logger.info("Generating CI/CD pipeline...")
        session.increment_metric("agent_calls")
        
        cicd_config = parsed_spec.get('cicd', {})
        platform = cicd_config.get('platform', 'github_actions')
        
        if platform == 'github_actions':
            pipeline_content = self._generate_github_actions(
                parsed_spec,
                artifacts
            )
            pipeline_file = "ansible-ci.yml"
            pipeline_dir = os.path.join(self.output_dir, ".github", "workflows")
        elif platform == 'gitlab_ci':
            pipeline_content = self._generate_gitlab_ci(parsed_spec, artifacts)
            pipeline_file = ".gitlab-ci.yml"
            pipeline_dir = self.output_dir
        else:
            pipeline_content = self._generate_jenkins(parsed_spec, artifacts)
            pipeline_file = "Jenkinsfile"
            pipeline_dir = self.output_dir
        
        os.makedirs(pipeline_dir, exist_ok=True)
        pipeline_path = os.path.join(pipeline_dir, pipeline_file)
        
        with open(pipeline_path, 'w') as f:
            f.write(pipeline_content)
        
        logger.info(f"CI/CD pipeline generated: {pipeline_path}")
        session.increment_metric("artifacts")
        
        return {
            "success": True,
            "pipeline_path": pipeline_path,
            "platform": platform
        }
    
    def _generate_github_actions(
        self,
        parsed_spec: Dict[str, Any],
        artifacts: Dict[str, str]
    ) -> str:
        """Generate GitHub Actions workflow"""
        
        return f"""name: Ansible CI/CD

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          pip install ansible ansible-lint yamllint
      
      - name: Run ansible-lint
        run: ansible-lint {artifacts.get('ansible_playbook', 'playbook.yml')}
      
      - name: Run yamllint
        run: yamllint {artifacts.get('ansible_playbook', 'playbook.yml')}
  
  test:
    needs: lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          pip install ansible molecule molecule-docker pytest
      
      - name: Run molecule tests
        run: |
          cd {artifacts.get('tests', 'tests/')}
          molecule test
      
      - name: Run pytest
        run: pytest {artifacts.get('tests', 'tests/')}
  
  deploy:
    needs: test
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Run Ansible Playbook
        run: |
          ansible-playbook {artifacts.get('ansible_playbook', 'playbook.yml')} --check
"""
    
    def _generate_gitlab_ci(
        self,
        parsed_spec: Dict[str, Any],
        artifacts: Dict[str, str]
    ) -> str:
        """Generate GitLab CI configuration"""
        
        return f"""stages:
  - lint
  - test
  - deploy

variables:
  PIP_CACHE_DIR: "$CI_PROJECT_DIR/.cache/pip"

cache:
  paths:
    - .cache/pip

lint:
  stage: lint
  image: python:3.10
  script:
    - pip install ansible ansible-lint yamllint
    - ansible-lint {artifacts.get('ansible_playbook', 'playbook.yml')}
    - yamllint {artifacts.get('ansible_playbook', 'playbook.yml')}

test:
  stage: test
  image: python:3.10
  services:
    - docker:dind
  script:
    - pip install ansible molecule molecule-docker pytest
    - cd {artifacts.get('tests', 'tests/')}
    - molecule test

deploy:
  stage: deploy
  image: python:3.10
  script:
    - ansible-playbook {artifacts.get('ansible_playbook', 'playbook.yml')} --check
  only:
    - main
"""
    
    def _generate_jenkins(
        self,
        parsed_spec: Dict[str, Any],
        artifacts: Dict[str, str]
    ) -> str:
        """Generate Jenkinsfile"""
        
        return f"""pipeline {{
    agent any
    
    stages {{
        stage('Lint') {{
            steps {{
                sh 'pip install ansible ansible-lint yamllint'
                sh 'ansible-lint {artifacts.get("ansible_playbook", "playbook.yml")}'
                sh 'yamllint {artifacts.get("ansible_playbook", "playbook.yml")}'
            }}
        }}
        
        stage('Test') {{
            steps {{
                sh 'pip install molecule molecule-docker pytest'
                sh 'cd {artifacts.get("tests", "tests/")} && molecule test'
                sh 'pytest {artifacts.get("tests", "tests/")}'
            }}
        }}
        
        stage('Deploy') {{
            when {{
                branch 'main'
            }}
            steps {{
                sh 'ansible-playbook {artifacts.get("ansible_playbook", "playbook.yml")} --check'
            }}
        }}
    }}
}}
"""


class DocumentationAgent:
    """Generate comprehensive documentation"""
    
    def __init__(self, model):
        self.model = model
        self.output_dir = "./output/docs"
        os.makedirs(self.output_dir, exist_ok=True)
    
    async def generate_documentation(
        self,
        parsed_spec: Dict[str, Any],
        session: Any
    ) -> Dict[str, Any]:
        """Generate README and usage documentation"""
        
        logger.info("Generating documentation...")
        session.increment_metric("agent_calls")
        
        # Use AI to generate comprehensive docs
        doc_content = await self._generate_readme(parsed_spec, session)
        
        doc_path = os.path.join(
            self.output_dir,
            f"{parsed_spec['name']}_README.md"
        )
        
        with open(doc_path, 'w') as f:
            f.write(doc_content)
        
        logger.info(f"Documentation generated: {doc_path}")
        session.increment_metric("artifacts")
        
        return {
            "success": True,
            "file_path": doc_path
        }
    
    async def _generate_readme(
        self,
        parsed_spec: Dict[str, Any],
        session: Any
    ) -> str:
        """Generate README content"""
        
        prompt = f"""
Generate comprehensive README documentation for this Ansible automation:

Name: {parsed_spec['name']}
Description: {parsed_spec['description']}
Target Devices: {len(parsed_spec.get('target_devices', []))} devices

Include:
1. Overview and purpose
2. Requirements
3. Installation instructions
4. Usage examples
5. Variables reference
6. Testing instructions
7. Troubleshooting
8. Contributing guidelines

Make it professional and well-structured in Markdown format.
"""
        
        try:
            response = await self.model.generate_content_async(prompt)
            session.increment_metric("tokens_used", len(prompt.split()))
            
            return response.text.strip()
            
        except Exception as e:
            logger.warning(f"AI documentation generation failed: {str(e)}")
            return self._generate_basic_readme(parsed_spec)
    
    def _generate_basic_readme(self, parsed_spec: Dict[str, Any]) -> str:
        """Fallback basic README"""
        
        return f"""# {parsed_spec['name']}

## Description

{parsed_spec['description']}

## Requirements

- Ansible >= 2.9
- Python >= 3.8
- Target devices: {len(parsed_spec.get('target_devices', []))}

## Usage

```bash
ansible-playbook -i inventory/hosts.yml {parsed_spec['name']}.yml
```

## Testing

```bash
# Run molecule tests
molecule test

# Run pytest
pytest tests/
```

## License

MIT
"""
