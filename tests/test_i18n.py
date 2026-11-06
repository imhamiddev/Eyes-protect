from eyecare.core import i18n


def test_every_english_key_has_persian():
    assert set(i18n.STRINGS["en"]) == set(i18n.STRINGS["fa"])


def test_switching_language():
    i18n.set_language("fa")
    assert i18n.is_rtl() and i18n.tr("nav.home") == "خانه"
    i18n.set_language("en")
    assert not i18n.is_rtl() and i18n.tr("nav.home") == "Home"


def test_unknown_key_and_language():
    i18n.set_language("xx")
    assert i18n.language() == "en"
    assert i18n.tr("no.such.key") == "no.such.key"
