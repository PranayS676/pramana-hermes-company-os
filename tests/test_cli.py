from hermes_company_os.cli import DEFAULT_HOST, DEFAULT_PORT, server_config_from_env


def test_cli_defaults_to_setup_runner_dashboard_port(monkeypatch):
    monkeypatch.delenv("HERMES_COMPANY_OS_HOST", raising=False)
    monkeypatch.delenv("HERMES_COMPANY_OS_PORT", raising=False)

    host, port = server_config_from_env()

    assert host == DEFAULT_HOST
    assert port == DEFAULT_PORT
    assert port == 8002


def test_cli_allows_dashboard_host_and_port_override(monkeypatch):
    monkeypatch.setenv("HERMES_COMPANY_OS_HOST", "0.0.0.0")
    monkeypatch.setenv("HERMES_COMPANY_OS_PORT", "8010")

    assert server_config_from_env() == ("0.0.0.0", 8010)
