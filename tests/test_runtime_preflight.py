from pathlib import Path

from hermes_company_os.runtime_preflight import (
    runtime_preflight_checks,
    runtime_preflight_json,
    runtime_preflight_markdown,
    runtime_preflight_powershell,
)
from hermes_company_os.secret_guard import secret_violations
from hermes_company_os.settings import Settings


def test_runtime_preflight_reports_local_runtime_without_secrets(tmp_path):
    database_path = tmp_path / "company.db"
    database_path.touch()
    profile_path = tmp_path / "hermes" / "profiles" / "chief-of-staff"
    profile_path.mkdir(parents=True)

    def which(command: str) -> str | None:
        return {
            "py": "C:/Windows/py.exe",
            "hermes": "C:/tools/hermes.exe",
            "chief-of-staff": "C:/tools/chief-of-staff.exe",
        }.get(command)

    checks = runtime_preflight_checks(
        Settings(database_path=database_path),
        agents=[
            {
                "id": "chief-of-staff",
                "name": "Chief of Staff",
                "hermes_command": "chief-of-staff",
            }
        ],
        integrations=[
            {
                "id": "slack-gateway",
                "name": "Slack Gateway",
                "status": "needs_setup",
                "setup_notes": "Create the Slack app and load credentials externally.",
            }
        ],
        which=which,
        hermes_home=tmp_path / "hermes",
    )

    by_id = {check.id: check for check in checks}
    assert by_id["poetry-command"].status == "ready"
    assert by_id["sqlite-database-file"].status == "ready"
    assert by_id["hermes-cli"].status == "ready"
    assert by_id["profile-path-chief-of-staff"].status == "ready"
    assert by_id["profile-command-chief-of-staff"].detail == "C:/tools/chief-of-staff.exe"
    assert by_id["integration-slack-gateway"].status == "needs_setup"

    markdown = runtime_preflight_markdown(checks)
    payload = runtime_preflight_json(checks)
    assert "Runtime Preflight" in markdown
    assert "/setup/runtime-preflight.ps1" in markdown
    assert "Credential Boundary" in markdown
    assert '"title": "Runtime Preflight"' in payload
    assert '"route": "/setup/runtime-preflight.ps1"' in payload
    assert secret_violations({"markdown": markdown, "json": payload}) == []


def test_runtime_preflight_marks_missing_profile_assets(tmp_path):
    checks = runtime_preflight_checks(
        Settings(database_path=tmp_path / "missing.db"),
        agents=[
            {
                "id": "engineering-manager",
                "name": "Engineering Manager",
                "hermes_command": "engineering-manager",
            }
        ],
        integrations=[],
        which=lambda command: None,
        hermes_home=Path(tmp_path / "hermes"),
    )

    by_id = {check.id: check for check in checks}
    assert by_id["sqlite-database-file"].status == "missing"
    assert by_id["hermes-cli"].status == "missing"
    assert by_id["profile-path-engineering-manager"].status == "missing"
    assert by_id["profile-command-engineering-manager"].status == "missing"


def test_runtime_preflight_powershell_exports_inspect_only_runner():
    script = runtime_preflight_powershell(
        [
            {
                "id": "chief-of-staff",
                "name": "Chief of Staff",
                "hermes_command": "chief-of-staff",
            }
        ]
    )

    assert "Hermes Company OS runtime preflight runner" in script
    assert "HERMES_HOME" in script
    assert "LOCALAPPDATA" in script
    assert "FailOnMissing" in script
    assert "Get-Command $CommandName" in script
    assert "profile-path-$($profile.Id)" in script
    assert "chief-of-staff" in script
    assert "SLACK_BOT_TOKEN" not in script
    assert "TELEGRAM_BOT_TOKEN" not in script
    assert "sk-" not in script
    assert secret_violations({"script": script}) == []
