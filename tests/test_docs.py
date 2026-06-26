from pathlib import Path

from hermes_company_os.secret_guard import secret_violations


def test_preflight_inputs_doc_uses_status_only_secret_guidance():
    markdown = Path("docs/preflight-inputs.md").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "/setup/input-ledger.md" in markdown
    assert "/setup/first-run.ps1" in markdown
    assert "/setup/progress-board.md" in readme
    assert "/setup/founder-inputs.ps1" in markdown
    assert "/setup/hermes-runtime.md" in readme
    assert "/setup/hermes-install.ps1" in readme
    assert "/setup/first-run.ps1" in readme
    assert "/setup/progress-board.json" in readme
    assert "/setup/founder-inputs.ps1" in readme
    assert "/setup/credential-status-template.md" in markdown
    assert "External Credential Status Only" in markdown
    assert "Verify starter profile installation" in markdown
    assert "Load and verify LLM provider credentials last" in markdown
    assert "Run role acceptance prompts" in markdown
    assert "xoxb-" not in markdown
    assert "xapp-" not in markdown
    assert "TELEGRAM_BOT_TOKEN" not in markdown
    assert "API_KEY=" not in markdown
    assert secret_violations({"markdown": markdown}) == []
