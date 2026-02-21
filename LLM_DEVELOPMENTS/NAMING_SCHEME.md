# Naming Scheme Preferences for Future AI Agents

## Purpose
This document captures the user's preferred naming patterns for projects, branches, folders, and task artifacts. Future AI agents must treat this as a working standard unless the user explicitly overrides it.

## Core Style Rules
1. Use **clear, descriptive names** over generic names.
2. Prefer **topic-focused folders** inside `LLM_DEVELOPMENTS`.
3. Keep artifact names **short but explicit**.
4. Use **underscores** for multi-word file names where readability matters.
5. Match user-provided capitalization exactly when user specifies it.

## Folder Naming Preferences
- Root context docs should live in `LLM_DEVELOPMENTS`.
- For a specific workstream, create a dedicated subfolder using a descriptive domain-style name.
- Example used by user preference:
  - `LLM_DEVELOPMENTS/POS_TOKEN_and_EDGE_RELAY/`

## Document/File Naming Preferences
- Main context PDF should use concise descriptive name.
- Current accepted name:
  - `POS_token_and_edge_relay.pdf`
- Supporting script names should be explicit and functional.
  - Example: `generate_pdf.py`

## Branch Naming Preferences
Observed accepted branch patterns from this project:
- `fix/app-install`
- `cline-codex-v1`
- `cline-codex-v2`
- `kilo-codex-v1`

Practical guidance:
- Use purpose + iteration suffix when relevant (e.g., `-v1`, `-v2`).
- Keep branch names human-readable and tied to task scope.

## Task / Commit Naming Preferences
User accepts concise imperative commit messages with scope prefix patterns such as:
- `feat(relay): ...`
- `feat(ui): ...`
- `chore(security): ...`
- `docs(llm): ...`

Guideline:
- Include scope in parentheses where possible.
- Keep subject specific to one intent.

## LLM Handoff Packaging Preference
For significant multi-step work:
1. Keep a markdown source document.
2. Generate a PDF from that source.
3. Store both in a clearly named topic folder under `LLM_DEVELOPMENTS`.
4. Include the generation script in the same folder for reproducibility.

## Enforced Convention for This Repository (current)
- Keep POS token/relay handoff assets under:
  - `LLM_DEVELOPMENTS/POS_TOKEN_and_EDGE_RELAY/`
- Expected files in that folder:
  - `POS_token_and_edge_relay.md`
  - `POS_token_and_edge_relay.pdf`
  - `generate_pdf.py`

## Change Control
If the user gives a new naming preference in chat, future agents should:
1. Update this document.
2. Apply the new convention in subsequent artifacts.
3. Avoid retroactive renaming unless asked.
