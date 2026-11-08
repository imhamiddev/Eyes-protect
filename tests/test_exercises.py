import pytest

from eyecare.core.exercises import EXERCISES, by_id


def test_ids_unique_and_nonempty():
    ids = [e.id for e in EXERCISES]
    assert len(ids) == len(set(ids)) and ids


def test_totals_positive():
    assert all(e.total_seconds > 0 and e.steps for e in EXERCISES)


def test_by_id():
    assert by_id("palming").title_en == "Palming"
    with pytest.raises(KeyError):
        by_id("nope")


def test_stretches_are_complete_and_bilingual():
    from eyecare.core.exercises import ALL_EXERCISES, EXERCISES, STRETCHES, by_id

    assert len(STRETCHES) >= 5 and all(e.kind == "body" for e in STRETCHES)
    assert all(e.kind == "eyes" for e in EXERCISES)
    ids = [e.id for e in ALL_EXERCISES]
    assert len(ids) == len(set(ids))
    for e in STRETCHES:
        assert e.title_en and e.title_fa and e.total_seconds >= 20
        assert all(s.en and s.fa and s.seconds > 0 for s in e.steps)
    assert by_id("neck").kind == "body"
