from pathlib import Path


def test_messaging_credential_loader_is_no_secret_prompt_script():
    script = Path("scripts/load-messaging-credentials.ps1").read_text(encoding="utf-8")

    assert "Read-Host" in script
    assert "-AsSecureString" in script
    assert "SLACK_BOT_TOKEN" in script
    assert "SLACK_APP_TOKEN" in script
    assert "TELEGRAM_BOT_TOKEN" in script
    assert "PostDashboardStatus" in script
    assert "xoxb-123" not in script
    assert "xapp-123" not in script
    assert ("123456789:" + "abcdefghijklmnopqrstuvwxyz") not in script
