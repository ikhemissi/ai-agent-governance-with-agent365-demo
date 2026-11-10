"""Configures the LiteLLM gateway for the demo. LiteLLM is not used by the chat: it stands next to API Management so
that the Agent 365 admin center shows a second gateway and its tools.

- registers Microsoft Learn's public MCP server as `MS_Learn_LiteLLM`, the name Agent 365 shows;
- creates the LiteLLM user `agent365` (proxy_admin) and its key, kept in Key Vault (agent365-gateway-key): the key
  you give Agent 365 when connecting the gateway, so that it can be revoked without touching the master key;
- creates a team `demo-probe` allowed to use that server, and its key in Key Vault (litellm-key-demo-probe), used by
  src/litellm_tools_probe.py;
- lists the server's tools with the probe key.

Idempotent. Reads the azd environment; uses your Azure CLI sign-in (Key Vault secrets officer). Never prints a key.
Adapted from the LiteLLM spike's src/01_configure_gateway.py and src/03_agent365_key.py.
    uv run python src/configure_litellm.py
"""

import os

from gateway_admin import Gateway, azd_values, read_secret, store_secret

# The name Agent 365 shows. LiteLLM allows only letters, digits, "_", "-" and "." (it is also the tools' prefix).
SERVER_NAME = "MS_Learn_LiteLLM"
SERVER_URL = "https://learn.microsoft.com/api/mcp"
AGENT365_USER = "agent365"
AGENT365_KEY_SECRET = "agent365-gateway-key"
PROBE_TEAM = "demo-probe"
PROBE_KEY_SECRET = "litellm-key-demo-probe"


def ensure_server(admin: Gateway) -> str:
    """Creates or updates the Microsoft Learn MCP server; returns its id."""
    settings = {
        "server_name": SERVER_NAME,
        "alias": SERVER_NAME,
        "description": "Microsoft Learn's public MCP server, through LiteLLM: search and read Microsoft's documentation.",
        "url": SERVER_URL,
        "transport": "http",
        "auth_type": "none",  # a public server
    }
    existing = [server for server in admin.call("GET", "/v1/mcp/server") if server.get("server_name") == SERVER_NAME]
    if existing:
        server_id = existing[0]["server_id"]
        admin.call("PUT", "/v1/mcp/server", {"server_id": server_id, **settings})
        print(f"MCP server '{SERVER_NAME}' updated ({server_id})")
        return server_id
    created = admin.call("POST", "/v1/mcp/server", settings)
    print(f"MCP server '{SERVER_NAME}' created ({created['server_id']})")
    return created["server_id"]


def ensure_agent365_key(admin: Gateway, vault: str) -> None:
    """The proxy_admin user Agent 365 acts as, and its key in Key Vault (blocking needs proxy_admin)."""
    users = admin.call("GET", "/user/list")
    existing = users.get("users", []) if isinstance(users, dict) else users
    if not any(user.get("user_id") == AGENT365_USER for user in existing):
        user = {
            "user_id": AGENT365_USER,
            "user_alias": "Agent 365",
            "user_role": "proxy_admin",
            "auto_create_key": False,
        }
        admin.call("POST", "/user/new", user)
        print(f"LiteLLM user '{AGENT365_USER}' created (proxy_admin)")
    if read_secret(vault, AGENT365_KEY_SECRET):
        print(f"Agent 365 key found in Key Vault ({AGENT365_KEY_SECRET})")
        return
    generated = admin.call("POST", "/key/generate", {"user_id": AGENT365_USER, "key_alias": "agent365-gateway"})
    store_secret(vault, AGENT365_KEY_SECRET, generated["key"])
    print(f"Agent 365 key generated and stored in Key Vault ({AGENT365_KEY_SECRET})")


def ensure_probe_key(admin: Gateway, vault: str, server_id: str) -> str:
    """A team allowed to use the Microsoft Learn server, and its key in Key Vault; returns the key."""
    permissions = {"object_permission": {"mcp_servers": [server_id]}}
    teams = [team for team in admin.call("GET", "/team/list") if team.get("team_alias") == PROBE_TEAM]
    if teams:
        team_id = teams[0]["team_id"]
        admin.call("POST", "/team/update", {"team_id": team_id, **permissions})
    else:
        team_id = admin.call("POST", "/team/new", {"team_alias": PROBE_TEAM, **permissions})["team_id"]
        print(f"Team '{PROBE_TEAM}' created ({team_id})")
    key = read_secret(vault, PROBE_KEY_SECRET)
    if key:
        return key
    key = admin.call("POST", "/key/generate", {"team_id": team_id, "key_alias": PROBE_TEAM})["key"]
    store_secret(vault, PROBE_KEY_SECRET, key)
    print(f"Probe key generated and stored in Key Vault ({PROBE_KEY_SECRET})")
    return key


def main() -> None:
    values = {**azd_values(), **os.environ}
    vault = values["KEY_VAULT_NAME"]
    admin_key = read_secret(vault, values["LITELLM_MASTER_KEY_SECRET_NAME"])
    if not admin_key:
        raise SystemExit(
            "The gateway's admin key is missing from Key Vault: provision the environment first (azd provision)."
        )

    admin = Gateway(values["LITELLM_URL"], admin_key)
    server_id = ensure_server(admin)
    ensure_agent365_key(admin, vault)
    probe_key = ensure_probe_key(admin, vault, server_id)

    listed = Gateway(values["LITELLM_URL"], probe_key).call("GET", f"/mcp-rest/tools/list?server_id={server_id}")
    tools = listed.get("tools", []) if isinstance(listed, dict) else listed
    print(f"Tools of '{SERVER_NAME}' through the gateway: {sorted(tool['name'] for tool in tools)}")
    print(f"\nFor the admin center: gateway URL {values['LITELLM_URL']}")
    print(f"Key: az keyvault secret show --vault-name {vault} -n {AGENT365_KEY_SECRET} --query value -o tsv")


if __name__ == "__main__":
    main()
