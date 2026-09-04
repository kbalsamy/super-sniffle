# Installation Guide

Comprehensive installation instructions for heybro CLI across different platforms and use cases.

## Table of Contents

- [Quick Install](#quick-install)
- [Platform-Specific Instructions](#platform-specific-instructions)
  - [macOS](#macos)
  - [Linux (Ubuntu/Debian)](#linux-ubuntudebian)
  - [Linux (CentOS/RHEL)](#linux-centosrhel)
  - [Windows (WSL2)](#windows-wsl2)
- [Installation Methods](#installation-methods)
  - [From Source](#from-source)
  - [Development Install](#development-install)
  - [With All Features](#with-all-features)
- [Provider Setup](#provider-setup)
  - [OpenAI Setup](#openai-setup)
  - [AWS Bedrock Setup](#aws-bedrock-setup)
  - [Custom OpenAI-compatible API](#custom-openai-compatible-api)
- [Optional Dependencies](#optional-dependencies)
- [Verifying Installation](#verifying-installation)
- [Troubleshooting](#troubleshooting)

## Quick Install

```bash
# Clone repository (replace with your actual repo URL)
git clone <repository-url> super-sniffle
cd super-sniffle

# Install using make (recommended)
make install

# Or install directly with pip
pip install -e .

# Verify installation
heybro --version
```

## Platform-Specific Instructions

### macOS

#### Prerequisites

1. **Install Homebrew** (if not already installed):
   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```

2. **Install Python 3.8+**:
   ```bash
   brew install python@3.11
   ```

3. **Install vim** (optional, for `/vim` command):
   ```bash
   brew install vim
   ```

#### Installation

```bash
# Using make (recommended)
make install

# Or manual installation
git clone <repository-url> super-sniffle
cd super-sniffle
python3 -m venv env
source env/bin/activate
pip install -e .
```

#### System Dependencies

```bash
# Install all system dependencies
make brew-deps

# Or manually
brew install vim
```

### Linux (Ubuntu/Debian)

#### Prerequisites

1. **Update package list**:
   ```bash
   sudo apt update
   ```

2. **Install Python 3.8+ and build tools**:
   ```bash
   sudo apt install -y python3 python3-pip python3-venv python3-dev
   sudo apt install -y build-essential
   ```

3. **Install vim** (optional):
   ```bash
   sudo apt install -y vim
   ```

4. **Install clipboard support** (optional):
   ```bash
   sudo apt install -y xclip  # For X11
   # or
   sudo apt install -y wl-clipboard  # For Wayland
   ```

#### Installation

```bash
# Clone repository
git clone <repository-url> super-sniffle
cd super-sniffle

# Using make
make install

# Or manual installation
python3 -m venv env
source env/bin/activate
pip install -e .
```

### Linux (CentOS/RHEL)

#### Prerequisites

1. **Enable EPEL repository** (if needed):
   ```bash
   sudo yum install -y epel-release
   ```

2. **Install Python 3.8+ and development tools**:
   ```bash
   sudo yum groupinstall -y "Development Tools"
   sudo yum install -y python3 python3-pip python3-devel
   ```

3. **Install vim** (optional):
   ```bash
   sudo yum install -y vim
   ```

4. **Install clipboard support** (optional):
   ```bash
   sudo yum install -y xclip
   ```

#### Installation

```bash
# Clone repository
git clone <repository-url> super-sniffle
cd super-sniffle

# Using make
make install

# Or manual installation
python3 -m venv env
source env/bin/activate
pip install -e .
```

### Windows (WSL2)

**Note:** Native Windows installation is not recommended. Use WSL2 for the best experience.

#### Setup WSL2

1. **Enable WSL2** (PowerShell as Administrator):
   ```powershell
   wsl --install
   ```

2. **Install Ubuntu from Microsoft Store**

3. **Launch Ubuntu and follow Ubuntu/Debian instructions above**

#### Windows-Specific Notes

- Use `clip.exe` for clipboard on Windows (automatically detected)
- Use WSL file paths: `/mnt/c/Users/YourName/...`
- Python and vim are available in WSL by default

## Installation Methods

### From Source (Recommended)

```bash
# Clone the repository
git clone <repository-url> super-sniffle
cd super-sniffle

# Install with make
make install

# Or manually
pip install -e .
```

### Development Install

```bash
# Install with development dependencies
make install-dev

# Or manually
pip install -e ".[dev]"
```

Development install includes:
- pytest (testing)
- flake8 (linting)
- pylint (linting)
- black (code formatting)
- isort (import sorting)

### With All Features

```bash
# Install with all optional dependencies
make install-all

# Or manually
pip install -e ".[all]"
```

This includes:
- MCP support
- pyperclip (clipboard)
- All development tools

### Minimal Install

```bash
# Install only core dependencies
pip install -e ".[core]"
```

## Provider Setup

### OpenAI Setup

#### Get API Key

1. Visit [OpenAI API Keys](https://platform.openai.com/api-keys)
2. Create a new secret key
3. Copy the key

#### Configuration Methods

**Method 1: Environment Variable (Recommended)**
```bash
export OPENAI_API_KEY='sk-...'
# Add to ~/.bashrc or ~/.zshrc for persistence
```

**Method 2: Command-Line**
```bash
heybro --api-key 'sk-...'
```

**Method 3: .env File**
```bash
# Create .env file
echo "OPENAI_API_KEY=sk-..." > .env
```

#### Testing OpenAI

```bash
heybro --provider openai --model gpt-3.5-turbo
```

Then in the CLI:
```
> /cost
> Hello, this is a test
```

### AWS Bedrock Setup

#### Prerequisites

1. **AWS Account** with Bedrock access
2. **IAM User/Role** with permissions:
   - `bedrock:InvokeModel`
   - `bedrock:ListFoundationModels`
   - `ce:GetCostAndUsage` (for cost tracking)

3. **Request Bedrock Access** in AWS Console

#### Setup Methods

**Method 1: AWS Profile (Recommended)**

```bash
# Configure AWS CLI
aws configure

# Or manually create ~/.aws/credentials
[default]
aws_access_key_id = AKIA...
aws_secret_access_key = ...

# And ~/.aws/config
[default]
region = us-east-1

# Set environment variable
export AWS_PROFILE=default
```

**Method 2: Direct Credentials**

```bash
export AWS_ACCESS_KEY_ID='AKIA...'
export AWS_SECRET_ACCESS_KEY='...'
export AWS_REGION='us-east-1'
```

**Method 3: IAM Role (EC2/ECS)**

```bash
# No configuration needed - uses instance role
export AWS_REGION='us-east-1'
```

#### Testing AWS Bedrock

```bash
heybro --provider bedrock
```

Then in the CLI:
```
> /models
> /model anthropic.claude-3-haiku-20240307-v1:0
> Tell me about AWS Bedrock
```

### Custom OpenAI-compatible API

#### Examples

**LocalAI:**
```bash
heybro --provider openai \
       --base-url http://localhost:8080/v1 \
       --api-key "dummy-key"
```

**Ollama:**
```bash
heybro --provider openai \
       --base-url http://localhost:11434/v1 \
       --api-key "ollama"
```

**AnyScale:**
```bash
heybro --provider openai \
       --base-url https://api.endpoints.anyscale.com/v1 \
       --api-key 'your-anyscale-key'
```

## Optional Dependencies

### Clipboard Support

For `/copy` command:

```bash
# macOS (already installed)
pip install pyperclip

# Linux X11
sudo apt install xclip
pip install pyperclip

# Linux Wayland
sudo apt install wl-clipboard
pip install pyperclip

# Windows (WSL)
pip install pyperclip  # Uses clip.exe automatically
```

### MCP Support

For Model Context Protocol:

```bash
pip install mcp
```

### Development Tools

```bash
pip install -e ".[dev]"
```

Includes:
- pytest
- flake8
- pylint
- black
- isort
- twine (for packaging)
- build (for packaging)

## Verifying Installation

### Check Installation

```bash
# Check if heybro is installed
which heybro
heybro --version

# Check Python environment
python3 --version
pip --version

# Check system dependencies
vim --version  # optional
```

### Test Basic Functionality

```bash
# Start heybro
heybro

# Test commands in CLI
> /help
> /exit
```

### Test Provider

```bash
# Test with OpenAI (if configured)
heybro --model gpt-3.5-turbo --max-tokens 100

# Test with Bedrock (if configured)
heybro --provider bedrock --model anthropic.claude-3-haiku-20240307-v1:0
```

### Run Tests

```bash
# Run test suite
make test

# Run with coverage
make test-cov
```

### Check Configuration

```bash
# Check if configuration files were created
ls -la ~/.heybro/

# Expected files:
# - usage.json
# - mcp.json (if MCP configured)
```

## Troubleshooting

### Installation Issues

#### "Command not found: heybro"

**Solution 1: Add to PATH**
```bash
# Find installation location
pip show heybro | grep Location

# Add to PATH (add to ~/.bashrc or ~/.zshrc)
export PATH="$HOME/.local/bin:$PATH"
```

**Solution 2: Use full path**
```bash
python src/heybro.py
```

**Solution 3: Reinstall**
```bash
pip uninstall heybro
pip install -e .
```

#### "Permission denied"

**Solution 1: Use virtual environment**
```bash
python3 -m venv env
source env/bin/activate
pip install -e .
```

**Solution 2: Use --user flag**
```bash
pip install --user -e .
```

#### "Module not found" errors

**Solution:**
```bash
# Reinstall with all dependencies
pip install -e ".[all]"

# Or install missing packages individually
pip install openai rich boto3
```

### Provider Issues

#### OpenAI: "Invalid API key"

**Solution:**
```bash
# Check if key is set
echo $OPENAI_API_KEY

# Verify key format (should start with sk-)
heybro --api-key "sk-..."
```

#### AWS: "Invalid profile"

**Solution:**
```bash
# List available profiles
aws configure list-profiles

# Check profile configuration
cat ~/.aws/credentials
```

#### AWS: "Access denied"

**Solution:**
```bash
# Check IAM permissions
aws bedrock list-foundation-models

# Verify region
aws configure get region
```

### Runtime Issues

#### "vim: command not found"

**Solution:**
```bash
# macOS
brew install vim

# Ubuntu/Debian
sudo apt install vim

# CentOS/RHEL
sudo yum install vim
```

#### "Clipboard not available"

**Solution:**
```bash
# Install clipboard support
pip install pyperclip

# Linux additional packages
sudo apt install xclip  # X11
# or
sudo apt install wl-clipboard  # Wayland
```

#### "Context window exceeded"

**Solution:**
```bash
# In heybro CLI:
> /prune
> /clear

# Or increase context window:
heybro --context-window 128000
```

### Manual Installation (Last Resort)

If all else fails:

```bash
# Create virtual environment
python3 -m venv env
source env/bin/activate

# Install dependencies manually
pip install openai rich boto3 pyperclip mcp

# Run directly
python src/heybro.py
```

### Getting Help

1. **Check logs:** Enable debug mode
   ```bash
   heybro --debug
   ```

2. **Check version:**
   ```bash
   heybro --version
   python --version
   ```

3. **System information:**
   ```bash
   make check
   ```

4. **Open an issue:** Include:
   - OS and version
   - Python version
   - Installation method
   - Error messages
   - Debug logs

## Next Steps

After installation:

1. **Read the [User Guide](USER_GUIDE.md)**
2. **Set up your [provider](#provider-setup)**
3. **Try the [examples](USER_GUIDE.md#examples)**
4. **Explore the [commands reference](COMMANDS.md)**

## Uninstallation

```bash
# Using make
make uninstall

# Or manually
pip uninstall heybro

# Clean configuration files
rm -rf ~/.heybro/
```