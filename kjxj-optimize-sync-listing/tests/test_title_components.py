import importlib.util
import unicodedata
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "validate-title-highlights.py"
SPEC = importlib.util.spec_from_file_location("title_highlights_validator", SCRIPT)
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


class TitleComponentTests(unittest.TestCase):
    def validate(self, title, highlights, **kwargs):
        return VALIDATOR.validate(title, highlights, "IE", **kwargs)

    def test_required_four_component_title_with_sku_in_title(self):
        result = self.validate(
            "CareCooo Cat Window Bed, Suction Cups, Grey, M",
            "foldable frame, washable cover, for indoor cats",
            brand="CareCooo",
            core_product_phrase="Cat Window Bed",
            differentiator="Suction Cups",
            sku_attributes=["Grey", "M"],
            sku_attribute_placement="title",
        )
        self.assertTrue(result["valid"], result["errors"])

    def test_german_cat_mat_title_pair_keeps_material_installation_protection_and_care(self):
        title = "CareCooo Kratzmatte selbstklebend aus Sisal für Sofa, Weiß 60 x 40 cm"
        highlights = (
            "Starke Klebestreifen und Klettband zur Wandmontage, schützt Sofa und Möbel, "
            "langlebiges Natursisal, einfach absaugbar"
        )
        result = VALIDATOR.validate(
            title,
            highlights,
            "DE",
            brand="CareCooo",
            core_product_phrase="Kratzmatte selbstklebend",
            sku_attributes=["Weiß", "60 x 40 cm"],
            sku_attribute_placement="title",
            required_core_keyword="kratzmatte selbstklebend",
        )
        self.assertTrue(result["valid"], result["errors"])
        self.assertEqual(result["title_characters"], 69)
        self.assertEqual(result["item_highlights_characters"], 117)
        self.assertEqual(result["item_highlights_phrase_count"], 4)
        self.assertEqual(result["informative_highlight_phrase_count"], 4)

    def test_brand_and_core_phrase_are_required_but_differentiator_is_optional(self):
        missing_core = self.validate(
            "CareCooo Cat Window Bed, Grey, M",
            "foldable frame, washable cover",
            brand="CareCooo",
            core_product_phrase="Cat Hammock",
            differentiator="Suction Cups",
            sku_attributes=["Grey", "M"],
            sku_attribute_placement="title",
        )
        self.assertFalse(missing_core["valid"])
        self.assertTrue(any("core_product_phrase" in error for error in missing_core["errors"]))

        no_differentiator = self.validate(
            "CareCooo Cat Window Bed, Grey, M",
            "foldable frame, washable cover",
            brand="CareCooo",
            core_product_phrase="Cat Window Bed",
            differentiator="",
            sku_attributes=["Grey", "M"],
            sku_attribute_placement="title",
        )
        self.assertTrue(no_differentiator["valid"], no_differentiator["errors"])

    def test_brand_precedes_core_but_reference_title_order_controls_other_phrases(self):
        wrong_title_order = self.validate(
            "Cat Window Bed CareCooo, Suction Cups, Grey, M",
            "foldable frame, washable cover",
            brand="CareCooo",
            core_product_phrase="Cat Window Bed",
            differentiator="Suction Cups",
            sku_attributes=["Grey", "M"],
            sku_attribute_placement="title",
        )
        self.assertFalse(wrong_title_order["valid"])
        self.assertTrue(any("brand before core" in error for error in wrong_title_order["errors"]))

        preserved_reference_order = self.validate(
            "CareCooo Cat Window Bed, Suction Cups, M, Grey",
            "foldable frame, washable cover",
            brand="CareCooo",
            core_product_phrase="Cat Window Bed",
            differentiator="Suction Cups",
            sku_attributes=["Grey", "M"],
            sku_attribute_placement="title",
        )
        self.assertTrue(preserved_reference_order["valid"], preserved_reference_order["errors"])

        sku_before_feature = self.validate(
            "CareCooo Cat Window Bed, Grey, M, Suction Cups",
            "foldable frame, washable cover",
            brand="CareCooo",
            core_product_phrase="Cat Window Bed",
            differentiator="Suction Cups",
            sku_attributes=["Grey", "M"],
            sku_attribute_placement="title",
        )
        self.assertTrue(sku_before_feature["valid"], sku_before_feature["errors"])

    def test_sku_moves_to_highlights_only_when_it_would_exceed_75_characters(self):
        long_title = "CareCooo Orthopedic Dog Bed, Removable Waterproof Memory Foam Zipper Cover"
        moved = self.validate(
            long_title,
            "Grey, XL, nonslip base, washable cover",
            brand="CareCooo",
            core_product_phrase="Orthopedic Dog Bed",
            differentiator="Removable Waterproof Memory Foam Zipper Cover",
            sku_attributes=["Grey", "XL"],
            sku_attribute_placement="item_highlights",
        )
        self.assertTrue(moved["valid"], moved["errors"])

        unnecessary_move = self.validate(
            "CareCooo Dog Bed, Memory Foam",
            "Grey, XL, nonslip base",
            brand="CareCooo",
            core_product_phrase="Dog Bed",
            differentiator="Memory Foam",
            sku_attributes=["Grey", "XL"],
            sku_attribute_placement="item_highlights",
        )
        self.assertFalse(unnecessary_move["valid"])
        self.assertTrue(any("still fit" in error for error in unnecessary_move["errors"]))

    def test_parent_without_sku_attributes_uses_not_applicable(self):
        result = self.validate(
            "CareCooo Cat Window Bed, Suction Cups",
            "foldable frame, washable cover, for indoor cats",
            brand="CareCooo",
            core_product_phrase="Cat Window Bed",
            differentiator="Suction Cups",
            sku_attributes=[],
            sku_attribute_placement="not_applicable",
        )
        self.assertTrue(result["valid"], result["errors"])

    def test_non_pet_product_uses_the_same_identity_and_sku_rules(self):
        result = self.validate(
            "BlendCo Portable Blender, White, 380 ml, USB-C",
            "BPA-free Tritan cup, travel lid, 6 blades",
            brand="BlendCo",
            core_product_phrase="Portable Blender",
            differentiator="USB-C",
            sku_attributes=["White", "380 ml"],
            sku_attribute_placement="title",
        )
        self.assertTrue(result["valid"], result["errors"])

    def test_required_core_keyword_preserves_all_tokens_and_order(self):
        valid = self.validate(
            "BlendCo Portable-Blender for Travel, White",
            "USB-C, 380 ml",
            brand="BlendCo",
            core_product_phrase="Portable-Blender for Travel",
            required_core_keyword="portable blender for travel",
            sku_attributes=["White"],
            sku_attribute_placement="title",
        )
        self.assertTrue(valid["valid"], valid["errors"])

        for changed_phrase in (
            "Portable Blender Travel",
            "Portable Travel Blender for",
            "Portable Blenders for Travel",
        ):
            invalid = self.validate(
                f"BlendCo {changed_phrase}, White",
                "USB-C, 380 ml",
                brand="BlendCo",
                core_product_phrase=changed_phrase,
                required_core_keyword="portable blender for travel",
                sku_attributes=["White"],
                sku_attribute_placement="title",
            )
            self.assertFalse(invalid["valid"], changed_phrase)
            self.assertTrue(
                any("required core keyword" in error for error in invalid["errors"]),
                invalid["errors"],
            )

    def test_hard_limits_and_field_delimiter_are_rejected(self):
        overlong = self.validate(
            "Brand " + "Portable Blender " * 6,
            "USB-C, 380 ml",
        )
        self.assertFalse(overlong["valid"])
        self.assertTrue(any("limit is 75" in error for error in overlong["errors"]))

        delimiter = self.validate(
            "BlendCo Portable Blender | White",
            "USB-C, 380 ml",
        )
        self.assertFalse(delimiter["valid"])
        self.assertTrue(any("delimiter" in error for error in delimiter["errors"]))

    def test_four_multilingual_allocation_benchmarks_and_headroom(self):
        cases = [
            (
                "DE",
                "CareCooo verstecktes Katzenklo Schrank für 2 Katzen, L 120x50x66cm, Weiß",
                "MDF-Material, Sandauffangmatte, Doppeltüren mit Magneten, modernes Kommoden-Design, robust und stabil",
                72,
                101,
            ),
            (
                "US",
                "CareCooo Heart Shaped Snuffle Mat for Dogs, 20 Inch Felt, Velcro, Green",
                "Self-adhesive Velcro base, slow feeder puzzle toy, for puppies and all breeds, promotes slower eating, fun and engaging",
                71,
                119,
            ),
            (
                "DE",
                "CareCooo Hundebett M 63x53x18cm, waschbar, Kunstkaninchenfell, weiß",
                "Für kleine & mittelgroße Hunde, rechteckiges Design, Wellenstruktur, rutschfest, pflegeleicht, weich, bequem",
                67,
                108,
            ),
            (
                "FR",
                "CareCooo Hamac Chat Fenêtre à Ventouses, 52x30x20cm, Fausse Fourrure, Blanc",
                "Pliable, effet lapin, supporte jusqu'à 18 kg, housse amovible et lavable, doux et confortable, fixation stable",
                75,
                110,
            ),
        ]
        for marketplace, title, highlights, title_chars, highlight_chars in cases:
            result = self.validate(title, highlights)
            self.assertTrue(result["valid"], result["errors"])
            self.assertEqual(result["title_characters"], title_chars)
            self.assertEqual(result["item_highlights_characters"], highlight_chars)
            self.assertFalse(any("spacing" in warning for warning in result["warnings"]))
            if title_chars >= 74:
                self.assertTrue(any("headroom" in warning for warning in result["warnings"]))

        french_title = unicodedata.normalize("NFD", cases[-1][1])
        normalized = self.validate(french_title, cases[-1][2])
        self.assertEqual(normalized["title_characters"], 75)


if __name__ == "__main__":
    unittest.main()
