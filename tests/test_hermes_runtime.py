import json

from hermes_company_os.hermes_runtime import (
    hermes_install_powershell,
    hermes_runtime_json,
    hermes_runtime_markdown,
    hermes_runtime_payload,
)
from hermes_company_os.secret_guard import secret_violations


def test_hermes_runtime_packet_explains_install_without_secrets():
    payload = hermes_runtime_payload()
    markdown = hermes_runtime_markdown()
    exported = json.loads(hermes_runtime_json())
    raw = markdown + json.dumps(payload) + json.dumps(exported)

    assert payload["title"] == "Hermes Runtime Connect"
    assert payload["decision"]["do_not_vendor_into_dashboard"] is True
    assert payload["source"]["upstream_repo"] == (
        "https://github.com/NousResearch/hermes-agent"
    )
    assert "iex (irm https://hermes-agent.nousresearch.com/install.ps1)" in raw
    assert "curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash" in raw
    assert "hermes doctor" in raw
    assert "/setup/hermes-install.ps1" in raw
    assert "/setup/runtime-preflight.ps1" in raw
    assert "xoxb-" not in raw
    assert "xapp-" not in raw
    assert "sk-" not in raw
    assert secret_violations({"raw": raw}) == []


def test_hermes_install_helper_is_guarded_and_no_secret():
    script = hermes_install_powershell()

    assert "Hermes runtime installer helper" in script
    assert "RunInstall" in script
    assert "Dry run only" in script
    assert "Invoke-Expression $WindowsCommand" in script
    assert "wsl.exe bash -lc $UnixCommand" in script
    assert "iex (irm https://hermes-agent.nousresearch.com/install.ps1)" in script
    assert "curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash" in script
    assert "hermes doctor" in script
    assert "xoxb-" not in script
    assert "xapp-" not in script
    assert "sk-" not in script
    assert secret_violations({"script": script}) == []
