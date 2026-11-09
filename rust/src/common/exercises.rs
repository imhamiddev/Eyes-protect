//! Built-in eye exercises and body stretches (each step: seconds, English, Persian).

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Step {
    pub seconds: u32,
    pub en: &'static str,
    pub fa: &'static str,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Kind {
    Eyes,
    Body,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Exercise {
    pub id: &'static str,
    pub icon: &'static str,
    pub title_en: &'static str,
    pub title_fa: &'static str,
    pub steps: &'static [Step],
    pub kind: Kind,
}

impl Exercise {
    pub fn total_seconds(&self) -> u32 {
        self.steps.iter().map(|s| s.seconds).sum()
    }
}

pub static EXERCISES: &[Exercise] = &[
    Exercise {
        id: "palming",
        icon: "hand",
        title_en: "Palming",
        title_fa: "کف دست روی چشم",
        kind: Kind::Eyes,
        steps: &[
            Step { seconds: 5, en: "Rub your palms together until warm.", fa: "کف دست‌ها را به هم بمالید تا گرم شوند." },
            Step { seconds: 20, en: "Cup your palms gently over closed eyes. Breathe slowly.", fa: "کف دست‌ها را آرام روی چشم‌های بسته بگذارید و آرام نفس بکشید." },
        ],
    },
    Exercise {
        id: "figure8",
        icon: "infinity",
        title_en: "Figure eight",
        title_fa: "حرکت عدد هشت",
        kind: Kind::Eyes,
        steps: &[
            Step { seconds: 15, en: "Trace a big imaginary figure eight with your eyes.", fa: "با چشم‌هایتان یک عدد هشت بزرگ خیالی بکشید." },
            Step { seconds: 15, en: "Reverse the direction.", fa: "جهت را برعکس کنید." },
        ],
    },
    Exercise {
        id: "focus",
        icon: "focus",
        title_en: "Near and far focus",
        title_fa: "تمرکز نزدیک و دور",
        kind: Kind::Eyes,
        steps: &[
            Step { seconds: 8, en: "Hold a thumb at arm's length and focus on it.", fa: "شست را به اندازه یک بازو جلوی خود بگیرید و روی آن تمرکز کنید." },
            Step { seconds: 8, en: "Focus on something far away.", fa: "روی چیزی دور تمرکز کنید." },
            Step { seconds: 8, en: "Back to your thumb.", fa: "دوباره به شست نگاه کنید." },
            Step { seconds: 8, en: "Far again.", fa: "دوباره دور را نگاه کنید." },
        ],
    },
    Exercise {
        id: "roll",
        icon: "rotate",
        title_en: "Eye rolls",
        title_fa: "چرخش چشم",
        kind: Kind::Eyes,
        steps: &[
            Step { seconds: 10, en: "Roll your eyes slowly clockwise.", fa: "چشم‌ها را آرام در جهت عقربه‌های ساعت بچرخانید." },
            Step { seconds: 10, en: "Now counter-clockwise.", fa: "حالا خلاف جهت عقربه‌های ساعت." },
        ],
    },
    Exercise {
        id: "blink",
        icon: "eye",
        title_en: "Slow blinks",
        title_fa: "پلک زدن آهسته",
        kind: Kind::Eyes,
        steps: &[
            Step { seconds: 15, en: "Close your eyes gently, then open. Repeat slowly.", fa: "پلک‌ها را آرام ببندید و باز کنید. آهسته تکرار کنید." },
        ],
    },
];

pub static STRETCHES: &[Exercise] = &[
    Exercise {
        id: "neck",
        icon: "person",
        title_en: "Neck release",
        title_fa: "رها کردن گردن",
        kind: Kind::Body,
        steps: &[
            Step { seconds: 10, en: "Drop your right ear toward your right shoulder. Breathe slowly.", fa: "گوش راست را به سمت شانه‌ی راست پایین بیاورید و آرام نفس بکشید." },
            Step { seconds: 10, en: "Switch sides: left ear toward your left shoulder.", fa: "طرف دیگر: گوش چپ به سمت شانه‌ی چپ." },
            Step { seconds: 10, en: "Gently lower your chin to your chest and hold.", fa: "چانه را آرام به سمت سینه پایین بیاورید و نگه دارید." },
        ],
    },
    Exercise {
        id: "shoulders",
        icon: "person",
        title_en: "Shoulder rolls",
        title_fa: "چرخش شانه‌ها",
        kind: Kind::Body,
        steps: &[
            Step { seconds: 10, en: "Lift both shoulders up toward your ears, then release.", fa: "هر دو شانه را به سمت گوش‌ها بالا ببرید و رها کنید." },
            Step { seconds: 10, en: "Roll your shoulders backward in big slow circles.", fa: "شانه‌ها را در دایره‌های بزرگ و آهسته به عقب بچرخانید." },
            Step { seconds: 10, en: "Now roll them forward.", fa: "حالا به جلو بچرخانید." },
        ],
    },
    Exercise {
        id: "wrists",
        icon: "hand",
        title_en: "Wrist and finger stretch",
        title_fa: "کشش مچ و انگشتان",
        kind: Kind::Body,
        steps: &[
            Step { seconds: 12, en: "Extend your right arm, palm up, and gently pull the fingers down with your left hand.", fa: "دست راست را با کف رو به بالا دراز کنید و انگشتان را با دست چپ آرام پایین بکشید." },
            Step { seconds: 12, en: "Turn the palm down and gently press the back of the hand.", fa: "کف دست را رو به پایین بچرخانید و پشت دست را آرام فشار دهید." },
            Step { seconds: 12, en: "Switch hands and repeat.", fa: "دست‌ها را عوض کنید و تکرار کنید." },
        ],
    },
    Exercise {
        id: "back",
        icon: "person",
        title_en: "Seated back twist",
        title_fa: "پیچش کمر در حالت نشسته",
        kind: Kind::Body,
        steps: &[
            Step { seconds: 12, en: "Sit tall, place your right hand on your left knee and twist gently to the left.", fa: "صاف بنشینید، دست راست را روی زانوی چپ بگذارید و آرام به چپ بچرخید." },
            Step { seconds: 12, en: "Return to the center, then twist to the right.", fa: "به وسط برگردید و بعد به راست بچرخید." },
        ],
    },
    Exercise {
        id: "stand",
        icon: "person",
        title_en: "Stand up and walk",
        title_fa: "بلند شوید و راه بروید",
        kind: Kind::Body,
        steps: &[
            Step { seconds: 10, en: "Stand up and take a deep breath, arms overhead.", fa: "بلند شوید و با دست‌های بالای سر یک نفس عمیق بکشید." },
            Step { seconds: 30, en: "Walk around, get some water or look out of a window.", fa: "کمی راه بروید، آب بنوشید یا از پنجره بیرون را نگاه کنید." },
        ],
    },
];

/// Eye exercises followed by the body stretches.
pub fn all_exercises() -> impl Iterator<Item = &'static Exercise> {
    EXERCISES.iter().chain(STRETCHES.iter())
}

pub fn by_id(id: &str) -> Option<&'static Exercise> {
    all_exercises().find(|e| e.id == id)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::HashSet;

    #[test]
    fn every_exercise_has_steps_and_both_languages() {
        for e in all_exercises() {
            assert!(!e.steps.is_empty(), "{}", e.id);
            assert!(e.total_seconds() > 0);
            assert!(!e.title_en.is_empty() && !e.title_fa.is_empty());
            assert!(e.steps.iter().all(|s| s.seconds > 0 && !s.en.is_empty() && !s.fa.is_empty()));
        }
    }

    #[test]
    fn ids_are_unique_and_lookup_works() {
        let ids: HashSet<_> = all_exercises().map(|e| e.id).collect();
        assert_eq!(ids.len(), EXERCISES.len() + STRETCHES.len());
        assert_eq!(by_id("palming").unwrap().total_seconds(), 25);
        assert!(by_id("nope").is_none());
    }

    #[test]
    fn kinds_match_their_lists() {
        assert!(EXERCISES.iter().all(|e| e.kind == Kind::Eyes));
        assert!(STRETCHES.iter().all(|e| e.kind == Kind::Body));
        assert_eq!(EXERCISES.len(), 5);
        assert_eq!(STRETCHES.len(), 5);
    }
}
