"""The dev and test splits are disjoint in templates and wording, and every string formats."""

import pytest

from arena import overlap
from arena.splits import SPLITS
from arena.splits import dev as dev_split
from arena.splits import test as test_split
from arena.settings import SETTINGS


def all_strings(split):
    found = overlap.strings_of(split.wording) + overlap.strings_of(list(split.families))
    for setting in SETTINGS:
        found += overlap.strings_of(list(split.templates(setting)))
    return found


def test_template_ids_disjoint_and_prefixed():
    for name, split in SPLITS.items():
        for setting in SETTINGS:
            for t in split.templates(setting):
                assert t.id.startswith(f"{name}.{setting}.")
    dev_ids = {t.id for s in SETTINGS for t in dev_split.SPLIT.templates(s)}
    test_ids = {t.id for s in SETTINGS for t in test_split.SPLIT.templates(s)}
    assert not dev_ids & test_ids


def test_no_shared_five_word_run():
    shared = overlap.shared_runs(all_strings(dev_split.SPLIT), all_strings(test_split.SPLIT))
    assert not shared, sorted(shared)[:5]


def test_name_pools_disjoint():
    d, t = dev_split.WORDING, test_split.WORDING
    for field in ("principals", "others", "marker_words"):
        assert not set(getattr(d, field)) & set(getattr(t, field)), field


def test_content_pools_disjoint():
    """Dev and test draw names, shops, items, events and places from disjoint pools."""
    from arena import vocab

    assert not vocab.pool_entries(vocab.POOLS["dev"]) & vocab.pool_entries(vocab.POOLS["test"])
    every = vocab.pool_entries(vocab.POOLS["dev"]) | vocab.pool_entries(vocab.POOLS["test"])
    names = set(dev_split.WORDING.principals) | set(test_split.WORDING.principals) | set(dev_split.WORDING.others) | set(test_split.WORDING.others)
    assert not names & every, "a principal or third party is never also a pool name"


def test_no_test_string_within_one_word_of_a_dev_string():
    """Measured with a word-level edit distance over every wording and template string."""
    assert overlap.near_duplicates(all_strings(dev_split.SPLIT), all_strings(test_split.SPLIT)) == []


@pytest.mark.parametrize("name", sorted(SPLITS))
def test_transform_ops_cover_all(name):
    assert {t.op for t in SPLITS[name].transform} == {"first", "upper", "count"}


@pytest.mark.parametrize("name", sorted(SPLITS))
def test_extract_questions_cover_fields(name):
    for t in SPLITS[name].extract:
        assert set(t.questions) == {"date", "sender", "amount"} == set(t.field_nouns)


def test_no_angle_placeholder_in_closings():
    """The pilot found OLMo 2 1B Instruct drops the answer label when the closing shows '<your answer>'."""
    for split in SPLITS.values():
        w = split.wording
        for line in (*w.answer_format, *w.go_ahead, *w.correction_wrap):
            assert "<" not in line


@pytest.mark.parametrize("name", sorted(SPLITS))
def test_every_family_template_has_a_builder_and_its_slots(name):
    from arena import generator
    from arena.settings.families import BUILDERS

    for t in SPLITS[name].families:
        assert (t.family, t.setting, t.kind) in BUILDERS, t.id
        assert t.id.startswith(f"{name}.{t.family}.{t.setting}.")
    for family in ("warn", "clarify", "report", "loop"):
        for setting in ("sums", "extract"):
            assert SPLITS[name].templates(setting, family), (family, setting)
            for i in range(12):
                generator.make_errand(name, setting, 0, i, family)  # a missing slot raises KeyError
