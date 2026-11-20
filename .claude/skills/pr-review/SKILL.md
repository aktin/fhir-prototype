---
name: pr-review
description: Review one pull request of fhir-prototype in a single pass and post one-sentence inline comments. Use when invoked as /pr-review OWNER/REPO NUMBER, usually from the Claude PR Review workflow.
allowed-tools: Read, Grep, Glob, Bash(gh pr view *), Bash(gh pr diff *), Bash(gh api repos/*/pulls/*/comments *), mcp__github_inline_comment__create_inline_comment
---

# PR review

`$ARGUMENTS` is `OWNER/REPO NUMBER`.

## Budget

One pass, one agent, no subagents. At most 8 comments, pick the ones with the most impact. Do not run tests, linters or installs, CI does that. Read a file outside the diff only when a finding depends on it.

## Project context

Python prototype that turns FHIR bundles (ICU data) into rows of the i2b2 table `observation_fact` for AKTIN. Mapping lives only in `src/fhir_prototype/icu_mapping.json`, the code applies it and must stay generic, so a hardcoded code, profile URL or concept in Python is a finding. Work is test driven, changed behaviour without a test is a finding. Test fixtures are synthetic, real patient data in the repo is a blocker.

## Steps

1. `gh pr view NUMBER --json title,body,headRefOid` for intent and linked issue.
2. `gh pr diff NUMBER` is the scope. Skip `uv.lock` and `*.md`. For exact line numbers, Read the changed file, the checkout is the PR head.
3. `gh api repos/OWNER/REPO/pulls/NUMBER/comments --paginate --jq '.[]|"\(.path):\(.line // .original_line) \(.body[0:100])"'` and skip any finding an existing comment already makes, match on content.
4. Read the diff with two lenses at once.
   Correctness: bugs, missed edge cases, wrong rows in `observation_fact`, missing or weak tests, swallowed errors.
   Simplicity: dead code, speculative generality, duplication, a shorter equivalent, logic that belongs in `icu_mapping.json`.
   Report only what you would defend in front of the senior developer. No praise, no nits ruff already catches.
5. Post each finding right away with `create_inline_comment`, `confirmed: true`, `side: RIGHT`. `line` must be an added or context line of the diff, for a range add `startLine`. If GitHub rejects the line, use the nearest diff line in that file. A finding with no diff line goes into the final message instead.
6. Comment body is exactly one sentence, action first, then a comma, then the reason. No tag, no severity label, no semicolon, no dash, no bold. A `suggestion` block may follow when the fix is a drop-in replacement of at most 5 lines.
   Example: `Read the RASS code from icu_mapping.json, the mapping file is the single source of truth and a constant here breaks the next profile.`

## Final message

Exactly one line, nothing else: `findings: N` and, only if there are any, ` | unanchored: <one sentence each>`.
