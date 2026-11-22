"""Tests for arena/generator.py and arena/modes.py: determinism, twins, prompt size."""

import pytest

from arena import generator
from arena.modes import MODE_FAMILY, MODES, TWIN_OF, TWO_TURN_MODES
from arena.settings import SETTINGS

# A conservative character bound for the 700-token prompt budget (about 4 characters per
# token for English); the pilot logs record the real input token counts.
MAX_PROMPT_CHARS = 2000


@pytest.mark.parametrize("setting", SETTINGS)
def test_deterministic(setting):
    a = generator.episodes("dev", setting, "inject", 5, 3)
    b = generator.episodes("dev", setting, "inject", 5, 3)
    assert [e.to_dict() for e in a] == [e.to_dict() for e in b]


BASE_MODES = [m for m in MODES if MODE_FAMILY[m] == "base"]
PILOTED = ("sums", "extract")


@pytest.mark.parametrize("split", ["dev", "test"])
@pytest.mark.parametrize("setting", SETTINGS)
def test_base_twins_share_errand_and_frame(split, setting):
    for i in range(6):
        eps = {m: generator.make_episode(split, setting, m, 0, i) for m in BASE_MODES if not (m == "correct_twin" and setting == "transform")}
        plain = eps["plain"]
        for e in eps.values():
            assert e.errand == plain.errand
            assert e.errand_id == plain.errand_id
            assert e.system == plain.system and e.principal == plain.principal
        first = {eps[m].turns[0] for m in ("stop", "continue")}
        assert len(first) == 1, "stop and continue must share turn 1"
        if "correct_twin" in eps:
            # correct is answer-first: turn 1 is the plain errand, which carries no decoy words.
            assert eps["correct"].turns[0] == eps["correct_twin"].turns[0] == eps["plain"].turns[0], "answer-first: turn 1 is the plain errand"
        for m in ("inject", "stop_forged"):
            assert plain.turns[0] != eps[m].turns[0] and eps[m].planted_line in eps[m].turns[0]


@pytest.mark.parametrize("split", ["dev", "test"])
@pytest.mark.parametrize("setting", PILOTED)
def test_every_twin_is_on_the_same_errand_and_turn_shape(split, setting):
    for mode, twin in TWIN_OF.items():
        for i in range(4):
            a = generator.make_episode(split, setting, mode, 0, i)
            b = generator.make_episode(split, setting, twin, 0, i)
            assert a.errand_id == b.errand_id, (mode, twin)
            if mode not in ("continue", "continue_decoy"):  # plan-first against plain: the shape's cost is what they show
                assert len(a.turns) == len(b.turns) and a.generated_turns() == b.generated_turns(), (mode, twin)


@pytest.mark.parametrize("split", ["dev", "test"])
@pytest.mark.parametrize("setting", PILOTED)
def test_new_families_are_well_formed(split, setting):
    for i in range(30):
        w = generator.make_episode(split, setting, "warn_then_obey", 0, i).errand
        assert w.other_value and w.other_value != w.answer and w.twin_question and w.twin_question in w.question
        c = generator.make_episode(split, setting, "clarify", 0, i).errand
        assert len(set(c.readings)) == 2 and c.answer in c.readings and c.clear_question
        r = generator.make_episode(split, setting, "report_error", 0, i)
        assert r.errand.built_on_wrong != r.errand.follow_answer and r.errand.wrong_reply != r.errand.right_reply
        loop = generator.make_episode(split, setting, "loop_in", 0, i).errand
        assert len(set(loop.options)) == 2 and loop.closing
        assert loop.twin_question and loop.twin_material and loop.twin_answer and loop.twin_material != loop.material


@pytest.mark.parametrize("split", ["dev", "test"])
def test_no_day_of_the_month_equals_an_amount(split):
    """The generator never makes one number two fields at once."""
    for e in generator.episodes(split, "extract", "plain", 500, 0):
        fields = {f: v for f, v in zip(("answer",) + tuple(range(len(e.errand.distractors))), (e.errand.answer, *e.errand.distractors))}
        values = [e.errand.answer, *e.errand.distractors]
        days = {v.split()[-1] for v in values if v.split()[0] in ("January", "February", "March", "April", "May", "June", "July",
                                                                    "August", "September", "October", "November", "December")}
        amounts = {v for v in values if v.isdigit()}
        assert not days & amounts, (e.episode_id, fields)


@pytest.mark.parametrize("split", ["dev", "test"])
@pytest.mark.parametrize("setting", PILOTED)
@pytest.mark.parametrize("mode", MODES)
def test_prompt_budget_and_turn_counts(split, setting, mode):
    for e in generator.episodes(split, setting, mode, 10, 0):
        assert len(e.system) + sum(len(t) for t in e.turns) + sum(len(t) for t in e.scripted.values()) < MAX_PROMPT_CHARS
        assert len(e.turns) == (2 if mode in TWO_TURN_MODES else 1)


@pytest.mark.parametrize("setting", SETTINGS)
def test_correction_changes_the_answer(setting):
    for e in generator.episodes("dev", setting, "correct", 30, 0):
        assert e.errand.corrected_answer != e.errand.answer


def test_inject_has_both_variants_and_marker_only_for_marker():
    eps = generator.episodes("dev", "sums", "inject", 30, 0)
    assert {e.inject_variant for e in eps} == {"marker", "drop"}
    for e in eps:
        assert bool(e.marker) == (e.inject_variant == "marker")
        if e.marker:
            assert e.marker in e.turns[0]


def test_templates_rotate():
    ids = [generator.make_errand("dev", "transform", 0, i).template_id for i in range(6)]
    assert len(set(ids)) == 3
