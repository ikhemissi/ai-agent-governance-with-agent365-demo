# AGENTS.md — AI agent governance with Agent 365 and AI gateways

This repository is a **demo**: a live, 14-minute walk-through of Agent 365 governing MCP servers exposed through AI
gateways (Azure API Management for the agent, LiteLLM shown next to it), run from [docs/DEMO-RUNBOOK.md](docs/DEMO-RUNBOOK.md).
Nothing here is production code. Read [README.md](README.md) first.

## How the demo works

- **The runbook is the product:** [docs/DEMO-RUNBOOK.md](docs/DEMO-RUNBOOK.md) is written for someone else to run:
  pre-flight checks, each step with its clicks, commands and expected output, a fallback per step, and the reset.
  Keep it in step with the code and the infrastructure.
- **Measured values come from the spikes:** every timing the runbook quotes (discovery, block, unblock) links to the
  experiment that measured it in one of the two spike repositories ([README.md](README.md), "Evidence behind this
  demo"). A new measurement goes to the local rehearsal notes, not into the repository.
- **Evidence queries:** [docs/queries.md](docs/queries.md) holds the queries for the records the demo shows; check the
  table names in the workspace before changing them.
- **Rehearsal notes stay local:** times, request and trace ids, tenant and user names go to `local/` (git-ignored),
  never into the repository.
- **Ask before** any tenant-level change (Agent 365 connections, consents, app registrations, role assignments,
  Conditional Access) and before anything that costs money beyond the deployed stack; propose a default.

## Rules

- **Never commit secrets**, keys, tokens, tenant or subscription IDs, object ids, user names, or the URLs of the
  deployed environment. Use your own Entra identity (Azure CLI) and managed identities; keys live in Key Vault; local
  settings go to `.env` (git-ignored). Screenshots for the repository are redacted.
- **Public content:** neutral, factual, dated observations; no internal, customer or tenant details.
- Scripts in `src/` stay small, one purpose each, with their purpose at the top, explicit names and settings from the
  azd environment.
- **Commits:** conventional commits (`feat(demo): …`, `docs(runbook): …`, `feat(infra): …`), ending with the trailer
  `Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>`.

## Infrastructure

- **One Terraform root** (`infra/`, one state), one file per part. The files from shared building blocks (`main.tf`, `providers.tf`, `network.tf`, `monitoring.tf`, `key-vault.tf`, `container-registry.tf`, `container-apps-environment.tf`, `foundry.tf`, `postgres.tf`, `litellm-gateway.tf`, `apim-gateway.tf`, `notes-mcp.tf`, `chat-ui.tf`), the modules in `infra/modules/` and the hook steps in `infra/hooks/<event>/` stay as they are, so that their improvements can be merged in later. The demo's own resources are `infra/apim-mcp.tf` and `infra/apim-purview.tf` (templates in `infra/policies/`); how the optional parts connect is `infra/connections.tf`.
- **LiteLLM settings** (MCP servers, teams, virtual keys) go through LiteLLM's admin API, in a script (`src/configure_litellm.py`), not into its configuration file.
- **API Management settings** (MCP servers and their policies) are Azure resources: register them in the demo's own file (`infra/apim-mcp.tf`, azapi for the MCP APIs), never by hand in the portal, so that a re-provision does not undo them. Never set `accessState` there: it is Agent 365's block.
- **Notes MCP server:** `infra/notes-mcp.tf` and `services/notes-mcp` come from a shared building block; its checks: `uv run --no-project --with-requirements requirements.txt --with-requirements requirements-dev.txt pytest` in `services/notes-mcp`.
- **Chat UI:** `infra/chat-ui.tf` and `services/chat-ui` come from a shared building block too: change what it shows and tells the model with its settings (`CHAT_UI_TITLE`, `CHAT_UI_INTRO`, `CHAT_UI_INSTRUCTIONS`), not its files. Its checks: `npm ci && npm run typecheck && npm run lint && npm test && npm run build` in `services/chat-ui`.
- **Before every `azd provision`:** `azd provision --preview` (one plan for the whole root), and read it.

## Code humans can maintain

Everything here must be maintainable by human developers, whoever (or whatever) wrote it. A developer new to the project understands a module in minutes and changes it with confidence.

- **Simple and explicit over clever:** no metaprogramming, hidden magic or generic frameworks; an abstraction only when a second real use exists.
- **One role per unit:** a module states its role in one or two lines at the top; a function does one thing and fits on a screen (about 40 lines), otherwise split it into named steps.
- **Names carry meaning:** domain words, full words, booleans that read as questions; no single letters except short loop indices.
- **Flat control flow:** early returns, named intermediate values, no dense one-liners or formatter opt-outs.
- **Comments explain why** (the decision, the constraint, a link to the design or ADR), never what the code already says.
- **Consistency beats preference:** follow the patterns already in the repository before introducing a new one.
- **Few dependencies:** ask before adding one; prefer the standard library and what is already used.
- **Tests read as documentation:** named after the behaviour or spec scenario they check; arrange, act, assert.
- **Read your diff as a reviewer before calling a change done;** if a piece cannot be explained simply, rewrite it.

## Known pitfalls

- None recorded yet.
Add a pitfall here every time something bites you, in one line: the symptom, then what to do.
