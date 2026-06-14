from __future__ import annotations

import gettext
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger("spry.i18n")


class I18nService:
    def __init__(self, locale_dir: str | Path | None = None, default_locale: str = "en") -> None:
        self._locale_dir = Path(locale_dir) if locale_dir else None
        self._default_locale = default_locale
        self._current_locale = default_locale
        self._translations: dict[str, gettext.GNUTranslations] = {}

    def set_locale(self, locale: str) -> None:
        self._current_locale = locale

    def get_locale(self) -> str:
        return self._current_locale

    def _load_translation(self, locale: str) -> gettext.GNUTranslations | None:
        if locale in self._translations:
            return self._translations[locale]
        if not self._locale_dir:
            return None
        mo_path = self._locale_dir / locale / "LC_MESSAGES" / "messages.mo"
        if mo_path.exists():
            try:
                with mo_path.open("rb") as f:
                    self._translations[locale] = gettext.GNUTranslations(f)
                return self._translations[locale]
            except Exception as exc:
                logger.debug("Failed to load .mo file for locale '%s': %s", locale, exc)
        po_path = self._locale_dir / locale / "LC_MESSAGES" / "messages.po"
        if po_path.exists():
            try:
                import warnings
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    import polib
                    po = polib.pofile(str(po_path))
                    translation_map = {entry.msgid: entry.msgstr for entry in po if entry.msgstr}
                    class DictTranslations(gettext.GNUTranslations):
                        def __init__(self) -> None:
                            super().__init__()
                            self._catalog = translation_map
                    self._translations[locale] = DictTranslations()
                    return self._translations[locale]
            except ImportError:
                pass
        return None

    def translate(self, message: str) -> str:
        locale = self._current_locale
        if locale == self._default_locale:
            return message
        trans = self._load_translation(locale)
        if trans:
            translated = trans.gettext(message)
            return translated if translated != message else message
        return message

    def ngettext(self, singular: str, plural: str, n: int) -> str:
        locale = self._current_locale
        if locale == self._default_locale:
            return singular if n == 1 else plural
        trans = self._load_translation(locale)
        if trans:
            result = trans.ngettext(singular, plural, n)
            if result:
                return result
        return singular if n == 1 else plural
