from __future__ import annotations

import importlib.util
import json
import os
import tempfile
import time
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "export_support.py"
SPEC = importlib.util.spec_from_file_location("export_support", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class ExportSupportTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.workspace = self.root / "workspace"
        self.downloads = self.root / "downloads"
        self.workspace.mkdir()
        self.downloads.mkdir()
        self.memory_path = self.root / "workflows.json"
        self.memory_path.write_text(json.dumps({"schema_version": 1, "updated_at": None, "workflows": []}), encoding="utf-8")
        self.config = {
            "schema_version": 1,
            "skill_name": "kjxj-export-ss-data",
            "sellersprite": {
                "welcome_url": "https://www.sellersprite.com/v2/welcome",
                "login_url": "https://www.sellersprite.com/cn/w/user/login",
                "export_log_url": "https://www.sellersprite.com/v2/export-log",
                "download_hosts": ["o.sellersprite.com"],
                "username": "kjxjkj",
                "password_env": "TEST_SELLERSPRITE_PASSWORD",
            },
            "chrome_profile": {
                "preferred_names": ["卖家精灵", "SellerSprite"],
                "match_tokens": ["卖家精灵", "sellersprite"],
                "create_name": "卖家精灵",
            },
            "paths": {
                "download_dir": str(self.downloads),
                "output_dir_name": "seller_sprite_exports",
                "memory_file": str(self.memory_path),
            },
            "polling": {
                "export_interval_seconds": 10,
                "export_timeout_seconds": 300,
                "download_interval_seconds": 0.01,
                "download_timeout_seconds": 1,
                "stable_observations": 2,
            },
        }

    def tearDown(self) -> None:
        self.temp.cleanup()

    def prepare(self, stamp: str = "20260726_120000") -> Path:
        result = MODULE.prepare_run(self.config, self.workspace, "关键词挖掘", "德国站", {"keyword": "hundebett"}, stamp)
        return Path(result["run_dir"])

    def workflow(self) -> dict:
        return {
            "id": "keyword-mining",
            "name": "关键词挖掘",
            "aliases": ["关键词挖掘数据", "keyword mining"],
            "entry_url": "https://example.test/tool",
            "menu_path": ["工具", "关键词挖掘"],
            "marketplace": {"parameter": "marketplace", "default": "德国站", "control": {"label": "站点"}},
            "parameter_schema": {
                "keyword": {"label": "关键词", "required": True},
                "relevance_min": {"label": "相关度最小值", "required": False},
                "monthly_search_volume_min": {"label": "月搜索量最小值", "required": False},
            },
            "defaults": {"keyword": "hundebett", "relevance_min": 30, "monthly_search_volume_min": 1},
            "steps": [{"action": "fill", "target": "keyword"}],
            "export_source": "关键词挖掘",
        }

    def collect(self, run_dir: Path, filename: str = "keyword-export.xlsx") -> dict:
        source = self.downloads / filename
        source.write_bytes(b"test-export")
        return MODULE.collect_download(self.config, run_dir, str(time.time() - 1), None, 1, 0.01, 2, None)

    def test_preflight_reports_secret_presence_without_exposing_value(self) -> None:
        old = os.environ.get("TEST_SELLERSPRITE_PASSWORD")
        os.environ["TEST_SELLERSPRITE_PASSWORD"] = "do-not-print"
        try:
            result = MODULE.preflight(self.config, self.workspace, None, True)
            self.assertTrue(result["password_present"])
            self.assertNotIn("do-not-print", json.dumps(result))
        finally:
            if old is None:
                os.environ.pop("TEST_SELLERSPRITE_PASSWORD", None)
            else:
                os.environ["TEST_SELLERSPRITE_PASSWORD"] = old

    def test_profile_exact_match_wins_over_related(self) -> None:
        profiles = [
            {"id": "related", "profileName": "我的 SellerSprite 数据"},
            {"id": "exact", "profileName": "卖家精灵"},
        ]
        result = MODULE.match_profile(self.config, profiles)
        self.assertEqual(result["match"]["id"], "exact")

    def test_profile_unique_related_match(self) -> None:
        result = MODULE.match_profile(self.config, [{"id": "one", "metadata": {"profileName": "团队-卖家精灵-导出"}}])
        self.assertEqual(result["match"]["id"], "one")

    def test_profile_ambiguity_fails(self) -> None:
        with self.assertRaises(MODULE.WorkflowError) as context:
            MODULE.match_profile(self.config, [
                {"id": "one", "profileName": "SellerSprite A"},
                {"id": "two", "profileName": "SellerSprite B"},
            ])
        self.assertEqual(context.exception.code, 3)

    def test_prepare_run_does_not_overwrite(self) -> None:
        first = self.prepare()
        second = self.prepare()
        self.assertNotEqual(first, second)
        self.assertTrue(str(second).endswith("_02"))

    def test_resolve_merges_new_parameters_over_defaults(self) -> None:
        memory = {"schema_version": 1, "workflows": [self.workflow()]}
        result = MODULE.resolve_workflow(memory, "keyword mining", None, {"keyword": "dog bed", "relevance_min": 45})
        self.assertEqual(result["marketplace"], "德国站")
        self.assertEqual(result["parameters"]["keyword"], "dog bed")
        self.assertEqual(result["parameters"]["relevance_min"], 45)
        self.assertEqual(result["parameters"]["monthly_search_volume_min"], 1)

    def test_unknown_workflow_fails(self) -> None:
        with self.assertRaises(MODULE.WorkflowError) as context:
            MODULE.resolve_workflow({"schema_version": 1, "workflows": []}, "未知工具", "德国站", {})
        self.assertEqual(context.exception.code, 3)

    def test_collect_ignores_old_and_partial_files(self) -> None:
        run_dir = self.prepare()
        old = self.downloads / "old.xlsx"
        old.write_bytes(b"old")
        old_time = time.time() - 3600
        os.utime(old, (old_time, old_time))
        (self.downloads / "active.xlsx.crdownload").write_bytes(b"partial")
        result = self.collect(run_dir)
        self.assertEqual(Path(result["download"]["path"]).name, "keyword-export.xlsx")
        self.assertTrue((self.downloads / "keyword-export.xlsx").is_file())

    def test_collect_refuses_ambiguous_candidates(self) -> None:
        run_dir = self.prepare()
        since = str(time.time() - 1)
        (self.downloads / "one.xlsx").write_bytes(b"one")
        (self.downloads / "two.csv").write_bytes(b"two")
        with self.assertRaises(MODULE.WorkflowError) as context:
            MODULE.collect_download(self.config, run_dir, since, None, 1, 0.01, 1, None)
        self.assertEqual(context.exception.code, 3)

    def test_download_destination_is_versioned(self) -> None:
        run_dir = self.prepare()
        first = self.collect(run_dir, "same.xlsx")
        since = str(time.time() - 1)
        second = MODULE.collect_download(self.config, run_dir, since, None, 1, 0.01, 1, r"same\.xlsx")
        self.assertNotEqual(first["download"]["path"], second["download"]["path"])
        self.assertTrue(second["download"]["path"].endswith("same_02.xlsx"))

    def test_fetch_download_rejects_unapproved_url(self) -> None:
        with self.assertRaises(MODULE.WorkflowError) as context:
            MODULE.fetch_download(self.config, "https://example.test/export.xlsx", None, None, 1)
        self.assertEqual(context.exception.code, 3)

    def test_fetch_download_uses_verified_host_and_avoids_overwrite(self) -> None:
        class Response(BytesIO):
            def geturl(self) -> str:
                return "https://o.sellersprite.com/export.xlsx"

        url = "https://o.sellersprite.com/export.xlsx"
        with patch.object(MODULE, "urlopen", side_effect=[Response(b"first"), Response(b"second")]):
            first = MODULE.fetch_download(self.config, url, None, None, 1)
            second = MODULE.fetch_download(self.config, url, None, None, 1)
        self.assertEqual(Path(first["download"]["path"]).name, "export.xlsx")
        self.assertEqual(Path(second["download"]["path"]).name, "export_02.xlsx")
        self.assertEqual(Path(first["download"]["path"]).read_bytes(), b"first")
        self.assertEqual(Path(second["download"]["path"]).read_bytes(), b"second")

    def test_record_workflow_requires_download(self) -> None:
        run_dir = self.prepare()
        with self.assertRaises(MODULE.WorkflowError) as context:
            MODULE.record_workflow(self.config, run_dir, self.workflow(), None)
        self.assertEqual(context.exception.code, 4)

    def test_record_and_upgrade_workflow_after_download(self) -> None:
        first_run = self.prepare()
        self.collect(first_run)
        first = MODULE.record_workflow(self.config, first_run, self.workflow(), None)
        self.assertEqual(first["workflow"]["version"], 1)
        second_run = self.prepare("20260726_130000")
        old = self.downloads / "keyword-export.xlsx"
        old.unlink()
        self.collect(second_run, "keyword-export-v2.xlsx")
        updated = self.workflow()
        updated["defaults"]["relevance_min"] = 40
        second = MODULE.record_workflow(self.config, second_run, updated, None)
        self.assertEqual(second["workflow"]["version"], 2)
        self.assertEqual(MODULE._load_memory(self.memory_path)["workflows"][0]["defaults"]["relevance_min"], 40)

    def test_sensitive_workflow_keys_are_rejected(self) -> None:
        run_dir = self.prepare()
        self.collect(run_dir)
        workflow = self.workflow()
        workflow["password_value"] = "forbidden"
        with self.assertRaises(MODULE.WorkflowError):
            MODULE.record_workflow(self.config, run_dir, workflow, None)

    def test_finalize_verifies_hash(self) -> None:
        run_dir = self.prepare()
        collected = self.collect(run_dir)
        result = MODULE.finalize_run(run_dir)
        self.assertEqual(result["outputs"], [collected["download"]["path"]])
        Path(collected["download"]["path"]).write_bytes(b"tampered")
        with self.assertRaises(MODULE.WorkflowError):
            MODULE.finalize_run(run_dir)


if __name__ == "__main__":
    unittest.main()
