import os

import pytest

from app.services.coding_studio_service import CodingStudioService


@pytest.fixture
def studio_service(tmp_path):
    # Setup mock workspace
    ws_dir = tmp_path / "workspace"
    ws_dir.mkdir()

    # Create dummy app files
    app_dir = ws_dir / "app"
    app_dir.mkdir()
    sample_py = app_dir / "sample.py"
    sample_py.write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")

    # Create dummy sensitive files
    secret_env = ws_dir / ".env"
    secret_env.write_text("SECRET_KEY=12345\n", encoding="utf-8")

    return CodingStudioService(workspace_path=str(ws_dir))


def test_path_resolution_and_security_guardrails(studio_service):
    # 1. Valid workspace path
    safe_path = studio_service.resolve_safe_path("app/sample.py")
    assert safe_path.endswith("app/sample.py")
    assert os.path.isabs(safe_path)

    # 2. Path traversal attack blocked
    with pytest.raises(PermissionError):
        studio_service.resolve_safe_path("../../etc/passwd")

    # 3. Sensitive .env file blocked
    with pytest.raises(PermissionError):
        studio_service.resolve_safe_path(".env")

    # 4. Git internal files blocked
    with pytest.raises(PermissionError):
        studio_service.resolve_safe_path(".git/config")


def test_list_workspace_files(studio_service):
    files = studio_service.list_workspace_files("app")
    assert len(files) >= 1
    sample = next((f for f in files if "sample.py" in f["path"]), None)
    assert sample is not None
    assert sample["name"] == "sample.py"
    assert sample["lines"] == 2
    assert not sample["is_dir"]


def test_read_code_file(studio_service):
    # 1. Read full file
    res = studio_service.read_code_file("app/sample.py")
    assert res["success"] is True
    assert "def add(a, b):" in res["content"]
    assert res["total_lines"] == 2
    assert res["language"] == "python"

    # 2. Read non-existent file
    res_missing = studio_service.read_code_file("app/missing.py")
    assert res_missing["success"] is False
    assert "찾을 수 없습니다" in res_missing["error"]


def test_generate_diff_preview(studio_service):
    diff_res = studio_service.generate_diff_preview(
        "app/sample.py",
        target_content="return a + b",
        replacement_content="return a + b  # added comment",
    )
    assert diff_res["success"] is True
    assert "+    return a + b  # added comment" in diff_res["diff"]
    assert "-    return a + b" in diff_res["diff"]
    assert diff_res["lines_added"] == 1
    assert diff_res["lines_removed"] == 1


def test_apply_patch_and_rollback(studio_service):
    # 1. Apply patch
    patch_res = studio_service.apply_code_patch(
        "app/sample.py",
        target_content="return a + b",
        replacement_content="return a + b + 1",
    )
    assert patch_res["success"] is True
    assert patch_res["backup_id"] is not None

    # Check updated content
    updated = studio_service.read_code_file("app/sample.py")
    assert "return a + b + 1" in updated["content"]

    # 2. Rollback
    rollback_res = studio_service.rollback_file("app/sample.py")
    assert rollback_res["success"] is True

    # Check restored content
    restored = studio_service.read_code_file("app/sample.py")
    assert "return a + b\n" in restored["content"]
    assert "return a + b + 1" not in restored["content"]


def test_format_code_card(studio_service):
    card = studio_service.format_code_card("app/sample.py")
    assert "### 📄 소스코드 확인:" in card
    assert "```python" in card
    assert "def add(a, b):" in card


def test_diagnose_test_failure(studio_service):
    sample_error = """
    def test_example():
>       assert add(1, 2) == 4
E       assert 3 == 4
    tests/test_sample.py:10: AssertionError
    """
    diagnosis = studio_service.diagnose_test_failure(sample_error)
    assert diagnosis["has_error"] is True
    assert "AssertionError" in diagnosis["error_type"]
    assert "test_sample.py" in diagnosis["file"]
