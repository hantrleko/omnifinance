import core.runtime_checks as runtime_checks
from core.runtime_checks import (
    RuntimeCheck,
    RuntimeReport,
    build_runtime_report,
    check_data_directory,
    check_importable,
    check_package_version,
    runtime_fingerprint,
)


def test_runtime_report_status_and_summary_prioritize_errors():
    report = RuntimeReport(
        (
            RuntimeCheck("a", "A", "ok", "ok"),
            RuntimeCheck("b", "B", "warning", "warn"),
            RuntimeCheck("c", "C", "error", "err"),
        )
    )

    assert report.status == "error"
    assert report.summary == "1 项错误，1 项提醒"


def test_runtime_report_summary_when_all_ok():
    report = RuntimeReport((RuntimeCheck("a", "A", "ok", "ok"),))

    assert report.status == "ok"
    assert report.summary == "全部检查通过"


def test_check_package_version_accepts_sufficient_version(monkeypatch):
    monkeypatch.setattr(runtime_checks.metadata, "version", lambda _: "1.40.2")

    result = check_package_version("streamlit", label="Streamlit", minimum="1.36.0")

    assert result.status == "ok"
    assert "1.40.2" in result.message


def test_check_package_version_flags_old_version(monkeypatch):
    monkeypatch.setattr(runtime_checks.metadata, "version", lambda _: "1.30.0")

    result = check_package_version("streamlit", label="Streamlit", minimum="1.36.0")

    assert result.status == "error"
    assert "低于要求" in result.message
    assert "pip install" in result.hint


def test_check_package_version_handles_optional_missing(monkeypatch):
    def _missing(_: str) -> str:
        raise runtime_checks.metadata.PackageNotFoundError

    monkeypatch.setattr(runtime_checks.metadata, "version", _missing)

    result = check_package_version("weasyprint", label="PDF 原生导出", required=False)

    assert result.status == "warning"
    assert "未安装" in result.message


def test_check_importable_uses_find_spec(monkeypatch):
    monkeypatch.setattr(runtime_checks.importlib.util, "find_spec", lambda module_name: object())

    result = check_importable("weasyprint", label="PDF 原生导出")

    assert result.status == "ok"


def test_check_data_directory_writes_probe_file(tmp_path):
    result = check_data_directory(tmp_path / "omnifinance")

    assert result.status == "ok"
    assert not (tmp_path / "omnifinance" / ".runtime_check").exists()


def test_build_runtime_report_includes_data_directory(tmp_path):
    report = build_runtime_report(tmp_path)

    keys = {check.key for check in report.checks}
    assert "python" in keys
    assert "streamlit" in keys
    assert "data_dir" in keys


def test_runtime_fingerprint_contains_status():
    report = RuntimeReport((RuntimeCheck("a", "A", "ok", "ok"),))

    fingerprint = runtime_fingerprint(report)

    assert "Python=" in fingerprint
    assert "Status=ok" in fingerprint
    assert "OS=" in fingerprint
