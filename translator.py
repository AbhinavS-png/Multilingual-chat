import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from sarvamai import SarvamAI

# Supported language codes and readable labels
SUPPORTED_LANGUAGES = {
    "en-IN": "English",
    "hi-IN": "Hindi (हिंदी)",
    "bn-IN": "Bengali (বাংলা)",
    "ta-IN": "Tamil (தமிழ்)",
    "te-IN": "Telugu (తెలుగు)",
    "mr-IN": "Marathi (मराठी)",
    "gu-IN": "Gujarati (ગુજરાતી)",
    "kn-IN": "Kannada (ಕನ್ನಡ)",
    "ml-IN": "Malayalam (മലയാളം)",
    "pa-IN": "Punjabi (ਪੰਜਾਬੀ)",
    "od-IN": "Odia (ଓଡ଼ିଆ)",
    "as-IN": "Assamese (অসমীয়া)",
    "ur-IN": "Urdu (اردو)",
    "ne-IN": "Nepali (नेपाली)",
    "sa-IN": "Sanskrit (संस्कृतम्)",
}


def get_language_display_name(lang_code: str, script_code: str = "") -> str:
    """Return user-friendly label, identifying Roman script / Hinglish / Tanglish."""
    base_name = SUPPORTED_LANGUAGES.get(lang_code, lang_code).split(" ")[0]
    if script_code == "Latn":
        if lang_code == "en-IN":
            return "English"
        elif lang_code == "hi-IN":
            return "Hinglish (Hindi in Roman script)"
        elif lang_code == "ta-IN":
            return "Tanglish (Tamil in Roman script)"
        elif lang_code == "bn-IN":
            return "Benglish (Bengali in Roman script)"
        elif lang_code == "te-IN":
            return "Telugu (Roman script)"
        else:
            return f"{base_name} (Roman script)"
    return SUPPORTED_LANGUAGES.get(lang_code, lang_code)


class ChatTranslator:
    """Service to handle language detection and translation for multilingual chat."""

    def __init__(self, env_path: Optional[str] = None):
        self._load_env(env_path)
        api_key = os.environ.get("SARVAM_API_KEY")
        if not api_key:
            raise ValueError("SARVAM_API_KEY is not set in environment or .env file.")
        self.client = SarvamAI(api_subscription_key=api_key)
        # In-memory translation cache: (text, source_lang, target_lang, script) -> translated_text
        self._cache: Dict[Tuple[str, str, str, str], str] = {}
        # In-memory language detection cache: text -> (lang_code, script_code)
        self._detect_cache: Dict[str, Tuple[str, str]] = {}

    @staticmethod
    def _load_env(env_path: Optional[str] = None):
        target = Path(env_path) if env_path else Path(__file__).resolve().parent / ".env"
        if target.exists():
            with open(target, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        os.environ.setdefault(k.strip(), v.strip().strip("'\""))

    def detect_language(self, text: str) -> Tuple[str, str]:
        """Detect language code (e.g. 'hi-IN') and script (e.g. 'Deva' or 'Latn')."""
        trimmed = text.strip()
        if trimmed in self._detect_cache:
            return self._detect_cache[trimmed]

        try:
            response = self.client.text.identify_language(input=trimmed)
            result = (response.language_code, response.script_code)
            self._detect_cache[trimmed] = result
            return result
        except Exception:
            return ("en-IN", "Latn")

    def translate_message(
        self,
        text: str,
        target_language_code: str,
        source_language_code: Optional[str] = None,
        script_code: Optional[str] = None,
        model: Optional[str] = None,
    ) -> str:
        """
        Translate text to the target language.
        Supports:
        - Native script Indic text (e.g. Hindi, Tamil in native scripts).
        - Roman script / Hinglish / Tanglish (e.g. 'mera naam abhinav hai').
        - English text.
        """
        trimmed = text.strip()
        if not source_language_code or source_language_code == "auto" or not script_code:
            source_language_code, detected_script = self.detect_language(trimmed)
            if not script_code:
                script_code = detected_script

        # If it's English text going to English, no translation needed
        if source_language_code == "en-IN" and target_language_code == "en-IN" and script_code == "Latn":
            return text

        # If source is same as target and NOT Roman script (e.g. already native Devanagari Hindi for Hindi reader), no translation needed
        if source_language_code == target_language_code and script_code != "Latn":
            return text

        cache_key = (trimmed, source_language_code, target_language_code, script_code)
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Use mayura:v1 for Roman script (Hinglish/Tanglish) and general Indic translation; sarvam-translate:v1 as fallback
        preferred_model = model or ("mayura:v1" if script_code == "Latn" else "sarvam-translate:v1")

        try:
            response = self.client.text.translate(
                input=trimmed,
                source_language_code="auto" if script_code == "Latn" else source_language_code,
                target_language_code=target_language_code,
                model=preferred_model,
            )
            translated = response.translated_text
            self._cache[cache_key] = translated
            return translated
        except Exception as e:
            # Fallback to secondary model
            fallback_model = "sarvam-translate:v1" if preferred_model == "mayura:v1" else "mayura:v1"
            try:
                response = self.client.text.translate(
                    input=trimmed,
                    source_language_code="auto",
                    target_language_code=target_language_code,
                    model=fallback_model,
                )
                translated = response.translated_text
                self._cache[cache_key] = translated
                return translated
            except Exception as e2:
                print(f"Translation error ({source_language_code} -> {target_language_code}): {e2}")
                return text

    def prepare_chat_message(
        self,
        sender_id: str,
        original_text: str,
        recipient_languages: List[str],
    ) -> dict:
        """Process chat message for all recipients in a room."""
        source_lang, script = self.detect_language(original_text)
        source_display_name = get_language_display_name(source_lang, script)
        unique_targets = set(recipient_languages)

        translations: Dict[str, str] = {}
        for target_lang in unique_targets:
            try:
                translations[target_lang] = self.translate_message(
                    text=original_text,
                    target_language_code=target_lang,
                    source_language_code=source_lang,
                    script_code=script,
                )
            except Exception:
                translations[target_lang] = original_text

        return {
            "sender_id": sender_id,
            "original_text": original_text,
            "source_language_code": source_lang,
            "source_language_name": source_display_name,
            "script": script,
            "is_roman": script == "Latn",
            "translations": translations,
        }


if __name__ == "__main__":
    translator = ChatTranslator()
    
    # Test case: User types in Roman Hindi (Hinglish)
    test_msg = "mera naam abhinav hai aur hum sab hackathon jeetne wale hain"
    recipients = ["en-IN", "ta-IN", "te-IN", "hi-IN", "bn-IN"]

    print(f"Input Text: '{test_msg}'\n")
    payload = translator.prepare_chat_message("user_1", test_msg, recipients)
    
    print(f"Detected: {payload['source_language_name']} (Script: {payload['script']})")
    print("Translations for Recipients:")
    for lang, trans in payload["translations"].items():
        print(f"  • [{SUPPORTED_LANGUAGES.get(lang, lang)}]: {trans}")
