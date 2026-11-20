#!/usr/bin/env bash
# Extracts token usage from the claude-code-action execution file.
# Usage: claude-usage.sh EXECUTION_FILE OUT_DIR
# Needs PR, SHA, RUN_ID, RUN_URL in the environment. Writes OUT_DIR/claude-usage.json and OUT_DIR/claude-usage.md.
set -euo pipefail

exec_file=$1
out_dir=$2
mkdir -p "$out_dir"

jq --arg pr "$PR" --arg sha "$SHA" --arg run "$RUN_ID" '
  [.[] | select(.type == "result")] | last | {
    pr: ($pr | tonumber), sha: $sha, run_id: ($run | tonumber),
    finished_at: (now | todate),
    status: .subtype,
    result: (.result // ""),
    num_turns, duration_ms, total_cost_usd,
    usage: (.usage | {input_tokens, cache_creation_input_tokens, cache_read_input_tokens, output_tokens}),
    models: (.modelUsage // {} | with_entries(.value |= {inputTokens, cacheCreationInputTokens, cacheReadInputTokens, outputTokens, costUSD}))
  }' "$exec_file" > "$out_dir/claude-usage.json"

jq -r --arg url "$RUN_URL" '
  def n: tostring | until(test("^[0-9]{4}") | not; sub("(?<a>[0-9])(?<b>[0-9]{3})(?<c>$|,)"; "\(.a),\(.b)\(.c)"));
  def usd: . * 10000 | round / 10000 | tostring;
  "<!-- claude-usage \(tojson | gsub("--"; "- -")) -->",
  "**Claude review** `\(.sha[0:7])`: \(.result | if . == "" then .status else . end)",
  "",
  "| Model | Input | Cache write | Cache read | Output | USD |",
  "|---|---:|---:|---:|---:|---:|",
  (.models | to_entries[] | "| \(.key) | \(.value.inputTokens | n) | \(.value.cacheCreationInputTokens | n) | \(.value.cacheReadInputTokens | n) | \(.value.outputTokens | n) | \(.value.costUSD | usd) |"),
  "",
  "\(.num_turns) turns, \(.duration_ms / 1000 | round) s, total \(.total_cost_usd | usd) USD at API list prices, [run \(.run_id)](\($url))"
' "$out_dir/claude-usage.json" > "$out_dir/claude-usage.md"
