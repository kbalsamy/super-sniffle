# heybro CLI - User Guide

Universal AI CLI for OpenAI-compatible APIs and AWS Bedrock with token tracking, cost monitoring, and MCP support.

## Table of Contents

- [Overview](#overview)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Usage](#usage)
  - [Chat Commands](#chat-commands)
  - [Context Management](#context-management)
  - [Cost Tracking](#cost-tracking)
  - [AWS Integration](#aws-integration)
- [MCP Support](#mcp-support)
- [Examples](#examples)
- [Troubleshooting](#troubleshooting)

## Overview

**heybro** is a universal command-line interface for interacting with AI models. It supports:

- **Multiple Providers**: OpenAI, AWS Bedrock, and any OpenAI-compatible API
- **Token & Cost Tracking**: Real-time tracking of token usage and estimated costs
- **Context Management**: Intelligent pruning and window management
- **MCP Support**: Model Context Protocol for tool integration
- **Vim Integration**: Edit prompts in vim using `/vim`
- **Cost Monitoring**: Track AWS Bedrock costs via Cost Explorer
- **File Operations**: Read files directly into context

## Installation

### Prerequisites

- Python 3.8+
- pip
- vim (optional, for `/vim` command)

### Quick Install

```bash
# Clone the repository
git clone <repository-url> cd super-sniffle cd super-sniffle

# Install with make (recommended)
make install

# Or install manually
pip install -e .
```

### Installation Options

```bash
# Core installation
make install

# With development dependencies
make install-dev

# With all optional dependencies
make install-all

# Check system requirements
make check
```

### Provider-Specific Setup

#### OpenAI
```bash
export OPENAI_API_KEY='your-api-key'
export OPENAI_BASE_URL='https://api.openai.com/v1'  # optional
```

#### AWS Bedrock
```bash
# Using AWS profile
export AWS_PROFILE='your-profile'

# Using direct credentials
export AWS_ACCESS_KEY_ID='your-key'
export AWS_SECRET_ACCESS_KEY='your-secret'
export AWS_REGION='us-east-1'
```

## Quick Start

1. **Start the CLI:**
   ```bash
   heybro
   ```

2. **Send your first message:**
   ```
   > Hello, what can you do?
   ```

3. **Try commands:**
   ```
   > /model gpt-4
   > /cost
   > /help
   ```

4. **Use vim for long prompts:**
   ```
   > /vim
   ```

5. **Exit:**
   ```
   > /exit
   ```

## Configuration

### Command-Line Options

```bash
heybro [OPTIONS]

Options:
  --model MODEL           Default model to use
  --provider PROVIDER     Provider (openai, bedrock)
  --base-url URL          Base URL for API
  --api-key KEY           API key
  --profile PROFILE       AWS profile
  --region REGION         AWS region
  --arn ARN               Model ARN (Bedrock)
  --max-tokens N          Max tokens per response
  --temperature N         Temperature (0.0-2.0)
  --context-window N      Context window size
  --usage-file PATH       Usage tracking file
  --history-file PATH     Chat history file
  --working-dir PATH      Working directory
  --mcp-config PATH       MCP configuration file
  --debug                 Enable debug mode
  --help                  Show help message
```

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key | `sk-...` |
| `OPENAI_BASE_URL` | Custom OpenAI endpoint | `https://api.openai.com/v1` |
| `AWS_PROFILE` | AWS profile name | `default` |
| `AWS_ACCESS_KEY_ID` | AWS access key | `AKIA...` |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | `...` |
| `AWS_REGION` | AWS region | `us-east-1` |

### Configuration Files

The CLI creates several files in `~/.heybro/`:

- `usage.json` - Token usage and cost tracking
- `history.json` - Chat history (when saved with `/save`)
- `mcp.json` - MCP server configuration

## Usage

### Basic Chat

Simply type your message and press Enter:

```
> What is the capital of France?
The capital of France is Paris.
```

### Special Commands

All commands start with `/`:

#### Provider & Model Commands

- `/model MODEL` - Change model (e.g., `/model gpt-4`)
- `/models` - List available models
- `/provider PROVIDER` - Change provider
- `/cost` - Show current session cost
- `/cost-mtd` - Show AWS Bedrock month-to-date cost

#### Context Management

- `/context` - Show context usage statistics
- `/clear` - Clear conversation history
- `/prune` - Manually prune old messages
- `/read FILE` - Read file into context
- `/vim` - Open vim editor for long input
- `/copy` - Copy last response to clipboard

#### Session Management

- `/save` - Save conversation to history file
- `/load` - Load conversation from history file
- `/working-dir PATH` - Set working directory
- `/debug` - Toggle debug mode

#### MCP Commands

- `/mcp add CONFIG` - Add MCP server
- `/mcp list` - List MCP servers
- `/mcp remove NAME` - Remove MCP server
- `/mcp reload` - Reload MCP configuration
- `/mcp tools` - List available tools

#### Utility Commands

- `/help` - Show help
- `/exit` or `/quit` - Exit the CLI

### Chat Commands

#### Changing Models

```
> /model gpt-4
Model set to: gpt-4 (Provider: openai)

> /model anthropic.claude-3-sonnet-20240229-v1:0
Model set to: anthropic.claude-3-sonnet-20240229-v1:0 (Provider: bedrock)
```

#### Listing Models

```
> /models
Available models:
  - gpt-3.5-turbo
  - gpt-4
  - claude-3-haiku-20240307
  - claude-3-sonnet-20240229
```

### Context Management

#### Check Context Usage

```
> /context
Context: 2,048 tokens (34% of 6,144 context window)
Remaining: 4,096 tokens
No pruning needed.
```

#### Read Files

```
> /read src/heybro.py
Loaded 150 lines from src/heybro.py into context.

> Analyze this code for security issues
[Analysis of the code...]
```

#### Use Vim Editor

```
> /vim
# Opens vim editor
# Type your prompt, save and exit
# Content is loaded into context
```

#### Copy Responses

```
> /copy
✓ Copied to clipboard: The capital of France is...
```

### Cost Tracking

The CLI tracks token usage and estimates costs in real-time.

#### View Session Cost

```
> /cost
+-----------+-------+-------+-----------+----------+
| Model     | Input | Output| Input $   | Output $ |
+-----------+-------+-------+-----------+----------+
| gpt-3.5-turbo | 1,234 | 567   | $0.0012   | $0.0011  |
+-----------+-------+-------+-----------+----------+
Total: $0.0023
```

#### View AWS Month-to-Date Cost

```
> /cost-mtd
+--------------------------------------+
| 💵 AWS Bedrock Cost (Cost Explorer) |
+--------------------------------------+
| Period: 2024-01-01 to 2024-01-31    |
| Bedrock Unblended Cost: $12.34      |
+--------------------------------------+
```

### AWS Integration

#### Using AWS Profiles

```bash
# Set profile via environment
export AWS_PROFILE=production
heybro --provider bedrock
```

```
> /provider bedrock
Provider set to: bedrock

> /model anthropic.claude-3-sonnet-20240229-v1:0
Model set to: anthropic.claude-3-sonnet-20240229-v1:0
```

#### Model ARNs

For custom models, use Model ARNs:

```
> /model-arn arn:aws:bedrock:us-east-1:123456789012:provisioned-model/abcdefg
Inference ARN set to: arn:aws:bedrock:us-east-1:123456789012:provisioned-model/abcdefg
```

## MCP Support

### What is MCP?

MCP (Model Context Protocol) allows AI models to use external tools and data sources.

### Adding MCP Servers

```
> /mcp add {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-filesystem", "/home/user"], "name": "filesystem"}
✓ MCP server 'filesystem' added
```

### Using MCP Tools

When MCP is enabled, the AI can automatically use available tools:

```
> List files in my Documents folder
[AI uses filesystem tool]
Files in /home/user/Documents:
- report.pdf
- notes.txt
```

## Examples

### Example 1: Code Review

```
> /read src/main.py
Loaded 85 lines from src/main.py

> Review this code for security vulnerabilities
[Security review...]
```

### Example 2: Document Analysis

```
> /read docs/specification.md
Loaded 1,234 lines from docs/specification.md

> /context
Context: 4,567 tokens (74% of 6,144 context window)

> Summarize the key requirements
[Summary...]
```

### Example 3: Multi-model Comparison

```
> /model gpt-3.5-turbo
Model set to: gpt-3.5-turbo

> Explain quantum computing
[GPT-3.5 response...]

> /model anthropic.claude-3-haiku-20240307-v1:0
Model set to: anthropic.claude-3-haiku-20240307-v1:0

> Explain quantum computing
[Claude response...]
```

### Example 4: Long-form Writing

```
> /vim
# Write a detailed blog post in vim
# Save and exit

> Please expand on this blog post with more examples
[Expanded content...]

> /copy
✓ Copied to clipboard
```

## Troubleshooting

### Common Issues

#### "Command not found: heybro"

**Solution:** Install with pip or use full path:
```bash
pip install -e .
# or
python src/heybro.py
```

#### "API key not found"

**Solution:** Set environment variables:
```bash
export OPENAI_API_KEY='your-key'
# or
export AWS_PROFILE='your-profile'
```

#### "vim: command not found"

**Solution:** Install vim:
```bash
# macOS
brew install vim

# Ubuntu/Debian
sudo apt install vim
```

#### "Context window exceeded"

**Solution:** Use `/prune` to remove old messages or `/clear` to start fresh.

#### "MCP server failed to connect"

**Solution:** Check the server configuration and ensure it's running:
```
> /mcp list
> /mcp reload
```

### Debug Mode

Enable debug mode for detailed logging:

```bash
heybro --debug
```

Or within the CLI:
```
> /debug
Debug mode: ON
```

### Getting Help

- Use `/help` within the CLI
- Check the [INSTALL.md](INSTALL.md) for installation issues
- Review the [COMMANDS.md](COMMANDS.md) for detailed command reference
- Run `make help` for build system help

## Tips & Best Practices

1. **Use `/vim` for long prompts** - Easier editing than the command line
2. **Monitor context with `/context`** - Know when you're approaching limits
3. **Track costs with `/cost`** - Keep an eye on spending
4. **Save important chats with `/save`** - Preserve valuable conversations
5. **Use `/copy` for responses** - Quickly copy formatted responses
6. **Experiment with models** - Compare different models for your use case
7. **Leverage MCP** - Connect to external tools and data sources
8. **Set working directory** - Use `/working-dir` for relative file paths
9. **Clear context regularly** - Start fresh conversations to save tokens
10. **Use AWS profiles** - Manage multiple AWS accounts easily

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.

## License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file for details.