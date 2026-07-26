#!/usr/bin/env python3
"""Deterministic local support for SellerSprite export workflows."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen


SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = SKILL_DIR / "config.json"
TEMP_SUFFIXES = (".crdownload", ".download", ".part", ".tmp")
ALLOWED_DOWNLOAD_SUFFIXES = (".csv", ".xlsx", ".xls", ".zip")
FORBIDDEN_KEY_PARTS = (
    "password",
    "secret",
    "token",
    "cookie",
    "local_storage",
    "session_storage",
    "dom_snapshot",
)


class WorkflowError(Exception):
    def __init__(self, message: str, code: int = 2, details: Any = None):
        super().__init__(message)
        self.code = code
        self.details = details


def _path(value: str | Path, base: Path | None = None) -> Path:
    expanded = Path(os.path.expandvars(os.path.expanduser(str(value))))
    if not expanded.is_absolute() and base is not None:
        expanded = base / expanded
    return expanded.resolve()


def _load_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            value = json.load(handle)
    except FileNotFoundError as exc:
        raise WorkflowError(f"JSON 文件不存在: {path}") from exc
    except json.JSONDecodeError as exc:
        raise WorkflowError(f"JSON 格式无效: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise WorkflowError(f"JSON 顶层必须是对象: {path}")
    return value


def _atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    temporary.replace(path)


def _json_print(value: Any, stream: Any = sys.stdout) -> None:
    json.dump(value, stream, ensure_ascii=False, indent=2)
    stream.write("\n")


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _file_record(path: Path, source: Path | None = None) -> dict[str, Any]:
    record = {
        "path": str(path),
        "filename": path.name,
        "size": path.stat().st_size,
        "sha256": _sha256(path),
    }
    if source is not None:
        record["source"] = str(source)
    return record


def _validate_config(config: dict[str, Any]) -> None:
    if config.get("schema_version") != 1:
        raise WorkflowError("config.json schema_version 必须为 1")
    for key in ("sellersprite", "chrome_profile", "paths", "polling"):
        if not isinstance(config.get(key), dict):
            raise WorkflowError(f"config.json 缺少对象: {key}")
    service = config["sellersprite"]
    for key in ("welcome_url", "login_url", "export_log_url", "username", "password_env"):
        if not str(service.get(key, "")).strip():
            raise WorkflowError(f"config.json 缺少 sellersprite.{key}")
    if not service.get("download_hosts") or not all(str(host).strip() for host in service["download_hosts"]):
        raise WorkflowError("config.json 缺少 sellersprite.download_hosts")
    profile = config["chrome_profile"]
    if not profile.get("preferred_names") or not profile.get("match_tokens"):
        raise WorkflowError("Chrome Profile 匹配规则不能为空")


def _load_config(path: Path) -> dict[str, Any]:
    config = _load_json(path)
    _validate_config(config)
    return config


def _memory_path(config: dict[str, Any], override: str | None = None) -> Path:
    return _path(override or config["paths"]["memory_file"], SKILL_DIR)


def _load_memory(path: Path) -> dict[str, Any]:
    memory = _load_json(path)
    if memory.get("schema_version") != 1 or not isinstance(memory.get("workflows"), list):
        raise WorkflowError(f"流程记忆格式无效: {path}")
    return memory


def _manifest_path(run_dir: Path) -> Path:
    return run_dir / "logs" / "run.json"


def _load_manifest(run_dir: Path) -> tuple[Path, dict[str, Any]]:
    path = _manifest_path(run_dir)
    return path, _load_json(path)


def _update_manifest(run_dir: Path, updater: Any) -> dict[str, Any]:
    path, manifest = _load_manifest(run_dir)
    updater(manifest)
    manifest["updated_at"] = _now()
    _atomic_write_json(path, manifest)
    return manifest


def _safe_segment(value: str, fallback: str) -> str:
    cleaned = re.sub(r"[\\/:*?\"<>|\s]+", "_", str(value)).strip("._")
    return cleaned[:80] or fallback


def _parse_json_object(value: str, label: str) -> dict[str, Any]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise WorkflowError(f"{label} 不是有效 JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise WorkflowError(f"{label} 必须是 JSON 对象")
    return parsed


def _parse_json_array(value: str, label: str) -> list[Any]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise WorkflowError(f"{label} 不是有效 JSON: {exc}") from exc
    if not isinstance(parsed, list):
        raise WorkflowError(f"{label} 必须是 JSON 数组")
    return parsed


def _parse_since(value: str) -> float:
    try:
        return float(value)
    except ValueError:
        pass
    try:
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except ValueError as exc:
        raise WorkflowError(f"无法解析 --since: {value}") from exc


def _normalize(value: str) -> str:
    return re.sub(r"[\s_-]+", "", str(value).strip().casefold())


def _contains_forbidden_key(value: Any) -> list[str]:
    matches: list[str] = []

    def visit(current: Any, prefix: str) -> None:
        if isinstance(current, dict):
            for key, child in current.items():
                key_text = str(key).casefold()
                path = f"{prefix}.{key}" if prefix else str(key)
                if any(part in key_text for part in FORBIDDEN_KEY_PARTS):
                    matches.append(path)
                visit(child, path)
        elif isinstance(current, list):
            for index, child in enumerate(current):
                visit(child, f"{prefix}[{index}]")

    visit(value, "")
    return matches


def preflight(config: dict[str, Any], workspace: Path, memory_override: str | None, require_password: bool) -> dict[str, Any]:
    if not workspace.is_dir():
        raise WorkflowError(f"项目目录不存在: {workspace}")
    if not os.access(workspace, os.W_OK):
        raise WorkflowError(f"项目目录不可写: {workspace}")
    download_dir = _path(config["paths"]["download_dir"])
    if not download_dir.is_dir():
        raise WorkflowError(f"下载目录不存在: {download_dir}")
    memory_path = _memory_path(config, memory_override)
    memory = _load_memory(memory_path)
    password_env = config["sellersprite"]["password_env"]
    password_present = bool(os.environ.get(password_env))
    if require_password and not password_present:
        raise WorkflowError(f"需要环境变量: {password_env}", code=4)
    output_root = workspace / config["paths"]["output_dir_name"]
    return {
        "ok": True,
        "workspace": str(workspace),
        "download_dir": str(download_dir),
        "output_root": str(output_root),
        "memory_file": str(memory_path),
        "workflow_count": len(memory["workflows"]),
        "password_env": password_env,
        "password_present": password_present,
        "profile_match": config["chrome_profile"],
    }


def match_profile(config: dict[str, Any], profiles: list[Any]) -> dict[str, Any]:
    candidates = []
    preferred = {_normalize(name) for name in config["chrome_profile"]["preferred_names"]}
    tokens = [_normalize(token) for token in config["chrome_profile"]["match_tokens"]]
    for profile in profiles:
        if not isinstance(profile, dict):
            continue
        name = str(profile.get("profileName") or profile.get("metadata", {}).get("profileName") or "").strip()
        browser_id = str(profile.get("id", "")).strip()
        if not name or not browser_id:
            continue
        normalized = _normalize(name)
        exact = normalized in preferred
        related = any(token and token in normalized for token in tokens)
        if exact or related:
            candidates.append({"id": browser_id, "profile_name": name, "exact": exact})
    exact_matches = [item for item in candidates if item["exact"]]
    if len(exact_matches) == 1:
        return {"ok": True, "match": exact_matches[0], "candidates": candidates}
    if len(exact_matches) > 1:
        raise WorkflowError("存在多个完全匹配的 SellerSprite Chrome Profile", code=3, details=exact_matches)
    if len(candidates) == 1:
        return {"ok": True, "match": candidates[0], "candidates": candidates}
    if not candidates:
        return {
            "ok": False,
            "reason": "not_found",
            "create_name": config["chrome_profile"]["create_name"],
            "candidates": [],
        }
    raise WorkflowError("存在多个相关 Chrome Profile，无法唯一选择", code=3, details=candidates)


def prepare_run(
    config: dict[str, Any],
    workspace: Path,
    tool: str,
    marketplace: str,
    parameters: dict[str, Any],
    timestamp: str | None,
) -> dict[str, Any]:
    preflight(config, workspace, None, False)
    stamp = timestamp or dt.datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
    run_root = workspace / config["paths"]["output_dir_name"] / "runs"
    base = run_root / f"{stamp}_{_safe_segment(tool, 'tool')}_{_safe_segment(marketplace, 'marketplace')}"
    run_dir = base
    suffix = 2
    while run_dir.exists():
        run_dir = Path(f"{base}_{suffix:02d}")
        suffix += 1
    (run_dir / "output").mkdir(parents=True)
    (run_dir / "logs").mkdir()
    now = _now()
    manifest = {
        "schema_version": 1,
        "skill_name": config.get("skill_name", "kjxj-export-ss-data"),
        "created_at": now,
        "updated_at": now,
        "workspace": str(workspace),
        "run_dir": str(run_dir),
        "tool": tool,
        "marketplace": marketplace,
        "parameters": parameters,
        "status": "prepared",
        "browser": {"status": "pending"},
        "export": {"status": "pending", "baseline": []},
        "downloads": [],
    }
    _atomic_write_json(_manifest_path(run_dir), manifest)
    return {"ok": True, "run_dir": str(run_dir), "manifest": str(_manifest_path(run_dir))}


def resolve_workflow(memory: dict[str, Any], tool: str, marketplace: str | None, parameters: dict[str, Any]) -> dict[str, Any]:
    requested = _normalize(tool)
    matches = []
    for workflow in memory["workflows"]:
        names = [workflow.get("id", ""), workflow.get("name", ""), *workflow.get("aliases", [])]
        if requested in {_normalize(name) for name in names if name}:
            matches.append(workflow)
    if not matches:
        raise WorkflowError(f"尚未记忆该流程: {tool}", code=3)
    if len(matches) > 1:
        raise WorkflowError(f"流程名称存在歧义: {tool}", code=3, details=[item.get("id") for item in matches])
    workflow = matches[0]
    resolved = dict(workflow.get("defaults", {}))
    resolved.update(parameters)
    schema = workflow.get("parameter_schema", {})
    missing = [
        key
        for key, definition in schema.items()
        if definition.get("required") and (key not in resolved or resolved[key] in (None, ""))
    ]
    if missing:
        raise WorkflowError("缺少必填参数", code=3, details=missing)
    marketplace_info = workflow.get("marketplace", {})
    resolved_marketplace = marketplace or marketplace_info.get("default")
    if not resolved_marketplace:
        raise WorkflowError("缺少站点参数", code=3)
    return {
        "ok": True,
        "workflow_id": workflow["id"],
        "workflow_version": workflow.get("version", 1),
        "tool": workflow["name"],
        "marketplace": resolved_marketplace,
        "parameters": resolved,
        "entry_url": workflow.get("entry_url", ""),
        "menu_path": workflow.get("menu_path", []),
        "marketplace_control": marketplace_info.get("control", {}),
        "parameter_schema": schema,
        "steps": workflow.get("steps", []),
        "export_source": workflow.get("export_source", ""),
    }


def record_browser(run_dir: Path, profile_name: str, login_status: str) -> dict[str, Any]:
    record = {"status": "verified", "profile_name": profile_name, "login_status": login_status, "verified_at": _now()}

    def updater(manifest: dict[str, Any]) -> None:
        manifest["browser"] = record
        manifest["status"] = "browser_verified"

    _update_manifest(run_dir, updater)
    return {"ok": True, "browser": record}


def _bounded_export_rows(rows: list[Any]) -> list[dict[str, str]]:
    if len(rows) > 100:
        raise WorkflowError("导出基线最多记录 100 行")
    result = []
    allowed = ("source", "generated_at", "status", "identifier")
    for row in rows:
        if not isinstance(row, dict):
            raise WorkflowError("导出基线中的每一行必须是对象")
        result.append({key: str(row[key])[:500] for key in allowed if row.get(key) is not None})
    return result


def record_export_baseline(run_dir: Path, rows: list[Any]) -> dict[str, Any]:
    bounded = _bounded_export_rows(rows)

    def updater(manifest: dict[str, Any]) -> None:
        manifest.setdefault("export", {})["baseline"] = bounded
        manifest["export"]["baseline_recorded_at"] = _now()
        manifest["export"]["status"] = "baseline_recorded"

    _update_manifest(run_dir, updater)
    return {"ok": True, "row_count": len(bounded)}


def record_export_job(run_dir: Path, source: str, generated_at: str, status: str, identifier: str | None) -> dict[str, Any]:
    job = {
        "source": source,
        "generated_at": generated_at,
        "status": status,
        "identifier": identifier or "",
        "observed_at": _now(),
    }

    def updater(manifest: dict[str, Any]) -> None:
        manifest.setdefault("export", {})["job"] = job
        manifest["export"]["status"] = "complete" if status == "已完成" else "waiting"
        manifest["status"] = "export_ready" if status == "已完成" else "export_waiting"

    _update_manifest(run_dir, updater)
    return {"ok": True, "job": job}


def _download_candidates(directory: Path, since: float, pattern: str | None) -> list[Path]:
    regex = re.compile(pattern, re.IGNORECASE) if pattern else None
    candidates = []
    for path in directory.iterdir():
        if not path.is_file() or path.name.startswith((".", "~$", ".~")):
            continue
        if path.name.casefold().endswith(TEMP_SUFFIXES):
            continue
        stat = path.stat()
        if stat.st_mtime + 0.001 < since or stat.st_size <= 0:
            continue
        if regex and not regex.search(path.name):
            continue
        candidates.append(path)
    return sorted(candidates, key=lambda item: item.stat().st_mtime, reverse=True)


def _unique_destination(directory: Path, filename: str) -> Path:
    candidate = directory / filename
    if not candidate.exists():
        return candidate
    stem = candidate.stem
    suffix = candidate.suffix
    counter = 2
    while True:
        alternative = directory / f"{stem}_{counter:02d}{suffix}"
        if not alternative.exists():
            return alternative
        counter += 1


def _validate_download_url(config: dict[str, Any], url: str) -> None:
    parsed = urlparse(url)
    allowed_hosts = {str(host).strip().casefold() for host in config["sellersprite"]["download_hosts"]}
    if parsed.scheme.casefold() != "https" or (parsed.hostname or "").casefold() not in allowed_hosts:
        raise WorkflowError("下载链接必须使用配置允许的 SellerSprite HTTPS 域名", code=3)


def fetch_download(
    config: dict[str, Any],
    url: str,
    download_dir: str | None,
    filename: str | None,
    timeout: int | None,
) -> dict[str, Any]:
    _validate_download_url(config, url)
    parsed = urlparse(url)
    source_name = filename or Path(unquote(parsed.path)).name
    if not source_name or Path(source_name).name != source_name:
        raise WorkflowError("下载文件名无效", code=3)
    if Path(source_name).suffix.casefold() not in ALLOWED_DOWNLOAD_SUFFIXES:
        raise WorkflowError("下载文件扩展名不受支持", code=3)
    directory = _path(download_dir or config["paths"]["download_dir"])
    if not directory.is_dir():
        raise WorkflowError(f"下载目录不存在: {directory}")
    destination = _unique_destination(directory, source_name).resolve()
    temporary = destination.with_suffix(destination.suffix + ".part")
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urlopen(request, timeout=timeout or config["polling"]["download_timeout_seconds"]) as response:
            _validate_download_url(config, response.geturl())
            with temporary.open("wb") as handle:
                shutil.copyfileobj(response, handle)
        if temporary.stat().st_size <= 0:
            raise WorkflowError("SellerSprite 下载响应为空", code=4)
        temporary.replace(destination)
    except WorkflowError:
        temporary.unlink(missing_ok=True)
        raise
    except Exception as exc:
        temporary.unlink(missing_ok=True)
        raise WorkflowError(f"SellerSprite 文件下载失败: {type(exc).__name__}", code=4) from exc
    record = _file_record(destination)
    record["downloaded_at"] = _now()
    return {"ok": True, "download": record}


def collect_download(
    config: dict[str, Any],
    run_dir: Path,
    since: str,
    download_dir: str | None,
    timeout: int | None,
    interval: float | None,
    stable_required: int | None,
    pattern: str | None,
) -> dict[str, Any]:
    directory = _path(download_dir or config["paths"]["download_dir"])
    if not directory.is_dir():
        raise WorkflowError(f"下载目录不存在: {directory}")
    _, manifest = _load_manifest(run_dir)
    deadline = time.monotonic() + (timeout if timeout is not None else config["polling"]["download_timeout_seconds"])
    poll_interval = interval if interval is not None else config["polling"]["download_interval_seconds"]
    required = stable_required if stable_required is not None else config["polling"]["stable_observations"]
    since_epoch = _parse_since(since)
    previous: tuple[str, int] | None = None
    stable = 0
    selected: Path | None = None
    while time.monotonic() <= deadline:
        candidates = _download_candidates(directory, since_epoch, pattern)
        if len(candidates) > 1:
            raise WorkflowError("发现多个符合条件的新下载文件，无法唯一选择", code=3, details=[str(item) for item in candidates])
        if candidates:
            candidate = candidates[0]
            current = (str(candidate), candidate.stat().st_size)
            stable = stable + 1 if current == previous else 1
            previous = current
            if stable >= required:
                selected = candidate
                break
        time.sleep(poll_interval)
    if selected is None:
        raise WorkflowError(f"在限定时间内未发现稳定的下载文件: {directory}", code=4)
    destination = _unique_destination(run_dir / "output", selected.name).resolve()
    shutil.copy2(selected, destination)
    record = _file_record(destination, selected)
    record["collected_at"] = _now()

    def updater(value: dict[str, Any]) -> None:
        value.setdefault("downloads", []).append(record)
        value["status"] = "downloaded"

    _update_manifest(run_dir, updater)
    return {"ok": True, "download": record, "run_dir": manifest["run_dir"]}


def _validate_workflow(workflow: dict[str, Any]) -> None:
    required = ("id", "name", "defaults", "parameter_schema", "steps", "export_source")
    missing = [key for key in required if key not in workflow]
    if missing:
        raise WorkflowError("流程定义缺少字段", details=missing)
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", str(workflow["id"])):
        raise WorkflowError("流程 id 必须使用小写 ASCII kebab-case")
    if not isinstance(workflow["defaults"], dict) or not isinstance(workflow["parameter_schema"], dict):
        raise WorkflowError("defaults 和 parameter_schema 必须是对象")
    if not isinstance(workflow["steps"], list):
        raise WorkflowError("steps 必须是数组")
    forbidden = _contains_forbidden_key(workflow)
    if forbidden:
        raise WorkflowError("流程定义包含禁止保存的敏感键", details=forbidden)


def record_workflow(config: dict[str, Any], run_dir: Path, workflow: dict[str, Any], memory_override: str | None) -> dict[str, Any]:
    _validate_workflow(workflow)
    _, manifest = _load_manifest(run_dir)
    downloads = manifest.get("downloads", [])
    if not downloads:
        raise WorkflowError("只有成功收集下载文件后才能写入流程记忆", code=4)
    for item in downloads:
        path = _path(item["path"])
        if not path.is_file() or path.stat().st_size <= 0 or _sha256(path) != item.get("sha256"):
            raise WorkflowError(f"下载记录验证失败: {path}")
    memory_path = _memory_path(config, memory_override)
    memory = _load_memory(memory_path)
    existing_index = next((index for index, item in enumerate(memory["workflows"]) if item.get("id") == workflow["id"]), None)
    previous_version = memory["workflows"][existing_index].get("version", 0) if existing_index is not None else 0
    saved = dict(workflow)
    saved["version"] = previous_version + 1
    saved["last_successful_at"] = _now()
    saved["source_run"] = str(run_dir)
    if existing_index is None:
        memory["workflows"].append(saved)
    else:
        memory["workflows"][existing_index] = saved
    aliases: dict[str, str] = {}
    for item in memory["workflows"]:
        for name in [item.get("id", ""), item.get("name", ""), *item.get("aliases", [])]:
            normalized = _normalize(name)
            if not normalized:
                continue
            owner = aliases.get(normalized)
            if owner and owner != item["id"]:
                raise WorkflowError("流程别名与其他流程冲突", details={"alias": name, "workflows": [owner, item["id"]]})
            aliases[normalized] = item["id"]
    memory["updated_at"] = _now()
    _atomic_write_json(memory_path, memory)

    def updater(value: dict[str, Any]) -> None:
        value["workflow_memory"] = {"id": saved["id"], "version": saved["version"], "path": str(memory_path)}

    _update_manifest(run_dir, updater)
    return {"ok": True, "workflow": saved, "memory_file": str(memory_path)}


def finalize_run(run_dir: Path) -> dict[str, Any]:
    manifest_path, manifest = _load_manifest(run_dir)
    downloads = manifest.get("downloads", [])
    if not downloads:
        raise WorkflowError("没有可交付的下载文件", code=4)
    verified = []
    for record in downloads:
        path = _path(record["path"])
        if not path.is_file() or path.stat().st_size <= 0:
            raise WorkflowError(f"下载文件不存在或为空: {path}")
        digest = _sha256(path)
        if digest != record.get("sha256"):
            raise WorkflowError(f"下载文件哈希不一致: {path}")
        verified.append(str(path))
    manifest["status"] = "complete"
    manifest["completed_at"] = _now()
    manifest["updated_at"] = manifest["completed_at"]
    _atomic_write_json(manifest_path, manifest)
    return {"ok": True, "run_dir": str(run_dir), "manifest": str(manifest_path), "outputs": verified}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    subparsers = parser.add_subparsers(dest="command", required=True)

    preflight_parser = subparsers.add_parser("preflight")
    preflight_parser.add_argument("--workspace", default=os.getcwd())
    preflight_parser.add_argument("--memory-file")
    preflight_parser.add_argument("--require-password", action="store_true")

    profile_parser = subparsers.add_parser("match-profile")
    profile_source = profile_parser.add_mutually_exclusive_group(required=True)
    profile_source.add_argument("--profiles-json")
    profile_source.add_argument("--profiles-file")

    prepare_parser = subparsers.add_parser("prepare-run")
    prepare_parser.add_argument("--workspace", default=os.getcwd())
    prepare_parser.add_argument("--tool", required=True)
    prepare_parser.add_argument("--marketplace", required=True)
    prepare_parser.add_argument("--params-json", default="{}")
    prepare_parser.add_argument("--timestamp", help=argparse.SUPPRESS)

    resolve_parser = subparsers.add_parser("resolve-workflow")
    resolve_parser.add_argument("--tool", required=True)
    resolve_parser.add_argument("--marketplace")
    resolve_parser.add_argument("--params-json", default="{}")
    resolve_parser.add_argument("--memory-file")

    browser_parser = subparsers.add_parser("record-browser")
    browser_parser.add_argument("--run-dir", required=True)
    browser_parser.add_argument("--profile-name", required=True)
    browser_parser.add_argument("--login-status", required=True, choices=("authenticated", "logged_out", "handoff"))

    baseline_parser = subparsers.add_parser("record-export-baseline")
    baseline_parser.add_argument("--run-dir", required=True)
    baseline_parser.add_argument("--rows-json", required=True)

    job_parser = subparsers.add_parser("record-export-job")
    job_parser.add_argument("--run-dir", required=True)
    job_parser.add_argument("--source", required=True)
    job_parser.add_argument("--generated-at", required=True)
    job_parser.add_argument("--status", required=True)
    job_parser.add_argument("--identifier")

    collect_parser = subparsers.add_parser("collect-download")
    collect_parser.add_argument("--run-dir", required=True)
    collect_parser.add_argument("--since", required=True)
    collect_parser.add_argument("--download-dir")
    collect_parser.add_argument("--timeout", type=int)
    collect_parser.add_argument("--interval", type=float, help=argparse.SUPPRESS)
    collect_parser.add_argument("--stable-observations", type=int, help=argparse.SUPPRESS)
    collect_parser.add_argument("--pattern")

    fetch_parser = subparsers.add_parser("fetch-download")
    fetch_parser.add_argument("--url", required=True)
    fetch_parser.add_argument("--download-dir")
    fetch_parser.add_argument("--filename")
    fetch_parser.add_argument("--timeout", type=int)

    workflow_parser = subparsers.add_parser("record-workflow")
    workflow_parser.add_argument("--run-dir", required=True)
    workflow_parser.add_argument("--workflow-file", required=True)
    workflow_parser.add_argument("--memory-file")

    finalize_parser = subparsers.add_parser("finalize-run")
    finalize_parser.add_argument("--run-dir", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        config = _load_config(_path(args.config))
        if args.command == "preflight":
            result = preflight(config, _path(args.workspace), args.memory_file, args.require_password)
        elif args.command == "match-profile":
            profiles = _parse_json_array(args.profiles_json, "--profiles-json") if args.profiles_json else _load_json_array_file(_path(args.profiles_file))
            result = match_profile(config, profiles)
        elif args.command == "prepare-run":
            result = prepare_run(config, _path(args.workspace), args.tool, args.marketplace, _parse_json_object(args.params_json, "--params-json"), args.timestamp)
        elif args.command == "resolve-workflow":
            memory = _load_memory(_memory_path(config, args.memory_file))
            result = resolve_workflow(memory, args.tool, args.marketplace, _parse_json_object(args.params_json, "--params-json"))
        elif args.command == "record-browser":
            result = record_browser(_path(args.run_dir), args.profile_name, args.login_status)
        elif args.command == "record-export-baseline":
            result = record_export_baseline(_path(args.run_dir), _parse_json_array(args.rows_json, "--rows-json"))
        elif args.command == "record-export-job":
            result = record_export_job(_path(args.run_dir), args.source, args.generated_at, args.status, args.identifier)
        elif args.command == "collect-download":
            result = collect_download(config, _path(args.run_dir), args.since, args.download_dir, args.timeout, args.interval, args.stable_observations, args.pattern)
        elif args.command == "fetch-download":
            result = fetch_download(config, args.url, args.download_dir, args.filename, args.timeout)
        elif args.command == "record-workflow":
            result = record_workflow(config, _path(args.run_dir), _load_json(_path(args.workflow_file)), args.memory_file)
        elif args.command == "finalize-run":
            result = finalize_run(_path(args.run_dir))
        else:
            parser.error(f"未知命令: {args.command}")
            return 2
        _json_print(result)
        return 0
    except WorkflowError as exc:
        payload = {"ok": False, "error": str(exc)}
        if exc.details is not None:
            payload["details"] = exc.details
        _json_print(payload, sys.stderr)
        return exc.code


def _load_json_array_file(path: Path) -> list[Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            value = json.load(handle)
    except FileNotFoundError as exc:
        raise WorkflowError(f"JSON 文件不存在: {path}") from exc
    except json.JSONDecodeError as exc:
        raise WorkflowError(f"JSON 格式无效: {path}: {exc}") from exc
    if not isinstance(value, list):
        raise WorkflowError(f"JSON 顶层必须是数组: {path}")
    return value


if __name__ == "__main__":
    raise SystemExit(main())
