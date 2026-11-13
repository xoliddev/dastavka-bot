"""Matnlarni lug‘atdan (LEXICON) til bo‘yicha xavfsiz olish uchun yordamchi funksiyalar."""

import json

# Bot qo'llab-quvvatlaydigan tillar (LEXICON'dagi har bir kalitda bo'lishi shart).
SUPPORTED_LANGUAGES: tuple[str, ...] = ("uz", "ru", "en")


def get_text(text_key: str, lang_code: str, lexicon: dict[str, dict[str, str]]) -> str:
    """
    :param text_key:  LEXICON dagi kalit
    :param lang_code: 'uz', 'ru', 'en', ...
    :param lexicon:   LEXICON lug‘ati
    :return:          So‘rov qilingan til versiyasi yoki fallback ('uz')
    """
    translations = lexicon.get(text_key, {})
    # Avval so‘ralgan tilni, bo‘lmasa o‘zbek tilini, bo‘lmasa kalitning o‘zini qaytaramiz
    return translations.get(lang_code) or translations.get("uz") or text_key


def get_i18n_name(name_json: str, lang_code: str) -> str:
    """
    JSONB string ichidan nomni til bo‘yicha olib, quyidagi tartibda fallback qiladi:
      1) user lang_code
      2) 'en'
      3) 'uz'
      4) birinchi mavjud qiymat
      5) agar hammasi muvaffaqiyatsiz bo‘lsa, "Nomsiz"
    Hech qachon None qaytarmaydi.
    """
    default = "Nomsiz"
    try:
        data = json.loads(name_json)
        if not isinstance(data, dict) or not data:
            return default
    except Exception:
        return default

    # 1) user lang
    if lang_code in data and isinstance(data[lang_code], str) and data[lang_code].strip():
        return data[lang_code]

    # 2) English
    if "en" in data and isinstance(data["en"], str) and data["en"].strip():
        return data["en"]

    # 3) Uzbek
    if "uz" in data and isinstance(data["uz"], str) and data["uz"].strip():
        return data["uz"]

    # 4) first available
    for val in data.values():
        if isinstance(val, str) and val.strip():
            return val

    return default
