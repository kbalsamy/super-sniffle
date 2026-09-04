# Command Reference

Complete reference for all heybro CLI commands and features.

## Table of Contents

- [Built-in Commands](#built-in-commands)
- [Slash Commands](#slash-commands)
- [Command-Line Options](#command-line-options)
- [MCP Commands](#mcp-commands)
- [Keyboard Shortcuts](#keyboard-shortcuts)
- [Environment Variables](#environment-variables)

## Built-in Commands

### `/help` - Show Help

**Usage:**
```
> /help
```

**Description:**
Displays all available commands and their usage information.

**Example:**
```
> /help
Available commands:
  /help                          Show this help
  /exit, /quit                   Exit the CLI
  /model MODEL                   Change model (e.g., gpt-4)
  /models                        List available models
  ...
```

---

### `/exit`, `/quit` - Exit CLI

**Usage:**
```
> /exit
> /quit
```

**Description:**
Exits the heybro CLI. Unsaved conversation history will be lost unless saved with `/save`.

**Example:**
```
> /exit
Goodbye!
```

---

## Slash Commands

### Provider & Model Commands

#### `/model` - Change Model

**Usage:**
```
> /model MODEL_NAME
```

**Description:**
Changes the active AI model. Automatically detects the appropriate provider.

**Valid Models:**
- OpenAI: `gpt-3.5-turbo`, `gpt-4`, `gpt-4-turbo`, etc.
- Bedrock: `anthropic.claude-3-haiku-20240307-v1:0`, `anthropic.claude-3-sonnet-20240229-v1:0`, etc.

**Examples:**
```
> /model gpt-4
Model set to: gpt-4 (Provider: openai)

> /model anthropic.claude-3-sonnet-20240229-v1:0
Model set to: anthropic.claude-3-sonnet-20240229-v1:0 (Provider: bedrock)
```

**Related:** `/models`, `/provider` 

---

#### `/models` - List Available Models

**Usage:**
```
> /models
```

**Description:**
Lists all available models for the current provider.

**Example:**
```
> /models
Available models (openai):
  - gpt-3.5-turbo
  - gpt-4
  - gpt-4-turbo
  - gpt-4-0125-preview
```

**Note:** For Bedrock, this lists foundation models available in your region.

---

#### `/provider` - Change Provider

**Usage:**
```
> /provider PROVIDER_NAME
```

**Description:**
Switches between AI providers (openai, bedrock, custom).

**Valid Providers:**
- `openai` - OpenAI API
- `bedrock` - AWS Bedrock
- Any custom OpenAI-compatible provider

**Examples:**
```
> /provider openai
Provider set to: openai

> /provider bedrock
Provider set to: bedrock
```

**Related:** `/model`, `/model-arn`

---

#### `/model-arn` - Set Model ARN

**Usage:**
```
> /model-arn arn:aws:bedrock:REGION:ACCOUNT:resource/ID
> /model-arn clear
```

**Description:**
Sets a custom Model ARN for AWS Bedrock (e.g., provisioned models). Use `clear` to remove and use standard models.

**Examples:**
```
> /model-arn arn:aws:bedrock:us-east-1:123456789012:provisioned-model/abcdefg
Inference ARN set to: arn:aws:bedrock:us-east-1:123456789012:provisioned-model/abcdefg

> /model-arn clear
Inference ARN cleared; using --model
```

**Note:** Only applies when provider is `bedrock`.

---

### Context Management Commands

#### `/context` - Show Context Status

**Usage:**
```
> /context
```

**Description:**
Displays current token usage and context window status.

**Example:**
```
> /context
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Context Status                                 ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Current usage: 2,048 tokens (34%)              │
│ Context window: 6,144 tokens                   │
│ Remaining: 4,096 tokens                        │
│ No pruning needed                                │
└────────────────────────────────────────────────┘
```

**Tip:** Watch this when working with long files or conversations.

---

#### `/clear` - Clear Conversation

**Usage:**
```
> /clear
```

**Description:**
Clears all messages from the current conversation. Starts fresh while keeping the same model and provider.

**Example:**
```
> /clear
🗑️ Cleared conversation. Context is reset.
```

**Warning:** This cannot be undone. Use `/save` first if you want to preserve the conversation.

---

#### `/prune` - Prune Old Messages

**Usage:**
```
> /prune
```

**Description:**
Manually triggers context pruning to remove old messages when approaching token limits. Usually automatic, but can be triggered manually.

**Example:**
```
> /prune
📌 Pruned 5 old messages to fit context window.
```

**Related:** `/context`

---

#### `/read` - Read File

**Usage:**
```
> /read FILE_PATH
> /read /absolute/path/to/file.txt
```

**Description:**
Reads a file into the conversation context. Supports relative paths (from working directory) or absolute paths.

**Examples:**
```
> /read README.md
Loaded 45 lines from README.md into context.

> /read src/main.py
Loaded 156 lines from src/main.py into context.

> /read /home/user/documents/report.pdf
Error: Format not supported
```

**Supported Formats:**
- Text files (.txt, .md, .py, .js, etc.)
- JSON files
- YAML files

**Related:** `/working-dir`

---

#### `/vim` - Open Vim Editor

**Usage:**
```
> /vim
```

**Description:**
Opens vim to compose a long message or prompt. After saving and exiting, content is loaded into context.

**Features:**
- Opens temporary file in vim
- Full vim editing capabilities
- Automatic cleanup after use
- Clipboard integration (if available)

**Example:**
```
> /vim
# Opens vim
# Type your content
# :wq to save and exit
Loaded 12 lines from Vim editor into context.
```

**Requirements:** vim must be installed and available in PATH.

**Installation:**
```bash
# macOS
brew install vim

# Ubuntu/Debian
sudo apt install vim

# CentOS/RHEL
sudo yum install vim
```

**Note:** If vim is not found, an error message will be displayed with installation instructions.

---

#### `/copy` - Copy Last Response

**Usage:**
```
> /copy
```

**Description:**
Copies the last assistant response to system clipboard.

**Example:**
```
> What is Python?
Python is a high-level programming language...

> /copy
✓ Copied to clipboard: Python is a high-level programming language...
```

**Requirements:** pyperclip must be installed.

**Installation:**
```bash
pip install pyperclip
```

---

#### `/working-dir` - Set Working Directory

**Usage:**
```
> /working-dir /path/to/directory
> /working-dir clear
```

**Description:**
Sets the working directory for relative file paths in `/read` and other file operations.

**Examples:**
```
> /working-dir /home/user/projects/myproject
Working directory set to: /home/user/projects/myproject

> /read src/main.py
Loaded 123 lines from src/main.py

> /working-dir clear
Working directory cleared. Use absolute paths.
```

**Tip:** Useful when working on a project with multiple files.

---

### Session Management Commands

#### `/save` - Save Conversation

**Usage:**
```
> /save
```

**Description:**
Saves the current conversation to a history file (default: `~/.heybro/history.json`).

**Example:**
```
> /save
💾 Saved conversation to /home/user/.heybro/conversation_20240115_143022.json
```

**Tip:** Save important conversations before `/clear` or exiting.

---

#### `/load` - Load Conversation

**Usage:**
```
> /load
```

**Description:**
Loads a previously saved conversation from the history file.

**Example:**
```
> /load
Available conversations:
  1. 2024-01-15 14:30
  2. 2024-01-14 09:15

Enter number to load: 1
📂 Loaded conversation from /home/user/.heybro/conversation_20240115_143022.json
```

**Note:** This loads the conversation context but continues in the same session.

---

#### `/debug` - Toggle Debug Mode

**Usage:**
```
> /debug
```

**Description:**
Toggles debug mode, which shows detailed API requests and responses.

**Example:**
```
> /debug
Debug mode: ON

> Hello
[DEBUG] Sending request to https://api.openai.com/v1/chat/completions
[DEBUG] Request body: {...}
[DEBUG] Response: {...}
```

**Use Case:** Troubleshooting API issues or understanding token usage.

---

### Cost Tracking Commands

#### `/cost` - Show Session Cost

**Usage:**
```
> /cost
```

**Description:**
Displays token usage and estimated cost for the current session.

**Example:**
```
> /cost
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ 💰 Session Cost                ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Model: gpt-3.5-turbo          │
│ Input tokens: 1,234           │
│ Output tokens: 567              │
│ Input cost: $0.0012           │
│ Output cost: $0.0011          │
│ ───────────────────────────── │
│ Total: $0.0023                │
└───────────────────────────────┘
```

**Note:** Costs are estimates based on token counts and provider pricing.

---

#### `/cost-mtd` - Show Month-to-Date AWS Cost

**Usage:**
```
> /cost-mtd
```

**Description:**
Fetches actual billed costs for AWS Bedrock from AWS Cost Explorer for the current month.

**Example:**
```
> /cost-mtd
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ 💵 AWS Bedrock Cost (Cost Explorer)     ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Period: 2024-01-01 to 2024-01-31      │
│ Bedrock Unblended Cost: $12.34          │
│ Currency: USD                           │
└─────────────────────────────────────────┘

Actual billed cost from AWS Cost Explorer (~24h reporting lag);
use /cost for this session's live token-based estimate.
```

**Requirements:**
- Provider must be `bedrock`
- AWS credentials with `ce:GetCostAndUsage` permission
- 24-hour reporting lag (not real-time)

**Permissions Required:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "ce:GetCostAndUsage",
      "Resource": "*"
    }
  ]
}
```

---

### Utility Commands

#### `/run` - Run Shell Command

**Usage:**
```
> /run COMMAND
```

**Description:**
Executes a shell command and displays its output.

**Examples:**
```
> /run ls -la
total 64
drwxr-xr-x  10 user staff  320 Jan 15 14:30 .
drwxr-xr-x  15 user staff  480 Jan 15 14:30 ..

> /run git status
On branch main
Your branch is up to date with 'origin/main'.

nothing to commit, working tree clean
```

**Security:** Commands are restricted to common utilities (ls, cat, grep, git, pwd, etc.).

**Exit Codes:**
- Command output is displayed in CLI
- Non-zero exits show error messages

---

## Command-Line Options

### Basic Options

```bash
heybro [OPTIONS]
```

#### `--model MODEL`
**Default model to use**
```bash
heybro --model gpt-4
heybro --model anthropic.claude-3-sonnet-20240229-v1:0
```

#### `--provider PROVIDER`
**Provider to use**
```bash
heybro --provider openai
heybro --provider bedrock
```

#### `--base-url URL`
**Custom API endpoint**
```bash
heybro --base-url https://api.openai.com/v1
heybro --base-url http://localhost:8080/v1
```

#### `--api-key KEY`
**API key for authentication**
```bash
heybro --api-key 'sk-...'
```

#### `--profile PROFILE`
**AWS profile name**
```bash
heybro --profile production
```

#### `--region REGION`
**AWS region**
```bash
heybro --region us-east-1
heybro --region us-west-2
```

#### `--arn ARN`
**Model ARN for Bedrock**
```bash
heybro --arn arn:aws:bedrock:us-east-1:123456789012:custom-model/abcdef
```

### Advanced Options

#### `--max-tokens N`
**Maximum tokens in response**
```bash
heybro --max-tokens 1000
heybro --max-tokens 4000
```

#### `--temperature N`
**Sampling temperature (0.0-2.0)**
```bash
heybro --temperature 0.7   # Creative
heybro --temperature 0.2   # Focused
heybro --temperature 1.0   # Very creative
```

#### `--context-window N`
**Context window size in tokens**
```bash
heybro --context-window 4096
heybro --context-window 128000
```

#### `--usage-file PATH`
**Usage tracking file**
```bash
heybro --usage-file /path/to/usage.json
```

#### `--history-file PATH`
**Chat history file**
```bash
heybro --history-file /path/to/history.json
```

#### `--working-dir PATH`
**Working directory**
```bash
heybro --working-dir /home/user/projects
```

#### `--mcp-config PATH`
**MCP configuration file**
```bash
heybro --mcp-config /path/to/mcp.json
```

#### `--debug`
**Enable debug mode**
```bash
heybro --debug
```

#### `--help`
**Show help message**
```bash
heybro --help
```

#### `--version`
**Show version**
```bash
heybro --version
```

### Combining Options

```bash
heybro --provider bedrock \
       --profile production \
       --region us-east-1 \
       --model anthropic.claude-3-sonnet-20240229-v1:0 \
       --max-tokens 2000 \
       --debug
```

## MCP Commands

### `/mcp add` - Add MCP Server

**Usage:**
```
> /mcp add {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-name"]}
```

**Description:**
Adds an MCP server configuration.

**Examples:**
```
> /mcp add {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-filesystem", "/home/user"], "name": "fs"}
```

---

### `/mcp list` - List MCP Servers

**Usage:**
```
> /mcp list
```

**Description:**
Lists all configured MCP servers.

---

### `/mcp remove` - Remove MCP Server

**Usage:**
```
> /mcp remove SERVER_NAME
```

**Description:**
Removes an MCP server configuration.

---

### `/mcp reload` - Reload MCP

**Usage:**
```
> /mcp reload
```

**Description:**
Reloads MCP configuration and reconnects to servers.

---

### `/mcp tools` - List MCP Tools

**Usage:**
```
> /mcp tools
```

**Description:**
Lists available tools from connected MCP servers.

---

## Keyboard Shortcuts

### Input Editing

- `↑` / `↓` - Navigate command history
- `Ctrl+A` - Move to beginning of line
- `Ctrl+E` - Move to end of line
- `Ctrl+W` - Delete previous word
- `Ctrl+U` - Delete entire line
- `Ctrl+R` - Reverse search history

### Program Control

- `Ctrl+C` - Interrupt current operation
- `Ctrl+D` - Exit (if input is empty)
- `Enter` - Submit message/command

---

## Environment Variables

### API Configuration

#### `OPENAI_API_KEY`
**OpenAI API key**
```bash
export OPENAI_API_KEY='sk-...'
```

#### `OPENAI_BASE_URL`
**OpenAI-compatible API endpoint**
```bash
export OPENAI_BASE_URL='https://api.openai.com/v1'
```

#### `AWS_PROFILE`
**AWS profile name**
```bash
export AWS_PROFILE='production'
```

#### `AWS_ACCESS_KEY_ID`
**AWS access key**
```bash
export AWS_ACCESS_KEY_ID='AKIA...'
```

#### `AWS_SECRET_ACCESS_KEY`
**AWS secret key**
```bash
export AWS_SECRET_ACCESS_KEY='...'
```

#### `AWS_REGION`
**AWS region**
```bash
export AWS_REGION='us-east-1'
```

### CLI Configuration

#### `HEYBRO_CONFIG_DIR`
**Configuration directory**
```bash
export HEYBRO_CONFIG_DIR='/custom/path'
```

#### `HEYBRO_USAGE_FILE`
**Usage tracking file**
```bash
export HEYBRO_USAGE_FILE='/path/to/usage.json'
```

#### `HEYBRO_HISTORY_FILE`
**History file**
```bash
export HEYBRO_HISTORY_FILE='/path/to/history.json'
```

---

## Command Quick Reference

| Command | Description | Example |
|---------|-------------|---------|
| `/help` | Show help | `/help` |
| `/exit` | Exit CLI | `/exit` |
| `/model` | Change model | `/model gpt-4` |
| `/models` | List models | `/models` |
| `/provider` | Change provider | `/provider bedrock` |
| `/model-arn` | Set Model ARN | `/model-arn arn:aws:...` |
| `/context` | Show context | `/context` |
| `/clear` | Clear conversation | `/clear` |
| `/prune` | Prune messages | `/prune` |
| `/read` | Read file | `/read file.txt` |
| `/vim` | Open vim | `/vim` |
| `/copy` | Copy response | `/copy` |
| `/working-dir` | Set directory | `/working-dir /path` |
| `/save` | Save conversation | `/save` |
| `/load` | Load conversation | `/load` |
| `/debug` | Toggle debug | `/debug` |
| `/cost` | Show session cost | `/cost` |
| `/cost-mtd` | Show AWS MTD cost | `/cost-mtd` |
| `/run` | Run shell command | `/run ls -la` |
| `/mcp add` | Add MCP server | `/mcp add {"command": "..."}` |
| `/mcp list` | List MCP servers | `/mcp list` |
| `/mcp remove` | Remove MCP server | `/mcp remove name` |
| `/mcp reload` | Reload MCP | `/mcp reload` |
| `/mcp tools` | List MCP tools | `/mcp tools` |