Install dependencies
pip install openai rich boto3
pip install mcp   # optional, needed for /mcp (Model Context Protocol tool servers)

--- Moonshot (Kimi K3) ---
export MOONSHOT_API_KEY="your-key"
python heybro.py --provider moonshot --reasoning max

 --- AWS Bedrock ---
export AWS_ACCESS_KEY_ID="your-key"
 export AWS_SECRET_ACCESS_KEY="your-secret"
 python heybro.py --provider bedrock --model anthropic.claude-3-5-sonnet-20241022-v2:0

  --- OpenAI ---
 export OPENAI_API_KEY="your-key"
 python heybro.py --provider openai --model gpt-4o

  --- View all-time stats ---
 > /stats

  --- Actual AWS Bedrock cost this month (Cost Explorer, requires ce:GetCostAndUsage) ---
 > /aws-cost

  --- MCP tool servers (stdio) ---
 fs (@modelcontextprotocol/server-filesystem, scoped to cwd), gcr (git-codereview),
 memory (persistent knowledge graph across sessions), desktop-commander (terminal +
 file editing), and bash (@ag-bash/mcp-server, sandboxed bash with 70 agentic tools)
 are registered automatically the first time you run heybro for a given --provider.
 Remove any with /mcp remove <name>; that sticks across future runs.
 > /mcp list
 > /mcp tools
 > /mcp remove bash

 > /mcp add fs npx -y @modelcontextprotocol/server-filesystem /tmp
> /mcp list          # confirm it says "connected"
> /mcp tools         # see read_file, list_directory, etc.
> list the files in /tmp

  --- Offline MCP test server (no network/npm needed) ---
 > /mcp add test env/bin/python3 src/test_mcp_server.py
 > /mcp tools
 > what is 17 plus 25?

 > /mcp add gcr npx -y git-codereview
> /mcp tools
> review the staged changes in 

git diff | python heybro.py --provider moonshot --single -
or, combine an instruction with piped context:
git diff | python heybro.py --single "Review this diff for bugs"

 git diff | python heybro.py --provider moonshot --single -

Bedrock policy 

  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": "arn:aws:bedrock:*::foundation-model/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ce:GetCostAndUsage"
      ],
      "Resource": "*"
    }
  ]

sed -n '492,560p' clis/heybro.py | python heyCli.py --single "Review this function:"

review() {
  local dir="${1:-.}"
  local provider="${2:-bedrock}"
  (cd "$dir" && git diff) | ../env/bin/python ..heyCli.py --provider "$provider" --single -
}

Inference ARN:                                                                                                        │
│ arn:aws:bedrock:ap-south-1:<Account-id>:inference-profile/apac.anthropic.claude-3-5-sonnet-20240620-v1:0 
arn:aws:bedrock:ap-south-1:<Accunt-id>:application-inference-profile/
eg7krioj0qsm-j0qsm-hfihewi8892snnk=6ardjugw2agr=ka 