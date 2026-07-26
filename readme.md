Install dependencies
pip install openai rich boto3

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
    }
  ]

sed -n '492,560p' clis/heybro.py | python heyCli.py --single "Review this function:"

review() {
  local dir="${1:-.}"
  local provider="${2:-bedrock}"
  (cd "$dir" && git diff) | ../env/bin/python ..heyCli.py --provider "$provider" --single -
}
