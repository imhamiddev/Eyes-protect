"""Tiny English/Persian translation table."""
from __future__ import annotations

RTL_LANGUAGES = {"fa"}

STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "app": "Eye Care",
        "tagline": "A quiet companion for your eyes",
        "nav.home": "Home", "nav.care": "Care", "nav.display": "Display",
        "nav.exercises": "Exercises", "nav.settings": "Settings",
        "home.next_break": "Next eye break", "home.today": "Today",
        "home.breaks": "Breaks", "home.water": "Water", "home.blinks": "Blink reminders",
        "home.week": "Breaks this week", "home.take_break": "Take a break now",
        "home.pause": "Pause", "home.resume": "Resume",
        "care.rule": "20-20-20 rule",
        "care.rule_desc": "Every 20 minutes, look at something 6 meters away for 20 seconds.",
        "care.interval": "Interval (min)", "care.break_len": "Break length (sec)",
        "care.snooze": "Snooze (min)", "care.natural": "Detect natural breaks",
        "care.break_lock": "Full-screen break", "care.skippable": "Allow skipping",
        "care.blink": "Blink reminder",
        "care.blink_desc": "A gentle nudge to blink, since we blink less in front of screens.",
        "care.hydration": "Hydration reminder", "care.hydration_desc": "Remember to drink water.",
        "display.night": "Night light", "display.night_desc": "Warm up the screen colors.",
        "display.warmth": "Warmth", "display.schedule": "Schedule by time",
        "display.from": "From", "display.to": "To",
        "display.dimmer": "Screen dimmer", "display.dimmer_desc": "Reduce perceived brightness.",
        "display.profile": "Profile", "display.day": "Day", "display.night_p": "Night",
        "display.study": "Reading", "display.brightness": "Brightness",
        "display.night_brightness": "Night brightness",
        "display.auto_dark": "Auto dark mode",
        "display.auto_dark_desc": "Switch Windows between light and dark by time.",
        "display.light_from": "Light from", "display.dark_from": "Dark from",
        "ex.title": "Eye exercises", "ex.subtitle": "Short routines to relax your eyes.",
        "ex.start": "Start", "ex.next": "Next", "ex.done": "Done", "ex.seconds": "sec",
        "set.theme": "Theme", "set.dark": "Dark", "set.light": "Light", "set.system": "System",
        "set.language": "Language", "set.autostart": "Start with Windows",
        "set.autostart_desc": "Run quietly in the background after sign-in.",
        "set.animations": "Animations",
        "set.animations_desc": "Smooth transitions and micro-interactions.",
        "set.about": "About",
        "toast.rule_title": "Look away for a moment",
        "toast.rule_body": "Focus on something about 6 meters away for 20 seconds.",
        "toast.snooze": "Snooze", "toast.start": "Start break", "toast.dismiss": "Dismiss",
        "toast.blink_title": "Blink",
        "toast.blink_body": "Blink slowly a few times to refresh your eyes.",
        "toast.water_title": "Time for water", "toast.water_body": "Take a few sips.",
        "toast.drank": "I drank",
        "break.title": "Rest your eyes",
        "break.hint": "Look at something far away", "break.skip": "Skip", "break.done": "All set",
        "tray.open": "Open Eye Care", "tray.pause": "Pause reminders",
        "tray.resume": "Resume reminders", "tray.break": "Take a break now",
        "tray.night": "Night light", "tray.quit": "Quit",
        "unit.min": "min",
    },
    "fa": {
        "app": "مراقبت از چشم",
        "tagline": "همراهی آرام برای چشم‌های شما",
        "nav.home": "خانه", "nav.care": "مراقبت", "nav.display": "نمایشگر",
        "nav.exercises": "تمرین‌ها", "nav.settings": "تنظیمات",
        "home.next_break": "استراحت بعدی چشم", "home.today": "امروز",
        "home.breaks": "استراحت‌ها", "home.water": "آب", "home.blinks": "یادآوری پلک",
        "home.week": "استراحت‌های این هفته", "home.take_break": "همین حالا استراحت کن",
        "home.pause": "توقف", "home.resume": "ادامه",
        "care.rule": "قانون ۲۰-۲۰-۲۰",
        "care.rule_desc": "هر ۲۰ دقیقه، ۲۰ ثانیه به نقطه‌ای در فاصله ۶ متری نگاه کنید.",
        "care.interval": "فاصله (دقیقه)", "care.break_len": "مدت استراحت (ثانیه)",
        "care.snooze": "تعویق (دقیقه)", "care.natural": "تشخیص استراحت طبیعی",
        "care.break_lock": "استراحت تمام‌صفحه", "care.skippable": "امکان رد کردن",
        "care.blink": "یادآوری پلک زدن",
        "care.blink_desc": "هنگام کار با صفحه‌نمایش کمتر پلک می‌زنیم؛ یادآوری ملایم.",
        "care.hydration": "یادآوری نوشیدن آب", "care.hydration_desc": "نوشیدن آب را فراموش نکنید.",
        "display.night": "نور شب", "display.night_desc": "رنگ‌های صفحه را گرم‌تر کن.",
        "display.warmth": "شدت زردی", "display.schedule": "زمان‌بندی بر اساس ساعت",
        "display.from": "از", "display.to": "تا",
        "display.dimmer": "کاهش روشنایی", "display.dimmer_desc": "کاهش روشنایی ادراکی صفحه.",
        "display.profile": "پروفایل", "display.day": "روز", "display.night_p": "شب",
        "display.study": "مطالعه", "display.brightness": "روشنایی",
        "display.night_brightness": "روشنایی شب",
        "display.auto_dark": "حالت تاریک خودکار",
        "display.auto_dark_desc": "تغییر ویندوز بین روشن و تاریک بر اساس ساعت.",
        "display.light_from": "روشن از", "display.dark_from": "تاریک از",
        "ex.title": "تمرین‌های چشم", "ex.subtitle": "تمرین‌های کوتاه برای آرام کردن چشم.",
        "ex.start": "شروع", "ex.next": "بعدی", "ex.done": "تمام", "ex.seconds": "ثانیه",
        "set.theme": "تم", "set.dark": "تاریک", "set.light": "روشن", "set.system": "سیستم",
        "set.language": "زبان", "set.autostart": "اجرا با ویندوز",
        "set.autostart_desc": "پس از ورود، بی‌صدا در پس‌زمینه اجرا شود.",
        "set.animations": "انیمیشن‌ها",
        "set.animations_desc": "انتقال‌ها و میکرواینتراکشن‌های نرم.",
        "set.about": "درباره",
        "toast.rule_title": "لحظه‌ای نگاهت را دور کن",
        "toast.rule_body": "۲۰ ثانیه به نقطه‌ای در فاصله حدود ۶ متری نگاه کن.",
        "toast.snooze": "بعداً", "toast.start": "شروع استراحت", "toast.dismiss": "بستن",
        "toast.blink_title": "پلک بزن",
        "toast.blink_body": "چند بار آرام پلک بزن تا چشم‌هایت تازه شود.",
        "toast.water_title": "وقت آب خوردن", "toast.water_body": "چند جرعه آب بنوش.",
        "toast.drank": "خوردم",
        "break.title": "به چشم‌هایت استراحت بده",
        "break.hint": "به نقطه‌ای دور نگاه کن", "break.skip": "رد کردن", "break.done": "تمام شد",
        "tray.open": "باز کردن مراقبت از چشم", "tray.pause": "توقف یادآوری‌ها",
        "tray.resume": "ادامه یادآوری‌ها", "tray.break": "همین حالا استراحت",
        "tray.night": "نور شب", "tray.quit": "خروج",
        "unit.min": "دقیقه",
    },
}

_current = "en"


def set_language(code: str) -> None:
    global _current
    _current = code if code in STRINGS else "en"


def language() -> str:
    return _current


def is_rtl() -> bool:
    return _current in RTL_LANGUAGES


def tr(key: str) -> str:
    return STRINGS.get(_current, {}).get(key) or STRINGS["en"].get(key, key)
