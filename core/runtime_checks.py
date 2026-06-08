"""Runtime environment checks for OmniFinance.

The Streamlit app depends on relatively new Streamlit APIs and optional export
features. This module provides lightweight, testable checks that can be shown in
UI before users hit a cryptic traceback.
"""

from __future__ import annotations

import importlib.util
import os
import platform
import sys
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path
from typing import Literal

RuntimeStatus = Literal["ok", "warning", "error"]


@dataclass(frozen=True)
class RuntimeCheck:
    """One runtime check result."""

    key: str
    label: str
    status: RuntimeStatus
    message: str
    hint: str = ""


@dataclass(frozen=True)
class RuntimeReport:
    """Aggregated runtime status."""

    checks: tuple[RuntimeCheck, ...]

    @property
    def status(self) -> RuntimeStatus:
        if any(check.status == "error" for check in self.checks):
            return "error"
        if any(check.status == "warning" for check in self.checks):
            return "warning"
        return "ok"

    @property
    def summary(self) -> str:
        counts = {"ok": 0, "warning": 0, "error": 0}
        for check in self.checks:
            counts[check.status] += 1
        if counts["error"]:
            return f"{counts['error']} 项错误，{counts['warning']} 项提醒"
        if counts["warning"]:
            return f"{counts['warning']} 项提醒，其余正常"
        return "全部检查通过"


def _parse_version(version: str) -> tuple[int, ...]:
    """Parse a package version into a comparable numeric prefix."""
    parts: list[int] = []
    for token in version.replace("-", ".").split("."):
        digits = "".join(ch for ch in token if ch.isdigit())
        if not digits:
            break
        parts.append(int(digits))
    return tuple(parts or [0])


def _version_at_least(current: str, minimum: str) -> bool:
    current_parts = _parse_version(current)
    minimum_parts = _parse_version(minimum)
    width = max(len(current_parts), len(minimum_parts))
    return current_parts + (0,) * (width - len(current_parts)) >= minimum_parts + (0,) * (width - len(minimum_parts))


def check_python_version(minimum: tuple[int, int] = (3, 10)) -> RuntimeCheck:
    current = sys.version_info
    current_label = f"{current.major}.{current.minor}.{current.micro}"
    minimum_label = ".".join(str(part) for part in minimum)
    if (current.major, current.minor) >= minimum:
        return RuntimeCheck("python", "Python", "ok", f"Python {current_label}")
    return RuntimeCheck(
        "python",
        "Python",
        "error",
        f"Python {current_label} 低于要求 {minimum_label}+",
        f"请升级运行环境到 Python {minimum_label} 或更高版本。",
    )


def check_package_version(
    package_name: str,
    *,
    label: str | None = None,
    minimum: str | None = None,
    required: bool = True,
) -> RuntimeCheck:
    """Check whether a package is installed and optionally satisfies a minimum version."""
    display = label or package_name
    try:
        current = metadata.version(package_name)
    except metadata.PackageNotFoundError:
        status: RuntimeStatus = "error" if required else "warning"
        severity = "缺失" if required else "未安装"
        return RuntimeCheck(
            package_name,
            display,
            status,
            f"{display} {severity}",
            f"请安装依赖：pip install {package_name}" if required else "这是可选能力，未安装时相关功能会降级。",
        )

    if minimum and not _version_at_least(current, minimum):
        return RuntimeCheck(
            package_name,
            display,
            "error" if required else "warning",
            f"{display} {current} 低于要求 {minimum}+",
            f"请执行：pip install -U '{package_name}>={minimum}'",
        )
    return RuntimeCheck(package_name, display, "ok", f"{display} {current}")


def check_importable(module_name: str, *, label: str | None = None, required: bool = False) -> RuntimeCheck:
    """Check whether an import module can be resolved without importing it."""
    display = label or module_name
    if importlib.util.find_spec(module_name) is not None:
        return RuntimeCheck(module_name, display, "ok", f"{display} 可用")
    status: RuntimeStatus = "error" if required else "warning"
    return RuntimeCheck(
        module_name,
        display,
        status,
        f"{display} 未安装",
        "这是可选能力，未安装时相关功能会降级。" if not required else f"请安装模块：{module_name}",
    )


def check_data_directory(data_dir: str | Path | None = None) -> RuntimeCheck:
    """Check whether the local OmniFinance data directory is writable."""
    target = Path(data_dir) if data_dir is not None else Path(os.path.expanduser("~")) / ".omnifinance"
    try:
        target.mkdir(parents=True, exist_ok=True)
        probe = target / ".runtime_check"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
    except OSError as exc:
        return RuntimeCheck(
            "data_dir",
            "数据目录",
            "error",
            f"数据目录不可写：{target}",
            f"请检查目录权限或磁盘空间。原始错误：{exc}",
        )
    return RuntimeCheck("data_dir", "数据目录", "ok", f"可写：{target}")


def build_runtime_report(data_dir: str | Path | None = None) -> RuntimeReport:
    """Run lightweight runtime checks for the current process."""
    checks = [
        check_python_version(),
        check_package_version("streamlit", label="Streamlit", minimum="1.36.0"),
        check_package_version("pandas", label="Pandas"),
        check_package_version("plotly", label="Plotly"),
        check_package_version("yfinance", label="Yahoo Finance 数据源"),
        check_package_version("akshare", label="AkShare 数据源", required=False),
        check_importable("weasyprint", label="PDF 原生导出", required=False),
        check_data_directory(data_dir),
    ]
    return RuntimeReport(tuple(checks))


def runtime_fingerprint(report: RuntimeReport) -> str:
    """Return a concise support fingerprint for bug reports."""
    return " | ".join(
        [
            f"OS={platform.system()} {platform.release()}",
            f"Python={sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            f"Status={report.status}",
            report.summary,
        ]
    )
