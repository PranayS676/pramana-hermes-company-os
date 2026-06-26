from __future__ import annotations


def profile_smoke_prompt(agent: dict, model_preference: dict | None = None) -> str:
    provider = model_preference["provider"] if model_preference else "configured provider"
    model = model_preference["model"] if model_preference else "configured model"
    capabilities = ", ".join(agent["capabilities"])
    return "\n".join(
        [
            "Hermes Company OS profile smoke check.",
            "",
            f"Profile: {agent['name']} ({agent['id']})",
            f"Role: {agent['role']}",
            f"Expected provider/model: {provider} / {model}",
            f"Capabilities: {capabilities}",
            "",
            "Respond without using Slack, Telegram, web browsing, or external tools.",
            "Return exactly three short bullets:",
            "- profile_ready: yes/no",
            "- identity_check: one sentence confirming this profile's role",
            "- next_action: one practical next setup check for this profile",
        ]
    )


def append_smoke_note(existing_notes: str, result: str) -> str:
    marker = f"Smoke check {result} via dashboard."
    notes = existing_notes.strip()
    if not notes:
        return marker
    if marker in notes:
        return notes
    return f"{notes} {marker}"
