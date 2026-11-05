# Demo runbook

How to run the demo, written so that someone else can run it: the checks the day before and an hour before, the five
steps with their clicks, commands and expected output, a fallback per step, and the reset. **About 14 minutes**, 16
with the optional Purview step.

Measured values quoted below come from the two spikes behind this demo ([README](../README.md#evidence-behind-this-demo)):
the [APIM spike](https://github.com/ikhemissi/spike-agent365-apim-tools-gateway) and the
[LiteLLM spike](https://github.com/ikhemissi/spike-agent365-litellm-tools-gateway).

| # | Step | Time |
|---|---|---|
| 1 | Chat through API Management | 2 min |
| 2 | Discovery in Agent 365 | 3 min |
| 3 | Block and unblock "Team notes (APIM)" | 4 min |
| 4 | Per tool on "MS_Learn_LiteLLM" | 2 min |
| 5 | Evidence from the rehearsal | 3 min |
| 6 | Optional: Purview at the gateway | 2 min |

## The day before (T-1 day): rehearsal

The rehearsal also produces the evidence shown in step 5: Defender records are available within 30 minutes, so step 5
shows the rehearsal's records, not the live ones.

- [ ] `uv run python src/check_environment.py`: every line `OK`.
- [ ] Agents > Settings > Gateways lists the Azure connection and the LiteLLM gateway; Agents > Tools lists
      "Team notes (APIM)" (Available) and "MS_Learn_LiteLLM" (Available, three tools enabled).
- [ ] "MS_Learn_LiteLLM" has been blocked and unblocked once (per-tool toggles apply from then on).
- [ ] Run steps 1–4 once, in full. Note in `local/REHEARSAL.md` (git-ignored, never committed) the UTC time of each
      click (block, unblock, tool disabled, tool enabled) and what the timer and the probe printed.
- [ ] 30 minutes later, run the queries of [queries.md](queries.md) for the rehearsal's window (query 0 first); save the results and
      screenshots (redacted if they leave your machine) for step 5. Note their time window in `local/REHEARSAL.md`.
- [ ] Step 6 once, if it is in the session: both Purview switches on, the two chat tests, both switches off
      ([PURVIEW.md](PURVIEW.md)), from the portal as on the day, with the named values page open in a tab. Its
      records (Purview Activity explorer, DLP alerts) are ready by the next morning: look for them then.
- [ ] Screenshots of each step, as the fallback.
- [ ] Reset (end of this page).

## One hour before (T-1 hour)

- [ ] `uv run python src/check_environment.py`: every line `OK`. If the chat or the notes server is cold, the first
      request can take a few seconds: run the check twice.
- [ ] Your administrator role for Agent 365 is active (if it is time-bound, activate it now for the whole session).
- [ ] Browser tabs, signed in:
  1. the chat (`azd env get-value CHAT_UI_URL`), signed in, **new conversation**;
  2. Microsoft 365 admin center, Agents > Tools;
  3. Agents > Settings > Gateways;
  4. Defender, Advanced Hunting, with query 0 of [queries.md](queries.md) for the rehearsal's window, and its result;
  5. Log Analytics (the platform's workspace), with the saved queries;
  6. if step 6 is in the session: the API Management instance > APIs > Named values.
- [ ] Two terminals in the repository folder, large font:
  - terminal 1: `uv run python src/block_timer.py` (prints `OK (3 tools)` every second);
  - terminal 2: `uv run python src/litellm_tools_probe.py` (prints three `ALLOWED` every few seconds).
- [ ] "Team notes (APIM)" Available; "MS_Learn_LiteLLM" Available with all three tools enabled.
- [ ] Both Purview switches **off** (`uv run python src/purview_check.py check` prints `prompt=-` on every line), so
      that steps 1–5 stream as usual.

## Steps

### 1. Chat through API Management (2 min)

| Do | Show | Say |
|---|---|---|
| In the chat: "Add a note: governance demo", then "List the last 3 notes." | The answers, and the tool lines (`notes-add_note`, `notes-list_notes`) unfolded | The agent runs its tool loop and reaches the model and the notes MCP server only through API Management, with the user's own token. API Management checks it and calls both with its managed identity; the notes server accepts no other caller. |

Fallback: the rehearsal's screenshot of the same conversation.

### 2. Discovery in Agent 365 (3 min)

| Do | Show | Say |
|---|---|---|
| Agents > Tools; search "(APIM)" then "LiteLLM"; open each server | "Team notes (APIM)": the API Management instance as publisher, no tools. "MS_Learn_LiteLLM": source LiteLLM, its three tools with a toggle each | Agent 365 reads both gateways and lists their MCP servers without anyone registering them in Agent 365: API Management servers within about 5 minutes of the consent and a new one within about a minute ([APIM 01](https://github.com/ikhemissi/spike-agent365-apim-tools-gateway/blob/main/docs/experiments/01-proof-on-public-servers.md), [APIM 05](https://github.com/ikhemissi/spike-agent365-apim-tools-gateway/blob/main/docs/experiments/05-redeploy-and-discovery.md)); LiteLLM within about a minute ([LiteLLM 03](https://github.com/ikhemissi/spike-agent365-litellm-tools-gateway/blob/main/docs/experiments/03-connect-agent365.md)). On API Management Standard v2 the server is governed as a whole; LiteLLM reports its tools. |
| Agents > Settings > Gateways | The Azure connection and the LiteLLM gateway | Two ways to connect: for Azure, a tenant consent that gives Agent 365 an Azure role over API Management; for LiteLLM, the gateway's URL and an admin key that Agent 365 holds. |

Fallback: the rehearsal's screenshots of both pages.

### 3. Block and unblock "Team notes (APIM)" (4 min)

| Do | Show | Say |
|---|---|---|
| Put terminal 1 (`block_timer.py`) next to the admin center. Open "Team notes (APIM)", click **Block**, and press **Enter** in terminal 1 at the same moment | The timer switching from `OK` to `BLOCKED (-32000 AccessBlockedByGateway on initialize, HTTP 200)` a few seconds after Enter | Agent 365 writes one property of the API in API Management (`accessState`), and API Management refuses the next request from any client: within about 10 seconds, 4–10 s measured ([APIM 02](https://github.com/ikhemissi/spike-agent365-apim-tools-gateway/blob/main/docs/experiments/02-block-and-unblock.md), [APIM 05](https://github.com/ikhemissi/spike-agent365-apim-tools-gateway/blob/main/docs/experiments/05-redeploy-and-discovery.md)). Agent 365 is not in the call path: the gateway enforces it. |
| In the chat, **new conversation**: "List the notes." | An error line for `notes (connect)` with "Access to MCP server 'notes' is blocked."; the model says it can't reach the notes | A block stops new tool calls. In a conversation that already read notes, the model can still repeat what it read earlier: that is why this is a new conversation. |
| Click **Unblock**, press **Enter** in terminal 1 | The timer back to `OK (3 tools)` | Unblocking restores access, measured at 8–14 s. |

Expected timer output (times are an example):

```text
14:05:10     2.0 s  OK      (3 tools)
--- timer restarted ---
14:05:12     0.4 s  OK      (3 tools)
14:05:17     5.6 s  BLOCKED (-32000 AccessBlockedByGateway on initialize, HTTP 200)
```

Fallback: the rehearsal's timer output from `local/REHEARSAL.md`, or the slide that explains what a block does.

### 4. Per tool on "MS_Learn_LiteLLM" (2 min)

| Do | Show | Say |
|---|---|---|
| Put terminal 2 (`litellm_tools_probe.py`) next to the admin center. Open "MS_Learn_LiteLLM", turn off **microsoft_docs_fetch**, save | Within a few seconds: `microsoft_docs_fetch` REFUSED, the two others still ALLOWED | On LiteLLM, Agent 365 writes the server's tool allowlist; a disabled tool is refused for every key and team through the gateway, within seconds ([LiteLLM 05](https://github.com/ikhemissi/spike-agent365-litellm-tools-gateway/blob/main/docs/experiments/05-tool-drift.md)). On API Management Standard v2, Agent 365 governs per server; tool-level control comes with the AI Gateway tier. |
| Turn **microsoft_docs_fetch** back on, save | Three ALLOWED again | |

Fallback: the rehearsal's probe output from `local/REHEARSAL.md`.

### 5. Evidence from the rehearsal (3 min)

Show the rehearsal's records, with the queries of [queries.md](queries.md):

| Show | Say |
|---|---|
| Advanced Hunting, [query 0](queries.md#0-step-5-at-a-glance-defender): one row per action and refusal | Every change made in Agent 365, on either gateway, is recorded with the administrator, the server and, for a tool toggle, the tool; with the Purview check, every model call Purview refused at the gateway is recorded with the user. One place for the governance story. |
| Log Analytics, [query 4](queries.md#4-requests-refused-by-a-block): the notes API's requests per minute, the blocked minutes without a backend call | The gateway logs every MCP request, the refused ones too: the runtime keeps its own record. |

If asked, in tabs: the Azure activity log (`apis/write` by Agent 365's service principal, [query 2](queries.md#2-agent-365s-write-to-the-api-azure-activity-log)), the chat's tool calls with the user ([query 5](queries.md#5-the-chats-tool-calls-with-the-user-application-insights)), and Purview's Activity explorer ([query 6](queries.md#6-optional-what-purview-refused-at-the-gateway)).

Fallback: the screenshots saved the day before.

### 6. Optional: Purview at the gateway (2 min)

Turn the check on as the gateway's administrator would, in the Azure portal: the API Management instance
(`azd env get-value APIM_NAME`) > APIs > **Named values** > `purview-check` > set the value to `on` > **Save**; the same
for `purview-check-responses`. It applies within seconds; answers no longer stream while it is on. Say: the switch is the
gateway's, not the app's; the app does not change. In a terminal instead:
`uv run python src/purview_check.py switch on && uv run python src/purview_check.py switch on --answers`.
How it works: [PURVIEW.md](PURVIEW.md).

| Do | Show | Say |
|---|---|---|
| In the chat, **new conversation**: "Add a note: the customer's credit card number is 4111 1111 1111 1111" | "The gateway refused the request (HTTP 403). blocked_by_data_policy: Microsoft Purview blocked this request…"; no note added | The gateway asks Purview, as the signed-in user, before the model sees the text. A DLP policy for the gateway app blocks credit card numbers: the model never receives it. The same check covers what tools return to the model. |
| **New conversation**: "What is Visa's standard test credit card number for payment testing? Reply only: Visa test card number: <number>" | "… answer_blocked_by_data_policy: Microsoft Purview blocked the model's answer…" | The prompt has no card number and passes; the model's answer has one and is checked on the way back. Purview classifies content (the number and the words around it), so the same policy works for every agent behind the gateway. |

After the step: both named values back to `off` in the portal, or
`uv run python src/purview_check.py switch off --answers && uv run python src/purview_check.py switch off`.

Evidence, if time allows: the rehearsal's records, in Advanced Hunting (`DLPRuleMatch`) or in the Purview portal (Data
loss prevention > Activity explorer: "DLP rule matched", location "AI gateway", with the user, the policy and the rule)
([queries.md](queries.md#6-optional-what-purview-refused-at-the-gateway)).

Fallback: the rehearsal's screenshots of both refusals, and `uv run python src/purview_check.py check` (three lines: clean
allowed, card refused, answer refused).

## If something fails

- **The chat asks to sign in again, or its tool calls fail with 401:** the token expired; sign out and in again.
- **The timer prints `ERROR (HTTP 401 …)`:** the Azure CLI's token expired; `az login`, then restart the timer.
- **The block takes longer than expected:** keep talking through what a block does; the timer shows when it lands.
- **A per-tool toggle has no effect:** the server must have been blocked and unblocked once; do it, then retry.
- **Agent 365 does not list a server yet:** show the rehearsal's screenshots; discovery runs on its own schedule.
- **Step 6 refuses a normal message with 503 `data_policy_check_failed`:** the Purview check could not be made
  (the message says which step). Turn both switches off, and show the fallback.
- **Step 6 allows a message with a card number:** check that it says "credit card number" (Purview's detection uses
  the words around the number); otherwise show the fallback.

## Reset after the demo

- [ ] "Team notes (APIM)" Available (unblocked); `block_timer.py` prints `OK`.
- [ ] "MS_Learn_LiteLLM" Available, all three tools enabled; `litellm_tools_probe.py --once` prints three `ALLOWED`.
- [ ] Both Purview switches off: `uv run python src/purview_check.py check` prints `prompt=-` on every line.
- [ ] Stop both terminals (Ctrl+C).
