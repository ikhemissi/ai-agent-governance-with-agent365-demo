"""Shows a block from Agent 365 landing on the APIM notes MCP server: every second, as the signed-in user, it does what
an MCP client does first (initialize, then tools/list) and prints OK or BLOCKED with the time since you pressed Enter.

    uv run python src/block_timer.py

Press Enter when you click Block (or Unblock) in the admin center: the timer restarts from that moment, so the
audience sees how many seconds the change takes. Stop with Ctrl+C. The user's token for the gateway comes from the
Azure CLI (pre-authorized on the gateway's app registration). Adapted from the APIM spike's src/02_probe.py.
"""

import json
import subprocess
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime

INTERVAL_SECONDS = 1
RENEW_BEFORE_SECONDS = 300
INITIALIZE = {
    "protocolVersion": "2025-06-18",
    "capabilities": {},
    "clientInfo": {"name": "block-timer", "version": "1"},
}


def azd_value(name: str) -> str:
    return subprocess.run(["azd", "env", "get-value", name], capture_output=True, text=True, check=True).stdout.strip()


class UserToken:
    """The signed-in user's token for the gateway, from the Azure CLI, renewed five minutes before it expires."""

    def __init__(self, scope: str):
        self.scope = scope
        self.value = ""
        self.expires_on = 0

    def get(self) -> str:
        if time.time() > self.expires_on - RENEW_BEFORE_SECONDS:
            command = ["az", "account", "get-access-token", "--scope", self.scope, "-o", "json"]
            token = json.loads(subprocess.run(command, capture_output=True, text=True, check=True).stdout)
            self.value, self.expires_on = token["accessToken"], token["expires_on"]
        return self.value


def rpc(url: str, token: str, request_id: int, method: str, params: dict | None = None) -> tuple[int, dict]:
    """One JSON-RPC request over Streamable HTTP; returns the HTTP status and the JSON body (or its error text)."""
    message = {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params or {}}
    request = urllib.request.Request(
        url,
        data=json.dumps(message).encode(),
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "MCP-Protocol-Version": "2025-06-18",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as error:
        return error.code, {"error": {"message": error.read().decode(errors="replace")[:200]}}
    except (urllib.error.URLError, TimeoutError) as error:
        # No HTTP answer at all (connection reset, DNS, timeout): reported as status 0, the timer goes on.
        return 0, {"error": {"message": str(getattr(error, "reason", error))[:200]}}


def check(url: str, token: str) -> str:
    """OK with the number of tools, BLOCKED with the gateway's JSON-RPC error, or ERROR for anything else."""
    for request_id, (method, params) in enumerate([("initialize", INITIALIZE), ("tools/list", None)], start=1):
        status, body = rpc(url, token, request_id, method, params)
        error = body.get("error")
        if error and (error.get("data") or {}).get("code") == "AccessBlockedByGateway":
            return f"BLOCKED ({error.get('code')} AccessBlockedByGateway on {method}, HTTP {status})"
        if status != 200 or error:
            return f"ERROR   (HTTP {status} on {method}: {str((error or {}).get('message', ''))[:80]})"
    return f"OK      ({len(body['result']['tools'])} tools)"


def main() -> None:
    url = azd_value("APIM_MCP_NOTES_URL")
    token = UserToken(azd_value("APIM_GATEWAY_SCOPE"))
    started = [time.monotonic()]

    def restart_on_enter() -> None:
        while True:
            try:
                input()
            except EOFError:
                return  # no terminal input (e.g. run from a script): the timer keeps counting from the start
            started[0] = time.monotonic()
            print("--- timer restarted ---", flush=True)

    # Waits for Enter on its own thread, so that the checks keep running every second.
    threading.Thread(target=restart_on_enter, daemon=True).start()
    print(f"Checking {url} every {INTERVAL_SECONDS} s. Press Enter when you click Block or Unblock.", flush=True)
    while True:
        outcome = check(url, token.get())
        elapsed = time.monotonic() - started[0]
        print(f"{datetime.now():%H:%M:%S}  {elapsed:6.1f} s  {outcome}", flush=True)
        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
