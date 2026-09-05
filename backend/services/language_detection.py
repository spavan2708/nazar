"""Small, deliberately tentative language hints; never used in risk scoring."""
import re
import unicodedata

from schemas.language import LanguageMetadata

HINGLISH_HINTS = {"aya", "aaya", "hoga", "bhej", "bhejo", "batao", "jaldi", "jldi", "chahiye", "aapka", "aapke", "aap", "apna", "abhi", "karo", "karein", "hai", "hain", "gaya", "jayega", "mat", "kabhi", "nahi", "kal", "milte"}
TANGLISH_HINTS = {"unga", "ungal", "aagum", "pannunga", "pannu", "anuppunga", "vendam", "yaarukkum", "naalai", "sandhippom"}
ENGLISH_HINTS = {"your", "you", "the", "this", "please", "send", "share", "verify", "account", "bank", "never", "hello", "meet", "tomorrow", "warning", "immediately", "install"}


def identify_language(text: str) -> LanguageMetadata:
    scripts = set()
    for char in text:
        if not char.isalpha():
            continue
        name = unicodedata.name(char, "")
        scripts.add(next((script for script in ("LATIN", "DEVANAGARI", "TAMIL") if script in name), "OTHER"))
    script = "Mixed" if len(scripts) > 1 else next(iter(scripts), "UNKNOWN").title()
    tokens = set(re.findall(r"[a-z]+", text.lower()))
    hi_latin = len(tokens & HINGLISH_HINTS) >= 2
    ta_latin = len(tokens & TANGLISH_HINTS) >= 2
    english = len(tokens & ENGLISH_HINTS) >= 2
    hi = "DEVANAGARI" in scripts
    ta = "TAMIL" in scripts
    mixed = (hi and ta) or ((hi or ta) and english) or (hi_latin and ta_latin)
    if mixed:
        language = "Mixed"
    elif hi:
        language = "Hindi"
    elif ta:
        language = "Tamil"
    elif hi_latin:
        language = "Hinglish"
    elif ta_latin:
        language = "Tanglish"
    elif english and scripts == {"LATIN"}:
        language = "English"
    else:
        language = "Unknown"
    # Devanagari is shared with other languages; script alone cannot prove Hindi.
    confidence = "low" if language in {"Unknown", "Hinglish", "Tanglish", "Hindi"} else "medium"
    return LanguageMetadata(
        detected_language=language, detected_script=script,
        is_mixed_language=mixed or language in {"Hinglish", "Tanglish"},
        language_confidence=confidence,
    )
