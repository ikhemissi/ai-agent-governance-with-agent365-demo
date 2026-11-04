"""Tries the gateway's Purview check (infra/apim-purview) as the signed-in user, through API Management.

    uv run python src/purview_check.py switch on      # or off: the named value purview-check (applies in seconds)
    uv run python src/purview_check.py switch on --answers   # the same for purview-check-responses
    uv run python src/purview_check.py check          # a clean prompt, then one with a test card number
    uv run python src/purview_check.py seed-note      # a note with the test card, for the tool-result scenario

The card number is Visa's public test number, not a real card. `check` prints, for each prompt, the HTTP status, the
gateway's verdicts on the prompt and on the answer (x-purview-verdict, x-purview-answer-verdict) and the start of the
answer or of the error. The user's
token for the gateway comes from the Azure CLI (pre-authorized on the gateway's app registration).
"""

import argparse
import json
import subprocess
import urllib.error
import urllib.request

TEST_CARD = "4111 1111 1111 1111"
PROMPTS = {
    "clean": "Reply with one short sentence: what is a team note?",
    "test card": f"Add a note: the customer's credit card number is {TEST_CARD}.",
    # No card number in the prompt: the model writes one in its answer (checked when purview-check-responses is on).
    "answer": "What is Visa's standard test credit card number for payment testing? Reply only: Visa test card number: <number>",
}


def azd_value(name: str) -> str:
    return subprocess.run(["azd", "env", "get-value", name], capture_output=True, text=True, check=True).stdout.strip()


def user_token() -> str:
    scope = azd_value("APIM_GATEWAY_SCOPE")
    command = ["az", "account", "get-access-token", "--scope", scope, "--query", "accessToken", "-o", "tsv"]
    return subprocess.run(command, capture_output=True, text=True, check=True).stdout.strip()


def post(url: str, token: str, body: dict) -> tuple[int, dict[str, str], str]:
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return response.status, dict(response.headers), response.read().decode(errors="replace")
    except urllib.error.HTTPError as error:
        return error.code, dict(error.headers), error.read().decode(errors="replace")


def switch(state: str, answers: bool) -> None:
    named_value = "purview-check-responses" if answers else "purview-check"
    command = [
        "az", "apim", "nv", "update",
        "--resource-group", azd_value("AZURE_RESOURCE_GROUP"),
        "--service-name", azd_value("APIM_NAME"),
        "--named-value-id", named_value,
        "--value", state,
        "--output", "none",
    ]  # fmt: skip
    subprocess.run(command, check=True)
    print(f"{named_value} is now '{state}'")


def answer_text(body: str) -> str:
    """The model's text from a Responses API answer, or the error message the gateway returned."""
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError:
        return body[:160]
    if parsed.get("error"):
        error = parsed["error"]
        return f"{error.get('type', '')}: {error.get('message', '')}"[:220]
    texts = [part.get("text", "") for item in parsed.get("output", []) for part in item.get("content", []) or []]
    return " ".join(texts)[:160]


def check() -> None:
    url = azd_value("APIM_MODELS_URL").rstrip("/") + "/responses"
    model = azd_value("FOUNDRY_MODEL_DEPLOYMENT_NAME")
    token = user_token()
    for label, prompt in PROMPTS.items():
        status, headers, body = post(url, token, {"model": model, "input": prompt})
        verdict = headers.get("x-purview-verdict", "-")
        answer_verdict = headers.get("x-purview-answer-verdict", "-")
        print(f"{label:10} HTTP {status}  prompt={verdict}  answer={answer_verdict}  {answer_text(body)}")


def seed_note() -> None:
    """Adds a note with the test card through the gateway's notes MCP API, which the Purview check does not cover."""
    url = azd_value("APIM_MCP_NOTES_URL")
    token = user_token()
    initialize = {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "seed", "version": "1"}}
    post(url, token, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": initialize})
    note = {"name": "add_note", "arguments": {"text": f"Customer credit card number: {TEST_CARD} (test number)"}}
    status, _, body = post(url, token, {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": note})
    print(f"add_note HTTP {status}: {body[-200:]}")


def main() -> None:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    switch_parser = commands.add_parser("switch")
    switch_parser.add_argument("state", choices=["on", "off"])
    switch_parser.add_argument("--answers", action="store_true", help="the answer check's switch")
    commands.add_parser("check")
    commands.add_parser("seed-note")
    arguments = parser.parse_args()
    if arguments.command == "switch":
        switch(arguments.state, arguments.answers)
    elif arguments.command == "check":
        check()
    else:
        seed_note()


if __name__ == "__main__":
    main()
