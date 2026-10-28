"""Tabel subkategori dan pembacaan field item dari API."""

import unittest

from trash2trace.bridge import _parse_flags
from trash2trace.catalog import ITEMS, find_item


class CatalogTests(unittest.TestCase):
    def test_each_item_has_one_category_and_a_unique_name(self):
        ids = [item.id for item in ITEMS]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(
            {item.category for item in ITEMS},
            {"organic", "nonorganic", "other"},
        )

    def test_known_examples_land_in_the_right_bin(self):
        self.assertEqual(find_item("kulit pisang").category, "organic")
        self.assertEqual(find_item("botol").name, "Botol")
        self.assertEqual(find_item("sampah kaleng minuman").category, "nonorganic")
        self.assertEqual(find_item("kaleng_minuman").name, "Kaleng minuman")

    def test_api_item_is_shown_and_can_choose_the_category(self):
        flagged = _parse_flags({"organic": True, "item": "kulit_pisang"})
        self.assertEqual(flagged.label, "organic")
        self.assertEqual(flagged.item, "Kulit pisang")

        from_item = _parse_flags({"item": "botol"})
        self.assertEqual(from_item.label, "nonorganic")
        self.assertEqual(from_item.item, "Botol")

        flags_win = _parse_flags({"organic": True, "item": "botol"})
        self.assertEqual(flags_win.label, "organic")
        self.assertEqual(flags_win.item, "Botol")

        unknown = _parse_flags({"anorganic": True, "item": "benda aneh"})
        self.assertEqual(unknown.label, "nonorganic")
        self.assertEqual(unknown.item, "benda aneh")

    def test_old_flags_still_work_without_an_item(self):
        reading = _parse_flags({"other": True})
        self.assertEqual((reading.label, reading.item), ("other", ""))
        with self.assertRaises(RuntimeError):
            _parse_flags({})


if __name__ == "__main__":
    unittest.main()
