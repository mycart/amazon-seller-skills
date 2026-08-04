import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


VALIDATOR = load_module("rufus_qa_validator", ROOT / "scripts" / "validate-rufus-qa.py")


class RufusQaTests(unittest.TestCase):
    def complete_qa(self) -> dict:
        topics = (
            ["product_identity"] * 2
            + ["feature_material"] * 3
            + ["audience_use_case"] * 2
            + ["buyer_concern"] * 3
            + ["setup_care_included"] * 2
        )
        ids = [f"QA-{index:02d}" for index in range(1, 13)]
        return {
            "status": "complete",
            "target_count": 12,
            "marketplace": "DE",
            "language": "de_DE",
            "items": [
                {
                    "id": qa_id,
                    "topic": topic,
                    "question": f"Welche bestätigte Produkteigenschaft gilt für Anwendungsfall {index}?",
                    "answer": f"Die bestätigte Produkteigenschaft {index} ist in den Produktunterlagen dokumentiert.",
                    "question_zh": f"经确认的产品属性适用于场景 {index} 吗？",
                    "answer_zh": f"经确认的产品属性 {index} 已记录在商品资料中。",
                    "semantic_keywords": [f"produktmerkmal {index}"],
                    "evidence_refs": ["E-01"],
                }
                for index, (qa_id, topic) in enumerate(zip(ids, topics), start=1)
            ],
            "evidence": [
                {
                    "id": "E-01",
                    "source_type": "user",
                    "source_title": "用户提供的商品资料",
                    "source_url": "",
                    "retrieved_at": "",
                    "marketplace": "DE",
                    "verified_facts": ["用户资料确认了全部测试商品事实"],
                    "used_by": ids,
                }
            ],
            "limitations": [],
        }

    def test_complete_qa_validates_and_renders(self):
        qa = self.complete_qa()
        result = VALIDATOR.validate_rufus_qa(qa, "DE")
        self.assertTrue(result["ok"])
        self.assertEqual(result["qa_count"], 12)
        markdown = VALIDATOR.render_markdown(qa)
        self.assertIn("QA-12", markdown)
        self.assertIn("中文翻译：** 经确认的产品属性适用于场景 1 吗？", markdown)
        self.assertIn("中文证据附录", markdown)

    def test_duplicate_question_and_missing_direct_evidence_are_blocked(self):
        qa = self.complete_qa()
        qa["items"][1]["question"] = qa["items"][0]["question"]
        with self.assertRaisesRegex(ValueError, "问题重复"):
            VALIDATOR.validate_rufus_qa(qa)

        qa = self.complete_qa()
        qa["evidence"][0]["source_type"] = "amazon_review"
        qa["evidence"][0]["source_url"] = "https://www.amazon.de/example"
        qa["evidence"][0]["retrieved_at"] = "2026-07-29T10:00:00+00:00"
        with self.assertRaisesRegex(ValueError, "直接商品事实证据"):
            VALIDATOR.validate_rufus_qa(qa)

    def test_missing_chinese_translation_is_blocked(self):
        qa = self.complete_qa()
        del qa["items"][0]["answer_zh"]
        with self.assertRaisesRegex(ValueError, "answer_zh"):
            VALIDATOR.validate_rufus_qa(qa)

    def test_evidence_insufficient_accepts_supported_subset(self):
        qa = self.complete_qa()
        qa["status"] = "evidence_insufficient"
        qa["items"] = qa["items"][:2]
        qa["evidence"][0]["used_by"] = ["QA-01", "QA-02"]
        qa["limitations"] = ["现有资料只能支持产品身份问题，未补写无法验证的材质和场景内容。"]
        result = VALIDATOR.validate_rufus_qa(qa)
        self.assertEqual(result["qa_count"], 2)

if __name__ == "__main__":
    unittest.main()
