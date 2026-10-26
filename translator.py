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


class ChatTranslator:
    """Service to handle language detection and translation for multilingual chat."""

    def __init__(self, env_path: Optional[str] = None):
        self._load_env(env_path)
        api_key = os.environ.get("SARVAM_API_KEY")
        if not api_key:
            raise ValueError("SARVAM_API_KEY is not set in environment or .env file.")
        self.client = SarvamAI(api_subscription_key=api_key)
        # In-memory translation cache: (text, source_lang, target_lang) -> translated_text
        self._cache: Dict[Tuple[str, str, str], str] = {}
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
        """Detect language code (e.g. 'hi-IN') and script (e.g. 'Deva')."""
        trimmed = text.strip()
        if trimmed in self._detect_cache:
            return self._detect_cache[trimmed]

        try:
            response = self.client.text.identify_language(input=trimmed)
            result = (response.language_code, response.script_code)
            self._detect_cache[trimmed] = result
            return result
        except Exception as e:
            # Fallback to English if identification fails
            return ("en-IN", "Latn")

    def translate_message(
        self,
        text: str,
        target_language_code: str,
        source_language_code: Optional[str] = None,
        model: str = "sarvam-translate:v1",
    ) -> str:
        """Translate text to the target language. If source is unknown, auto-detects first."""
        trimmed = text.strip()
        if not source_language_code or source_language_code == "auto":
            source_language_code, _ = self.detect_language(trimmed)

        # Skip translation if already in the target language
        if source_language_code == target_language_code:
            return text

        cache_key = (trimmed, source_language_code, target_language_code)
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            response = self.client.text.translate(
                input=trimmed,
                source_language_code=source_language_code,
                target_language_code=target_language_code,
                model=model,
            )
            translated = response.translated_text
            self._cache[cache_key] = translated
            return translated
        except Exception as e:
            print(f"Translation error ({source_language_code} -> {target_language_code}): {e}")
            return text

    def prepare_chat_message(
        self,
        sender_id: str,
        original_text: str,
        recipient_languages: List[str],
    ) -> dict:
        """
        Process a sent chat message:
        1. Identify the source language.
        2. Translate to each recipient's chosen language.
        3. Return payload ready for WhatsApp-style display (original + translated).
        """
        source_lang, script = self.detect_language(original_text)
        unique_targets = set(recipient_languages)

        translations: Dict[str, str] = {}
        for target_lang in unique_targets:
            if target_lang == source_lang:
                translations[target_lang] = original_text
            else:
                try:
                    translations[target_lang] = self.translate_message(
                        text=original_text,
                        source_language_code=source_lang,
                        target_language_code=target_lang,
                    )
                except Exception as e:
                    # Fallback to original text on translation error
                    translations[target_lang] = original_text

        return {
            "sender_id": sender_id,
            "original_text": original_text,
            "source_language_code": source_lang,
            "source_language_name": SUPPORTED_LANGUAGES.get(source_lang, source_lang),
            "script": script,
            "translations": translations,
        }


if __name__ == "__main__":
    translator = ChatTranslator()
    
    # Test chat scenario: User sends a message in Hindi
    sender_msg = "अरे भाई! आज शाम को क्या प्लान है? क्या हम मैच देखने जा रहे हैं?"
    recipients = ["en-IN", "ta-IN", "bn-IN", "te-IN", "hi-IN"]

    print(f"Original Message ({SUPPORTED_LANGUAGES['hi-IN']}):\n  {sender_msg}\n")
    
    chat_payload = translator.prepare_chat_message(
        sender_id="user_123",
        original_text=sender_msg,
        recipient_languages=recipients,
    )

    print(f"Detected Source: {chat_payload['source_language_name']} (Script: {chat_payload['script']})")
    print("Translations for Recipients:")
    for lang, trans in chat_payload["translations"].items():
        lang_name = SUPPORTED_LANGUAGES.get(lang, lang)
        print(f"  • [{lang_name}]: {trans}")
