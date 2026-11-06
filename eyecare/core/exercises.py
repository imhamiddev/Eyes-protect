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


def by_id(exercise_id: str) -> Exercise:
    for e in EXERCISES:
        if e.id == exercise_id:
            return e
    raise KeyError(exercise_id)
