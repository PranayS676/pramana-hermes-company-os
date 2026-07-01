import json

from hermes_company_os.secret_guard import secret_violations
from hermes_company_os.verification_evidence import (
    verification_evidence_json,
    verification_evidence_markdown,
    verification_evidence_payload,
)

AGENTS = [
    {"id": "chief-of-staff", "name": "Chief of Staff"},
    {"id": "engineering-manager", "name": "Engineering Manager"},
]

SECRET_REQUIREMENTS = [
    {
        "id": "chief-of-staff-slack-bot-token",
        "label": "Chief of Staff Slack bot token",
        "status": "loaded",
    },
    {
        "id": "engineering-manager-llm-provider-credential",
        "label": "Engineering Manager LLM provider credential",
        "status": "needed",
    },
]

MESSAGING_CHECKS = [
    {
        "id": "chief-of-staff-slack-dm",
        "label": "Chief of Staff Slack DM",
        "status": "verified",
        "evidence": "Private reply observed in Slack DM with sensitive surrounding text.",
    },
    {
        "id": "chief-of-staff-telegram-urgent",
        "label": "Chief of Staff Telegram urgent alert",
        "status": "verified",
        "evidence": "",
    },
]

SCHEDULE_CHECKS = [
    {
        "id": "morning-standup-manual-run",
        "label": "Morning standup manual run",
        "status": "verified",
        "evidence": "Standup posted in Slack.",
        "schedule_active": 1,
    },
    {
        "id": "paused-standup-manual-run",
        "label": "Paused standup manual run",
        "status": "needed",
        "evidence": "",
        "schedule_active": 0,
    },
]

KANBAN_CHECKS = [
    {
        "id": "kanban-diagnostics-pass",
        "label": "Hermes Kanban diagnostics pass",
        "status": "verified",
        "evidence": "",
    },
    {
        "id": "kanban-task-create",
        "label": "Dashboard task creates Hermes Kanban task",
        "status": "needed",
        "evidence": "",
    },
]

MODEL_PREFERENCES = [
    {"agent_id": "chief-of-staff", "status": "verified"},
    {"agent_id": "engineering-manager", "status": "planned"},
]

PROFILE_SMOKE_RUNS = {
    "chief-of-staff": {
        "status": "completed",
        "completed_at": "2026-06-23T14:00:00+00:00",
        "output": "Do not export this profile output.",
    }
}

PROFILE_INSTALLATION_CHECKS = [
    {
        "id": "chief-of-staff-profile-installation",
        "label": "Chief of Staff profile installation verified",
        "status": "verified",
        "evidence": "Private local file path was checked.",
    },
    {
        "id": "engineering-manager-profile-installation",
        "label": "Engineering Manager profile installation verified",
        "status": "needed",
        "evidence": "",
    },
]

PROFILE_ACCEPTANCE_CHECKS = [
    {
        "id": "engineering-manager-acceptance-1",
        "title": "Architecture and test plan",
        "status": "verified",
        "evidence": "Founder accepted after review.",
    },
    {
        "id": "product-manager-acceptance-1",
        "title": "Less-is-more PRD",
        "status": "needed",
        "evidence": "",
    },
]

FOUNDER_DECISIONS = [
    {
        "id": "decision-operating-model",
        "title": "Approve operating model",
        "status": "approved",
        "decision": "Approved after review.",
    },
    {
        "id": "decision-first-idea-start",
        "title": "Approve first idea intake start",
        "status": "needed",
        "decision": "",
    },
]


def test_verification_evidence_payload_tracks_open_items_without_raw_evidence():
    payload = verification_evidence_payload(
        agents=AGENTS,
        secret_requirements=SECRET_REQUIREMENTS,
        messaging_checks=MESSAGING_CHECKS,
        schedule_checks=SCHEDULE_CHECKS,
        kanban_checks=KANBAN_CHECKS,
        model_preferences=MODEL_PREFERENCES,
        profile_smoke_runs=PROFILE_SMOKE_RUNS,
        profile_installation_checks=PROFILE_INSTALLATION_CHECKS,
        profile_acceptance_checks=PROFILE_ACCEPTANCE_CHECKS,
    )

    assert payload["title"] == "Verification Evidence Pack"
    assert payload["ready"] is False
    assert payload["summary"]["phases"] == 7
    assert payload["summary"]["open_items"] == 5
    assert payload["summary"]["missing_evidence"] == 2
    messaging = next(phase for phase in payload["phases"] if phase["id"] == "messaging")
    assert messaging["evidence_present"] == 1
    assert messaging["missing_evidence"][0]["id"] == "chief-of-staff-telegram-urgent"
    scheduling = next(phase for phase in payload["phases"] if phase["id"] == "scheduling")
    assert scheduling["status_counts"] == {"verified": 1}
    installation = next(
        phase for phase in payload["phases"] if phase["id"] == "profile_installation"
    )
    assert installation["open_items"][0]["id"] == (
        "engineering-manager-profile-installation"
    )
    profile_smoke = next(phase for phase in payload["phases"] if phase["id"] == "profile_smoke")
    assert profile_smoke["open_items"][0]["id"] == "engineering-manager"
    acceptance = next(
        phase for phase in payload["phases"] if phase["id"] == "profile_acceptance"
    )
    assert acceptance["open_items"][0]["id"] == "product-manager-acceptance-1"


def test_verification_evidence_markdown_and_json_omit_raw_evidence_and_outputs():
    markdown = verification_evidence_markdown(
        agents=AGENTS,
        secret_requirements=SECRET_REQUIREMENTS,
        messaging_checks=MESSAGING_CHECKS,
        schedule_checks=SCHEDULE_CHECKS,
        kanban_checks=KANBAN_CHECKS,
        model_preferences=MODEL_PREFERENCES,
        profile_smoke_runs=PROFILE_SMOKE_RUNS,
        profile_installation_checks=PROFILE_INSTALLATION_CHECKS,
        profile_acceptance_checks=PROFILE_ACCEPTANCE_CHECKS,
    )
    payload = json.loads(
        verification_evidence_json(
            agents=AGENTS,
            secret_requirements=SECRET_REQUIREMENTS,
            messaging_checks=MESSAGING_CHECKS,
            schedule_checks=SCHEDULE_CHECKS,
            kanban_checks=KANBAN_CHECKS,
            model_preferences=MODEL_PREFERENCES,
            profile_smoke_runs=PROFILE_SMOKE_RUNS,
            profile_installation_checks=PROFILE_INSTALLATION_CHECKS,
            profile_acceptance_checks=PROFILE_ACCEPTANCE_CHECKS,
        )
    )

    assert "Verification Evidence Pack" in markdown
    assert "Verified items missing evidence" in markdown
    assert payload["entry_points"]["profile_smoke"] == "/setup/profiles#profile-smoke"
    assert payload["entry_points"]["profile_installation"] == (
        "/setup/profiles#profile-installation-tracking"
    )
    assert payload["entry_points"]["profile_acceptance"] == (
        "/setup/profiles#profile-acceptance-tracking"
    )
    raw = json.dumps(payload) + markdown
    assert "Private reply observed" not in raw
    assert "Private local file path was checked" not in raw
    assert "Do not export this profile output" not in raw
    assert "Founder accepted after review" not in raw
    assert "xoxb-" not in raw
    assert "xapp-" not in raw
    assert "sk-" not in raw
    assert secret_violations({"raw": raw}) == []


def test_verification_evidence_can_include_founder_decision_phase():
    payload = verification_evidence_payload(
        agents=AGENTS,
        secret_requirements=SECRET_REQUIREMENTS,
        messaging_checks=MESSAGING_CHECKS,
        schedule_checks=SCHEDULE_CHECKS,
        kanban_checks=KANBAN_CHECKS,
        model_preferences=MODEL_PREFERENCES,
        profile_smoke_runs=PROFILE_SMOKE_RUNS,
        profile_installation_checks=PROFILE_INSTALLATION_CHECKS,
        profile_acceptance_checks=PROFILE_ACCEPTANCE_CHECKS,
        founder_decisions=FOUNDER_DECISIONS,
    )

    decisions = next(
        phase for phase in payload["phases"] if phase["id"] == "founder_decisions"
    )
    assert payload["summary"]["phases"] == 8
    assert decisions["open_items"][0]["id"] == "decision-first-idea-start"
    assert decisions["evidence_present"] == 1
