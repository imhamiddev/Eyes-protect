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
