"""Shows Agent 365's per-tool control on a LiteLLM gateway: every few seconds, it lists Microsoft Learn's tools through
LiteLLM and calls each one with a harmless query, printing ALLOWED or REFUSED per tool.

    uv run python src/litellm_tools_probe.py            # a round every few seconds until Ctrl+C
    uv run python src/litellm_tools_probe.py --once

Disable one tool on "MS_Learn_LiteLLM" in the admin center: within seconds it shows as REFUSED while the others stay
ALLOWED. The calls use the probe team's key from Key Vault (src/configure_litellm.py). Never prints a key.
"""

import argparse
import os
import time
from datetime import datetime

from gateway_admin import Gateway, azd_values, read_secret

SERVER_NAME = "MS_Learn_LiteLLM"
PROBE_KEY_SECRET = "litellm-key-demo-probe"
INTERVAL_SECONDS = 2  # a round itself takes a few seconds: each tool call goes to Microsoft Learn
HARMLESS_CALLS = {
    "microsoft_docs_search": {"query": "Azure API Management MCP server"},
    "microsoft_code_sample_search": {"query": "DefaultAzureCredential", "language": "python"},
    "microsoft_docs_fetch": {"url": "https://learn.microsoft.com/azure/api-management/"},
}


def server_id(gateway: Gateway) -> str:
    """The id of the Microsoft Learn server, as the probe key sees it."""
    servers = gateway.call("GET", "/v1/mcp/server")
    return next(server["server_id"] for server in servers if server.get("server_name") == SERVER_NAME)


def call_tool(gateway: Gateway, server: str, tool: str) -> str:
    """ALLOWED, or REFUSED with the start of the gateway's message."""
    body = {"server_id": server, "name": tool, "arguments": HARMLESS_CALLS[tool]}
    try:
        result = gateway.call("POST", "/mcp-rest/tools/call", body)
    except RuntimeError as error:
        return f"REFUSED  {str(error)[:110]}"
    if isinstance(result, dict) and result.get("isError"):
        return f"REFUSED  {str(result.get('content'))[:110]}"
    return "ALLOWED"


def probe_round(gateway: Gateway, server: str) -> None:
    listed = gateway.call("GET", f"/mcp-rest/tools/list?server_id={server}")
    tools = listed.get("tools", []) if isinstance(listed, dict) else listed
    print(f"{datetime.now():%H:%M:%S}  listed: {sorted(tool['name'] for tool in tools) or '(none)'}", flush=True)
    for tool in HARMLESS_CALLS:
        print(f"          {tool:30} {call_tool(gateway, server, tool)}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="one round, then exit")
    arguments = parser.parse_args()

    values = {**azd_values(), **os.environ}
    key = read_secret(values["KEY_VAULT_NAME"], PROBE_KEY_SECRET)
    if not key:
        raise SystemExit("The probe key is missing from Key Vault: run src/configure_litellm.py first.")
    gateway = Gateway(values["LITELLM_URL"], key)
    server = server_id(gateway)
    while True:
        probe_round(gateway, server)
        if arguments.once:
            return
        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
