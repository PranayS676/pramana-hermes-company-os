from __future__ import annotations

import json
from collections import Counter, defaultdict

from hermes_company_os.llm_artifacts import provider_requirements

PRE_LLM_CATEGORIES = {"slack", "telegram"}


def credential_loading_payload(
    *,
    secret_requirements: list[dict],
    model_preferences: list[dict],
    integrations: list[dict],
    profile_installation_checks: list[dict] | None = None,
    profile_acceptance_checks: list[dict] | None = None,
) -> dict:
    preferences_by_agent = {
        preference["agent_id"]: preference for preference in model_preferences
    }
    messaging_requirements = [
        _requirement(item, preferences_by_agent)
        for item in secret_requirements
        if item["category"] in PRE_LLM_CATEGORIES
    ]
    llm_requirements = [
        _requirement(item, preferences_by_agent)
        for item in secret_requirements
        if item["category"] == "llm"
    ]
    coordination = [
        _integration(item)
        for item in integrations
        if item["category"] in {"kanban", "schedule"}
    ]
    installation_checks = profile_installation_checks or []
    acceptance_checks = profile_acceptance_checks or []
    return {
        "title": "External Credential Loading Sequence",
        "credential_boundary": (
            "This sequence names credential categories, environment key names, "
            "profile destinations, status values, and verification routes only. "
            "It does not include Slack tokens, Telegram bot tokens, provider API "
            "keys, OAuth payloads, request headers, private endpoints, raw logs, "
            "or verification evidence text."
        ),
        "verification_last": True,
        "phase_order": [
            {
                "id": "profile_installation_precheck",
                "name": "Verify starter Hermes profile installation",
                "order": 1,
                "dashboard_anchor": "/setup#profile-installation-tracking",
                "requirements": [],
                "status": _status_counts(installation_checks),
            },
            {
                "id": "messaging_credentials",
                "name": "Load Slack and Telegram credentials",
                "order": 2,
                "dashboard_anchor": "/setup#secret-status",
                "requirements": messaging_requirements,
                "status": _status_counts(messaging_requirements),
            },
            {
                "id": "messaging_verification",
                "name": "Verify Slack and Telegram messaging",
                "order": 3,
                "dashboard_anchor": "/setup#messaging-verification",
                "requirements": [],
                "status": {},
            },
            {
                "id": "kanban_and_scheduling",
                "name": "Verify Kanban and standup scheduling",
                "order": 4,
                "dashboard_anchor": "/setup#kanban-verification",
                "integrations": coordination,
                "status": _status_counts(coordination),
            },
            {
                "id": "llm_credentials_last",
                "name": "Load and verify LLM provider credentials last",
                "order": 5,
                "dashboard_anchor": "/setup#profile-smoke",
                "requirements": llm_requirements,
                "status": _status_counts(llm_requirements),
            },
            {
                "id": "profile_acceptance_final",
                "name": "Run profile acceptance after profile smoke checks",
                "order": 6,
                "dashboard_anchor": "/setup#profile-acceptance-tracking",
                "requirements": [],
                "status": _status_counts(acceptance_checks),
            },
        ],
        "profile_files": _profile_files(secret_requirements),
        "bulk_status_template": "/setup/credential-status-template.md",
        "secret_audit": {
            "messaging_command": ".\\secret-audit.ps1 -PostDashboardStatus",
            "llm_command": ".\\secret-audit.ps1 -AuditLlm -PostDashboardStatus",
            "route": "/setup/secret-audit.ps1",
        },
        "entry_points": {
            "credential_status": "/setup#secret-status",
            "credential_status_template": "/setup/credential-status-template.md",
            "profile_installation": "/setup#profile-installation-tracking",
            "secret_audit": "/setup/secret-audit.md",
            "gateway_operations": "/setup/gateway-operations.md",
            "messaging_drill": "/setup/messaging-drill.md",
            "kanban_runbook": "/setup/kanban-runbook.md",
            "standup_runbook": "/setup/standup-runbook.md",
            "llm_credentials": "/setup/llm-credentials.md",
            "llm_provisioning": "/setup/llm-provisioning.md",
            "llm_finalization": "/setup/llm-finalize.md",
            "profile_smoke": "/setup#profile-smoke",
            "profile_acceptance": "/setup#profile-acceptance-tracking",
            "profile_acceptance_suite": "/setup/profile-acceptance.md",
            "live_verification": "/setup/live-verification.md",
        },
    }


def credential_loading_json(**kwargs) -> str:
    return json.dumps(credential_loading_payload(**kwargs), indent=2, sort_keys=True) + "\n"


def credential_loading_markdown(**kwargs) -> str:
    payload = credential_loading_payload(**kwargs)
    phase_by_id = {phase["id"]: phase for phase in payload["phase_order"]}
    lines = [
        "# External Credential Loading Sequence",
        "",
        "Use this after starter profiles are defined and before live verification. "
        "It verifies profile installation first, keeps Slack and Telegram before "
        "coordination checks, and leaves LLM provider credentials until the end.",
        "",
        "## Credential Boundary",
        "",
        payload["credential_boundary"],
        "",
        "## Phase Order",
        "",
    ]
    for phase in payload["phase_order"]:
        lines.append(
            f"{phase['order']}. {phase['name']} - `{phase['dashboard_anchor']}`"
        )
    lines.extend(
        [
            "",
            "## Profile Installation Precheck",
            "",
            "- Run `/setup/profile-installation.ps1` before loading live messaging or "
            "LLM credentials.",
            "- Import no-secret audit output at `/setup#profile-installation-tracking`.",
            "- Profile smoke checks stay blocked until the matching installation check "
            "is verified.",
            "",
            "## Messaging Credentials",
            "",
        ]
    )
    lines.extend(_requirement_lines(phase_by_id["messaging_credentials"]["requirements"]))
    lines.extend(
        [
            "",
            "## Messaging Verification",
            "",
            "- Start Hermes profile gateways after credentials are loaded externally.",
            "- Verify Slack direct messages, Slack channel mentions, and Chief of Staff "
            "urgent Telegram delivery in `/setup#messaging-verification`.",
            "- Record only short non-secret evidence.",
            "",
            "## Kanban And Scheduling",
            "",
        ]
    )
    lines.extend(_integration_lines(phase_by_id["kanban_and_scheduling"]["integrations"]))
    lines.extend(["", "## LLM Credentials Last", ""])
    lines.extend(_requirement_lines(phase_by_id["llm_credentials_last"]["requirements"]))
    lines.extend(
        [
            "",
            "Use `/setup/llm-provisioning.md` before finalization to review provider "
            "choices, starter file downloads, and model-picker commands.",
            "Run profile smoke checks at `/setup#profile-smoke` only after the "
            "matching profile installation and LLM provider credential are ready.",
            "",
            "## Profile Acceptance Last",
            "",
            "- Run `/setup/profile-acceptance.md` after every profile smoke check passes.",
            "- Import acceptance outcomes at `/setup#profile-acceptance-tracking`.",
            "- Store only pass, fail, blocked, or deferred status with short non-secret "
            "notes.",
            "",
            "## Audit Commands",
            "",
            "```powershell",
            "Invoke-WebRequest -UseBasicParsing "
            "http://127.0.0.1:8002/setup/secret-audit.ps1 "
            "-OutFile .\\secret-audit.ps1",
            payload["secret_audit"]["messaging_command"],
            payload["secret_audit"]["llm_command"],
            "```",
            "",
            "## Profile Files",
            "",
        ]
    )
    for profile in payload["profile_files"]:
        lines.append(
            f"- `{profile['profile_id']}`: gateway `{profile['gateway_env']}`, "
            f"LLM `{profile['llm_env']}`"
        )
    lines.extend(
        [
            "",
            "## Status Import",
            "",
            "- Use `/setup/credential-status-template.md` after loading credentials externally.",
            "- Import status metadata at `/setup#credential-status-import`.",
            "- Use `/setup/live-verification.md` only after loaded statuses are current.",
            "",
        ]
    )
    return "\n".join(lines)


def _requirement(item: dict, preferences_by_agent: dict[str, dict]) -> dict:
    profile_id = item.get("owner_agent_id") or ""
    preference = preferences_by_agent.get(profile_id)
    keys = _resolved_keys(item, preference)
    return {
        "id": item["id"],
        "category": item["category"],
        "label": item["label"],
        "owner_agent_id": profile_id,
        "owner_name": item.get("owner_name") or profile_id,
        "owner_command": item.get("owner_command") or profile_id,
        "destination": item["destination"],
        "environment_key": item["environment_key"],
        "resolved_keys": keys,
        "status": item["status"],
        "gateway_env": f"/setup/profile-env/{profile_id}.env" if profile_id else "",
        "llm_env": f"/setup/profile-llm-env/{profile_id}.env" if profile_id else "",
        "provider": preference.get("provider", "") if preference else "",
        "model": preference.get("model", "") if preference else "",
        "audit_last": item["category"] == "llm",
    }


def _integration(item: dict) -> dict:
    return {
        "id": item["id"],
        "name": item["name"],
        "category": item["category"],
        "owner": item.get("owner_name") or item.get("owner_agent_id") or "",
        "status": item["status"],
        "validation_command": item["validation_command"],
    }


def _resolved_keys(item: dict, preference: dict | None) -> list[str]:
    if item["category"] != "llm":
        return [item["environment_key"]]
    if preference is None:
        return [item["environment_key"]]
    primary = provider_requirements(preference["provider"])
    keys = list(primary["env"])
    if preference.get("fallback_provider"):
        fallback = provider_requirements(preference["fallback_provider"])
        keys.extend(fallback["env"])
    return list(dict.fromkeys(keys))


def _profile_files(secret_requirements: list[dict]) -> list[dict]:
    grouped: dict[str, set[str]] = defaultdict(set)
    for item in secret_requirements:
        profile_id = item.get("owner_agent_id")
        if profile_id:
            grouped[profile_id].add(item["category"])
    return [
        {
            "profile_id": profile_id,
            "categories": sorted(categories),
            "gateway_env": f"/setup/profile-env/{profile_id}.env",
            "llm_env": f"/setup/profile-llm-env/{profile_id}.env",
        }
        for profile_id, categories in sorted(grouped.items())
    ]


def _status_counts(items: list[dict]) -> dict[str, int]:
    return dict(Counter(item["status"] for item in items))


def _requirement_lines(requirements: list[dict]) -> list[str]:
    if not requirements:
        return ["- None."]
    lines = []
    for item in requirements:
        keys = ", ".join(f"`{key}`" for key in item["resolved_keys"])
        destination = item["llm_env"] if item["audit_last"] else item["gateway_env"]
        lines.append(
            f"- `{item['id']}`: {item['owner_name']} loads {keys} using "
            f"`{destination}`; current status `{item['status']}`"
        )
    return lines


def _integration_lines(integrations: list[dict]) -> list[str]:
    if not integrations:
        return ["- No Kanban or schedule integrations are tracked."]
    return [
        f"- {item['name']}: status `{item['status']}`, validation "
        f"`{item['validation_command']}`"
        for item in integrations
    ]
