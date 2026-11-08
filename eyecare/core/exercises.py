"""Built-in eye exercises: (id, steps) where each step is (seconds, en, fa)."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Step:
    seconds: int
    en: str
    fa: str


@dataclass(frozen=True)
class Exercise:
    id: str
    icon: str
    title_en: str
    title_fa: str
    steps: tuple[Step, ...]
    kind: str = "eyes"   # eyes | body

    @property
    def total_seconds(self) -> int:
        return sum(s.seconds for s in self.steps)


EXERCISES: tuple[Exercise, ...] = (
    Exercise("palming", "hand", "Palming", "کف دست روی چشم", (
        Step(5, "Rub your palms together until warm.", "کف دست‌ها را به هم بمالید تا گرم شوند."),
        Step(20, "Cup your palms gently over closed eyes. Breathe slowly.",
             "کف دست‌ها را آرام روی چشم‌های بسته بگذارید و آرام نفس بکشید."),
    )),
    Exercise("figure8", "infinity", "Figure eight", "حرکت عدد هشت", (
        Step(15, "Trace a big imaginary figure eight with your eyes.",
             "با چشم‌هایتان یک عدد هشت بزرگ خیالی بکشید."),
        Step(15, "Reverse the direction.", "جهت را برعکس کنید."),
    )),
    Exercise("focus", "focus", "Near and far focus", "تمرکز نزدیک و دور", (
        Step(8, "Hold a thumb at arm's length and focus on it.",
             "شست را به اندازه یک بازو جلوی خود بگیرید و روی آن تمرکز کنید."),
        Step(8, "Focus on something far away.", "روی چیزی دور تمرکز کنید."),
        Step(8, "Back to your thumb.", "دوباره به شست نگاه کنید."),
        Step(8, "Far again.", "دوباره دور را نگاه کنید."),
    )),
    Exercise("roll", "rotate", "Eye rolls", "چرخش چشم", (
        Step(10, "Roll your eyes slowly clockwise.", "چشم‌ها را آرام در جهت عقربه‌های ساعت بچرخانید."),
        Step(10, "Now counter-clockwise.", "حالا خلاف جهت عقربه‌های ساعت."),
    )),
    Exercise("blink", "eye", "Slow blinks", "پلک زدن آهسته", (
        Step(15, "Close your eyes gently, then open. Repeat slowly.",
             "پلک‌ها را آرام ببندید و باز کنید. آهسته تکرار کنید."),
    )),
)


STRETCHES: tuple[Exercise, ...] = (
    Exercise("neck", "person", "Neck release", "رها کردن گردن", (
        Step(10, "Drop your right ear toward your right shoulder. Breathe slowly.",
             "گوش راست را به سمت شانه‌ی راست پایین بیاورید و آرام نفس بکشید."),
        Step(10, "Switch sides: left ear toward your left shoulder.",
             "طرف دیگر: گوش چپ به سمت شانه‌ی چپ."),
        Step(10, "Gently lower your chin to your chest and hold.",
             "چانه را آرام به سمت سینه پایین بیاورید و نگه دارید."),
    ), "body"),
    Exercise("shoulders", "person", "Shoulder rolls", "چرخش شانه‌ها", (
        Step(10, "Lift both shoulders up toward your ears, then release.",
             "هر دو شانه را به سمت گوش‌ها بالا ببرید و رها کنید."),
        Step(10, "Roll your shoulders backward in big slow circles.",
             "شانه‌ها را در دایره‌های بزرگ و آهسته به عقب بچرخانید."),
        Step(10, "Now roll them forward.", "حالا به جلو بچرخانید."),
    ), "body"),
    Exercise("wrists", "hand", "Wrist and finger stretch", "کشش مچ و انگشتان", (
        Step(12, "Extend your right arm, palm up, and gently pull the fingers down with your left hand.",
             "دست راست را با کف رو به بالا دراز کنید و انگشتان را با دست چپ آرام پایین بکشید."),
        Step(12, "Turn the palm down and gently press the back of the hand.",
             "کف دست را رو به پایین بچرخانید و پشت دست را آرام فشار دهید."),
        Step(12, "Switch hands and repeat.", "دست‌ها را عوض کنید و تکرار کنید."),
    ), "body"),
    Exercise("back", "person", "Seated back twist", "پیچش کمر در حالت نشسته", (
        Step(12, "Sit tall, place your right hand on your left knee and twist gently to the left.",
             "صاف بنشینید، دست راست را روی زانوی چپ بگذارید و آرام به چپ بچرخید."),
        Step(12, "Return to the center, then twist to the right.",
             "به وسط برگردید و بعد به راست بچرخید."),
    ), "body"),
    Exercise("stand", "person", "Stand up and walk", "بلند شوید و راه بروید", (
        Step(10, "Stand up and take a deep breath, arms overhead.",
             "بلند شوید و با دست‌های بالای سر یک نفس عمیق بکشید."),
        Step(30, "Walk around, get some water or look out of a window.",
             "کمی راه بروید، آب بنوشید یا از پنجره بیرون را نگاه کنید."),
    ), "body"),
)

ALL_EXERCISES: tuple[Exercise, ...] = EXERCISES + STRETCHES


def by_id(exercise_id: str) -> Exercise:
    for e in ALL_EXERCISES:
        if e.id == exercise_id:
            return e
    raise KeyError(exercise_id)
