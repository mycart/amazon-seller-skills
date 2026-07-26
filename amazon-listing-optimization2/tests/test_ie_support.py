import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).parents[1]


class IrelandSupportTests(unittest.TestCase):
    def test_skill_and_fetcher_expose_ie(self):
        skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        fetcher = (SKILL_DIR / "scripts" / "fetch-listing.sh").read_text(encoding="utf-8")
        self.assertIn("US, UK, DE, FR, IT, ES, JP, CA, AU, IN, MX, BR, IE", skill)
        self.assertIn("Amazon US/UK/IE/AU/CA/IN", skill)
        self.assertIn('[ie]="www.amazon.ie"', fetcher)


if __name__ == "__main__":
    unittest.main()
