from hermes_company_os.readiness import ReadinessService


def test_readiness_summarizes_integrations(tmp_path):
    database_path = tmp_path / "company.db"
    database_path.touch()
    service = ReadinessService(database_path)

    items = service.check(
        agents=[],
        integrations=[
            {"category": "slack", "status": "configured"},
            {"category": "telegram", "status": "needs_input"},
            {"category": "runtime", "status": "deferred"},
        ],
    )

    by_id = {item.id: item for item in items}
    assert by_id["database"].status == "ready"
    assert by_id["integration-slack"].status == "ready"
    assert by_id["integration-telegram"].status == "needs_input"
    assert by_id["integration-runtime"].status == "deferred"
