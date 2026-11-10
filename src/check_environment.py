"""Checks that everything the demo needs answers, before a rehearsal or the demo itself: one line per check, OK or
FAILED, and exit code 1 if anything failed.

    uv run python src/check_environment.py

Checks the chat UI, API Management (model API and the notes MCP server as the signed-in user), the notes server's own
health, LiteLLM's readiness, and that LiteLLM lists the Microsoft Learn server. Read-only; never prints a key.
"""

import json
import subprocess
import urllib.error
import urllib.request

from gateway_admin import Gateway, azd_values, read_secret

INITIALIZE = {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "check", "version": "1"}}


def http(method: str, url: str, token: str = "", body: dict | None = None) -> tuple[int, str]:
    headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, response.read().decode(errors="replace")
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode(errors="replace")
    except (urllib.error.URLError, TimeoutError) as error:
        return 0, str(getattr(error, "reason", error))


def user_token(scope: str) -> str:
    command = ["az", "account", "get-access-token", "--scope", scope, "--query", "accessToken", "-o", "tsv"]
    return subprocess.run(command, capture_output=True, text=True, check=True).stdout.strip()


def report(name: str, passed: bool, detail: str) -> bool:
    print(f"{'OK    ' if passed else 'FAILED'}  {name:38} {detail}", flush=True)
    return passed


def check_apps(values: dict[str, str]) -> list[bool]:
    chat_health = values["CHAT_UI_URL"].rstrip("/") + "/api/health"
    notes_health = values["NOTES_MCP_URL"].removesuffix("/mcp") + "/health"
    return [
        report("Chat UI", http("GET", chat_health)[0] == 200, values["CHAT_UI_URL"]),
        report("Notes server health", http("GET", notes_health)[0] == 200, ""),
    ]


def check_apim(values: dict[str, str]) -> list[bool]:
    token = user_token(values["APIM_GATEWAY_SCOPE"])
    initialize = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": INITIALIZE}
    notes_url = values["APIM_MCP_NOTES_URL"]

    status, _ = http("GET", values["APIM_MODELS_URL"].rstrip("/") + "/models", token)
    results = [report("APIM model API (user's token)", status == 200, f"HTTP {status}")]
    status, text = http("POST", notes_url, token, initialize)
    blocked = "AccessBlockedByGateway" in text
    detail = "blocked in Agent 365" if blocked else f"HTTP {status}"
    results.append(report("APIM notes MCP server (user's token)", status == 200 and not blocked, detail))
    status, _ = http("POST", notes_url, "", initialize)
    results.append(report("APIM refuses a call without a token", status == 401, f"HTTP {status}"))
    return results


def check_litellm(values: dict[str, str]) -> list[bool]:
    status, _ = http("GET", values["LITELLM_URL"].rstrip("/") + "/health/readiness")
    results = [report("LiteLLM readiness", status == 200, f"HTTP {status}")]
    key = read_secret(values["KEY_VAULT_NAME"], "litellm-key-demo-probe")
    if not key:
        return [
            *results,
            report("LiteLLM lists MS_Learn_LiteLLM", False, "probe key missing: run src/configure_litellm.py"),
        ]
    servers = Gateway(values["LITELLM_URL"], key).call("GET", "/v1/mcp/server")
    names = sorted(server.get("server_name", "") for server in servers)
    return [*results, report("LiteLLM lists MS_Learn_LiteLLM", "MS_Learn_LiteLLM" in names, f"servers: {names}")]


def main() -> None:
    values = azd_values()
    results = [*check_apps(values), *check_apim(values), *check_litellm(values)]
    if not all(results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
