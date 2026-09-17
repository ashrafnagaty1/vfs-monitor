"""Compatibility aliases for labels visible in the supplied reference UI."""

ALIASES = {
    "📈 تحليل الأسهم": "🔍 تحليل سهم",
    "📈 أسهم المضاربة اليومية": "🎯 فرص اليوم",
    "📊 الصفقات": "🚀 الإشارات النشطة",
}


def apply(base):
    original = base.handle

    def handle(chat_id, text, state):
        target = ALIASES.get((text or "").strip())
        return original(chat_id, target if target else text, state)

    base.handle = handle
    return base


def self_test():
    assert ALIASES["📊 الصفقات"] == "🚀 الإشارات النشطة"
    print("bot reference menu self-test: PASS")


if __name__ == "__main__":
    self_test()
