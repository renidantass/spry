from __future__ import annotations

import unittest

from spry.i18n import BUILTIN_LOCALE_DIR, I18nService


class TestI18nService(unittest.TestCase):
    def setUp(self):
        self.service = I18nService()

    def test_default_locale_returns_original_message(self):
        self.assertEqual(self.service.get_locale(), "en")
        self.assertEqual(self.service.translate("Hello"), "Hello")
        self.assertEqual(self.service.ngettext("item", "items", 1), "item")
        self.assertEqual(self.service.ngettext("item", "items", 5), "items")

    def test_french_translate(self):
        self.service.set_locale("fr")
        self.assertEqual(self.service.translate("Hello"), "Bonjour")
        self.assertEqual(self.service.translate("Welcome"), "Bienvenue")
        self.assertEqual(self.service.translate("Goodbye"), "Au revoir")
        self.assertEqual(self.service.translate("Not Found"), "Non trouvé")

    def test_french_translate_unknown_message(self):
        self.service.set_locale("fr")
        self.assertEqual(self.service.translate("NonExistentString"), "NonExistentString")

    def test_french_ngettext_singular(self):
        self.service.set_locale("fr")
        self.assertEqual(self.service.ngettext("item", "items", 1), "élément")

    def test_french_ngettext_plural(self):
        self.service.set_locale("fr")
        self.assertEqual(self.service.ngettext("item", "items", 2), "éléments")
        self.assertEqual(self.service.ngettext("item", "items", 100), "éléments")

    def test_french_ngettext_unknown(self):
        self.service.set_locale("fr")
        self.assertEqual(self.service.ngettext("unknown", "unknowns", 1), "unknown")
        self.assertEqual(self.service.ngettext("unknown", "unknowns", 2), "unknowns")

    def test_set_and_get_locale(self):
        service = I18nService()
        self.assertEqual(service.get_locale(), "en")
        service.set_locale("fr")
        self.assertEqual(service.get_locale(), "fr")

    def test_default_locale_custom(self):
        service = I18nService(default_locale="fr")
        self.assertEqual(service.get_locale(), "fr")
        self.assertEqual(service.translate("Hello"), "Hello")

    def test_explicit_none_disables_builtin(self):
        service = I18nService(locale_dir=None)
        service.set_locale("fr")
        self.assertEqual(service.translate("Hello"), "Hello")
        self.assertEqual(service.ngettext("item", "items", 2), "items")

    def test_custom_locale_dir_nonexistent(self):
        service = I18nService(locale_dir="/nonexistent/path")
        service.set_locale("fr")
        self.assertEqual(service.translate("Hello"), "Hello")

    def test_unknown_locale(self):
        self.service.set_locale("de")
        self.assertEqual(self.service.translate("Hello"), "Hello")

    def test_multiple_switches(self):
        self.service.set_locale("fr")
        self.assertEqual(self.service.translate("Hello"), "Bonjour")
        self.service.set_locale("en")
        self.assertEqual(self.service.translate("Hello"), "Hello")
        self.service.set_locale("fr")
        self.assertEqual(self.service.translate("Hello"), "Bonjour")

    def test_builtin_locale_dir_exists(self):
        self.assertTrue(BUILTIN_LOCALE_DIR.exists())
        self.assertTrue((BUILTIN_LOCALE_DIR / "fr" / "LC_MESSAGES" / "messages.po").exists())

    def test_plural_forms_french(self):
        self.service.set_locale("fr")
        self.assertEqual(self.service.ngettext("day", "days", 1), "jour")
        self.assertEqual(self.service.ngettext("day", "days", 2), "jours")
        self.assertEqual(self.service.ngettext("hour", "hours", 1), "heure")
        self.assertEqual(self.service.ngettext("hour", "hours", 2), "heures")
