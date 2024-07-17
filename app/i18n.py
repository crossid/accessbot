class i18n:
    lang: str
    _i18n = {
        "en": {
            "request_waiting": "you have a new request from",
            "app_name": "app name",
            "summary": "summary",
            "my_recommendation": "my recommendation",
            "basic_info": "basic information",
            "approval_q": "would you like to approve any of the above recommendations?",
        },
        "he": {
            "hello": "שלום",
            "request_waiting": "יש לך בקשה חדשה מ",
            "app_name": "מערכת",
            "summary": "סיכום",
            "my_recommendation": "ההמלצות שלי",
            "basic_info": "מידע בסיסי",
            "approval_q": "האם תרצה לאשר אחת מההמלצות?",
        },
    }

    def __init__(self, lang: str = "en"):
        if lang not in self._i18n:
            lang = "en"
        self.lang = lang

    def t(self, key: str, **kwargs) -> str:
        lang_keys = self._i18n[self.lang]

        if key in lang_keys:
            translation = lang_keys[key]
            if kwargs:
                try:
                    return translation.format(**kwargs)
                except KeyError:
                    # If a required placeholder is missing, return the raw translation
                    return translation
            return translation
        else:
            return key
