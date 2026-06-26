from hermes_company_os.kanban_client import KanbanClient


def test_extract_task_id_from_json_id():
    assert KanbanClient._extract_task_id('{"id": "t_abc"}') == "t_abc"


def test_extract_task_id_from_nested_task():
    assert KanbanClient._extract_task_id('{"task": {"id": "t_nested"}}') == "t_nested"


def test_extract_task_id_returns_empty_for_non_json():
    assert KanbanClient._extract_task_id("Created t_abc") == ""


def test_run_uses_resolved_executable_path(monkeypatch):
    calls = {}

    def fake_which(command):
        assert command == "hermes"
        return r"C:\Users\masadis\.local\bin\hermes.bat"

    class Completed:
        returncode = 0
        stdout = '{"ok": true}'
        stderr = ""

    def fake_run(args, **kwargs):
        calls["args"] = args
        calls["kwargs"] = kwargs
        return Completed()

    monkeypatch.setattr("hermes_company_os.kanban_client.shutil.which", fake_which)
    monkeypatch.setattr("hermes_company_os.kanban_client.subprocess.run", fake_run)

    result = KanbanClient().diagnostics()

    assert result.ok is True
    assert calls["args"] == [
        r"C:\Users\masadis\.local\bin\hermes.bat",
        "kanban",
        "diagnostics",
        "--json",
    ]
    assert calls["kwargs"]["check"] is False
