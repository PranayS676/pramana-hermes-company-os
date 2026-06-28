from hermes_company_os.settings import Settings, env_flag


def test_live_hermes_execution_flag_defaults_disabled(monkeypatch):
    monkeypatch.delenv("HERMES_LIVE_EXECUTION_ENABLED", raising=False)

    settings = Settings()

    assert settings.hermes_live_execution_enabled is False


def test_live_hermes_execution_flag_accepts_explicit_truthy_values(monkeypatch):
    monkeypatch.setenv("HERMES_LIVE_EXECUTION_ENABLED", "true")

    settings = Settings()

    assert settings.hermes_live_execution_enabled is True
    assert env_flag("HERMES_LIVE_EXECUTION_ENABLED") is True


def test_codex_execution_flag_defaults_disabled(monkeypatch):
    monkeypatch.delenv("HERMES_CODEX_EXECUTION_ENABLED", raising=False)

    settings = Settings()

    assert settings.codex_execution_enabled is False


def test_codex_execution_flag_accepts_explicit_truthy_values(monkeypatch):
    monkeypatch.setenv("HERMES_CODEX_EXECUTION_ENABLED", "true")

    settings = Settings()

    assert settings.codex_execution_enabled is True
    assert env_flag("HERMES_CODEX_EXECUTION_ENABLED") is True
