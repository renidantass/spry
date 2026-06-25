from __future__ import annotations

import unittest
from pathlib import Path

from spry.i18n import I18nService

LOCALE_DIR = Path(__file__).resolve().parents[1] / "locale"


class I18nServiceTests(unittest.TestCase):
    def test_default_locale_returns_original_message(self) -> None:
        service = I18nService(default_locale="en")
        self.assertEqual(service.translate("Hello"), "Hello")

    def test_set_and_get_locale(self) -> None:
        service = I18nService(default_locale="en")
        service.set_locale("fr")
        self.assertEqual(service.get_locale(), "fr")

    def test_get_locale_default(self) -> None:
        service = I18nService(default_locale="en")
        self.assertEqual(service.get_locale(), "en")

    def test_locale_without_translations_returns_original(self) -> None:
        service = I18nService(locale_dir=LOCALE_DIR, default_locale="en")
        service.set_locale("en")
        self.assertEqual(service.translate("Some unknown string"), "Some unknown string")

    def test_ngettext_default_locale_singular(self) -> None:
        service = I18nService(default_locale="en")
        result = service.ngettext("item", "items", 1)
        self.assertEqual(result, "item")

    def test_ngettext_default_locale_plural(self) -> None:
        service = I18nService(default_locale="en")
        result = service.ngettext("item", "items", 2)
        self.assertEqual(result, "items")

    def test_ngettext_fallback_without_translations(self) -> None:
        service = I18nService(locale_dir=LOCALE_DIR, default_locale="en")
        service.set_locale("fr")
        result = service.ngettext("item", "items", 1)
        self.assertEqual(result, "item")


class FrenchLocaleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = I18nService(locale_dir=str(LOCALE_DIR), default_locale="en")
        self.service.set_locale("fr")

    def test_error_titles_translated(self) -> None:
        cases = {
            "Internal Server Error": "Erreur interne du serveur",
            "Bad Request": "Requête invalide",
            "Unauthorized": "Non autorisé",
            "Forbidden": "Accès interdit",
            "Not Found": "Introuvable",
            "Conflict": "Conflit",
            "Unprocessable Entity": "Entité non traitable",
        }
        for english, french in cases.items():
            with self.subTest(english=english):
                self.assertEqual(self.service.translate(english), french)

    def test_validation_messages_translated(self) -> None:
        cases = {
            "Field '{field}' is required": "Le champ '{field}' est requis",
            "Field '{field}' must be a valid email address": "Le champ '{field}' doit être une adresse email valide",
            "Field '{field}' must be a number": "Le champ '{field}' doit être un nombre",
            "Invalid CSRF token.": "Jeton CSRF invalide.",
            "Validation Failed": "Échec de la validation",
        }
        for english, french in cases.items():
            with self.subTest(english=english):
                self.assertEqual(self.service.translate(english), french)

    def test_unknown_message_returns_original(self) -> None:
        result = self.service.translate("Some untranslated string")
        self.assertEqual(result, "Some untranslated string")


class I18nServiceEdgeCases(unittest.TestCase):
    def test_init_with_none_locale_dir(self) -> None:
        service = I18nService(locale_dir=None, default_locale="en")
        service.set_locale("fr")
        self.assertEqual(service.translate("Hello"), "Hello")

    def test_init_with_pathlib_path(self) -> None:
        service = I18nService(locale_dir=LOCALE_DIR, default_locale="en")
        service.set_locale("fr")
        self.assertEqual(service.translate("Not Found"), "Introuvable")

    def test_cache_loaded_translation(self) -> None:
        service = I18nService(locale_dir=str(LOCALE_DIR), default_locale="en")
        service.set_locale("fr")
        service.translate("Not Found")
        # Second call should use cached translation
        self.assertEqual(service.translate("Not Found"), "Introuvable")

    def test_default_locale_skips_loading(self) -> None:
        service = I18nService(locale_dir=str(LOCALE_DIR), default_locale="en")
        # Should not try to load any file for default locale
        self.assertEqual(service.translate("Not Found"), "Not Found")
