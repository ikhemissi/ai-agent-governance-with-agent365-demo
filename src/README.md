# Demo scripts

Small scripts, one purpose each, reading the azd environment (`azd env get-values`) and using your Azure CLI sign-in.
Run them with `uv run python src/<script>.py`.

| Script | Purpose |
|---|---|
| `configure_litellm.py` | Registers Microsoft Learn's MCP server in LiteLLM as "MS_Learn_LiteLLM"; creates the key Agent 365 holds and the probe's key, in Key Vault |
| `check_environment.py` | Checks every part before a rehearsal or the demo |
| `block_timer.py` | Every second, `initialize` and `tools/list` on the APIM notes server as you: OK or BLOCKED, timed from your Enter |
| `litellm_tools_probe.py` | Calls each Microsoft Learn tool through LiteLLM: ALLOWED or REFUSED per tool |
| `purview_check.py` | The Purview switches, a check with three test prompts, and a note with a test card number ([PURVIEW.md](../docs/PURVIEW.md)) |
| `create-dlp-policy.ps1` | The DLP policy the Purview check enforces (PowerShell, Compliance Administrator) |
| `gateway_admin.py` | Shared helpers: the azd environment, Key Vault secrets, LiteLLM's admin API |
