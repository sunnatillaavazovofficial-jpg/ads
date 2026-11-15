"""Holatlar, rollar va boshqa doimiy qiymatlar."""

# Ish jarayoni bosqichlari (tartib muhim: Kanban ustunlari shu tartibda)
STATUSES: list[tuple[str, str, str]] = [
    # (kod, nomi, rang)
    ("new", "Yangi", "#64748b"),
    ("design", "Dizayn jarayonida", "#3b82f6"),
    ("review", "Mijoz tasdig'ida", "#a855f7"),
    ("revision", "Tuzatishda", "#f59e0b"),
    ("approved", "Tasdiqlandi", "#14b8a6"),
    ("production", "Ishlab chiqarishda", "#6366f1"),
    ("installation", "O'rnatishda", "#0ea5e9"),
    ("done", "Bajarildi", "#22c55e"),
    ("cancelled", "Bekor qilindi", "#ef4444"),
]
STATUS_LABELS = {code: label for code, label, _ in STATUSES}
STATUS_COLORS = {code: color for code, _, color in STATUSES}
STATUS_CODES = [code for code, _, _ in STATUSES]
# Yakunlangan holatlar (faol ishlar hisobiga kirmaydi)
CLOSED_STATUSES = {"done", "cancelled"}
ACTIVE_STATUSES = [s for s in STATUS_CODES if s not in CLOSED_STATUSES]

ROLES = {
    "admin": "Administrator",
    "manager": "Menejer",
    "designer": "Dizayner",
}

PRIORITIES = {
    "normal": "Oddiy",
    "urgent": "Shoshilinch",
}

FILE_KINDS = {
    "place": "Joy rasmi",
    "logo": "Logo va qo'shimcha fayllar",
    "design": "Tayyor dizayn",
}

UNITS = ["m²", "dona", "metr", "xizmat", "soat", "komplekt"]

SIZE_UNITS = {"m": "metr", "sm": "santimetr"}

SOURCES = {"web": "Sayt", "bot": "Telegram bot", "inbox": "Telegram chat"}

ACCOUNT_COLORS = [
    "#3b82f6", "#ef4444", "#22c55e", "#f59e0b", "#a855f7",
    "#0ea5e9", "#ec4899", "#14b8a6", "#f97316", "#6366f1",
]
