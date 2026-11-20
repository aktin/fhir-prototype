#!/usr/bin/env bash
# Sums the token usage of all Claude reviews in a repository.
# Reads the JSON that the workflow hides in each usage comment, so it keeps
# working after the run artifacts have expired.
# Usage: claude-usage-stats.sh [OWNER/REPO]   (default: current repo)
set -euo pipefail

repo=${1:-$(gh repo view --json nameWithOwner --jq .nameWithOwner)}

gh api --paginate "repos/$repo/issues/comments" \
  --jq '.[] | .body | select(startswith("<!-- claude-usage ")) | capture("^<!-- claude-usage (?<j>.*) -->").j' |
  jq -s '
    map(fromjson) | {
      reviews: length,
      prs: (map(.pr) | unique | length),
      total_cost_usd: (map(.total_cost_usd) | add // 0 | . * 100 | round / 100),
      input_tokens: (map(.usage.input_tokens) | add // 0),
      cache_creation_input_tokens: (map(.usage.cache_creation_input_tokens) | add // 0),
      cache_read_input_tokens: (map(.usage.cache_read_input_tokens) | add // 0),
      output_tokens: (map(.usage.output_tokens) | add // 0),
      per_pr: (group_by(.pr) | map({pr: .[0].pr, runs: length, cost_usd: (map(.total_cost_usd) | add | . * 10000 | round / 10000)}))
    }'
