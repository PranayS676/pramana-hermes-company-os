from hermes_company_os.activation_runner import (
    activation_runner_markdown,
    activation_runner_powershell,
)
from hermes_company_os.secret_guard import secret_violations


def test_activation_runner_exports_reviewable_no_secret_script():
    agents = [
        {
            "id": "chief-of-staff",
            "name": "Chief of Staff",
        },
        {
            "id": "engineering-manager",
            "name": "Engineering Manager",
        },
    ]
    schedules = [
        {
            "id": "morning-standup",
            "name": "Morning Standup",
            "hour": 9,
            "minute": 0,
            "timezone": "America/New_York",
            "slack_channel": "#agent-standup",
            "telegram_policy": "urgent only",
            "active": 1,
        }
    ]

    script = activation_runner_powershell(
        agents,
        {"standup_cadence": "every day"},
        schedules,
    )

    assert "param(" in script
    assert "Get-Command hermes" in script
    assert "InstallHermes" in script
    assert "/setup/hermes-install.ps1" in script
    assert "& $scriptPath -RunInstall" in script
    assert "/setup/profile-apply/chief-of-staff.ps1" in script
    assert "/setup/profile-apply/engineering-manager.ps1" in script
    assert "SkipProfileAudit" in script
    assert "/setup/profile-installation.ps1" in script
    assert "/setup/profile-installation-audit" in script
    assert "audit_text = $auditText" in script
    assert "-Fields $auditBody" in script
    assert "curl.exe @curlArguments" in script
    assert "--data-urlencode" in script
    assert "New-TemporaryFile" in script
    assert "Remove-Item -LiteralPath $tempFile" in script
    assert "hermes kanban init" in script
    assert "/setup/kanban-checks/kanban-board-initialized" in script
    assert "Activation runner confirmed hermes kanban init" in script
    assert "Invoke-DashboardPost \"/setup/kanban/diagnostics\"" in script
    assert "RunSlackProvisioning" in script
    assert "/setup/slack-provisioning.ps1" in script
    assert "-PostDashboardInputs" in script
    assert "RunTelegramProvisioning" in script
    assert "SendTelegramTest" in script
    assert "TelegramChatId" in script
    assert "/setup/telegram-provisioning.ps1" in script
    assert "-PostDashboardStatus" in script
    assert "RunScheduleProvisioning" in script
    assert "/setup/schedule-provisioning.ps1" in script
    assert "RunLlmProvisioning" in script
    assert "/setup/llm-provisioning.ps1" in script
    assert "RunLlmFinalization" in script
    assert "/setup/llm-finalize.ps1" in script
    assert "Profile smoke checks were delegated to the LLM finalization bridge" in script
    assert '$resolvedArguments = @("-DashboardBaseUrl", $DashboardBaseUrl)' in script
    assert "ExecuteProvisioning" in script
    assert "chief-of-staff cron create" in script
    assert "/setup/schedule-checks/morning-standup-cron-installed" in script
    assert "Activation runner confirmed cron install/list" in script
    assert "DASHBOARD skipped morning-standup-cron-installed" in script
    assert "RunSmokeChecks" in script
    assert "/setup/profile-smoke/chief-of-staff" in script
    assert "SLACK_BOT_TOKEN" not in script
    assert "TELEGRAM_BOT_TOKEN" not in script
    assert secret_violations({"script": script}) == []


def test_activation_runner_markdown_explains_flags_and_boundaries():
    markdown = activation_runner_markdown(
        [{"id": "chief-of-staff", "name": "Chief of Staff"}],
        {"standup_cadence": "weekdays"},
        [],
    )

    assert "Local Activation Runner" in markdown
    assert "- `-InstallHermes`" in markdown
    assert "/setup/hermes-install.ps1" in markdown
    assert "- `-SkipProfileAudit`" in markdown
    assert "profile installation audit" in markdown
    assert "- `-RunSlackProvisioning`" in markdown
    assert "- `-RunTelegramProvisioning`" in markdown
    assert "- `-SendTelegramTest`" in markdown
    assert "- `-TelegramChatId`" in markdown
    assert "- `-RunScheduleProvisioning`" in markdown
    assert "- `-RunLlmProvisioning`" in markdown
    assert "- `-RunLlmFinalization`" in markdown
    assert "- `-ExecuteProvisioning`" in markdown
    assert "- `-InstallCron`" in markdown
    assert "- `-RunSmokeChecks`" in markdown
    assert "/setup/runtime-preflight.md" in markdown
    assert "/setup/activation-runner.ps1" in markdown
    assert "Slack, Telegram, or provider credential values" in markdown
    assert secret_violations({"markdown": markdown}) == []
