import json

from hermes_company_os.first_run import (
    first_run_json,
    first_run_markdown,
    first_run_payload,
    first_run_powershell,
)
from hermes_company_os.secret_guard import secret_violations


def test_first_run_exports_guided_no_secret_helper():
    payload = first_run_payload()
    markdown = first_run_markdown()
    script = first_run_powershell()
    exported = json.loads(first_run_json())
    raw = json.dumps(payload) + markdown + script + json.dumps(exported)

    assert payload["title"] == "First Run Helper"
    assert payload["entry_points"]["script"] == "/setup/first-run.ps1"
    assert "/setup/founder-inputs.ps1" in raw
    assert "/setup/hermes-install.ps1" in raw
    assert "/setup/runtime-preflight.ps1" in raw
    assert "/setup/activation-runner.ps1" in raw
    assert "InstallHermes" in script
    assert "RunActivation" in script
    assert "PostDashboardInputs" in script
    assert "Skipping Hermes install" in script
    assert "xoxb-" not in raw
    assert "xapp-" not in raw
    assert "sk-" not in raw
    assert "TELEGRAM_BOT_TOKEN" not in raw
    assert secret_violations({"raw": raw}) == []
