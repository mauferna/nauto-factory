# Quick Start Guide - Network Automation Factory

## 🚀 Get Started in 5 Minutes

### Prerequisites
- Python 3.10 or higher
- Google AI API key ([Get one here](https://ai.google.dev/))
- Git (optional)

### Installation

```bash
# 1. Navigate to project directory
cd network_automation_factory

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set your Google AI API key
export GOOGLE_API_KEY="your-api-key-here"
```

### Run Your First Automation

```bash
# Process the example specification
python main.py --spec examples/example_spec.yaml
```

This will:
1. Parse and validate the specification
2. Generate an Ansible playbook
3. Create comprehensive tests
4. Set up CI/CD pipeline
5. Generate documentation
6. Perform code review

**Expected output:** All artifacts in `./output/` directory in ~15 minutes

### View Your Results

```bash
# Generated artifacts
ls -la output/playbooks/       # Ansible playbooks
ls -la output/tests/          # Test suites
ls -la output/cicd/           # CI/CD configs
ls -la output/docs/           # Documentation
ls -la output/reviews/        # Code review reports

# View statistics
python main.py --stats
```

### Create Your Own Automation

```bash
# 1. Copy the example specification
cp examples/example_spec.yaml my_automation.yaml

# 2. Edit with your requirements
nano my_automation.yaml

# 3. Run the automation factory
python main.py --spec my_automation.yaml
```

### Example Specification

```yaml
automation_spec:
  name: "my_network_automation"
  description: "My custom network automation"
  
  target_devices:
    - type: "cisco_ios"
      count: 10
      connection: "network_cli"
  
  tasks:
    - name: "Collect device info"
      action: "ios_facts"
      register: "device_facts"
  
  cicd:
    platform: "github_actions"
```

### Command Line Options

```bash
# Basic usage
python main.py --spec path/to/spec.yaml

# Custom output directory
python main.py --spec spec.yaml --output-dir /custom/path

# Verbose logging
python main.py --spec spec.yaml --verbose

# View statistics
python main.py --stats

# Custom session ID
python main.py --spec spec.yaml --session-id my-session-123
```

### Troubleshooting

**Problem:** `GOOGLE_API_KEY not set`  
**Solution:** Export your API key: `export GOOGLE_API_KEY="your-key"`

**Problem:** `Specification file not found`  
**Solution:** Check the file path is correct and the file exists

**Problem:** `Module not found`  
**Solution:** Install dependencies: `pip install -r requirements.txt`

**Problem:** `ansible-lint not found`  
**Solution:** Install Ansible tools: `pip install ansible ansible-lint`

### Next Steps

1. **Review Generated Artifacts** - Check the output directory
2. **Run Tests** - Execute the generated test suite
3. **Deploy** - Use the CI/CD pipeline configuration
4. **Customize** - Create your own specifications
5. **Learn More** - Read the full [README.md](README.md)

### Support

- 📖 Full documentation: [README.md](README.md)
- 📝 Submission details: [SUBMISSION.md](SUBMISSION.md)
- 🐛 Issues: Create an issue on GitHub
- 💬 Questions: [email@example.com]

### What's Generated?

For each automation specification, you get:

✅ **Production-Ready Playbook** - Follows all Ansible best practices  
✅ **Inventory Configuration** - Pre-configured for your devices  
✅ **Comprehensive Tests** - Molecule + pytest test suites  
✅ **CI/CD Pipeline** - GitHub Actions/GitLab CI/Jenkins  
✅ **Code Review Report** - Quality analysis with scoring  
✅ **Complete Documentation** - README with usage examples  

**Time Saved:** 10-15 hours → 15 minutes (98% reduction!)

---

Happy Automating! 🎉
