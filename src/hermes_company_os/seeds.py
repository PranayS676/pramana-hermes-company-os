import json

from hermes_company_os.profile_doctrine import PROFILE_DOCTRINES, PROFILE_ORDER


def _default_agent(agent_id: str) -> dict:
    doctrine = PROFILE_DOCTRINES[agent_id]
    return {
        "id": agent_id,
        "name": doctrine["name"],
        "role": doctrine["role"],
        "slack_channel": doctrine["slack_channel"],
        "telegram_policy": doctrine["telegram_policy"],
        "hermes_command": doctrine["hermes_command"],
        "description": doctrine["description"],
        "capabilities": json.dumps(doctrine["capabilities"]),
        "soul": doctrine["soul"],
    }


DEFAULT_AGENTS = [_default_agent(agent_id) for agent_id in PROFILE_ORDER]


DEFAULT_AGENT_RELATIONSHIPS = [
    {
        "id": "engineering-manager-backend-engineer",
        "manager_agent_id": "engineering-manager",
        "member_agent_id": "backend-engineer",
        "relationship_type": "reports_to",
        "sort_order": 10,
        "responsibility": "Own backend service design, APIs, data model, and integration testing.",
    },
    {
        "id": "engineering-manager-frontend-engineer",
        "manager_agent_id": "engineering-manager",
        "member_agent_id": "frontend-engineer",
        "relationship_type": "reports_to",
        "sort_order": 20,
        "responsibility": "Own product UI architecture, frontend workflow plans, and E2E tests.",
    },
    {
        "id": "engineering-manager-cloud-infra-agent",
        "manager_agent_id": "engineering-manager",
        "member_agent_id": "cloud-infra-agent",
        "relationship_type": "reports_to",
        "sort_order": 30,
        "responsibility": "Own AWS, deployment, observability, reliability, and cost controls.",
    },
    {
        "id": "engineering-manager-test-automation-agent",
        "manager_agent_id": "engineering-manager",
        "member_agent_id": "test-automation-agent",
        "relationship_type": "reports_to",
        "sort_order": 40,
        "responsibility": "Own test architecture, CI quality gates, and acceptance coverage.",
    },
]


DEFAULT_STANDUPS = [
    {
        "id": "morning-standup",
        "name": "Morning Standup",
        "hour": 9,
        "minute": 0,
        "timezone": "America/New_York",
        "slack_channel": "#agent-standup",
        "telegram_policy": "Only blockers, failed runs, or founder approvals",
    },
    {
        "id": "afternoon-standup",
        "name": "Afternoon Standup",
        "hour": 15,
        "minute": 0,
        "timezone": "America/New_York",
        "slack_channel": "#agent-standup",
        "telegram_policy": "Only blockers, failed runs, or founder approvals",
    },
]


DEFAULT_FOUNDER_DECISIONS = [
    {
        "id": "decision-company-operating-model",
        "title": "Approve company operating model",
        "status": "needed",
        "urgency": "routine",
        "source": "setup",
        "owner_agent_id": "chief-of-staff",
        "slack_channel": "#decisions",
        "telegram_policy": "Slack discussion first; Telegram only if blocked",
        "context": (
            "Confirm Slack as the main workspace, Telegram as urgent-only, "
            "two daily standups, Kanban as source of truth, and LLM credentials last."
        ),
        "decision": "",
    },
    {
        "id": "decision-first-idea-start",
        "title": "Approve first idea intake start",
        "status": "needed",
        "urgency": "urgent",
        "source": "setup",
        "owner_agent_id": "chief-of-staff",
        "slack_channel": "#founder-command",
        "telegram_policy": "Escalate to Telegram when all setup gates are ready",
        "context": (
            "Use this decision after profile acceptance and launch drill gates are "
            "verified, before starting the first real company project."
        ),
        "decision": "",
    },
]


DEFAULT_INTEGRATIONS = [
    {
        "id": "llm-provider",
        "name": "LLM provider",
        "category": "runtime",
        "owner_agent_id": None,
        "status": "deferred",
        "required_inputs": json.dumps(
            [
                "provider name",
                "model name",
                "API key or local endpoint",
                "fallback model policy",
            ]
        ),
        "setup_notes": (
            "Configure last through each Hermes profile setup flow after profiles, messaging, "
            "and schedules are ready."
        ),
        "validation_command": "chief-of-staff doctor",
        "docs_url": "https://hermes-agent.nousresearch.com/docs/user-guide/profiles",
    },
    {
        "id": "slack-chief-of-staff",
        "name": "Chief of Staff Slack bot",
        "category": "slack",
        "owner_agent_id": "chief-of-staff",
        "status": "needs_input",
        "required_inputs": json.dumps(
            [
                "Slack workspace",
                "bot token starting with xoxb-",
                "app token starting with xapp-",
                "founder Slack member ID",
                "#founder-command channel ID",
                "#agent-standup channel ID",
            ]
        ),
        "setup_notes": (
            "Primary Slack coordinator. Invite to #founder-command, #agent-standup, "
            "#decisions, and #alerts."
        ),
        "validation_command": "chief-of-staff gateway setup",
        "docs_url": "https://hermes-agent.nousresearch.com/docs/user-guide/messaging/slack",
    },
    {
        "id": "slack-product-manager",
        "name": "Product Manager Slack bot",
        "category": "slack",
        "owner_agent_id": "product-manager",
        "status": "needs_input",
        "required_inputs": json.dumps(
            [
                "bot token starting with xoxb-",
                "app token starting with xapp-",
                "founder Slack member ID",
                "#product channel ID",
            ]
        ),
        "setup_notes": "Invite to #product and mention it only when product planning is needed.",
        "validation_command": "product-manager gateway setup",
        "docs_url": "https://hermes-agent.nousresearch.com/docs/user-guide/messaging/slack",
    },
    {
        "id": "slack-research-agent",
        "name": "Research Agent Slack bot",
        "category": "slack",
        "owner_agent_id": "research-agent",
        "status": "needs_input",
        "required_inputs": json.dumps(
            [
                "bot token starting with xoxb-",
                "app token starting with xapp-",
                "founder Slack member ID",
                "#research channel ID",
            ]
        ),
        "setup_notes": "Invite to #research for evidence-backed market and technical research.",
        "validation_command": "research-agent gateway setup",
        "docs_url": "https://hermes-agent.nousresearch.com/docs/user-guide/messaging/slack",
    },
    {
        "id": "slack-engineering-manager",
        "name": "Engineering Manager Slack bot",
        "category": "slack",
        "owner_agent_id": "engineering-manager",
        "status": "needs_input",
        "required_inputs": json.dumps(
            [
                "bot token starting with xoxb-",
                "app token starting with xapp-",
                "founder Slack member ID",
                "#engineering channel ID",
            ]
        ),
        "setup_notes": "Invite to #engineering for architecture, testing, and AWS planning.",
        "validation_command": "engineering-manager gateway setup",
        "docs_url": "https://hermes-agent.nousresearch.com/docs/user-guide/messaging/slack",
    },
    {
        "id": "slack-backend-engineer",
        "name": "Backend Engineer Slack bot",
        "category": "slack",
        "owner_agent_id": "backend-engineer",
        "status": "needs_input",
        "required_inputs": json.dumps(
            [
                "bot token starting with xoxb-",
                "app token starting with xapp-",
                "founder Slack member ID",
                "#engineering channel ID",
            ]
        ),
        "setup_notes": "Invite to #engineering for backend services, APIs, and data work.",
        "validation_command": "backend-engineer gateway setup",
        "docs_url": "https://hermes-agent.nousresearch.com/docs/user-guide/messaging/slack",
    },
    {
        "id": "slack-frontend-engineer",
        "name": "Frontend Engineer Slack bot",
        "category": "slack",
        "owner_agent_id": "frontend-engineer",
        "status": "needs_input",
        "required_inputs": json.dumps(
            [
                "bot token starting with xoxb-",
                "app token starting with xapp-",
                "founder Slack member ID",
                "#engineering channel ID",
            ]
        ),
        "setup_notes": (
            "Invite to #engineering for UI workflows, frontend architecture, and E2E tests."
        ),
        "validation_command": "frontend-engineer gateway setup",
        "docs_url": "https://hermes-agent.nousresearch.com/docs/user-guide/messaging/slack",
    },
    {
        "id": "slack-cloud-infra-agent",
        "name": "Cloud Infrastructure Agent Slack bot",
        "category": "slack",
        "owner_agent_id": "cloud-infra-agent",
        "status": "needs_input",
        "required_inputs": json.dumps(
            [
                "bot token starting with xoxb-",
                "app token starting with xapp-",
                "founder Slack member ID",
                "#engineering channel ID",
            ]
        ),
        "setup_notes": "Invite to #engineering for AWS, deployment, reliability, and cost work.",
        "validation_command": "cloud-infra-agent gateway setup",
        "docs_url": "https://hermes-agent.nousresearch.com/docs/user-guide/messaging/slack",
    },
    {
        "id": "slack-test-automation-agent",
        "name": "Test Automation Agent Slack bot",
        "category": "slack",
        "owner_agent_id": "test-automation-agent",
        "status": "needs_input",
        "required_inputs": json.dumps(
            [
                "bot token starting with xoxb-",
                "app token starting with xapp-",
                "founder Slack member ID",
                "#engineering channel ID",
            ]
        ),
        "setup_notes": (
            "Invite to #engineering for test architecture, CI gates, and acceptance coverage."
        ),
        "validation_command": "test-automation-agent gateway setup",
        "docs_url": "https://hermes-agent.nousresearch.com/docs/user-guide/messaging/slack",
    },
    {
        "id": "slack-marketing-agent",
        "name": "Marketing Agent Slack bot",
        "category": "slack",
        "owner_agent_id": "marketing-agent",
        "status": "needs_input",
        "required_inputs": json.dumps(
            [
                "bot token starting with xoxb-",
                "app token starting with xapp-",
                "founder Slack member ID",
                "#marketing channel ID",
            ]
        ),
        "setup_notes": "Invite to #marketing for positioning, launches, campaigns, and copy.",
        "validation_command": "marketing-agent gateway setup",
        "docs_url": "https://hermes-agent.nousresearch.com/docs/user-guide/messaging/slack",
    },
    {
        "id": "slack-qa-critic",
        "name": "QA / Critic Slack bot",
        "category": "slack",
        "owner_agent_id": "qa-critic",
        "status": "needs_input",
        "required_inputs": json.dumps(
            [
                "bot token starting with xoxb-",
                "app token starting with xapp-",
                "founder Slack member ID",
                "#qa-review channel ID",
            ]
        ),
        "setup_notes": "Invite to #qa-review for risk, test-gap, and assumption review.",
        "validation_command": "qa-critic gateway setup",
        "docs_url": "https://hermes-agent.nousresearch.com/docs/user-guide/messaging/slack",
    },
    {
        "id": "telegram-founder-alerts",
        "name": "Founder Telegram urgent alerts",
        "category": "telegram",
        "owner_agent_id": "chief-of-staff",
        "status": "needs_input",
        "required_inputs": json.dumps(
            [
                "Telegram bot token from BotFather",
                "founder Telegram user ID",
                "urgent chat ID if different from direct message",
            ]
        ),
        "setup_notes": (
            "Configure only on Chief of Staff. Do not give routine agents Telegram access."
        ),
        "validation_command": "chief-of-staff gateway setup",
        "docs_url": "https://hermes-agent.nousresearch.com/docs/user-guide/messaging/telegram",
    },
    {
        "id": "hermes-kanban",
        "name": "Hermes Kanban board",
        "category": "kanban",
        "owner_agent_id": "chief-of-staff",
        "status": "needs_setup",
        "required_inputs": json.dumps(
            [
                "Hermes installed",
                "profiles created with descriptions",
                "gateway running for dispatcher",
            ]
        ),
        "setup_notes": (
            "Use the Hermes Kanban board as the multi-agent source of truth once profiles exist."
        ),
        "validation_command": "hermes kanban diagnostics --json",
        "docs_url": "https://hermes-agent.nousresearch.com/docs/user-guide/features/kanban",
    },
    {
        "id": "standup-cron",
        "name": "9 AM / 3 PM standup cron",
        "category": "schedule",
        "owner_agent_id": "chief-of-staff",
        "status": "needs_setup",
        "required_inputs": json.dumps(
            [
                "Chief of Staff profile configured",
                "Slack home channel",
                "Telegram urgent policy",
                "timezone confirmation",
            ]
        ),
        "setup_notes": "Create two Chief of Staff cron jobs after Slack and Telegram are working.",
        "validation_command": "chief-of-staff cron list",
        "docs_url": "https://hermes-agent.nousresearch.com/docs/user-guide/features/cron",
    },
]


DEFAULT_SETUP_STEPS = [
    {
        "id": "install-hermes",
        "phase": "runtime",
        "name": "Install Hermes",
        "status": "manual",
        "owner": "Founder",
        "sort_order": 10,
        "description": (
            "Install Hermes Agent locally so profile aliases and gateways are available."
        ),
        "command": "See Hermes install docs for the current installer path.",
        "docs_url": "https://hermes-agent.nousresearch.com/docs/",
    },
    {
        "id": "create-profiles",
        "phase": "profiles",
        "name": "Create company profiles",
        "status": "ready",
        "owner": "Founder / Codex",
        "sort_order": 20,
        "description": "Create persistent Hermes profiles with descriptions for Kanban routing.",
        "command": "Use the generated bootstrap script on the Setup page.",
        "docs_url": "https://hermes-agent.nousresearch.com/docs/user-guide/profiles",
    },
    {
        "id": "seed-souls",
        "phase": "profiles",
        "name": "Seed SOUL.md files",
        "status": "ready",
        "owner": "Founder / Codex",
        "sort_order": 30,
        "description": "Write starter personalization files for each profile.",
        "command": "Use the generated bootstrap script on the Setup page.",
        "docs_url": "https://hermes-agent.nousresearch.com/docs/user-guide/features/personality",
    },
    {
        "id": "configure-slack",
        "phase": "messaging",
        "name": "Configure Slack bots",
        "status": "needs_input",
        "owner": "Founder",
        "sort_order": 40,
        "description": (
            "Create Slack apps, collect tokens, set allowed users, invite bots to channels."
        ),
        "command": "Run each profile's gateway setup and choose Slack.",
        "docs_url": "https://hermes-agent.nousresearch.com/docs/user-guide/messaging/slack",
    },
    {
        "id": "configure-telegram",
        "phase": "messaging",
        "name": "Configure Telegram urgent alerts",
        "status": "needs_input",
        "owner": "Founder",
        "sort_order": 50,
        "description": "Create a BotFather bot for Chief of Staff urgent founder notifications.",
        "command": "Run chief-of-staff gateway setup and choose Telegram.",
        "docs_url": "https://hermes-agent.nousresearch.com/docs/user-guide/messaging/telegram",
    },
    {
        "id": "init-kanban",
        "phase": "coordination",
        "name": "Initialize Hermes Kanban",
        "status": "ready",
        "owner": "Founder / Codex",
        "sort_order": 60,
        "description": "Initialize the shared multi-agent board and confirm diagnostics.",
        "command": "hermes kanban init; hermes kanban diagnostics --json",
        "docs_url": "https://hermes-agent.nousresearch.com/docs/user-guide/features/kanban",
    },
    {
        "id": "create-standup-cron",
        "phase": "scheduling",
        "name": "Create standup cron jobs",
        "status": "ready_after_messaging",
        "owner": "Founder / Codex",
        "sort_order": 70,
        "description": "Create 9 AM and 3 PM Chief of Staff standup jobs.",
        "command": "Use the generated cron commands on the Setup page.",
        "docs_url": "https://hermes-agent.nousresearch.com/docs/user-guide/features/cron",
    },
    {
        "id": "configure-llm",
        "phase": "runtime",
        "name": "Configure LLM provider",
        "status": "deferred",
        "owner": "Founder",
        "sort_order": 80,
        "description": "Configure provider, model, API keys, and fallback policy last.",
        "command": "chief-of-staff setup --portal",
        "docs_url": "https://hermes-agent.nousresearch.com/docs/user-guide/profiles",
    },
]


DEFAULT_SETUP_INPUTS = [
    {
        "key": "founder_name",
        "group_name": "founder",
        "label": "Founder name",
        "value": "",
        "required": 1,
        "secret_policy": "non_secret",
        "help_text": "Name agents should use when addressing or summarizing for you.",
        "sort_order": 10,
    },
    {
        "key": "timezone",
        "group_name": "founder",
        "label": "Timezone",
        "value": "America/New_York",
        "required": 1,
        "secret_policy": "non_secret",
        "help_text": "Used for 9 AM and 3 PM standups.",
        "sort_order": 20,
    },
    {
        "key": "standup_cadence",
        "group_name": "founder",
        "label": "Standup cadence",
        "value": "every day",
        "required": 1,
        "secret_policy": "non_secret",
        "help_text": "Use 'every day' or 'weekdays' before the cron jobs are created.",
        "sort_order": 30,
    },
    {
        "key": "separate_slack_bots",
        "group_name": "slack",
        "label": "Separate Slack bots per profile",
        "value": "yes",
        "required": 1,
        "secret_policy": "non_secret",
        "help_text": "Keep 'yes' for distinct bot identities per Hermes profile.",
        "sort_order": 40,
    },
    {
        "key": "slack_workspace_name",
        "group_name": "slack",
        "label": "Slack workspace name",
        "value": "",
        "required": 1,
        "secret_policy": "non_secret",
        "help_text": "Human-readable workspace name for setup tracking.",
        "sort_order": 50,
    },
    {
        "key": "founder_slack_member_id",
        "group_name": "slack",
        "label": "Founder Slack member ID",
        "value": "",
        "required": 1,
        "secret_policy": "non_secret",
        "help_text": "Slack member IDs start with U, for example U01ABC2DEF3.",
        "sort_order": 60,
    },
    {
        "key": "slack_channel_founder_command",
        "group_name": "slack",
        "label": "#founder-command channel ID",
        "value": "",
        "required": 1,
        "secret_policy": "non_secret",
        "help_text": "Slack channel IDs usually start with C or G.",
        "sort_order": 70,
    },
    {
        "key": "slack_channel_agent_standup",
        "group_name": "slack",
        "label": "#agent-standup channel ID",
        "value": "",
        "required": 1,
        "secret_policy": "non_secret",
        "help_text": "Home channel for 9 AM and 3 PM standup delivery.",
        "sort_order": 80,
    },
    {
        "key": "slack_channel_product",
        "group_name": "slack",
        "label": "#product channel ID",
        "value": "",
        "required": 1,
        "secret_policy": "non_secret",
        "help_text": "Product Manager bot channel.",
        "sort_order": 90,
    },
    {
        "key": "slack_channel_research",
        "group_name": "slack",
        "label": "#research channel ID",
        "value": "",
        "required": 1,
        "secret_policy": "non_secret",
        "help_text": "Research Agent bot channel.",
        "sort_order": 100,
    },
    {
        "key": "slack_channel_engineering",
        "group_name": "slack",
        "label": "#engineering channel ID",
        "value": "",
        "required": 1,
        "secret_policy": "non_secret",
        "help_text": "Engineering Manager bot channel.",
        "sort_order": 110,
    },
    {
        "key": "slack_channel_marketing",
        "group_name": "slack",
        "label": "#marketing channel ID",
        "value": "",
        "required": 1,
        "secret_policy": "non_secret",
        "help_text": "Marketing Agent bot channel.",
        "sort_order": 120,
    },
    {
        "key": "slack_channel_qa_review",
        "group_name": "slack",
        "label": "#qa-review channel ID",
        "value": "",
        "required": 1,
        "secret_policy": "non_secret",
        "help_text": "QA / Critic bot channel.",
        "sort_order": 130,
    },
    {
        "key": "slack_channel_decisions",
        "group_name": "slack",
        "label": "#decisions channel ID",
        "value": "",
        "required": 0,
        "secret_policy": "non_secret",
        "help_text": "Optional decisions archive channel for Chief of Staff.",
        "sort_order": 140,
    },
    {
        "key": "slack_channel_alerts",
        "group_name": "slack",
        "label": "#alerts channel ID",
        "value": "",
        "required": 0,
        "secret_policy": "non_secret",
        "help_text": "Optional blocker and failed-run channel for Chief of Staff.",
        "sort_order": 150,
    },
    {
        "key": "slack_bot_user_id_chief_of_staff",
        "group_name": "slack",
        "label": "Chief of Staff Slack bot user ID",
        "value": "",
        "required": 0,
        "secret_policy": "non_secret",
        "help_text": "Safe bot user ID for invite automation; usually starts with U.",
        "sort_order": 151,
    },
    {
        "key": "slack_bot_user_id_product_manager",
        "group_name": "slack",
        "label": "Product Manager Slack bot user ID",
        "value": "",
        "required": 0,
        "secret_policy": "non_secret",
        "help_text": "Safe bot user ID for invite automation; usually starts with U.",
        "sort_order": 152,
    },
    {
        "key": "slack_bot_user_id_research_agent",
        "group_name": "slack",
        "label": "Research Agent Slack bot user ID",
        "value": "",
        "required": 0,
        "secret_policy": "non_secret",
        "help_text": "Safe bot user ID for invite automation; usually starts with U.",
        "sort_order": 153,
    },
    {
        "key": "slack_bot_user_id_engineering_manager",
        "group_name": "slack",
        "label": "Engineering Manager Slack bot user ID",
        "value": "",
        "required": 0,
        "secret_policy": "non_secret",
        "help_text": "Safe bot user ID for invite automation; usually starts with U.",
        "sort_order": 154,
    },
    {
        "key": "slack_bot_user_id_backend_engineer",
        "group_name": "slack",
        "label": "Backend Engineer Slack bot user ID",
        "value": "",
        "required": 0,
        "secret_policy": "non_secret",
        "help_text": "Safe bot user ID for invite automation; usually starts with U.",
        "sort_order": 155,
    },
    {
        "key": "slack_bot_user_id_frontend_engineer",
        "group_name": "slack",
        "label": "Frontend Engineer Slack bot user ID",
        "value": "",
        "required": 0,
        "secret_policy": "non_secret",
        "help_text": "Safe bot user ID for invite automation; usually starts with U.",
        "sort_order": 156,
    },
    {
        "key": "slack_bot_user_id_cloud_infra_agent",
        "group_name": "slack",
        "label": "Cloud Infrastructure Agent Slack bot user ID",
        "value": "",
        "required": 0,
        "secret_policy": "non_secret",
        "help_text": "Safe bot user ID for invite automation; usually starts with U.",
        "sort_order": 157,
    },
    {
        "key": "slack_bot_user_id_test_automation_agent",
        "group_name": "slack",
        "label": "Test Automation Agent Slack bot user ID",
        "value": "",
        "required": 0,
        "secret_policy": "non_secret",
        "help_text": "Safe bot user ID for invite automation; usually starts with U.",
        "sort_order": 158,
    },
    {
        "key": "slack_bot_user_id_marketing_agent",
        "group_name": "slack",
        "label": "Marketing Agent Slack bot user ID",
        "value": "",
        "required": 0,
        "secret_policy": "non_secret",
        "help_text": "Safe bot user ID for invite automation; usually starts with U.",
        "sort_order": 159,
    },
    {
        "key": "slack_bot_user_id_qa_critic",
        "group_name": "slack",
        "label": "QA / Critic Slack bot user ID",
        "value": "",
        "required": 0,
        "secret_policy": "non_secret",
        "help_text": "Safe bot user ID for invite automation; usually starts with U.",
        "sort_order": 160,
    },
    {
        "key": "founder_telegram_user_id",
        "group_name": "telegram",
        "label": "Founder Telegram user ID",
        "value": "",
        "required": 1,
        "secret_policy": "non_secret",
        "help_text": "Numeric Telegram user ID. Your DM chat ID is usually the same value.",
        "sort_order": 200,
    },
    {
        "key": "telegram_home_channel",
        "group_name": "telegram",
        "label": "Telegram home channel",
        "value": "",
        "required": 0,
        "secret_policy": "non_secret",
        "help_text": "Optional group/channel ID for urgent alerts; leave blank for founder DM.",
        "sort_order": 210,
    },
    {
        "key": "llm_provider",
        "group_name": "llm",
        "label": "LLM provider",
        "value": "",
        "required": 0,
        "secret_policy": "secret_external",
        "help_text": "Deferred until last. Store API keys in Hermes profile .env files.",
        "sort_order": 220,
    },
    {
        "key": "llm_model",
        "group_name": "llm",
        "label": "LLM model",
        "value": "",
        "required": 0,
        "secret_policy": "secret_external",
        "help_text": "Deferred until last. This dashboard stores model preference only.",
        "sort_order": 230,
    },
]


DEFAULT_WORKFLOW_TEMPLATES = [
    {
        "id": "idea-opportunity-research",
        "name": "Opportunity research",
        "phase": "research",
        "owner_agent_id": "research-agent",
        "sort_order": 10,
        "doc_type": "research",
        "priority": "high",
        "title_template": "Opportunity research for {project_name}",
        "prompt_template": (
            "Research the founder's startup idea: {idea}\n\n"
            "Return market problem, target users, existing alternatives, adoption risks, "
            "evidence quality, and open questions. Separate facts from inference."
        ),
    },
    {
        "id": "product-concept-prd",
        "name": "Product concept PRD",
        "phase": "product",
        "owner_agent_id": "product-manager",
        "sort_order": 20,
        "doc_type": "prd",
        "priority": "high",
        "title_template": "Lean PRD for {project_name}",
        "prompt_template": (
            "Turn this startup idea into a focused PRD: {idea}\n\n"
            "Use less-is-more product judgment. Define user, problem, narrow workflow, "
            "non-goals, initial feature set, and what can be removed."
        ),
    },
    {
        "id": "competitor-positioning-research",
        "name": "Competitor and positioning scan",
        "phase": "research",
        "owner_agent_id": "research-agent",
        "sort_order": 30,
        "doc_type": "research",
        "priority": "medium",
        "title_template": "Competitor scan for {project_name}",
        "prompt_template": (
            "Find direct and indirect competitors for: {idea}\n\n"
            "Return competitor categories, likely differentiation, weak assumptions, "
            "and what a founder should verify before building."
        ),
    },
    {
        "id": "architecture-plan",
        "name": "Architecture plan",
        "phase": "engineering",
        "owner_agent_id": "engineering-manager",
        "sort_order": 40,
        "doc_type": "architecture",
        "priority": "high",
        "title_template": "Architecture plan for {project_name}",
        "prompt_template": (
            "Create an architecture plan for this product idea: {idea}\n\n"
            "Think ambitiously but justify complexity. Cover system boundaries, data model, "
            "interfaces, distributed-system needs, observability, reliability, and risks."
        ),
    },
    {
        "id": "aws-operating-plan",
        "name": "AWS operating plan",
        "phase": "engineering",
        "owner_agent_id": "cloud-infra-agent",
        "sort_order": 50,
        "doc_type": "architecture",
        "priority": "medium",
        "title_template": "AWS operating plan for {project_name}",
        "prompt_template": (
            "Draft an AWS operating plan for: {idea}\n\n"
            "Cover minimal viable AWS setup, later scale path, security boundaries, "
            "cost controls, observability, deployment flow, and operational risks."
        ),
    },
    {
        "id": "backend-implementation-plan",
        "name": "Backend implementation plan",
        "phase": "engineering",
        "owner_agent_id": "backend-engineer",
        "sort_order": 55,
        "doc_type": "implementation-plan",
        "priority": "high",
        "title_template": "Backend implementation plan for {project_name}",
        "prompt_template": (
            "Draft the backend implementation plan for: {idea}\n\n"
            "Cover service boundaries, APIs, data model, background jobs, integration "
            "points, error handling, observability, and integration tests."
        ),
    },
    {
        "id": "frontend-implementation-plan",
        "name": "Frontend implementation plan",
        "phase": "engineering",
        "owner_agent_id": "frontend-engineer",
        "sort_order": 57,
        "doc_type": "implementation-plan",
        "priority": "high",
        "title_template": "Frontend implementation plan for {project_name}",
        "prompt_template": (
            "Draft the frontend implementation plan for: {idea}\n\n"
            "Use less-is-more UI judgment. Cover core screens, state flow, accessibility, "
            "empty/loading/error states, and end-to-end tests."
        ),
    },
    {
        "id": "testing-strategy",
        "name": "Testing strategy",
        "phase": "quality",
        "owner_agent_id": "test-automation-agent",
        "sort_order": 60,
        "doc_type": "test-plan",
        "priority": "high",
        "title_template": "Testing strategy for {project_name}",
        "prompt_template": (
            "Create a testing strategy for this product idea: {idea}\n\n"
            "Require unit, integration, end-to-end, regression, observability, "
            "and acceptance test coverage. Identify test gaps and launch blockers."
        ),
    },
    {
        "id": "marketing-positioning",
        "name": "Marketing positioning",
        "phase": "marketing",
        "owner_agent_id": "marketing-agent",
        "sort_order": 70,
        "doc_type": "marketing",
        "priority": "medium",
        "title_template": "Marketing positioning for {project_name}",
        "prompt_template": (
            "Create positioning for this startup idea: {idea}\n\n"
            "Return target audience, category, value proposition, proof points, "
            "launch message, channels, and first experiments."
        ),
    },
    {
        "id": "qa-critic-review",
        "name": "QA / critic review",
        "phase": "quality",
        "owner_agent_id": "qa-critic",
        "sort_order": 80,
        "doc_type": "review",
        "priority": "high",
        "title_template": "Critical review for {project_name}",
        "prompt_template": (
            "Critically review this startup idea and the expected plan set: {idea}\n\n"
            "Find contradictions, weak assumptions, missing tests, operational risks, "
            "unclear decisions, and questions the founder must answer."
        ),
    },
    {
        "id": "founder-decision-memo",
        "name": "Founder decision memo",
        "phase": "orchestration",
        "owner_agent_id": "chief-of-staff",
        "sort_order": 90,
        "doc_type": "decision-memo",
        "priority": "high",
        "title_template": "Founder decision memo for {project_name}",
        "prompt_template": (
            "Prepare the founder decision memo for this startup idea: {idea}\n\n"
            "Synthesize research, product, engineering, testing, and marketing work into "
            "decisions needed, risks, recommended next step, and what not to build yet."
        ),
    },
]
