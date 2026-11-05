# Evidence queries

Queries for the records the demo shows in step 5 ([runbook](DEMO-RUNBOOK.md)). Set the time window to the rehearsal's
(`local/REHEARSAL.md`). Time filters in the queries are UTC; the Defender portal shows results in your time zone,
Log Analytics and the Azure CLI in UTC. Table names were checked in the platform's Log Analytics
workspace on 2026-11-04.

| Record | Where | Query |
|---|---|---|
| The administrator's actions on both gateways (block, unblock, tool toggles) | Microsoft Defender, Advanced Hunting | [1](#1-the-administrators-actions-defender) |
| Agent 365's write to the API | Azure activity log | [2](#2-agent-365s-write-to-the-api-azure-activity-log) |
| Each MCP request, refused ones without a backend call | Log Analytics, API Management gateway logs | [3](#3-each-request-to-the-notes-server-api-management-gateway-logs), [4](#4-requests-refused-by-a-block) |
| The chat's tool calls with the user | Log Analytics, Application Insights | [5](#5-the-chats-tool-calls-with-the-user-application-insights) |
| Optional: what Purview refused at the gateway | Microsoft Purview portal | [6](#6-optional-what-purview-refused-at-the-gateway) |

## 1. The administrator's actions (Defender)

Microsoft Defender portal > Hunting > Advanced hunting. Records arrive 10–30 minutes after the action.

```kusto
CloudAppEvents
| where Timestamp > ago(1d)
| where ActionType == "ApiEndpointCallEvent"
| where tostring(RawEventData) has "mcpservers"
| extend Path = tostring(parse_json(tostring(RawEventData.JsonPropertiesCollection))["url.path"])
| extend Gateway = extract(@"/agent365/([^/]+)/", 1, Path),
         Server = extract(@"/mcpservers/([^/]+)", 1, Path),
         Tool = extract(@"/tools/([^/]+)/", 1, Path),
         Change = case(Path endswith "/access/all", "server access",
                       Path endswith "/updateState", "server state",
                       Path endswith "/state", "tool state",
                       "other")
| project Timestamp, AccountDisplayName, Gateway, Change, Server, Tool
| order by Timestamp asc
```

One record per administrator action, with the administrator, the gateway (`apim` or `litellm`), the server and, for
a tool toggle, the tool:

| Action in Agent 365 | Gateway | Change | Server |
|---|---|---|---|
| Block or unblock "Team notes (APIM)" | `apim` | `server access` | `notes` (the API's name) |
| Block or unblock "MS_Learn_LiteLLM" | `litellm` | `server state` | the server's id in LiteLLM (`src/configure_litellm.py` prints it) |
| Turn a tool of "MS_Learn_LiteLLM" off or on | `litellm` | `tool state` | the same id, and the tool in `Tool` |

The records do not say which way the change went (blocked or unblocked, off or on): read it from the order of the
actions, from query 2 for API Management, or from the timer's and the probe's output.

## 2. Agent 365's write to the API (Azure activity log)

The activity log is not sent to the workspace; read it with the Azure CLI (or in the portal: the resource group >
Activity log, operation "Create or update API").

```bash
az monitor activity-log list --resource-group "$(azd env get-value AZURE_RESOURCE_GROUP)" --offset 1d \
  --query "[?operationName.value=='Microsoft.ApiManagement/service/apis/write' && status.value=='Succeeded'].{time:eventTimestamp, caller:caller, api:resourceId}" \
  -o table
```

Agent 365's writes have its service principal's object id as caller (a GUID, where a person's writes show their user
name). The API's current state: `accessState` on the API, read with management API version 2025-09-01-preview.

## 3. Each request to the notes server (API Management gateway logs)

Log Analytics, the platform's workspace (`AzureDiagnostics`, category `GatewayLogs`).

```kusto
AzureDiagnostics
| where TimeGenerated > ago(1d)
| where ResourceProvider == "MICROSOFT.APIMANAGEMENT" and Category == "GatewayLogs"
| where apiId_s == "notes"
| project TimeGenerated, apiType_s, operationId_s, method_s, responseCode_d, backendResponseCode_d,
          CallerIPAddress, userAgent_s, DurationMs, CorrelationId
| order by TimeGenerated desc
```

Each MCP request is one record: API `notes`, type `mcp`, operation `passThroughMcp`, the caller's IP address and user
agent, the status, and the backend call.

## 4. Requests refused by a block

The same records, per minute: during a block, requests are answered by API Management itself (status 200 with the
JSON-RPC error) and have no backend call.

```kusto
AzureDiagnostics
| where TimeGenerated > ago(1d)
| where ResourceProvider == "MICROSOFT.APIMANAGEMENT" and Category == "GatewayLogs"
| where apiId_s == "notes"
| summarize Requests = count(), WithBackendCall = countif(isnotempty(backendResponseCode_d)) by bin(TimeGenerated, 1m)
| order by TimeGenerated asc
```

## 5. The chat's tool calls with the user (Application Insights)

Log Analytics, the same workspace. The chat records one `chat run` span per question, with the signed-in user's object
id (`UserAuthenticatedId`), and one `MCP tools/call <tool>` span per tool call.

```kusto
let runs = AppDependencies
    | where TimeGenerated > ago(1d) and AppRoleName == "chat-ui" and Name == "chat run"
    | project OperationId, User = UserAuthenticatedId, Outcome = tostring(Properties["chat.outcome"]);
AppDependencies
| where TimeGenerated > ago(1d) and AppRoleName == "chat-ui" and Name startswith "MCP tools/call"
| project TimeGenerated, OperationId, Tool = tostring(Properties["gen_ai.tool.name"]),
          Server = tostring(Properties["chat.mcp.server"]), Success, DurationMs
| join kind=inner runs on OperationId
| project TimeGenerated, User, Tool, Server, Success, DurationMs, Outcome, OperationId
| order by TimeGenerated asc
```

## 6. Optional: what Purview refused at the gateway

With the Purview check of [PURVIEW.md](PURVIEW.md), each refusal is recorded in the Microsoft Purview portal (checked
the morning after a test, 2026-11-05):

- **Data loss prevention > Activity explorer**: activity "DLP rule matched", location "AI gateway" (the gateway app),
  enforcement plane "Application", with the user, the policy and the rule. One record per refused check (a prompt, a
  tool result or an answer).
- **Data loss prevention > Alerts**: "DLP policy match for applications", severity High (as set in the rule), with the
  user; location "ExtendedApplications".

The model calls themselves reach Foundry with API Management's identity, so the evidence of a check is the gateway's
DLP record above, with the user.

