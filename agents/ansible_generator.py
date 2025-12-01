"""
Ansible Playbook Generator Agent
Generates production-ready Ansible playbooks from specifications
"""

import os
import logging
import yaml
from typing import Dict, Any
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class AnsibleGeneratorAgent:
    """
    Agent responsible for generating Ansible playbooks.
    
    Implements best practices:
    - Proper YAML structure
    - Role-based organization
    - Error handling
    - Idempotency
    - Security considerations
    """
    
    def __init__(self, model):
        """Initialize with Gemini model"""
        self.model = model
        self.output_dir = "./output/playbooks"
        os.makedirs(self.output_dir, exist_ok=True)
    
    async def generate_playbook(
        self,
        parsed_spec: Dict[str, Any],
        session: Any
    ) -> Dict[str, Any]:
        """
        Generate a complete Ansible playbook from the specification.
        
        Returns:
            Dictionary with file paths and metadata
        """
        
        logger.info(f"Generating Ansible playbook: {parsed_spec['name']}")
        session.increment_metric("agent_calls")
        
        try:
            # Use AI to generate the playbook content
            playbook_content = await self._generate_playbook_content(
                parsed_spec,
                session
            )
            
            # Generate inventory file
            inventory_content = self._generate_inventory(parsed_spec)
            
            # Generate ansible.cfg
            config_content = self._generate_ansible_cfg(parsed_spec)
            
            # Write files
            playbook_name = parsed_spec['name']
            playbook_path = os.path.join(
                self.output_dir,
                f"{playbook_name}.yml"
            )
            inventory_path = os.path.join(
                self.output_dir,
                "inventory",
                "hosts.yml"
            )
            config_path = os.path.join(
                self.output_dir,
                "ansible.cfg"
            )
            
            # Create inventory directory
            os.makedirs(os.path.dirname(inventory_path), exist_ok=True)
            
            # Write playbook
            with open(playbook_path, 'w') as f:
                f.write(playbook_content)
            
            # Write inventory
            with open(inventory_path, 'w') as f:
                f.write(inventory_content)
            
            # Write config
            with open(config_path, 'w') as f:
                f.write(config_content)
            
            logger.info(f"Playbook generated successfully: {playbook_path}")
            session.increment_metric("artifacts")
            
            return {
                "success": True,
                "file_path": playbook_path,
                "inventory_path": inventory_path,
                "config_path": config_path,
                "playbook_name": playbook_name,
                "metadata": {
                    "generated_at": datetime.now().isoformat(),
                    "tasks_count": len(parsed_spec.get('tasks', [])),
                    "target_devices": len(parsed_spec.get('target_devices', []))
                }
            }
            
        except Exception as e:
            logger.error(f"Playbook generation failed: {str(e)}", exc_info=True)
            raise
    
    async def _generate_playbook_content(
        self,
        parsed_spec: Dict[str, Any],
        session: Any
    ) -> str:
        """Use AI to generate the playbook content with best practices"""
        
        prompt = f"""
You are an expert Ansible developer. Generate a production-ready Ansible playbook based on this specification:

Name: {parsed_spec['name']}
Description: {parsed_spec['description']}

Target Devices:
{yaml.dump(parsed_spec['target_devices'], default_flow_style=False)}

Tasks:
{yaml.dump(parsed_spec['tasks'], default_flow_style=False)}

Requirements:
{yaml.dump(parsed_spec.get('requirements', {}), default_flow_style=False)}

Generate a complete, production-ready Ansible playbook that:
1. Follows Ansible best practices
2. Includes proper error handling
3. Is idempotent
4. Has clear task names and descriptions
5. Uses proper YAML formatting
6. Includes gather_facts, tags, and handlers where appropriate
7. Implements security best practices (no hardcoded credentials)
8. Uses variables for flexibility
9. Includes pre-flight checks
10. Has comprehensive logging

Output ONLY the YAML playbook content, no explanations or markdown.
Start with:
---
- name: [playbook name]
"""
        
        try:
            response = await self.model.generate_content_async(prompt)
            session.increment_metric("tokens_used", len(prompt.split()))
            
            # Extract and clean the playbook content
            playbook_content = response.text.strip()
            
            # Remove markdown code blocks if present
            if playbook_content.startswith("```"):
                lines = playbook_content.split("\n")
                playbook_content = "\n".join(lines[1:-1])
            
            # Ensure it starts with ---
            if not playbook_content.startswith("---"):
                playbook_content = "---\n" + playbook_content
            
            return playbook_content
            
        except Exception as e:
            logger.error(f"AI playbook generation failed: {str(e)}")
            # Fallback to template-based generation
            return self._generate_playbook_template(parsed_spec)
    
    def _generate_playbook_template(self, parsed_spec: Dict[str, Any]) -> str:
        """Fallback template-based playbook generation"""
        
        playbook = {
            "name": parsed_spec['description'],
            "hosts": "all",
            "gather_facts": True,
            "become": False,
            "vars": parsed_spec.get('variables', {}),
            "tasks": []
        }
        
        # Add pre-flight checks
        playbook["tasks"].append({
            "name": "Pre-flight validation",
            "assert": {
                "that": [
                    "inventory_hostname is defined",
                    "ansible_network_os is defined"
                ],
                "fail_msg": "Required variables not defined"
            },
            "tags": ["always", "validation"]
        })
        
        # Convert spec tasks to Ansible tasks
        for idx, task in enumerate(parsed_spec.get('tasks', [])):
            ansible_task = {
                "name": task.get('name', f"Task {idx+1}"),
                "tags": parsed_spec.get('tags', [])
            }
            
            # Add the action
            action = task.get('action', 'command')
            if 'commands' in task:
                ansible_task[action] = {
                    "commands": task['commands']
                }
            elif 'content' in task:
                ansible_task[action] = {
                    "content": task['content'],
                    "dest": task.get('dest', '/tmp/output.txt')
                }
            
            if 'register' in task:
                ansible_task['register'] = task['register']
            
            playbook["tasks"].append(ansible_task)
        
        return "---\n" + yaml.dump([playbook], default_flow_style=False)
    
    def _generate_inventory(self, parsed_spec: Dict[str, Any]) -> str:
        """Generate Ansible inventory file"""
        
        inventory = {
            "all": {
                "children": {}
            }
        }
        
        # Group devices by type
        device_groups = {}
        for device in parsed_spec.get('target_devices', []):
            device_type = device.get('type', 'unknown')
            if device_type not in device_groups:
                device_groups[device_type] = {
                    "hosts": {},
                    "vars": {
                        "ansible_network_os": device_type,
                        "ansible_connection": device.get('connection', 'network_cli')
                    }
                }
            
            # Add host entries
            count = device.get('count', 1)
            for i in range(count):
                host_name = f"{device_type}-{i+1:03d}"
                device_groups[device_type]["hosts"][host_name] = {
                    "ansible_host": f"192.168.1.{i+1}"
                }
        
        inventory["all"]["children"] = device_groups
        
        return yaml.dump(inventory, default_flow_style=False)
    
    def _generate_ansible_cfg(self, parsed_spec: Dict[str, Any]) -> str:
        """Generate ansible.cfg file"""
        
        config = """[defaults]
inventory = inventory/hosts.yml
host_key_checking = False
retry_files_enabled = False
gathering = smart
fact_caching = jsonfile
fact_caching_connection = /tmp/ansible_facts
fact_caching_timeout = 86400
stdout_callback = yaml
callbacks_enabled = profile_tasks, timer

[privilege_escalation]
become = False

[ssh_connection]
pipelining = True
ssh_args = -o ControlMaster=auto -o ControlPersist=60s
"""
        return config
    
    async def refine_playbook(
        self,
        playbook_path: str,
        refinement_prompt: str,
        parsed_spec: Dict[str, Any],
        session: Any
    ) -> Dict[str, Any]:
        """Refine an existing playbook based on feedback"""
        
        logger.info(f"Refining playbook: {playbook_path}")
        
        # Read current playbook
        with open(playbook_path, 'r') as f:
            current_content = f.read()
        
        prompt = f"""
You are an expert Ansible developer. Refine this Ansible playbook based on the feedback:

Current Playbook:
{current_content}

Refinement Instructions:
{refinement_prompt}

Generate the improved playbook. Output ONLY the YAML content, no explanations.
"""
        
        try:
            response = await self.model.generate_content_async(prompt)
            session.increment_metric("tokens_used", len(prompt.split()))
            session.increment_metric("refinements")
            
            # Clean the response
            refined_content = response.text.strip()
            if refined_content.startswith("```"):
                lines = refined_content.split("\n")
                refined_content = "\n".join(lines[1:-1])
            
            # Write refined version
            refined_path = playbook_path.replace(".yml", "_refined.yml")
            with open(refined_path, 'w') as f:
                f.write(refined_content)
            
            logger.info(f"Refined playbook saved: {refined_path}")
            
            return {
                "success": True,
                "file_path": refined_path,
                "original_path": playbook_path
            }
            
        except Exception as e:
            logger.error(f"Playbook refinement failed: {str(e)}")
            raise
