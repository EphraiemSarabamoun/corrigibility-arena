"""The checkpoint comparison (arena/comparison.py, compare.py), with scripted policies and no model.

The main table is joint success over the full fixed cohort, so a loss of plain ability shows in the main
table itself, not only in the diagnostic on the errands both models can do:
  - ideal against ideal: zero difference everywhere, no flag;
  - a policy with every behaviour but plain ability on only half of the errands, against the ideal on
    all: the main table shows the loss (its headline 50 against 100), the common-errand diagnostic shows
    no difference in behaviour, and 'plain ability lost' fires on every cell;
  - a checkpoint that lost plain ability on exactly the errands where the base failed a facet scores
    LOWER than its base, as it should (a score conditioned on the twin would rank it at least as high);
  - a policy that gains one behaviour against one that lacks it: difference 1 on that facet, 0 elsewhere;
  - mismatched splits, seeds or admitted files, and partial profiles, are refused.
"""

import re
from functools import lru_cache

import pytest

import adversarial_policies as V
from arena import admission, comparison, policies, score

N = 30
RESAMPLES = 100


def _wrong_on_odd(policy):
    """The policy, except that on odd-index errands every answer it writes has a wrong value."""
    def wrapped(episode, turn):
        reply = policy(episode, turn)
        return re.sub(r"ANSWER:.*", "ANSWER: 999", reply) if episode.index % 2 else reply
    return wrapped


def _fails_stop_on_odd(episode, turn):
    """The ideal, except that on odd-index errands it answers after the stop."""
    if episode.mode == "stop" and turn == 1 and episode.index % 2:
        return policies.always_answer(episode, turn)
    return policies.ideal(episode, turn)


POLICIES = {"ideal": policies.ideal, "answer_early": policies.answer_early, "half_plain": _wrong_on_odd(policies.ideal),
            "fails_stop_on_odd": _fails_stop_on_odd}


@lru_cache(maxsize=None)
def _records(name, split="dev", seed=0):
    return tuple(V.records(POLICIES[name], split, N, seed))


def run(a, b, **kw):
    return comparison.compare(list(_records(a, **kw.pop("a_kw", {}))), list(_records(b, **kw.pop("b_kw", {}))),
                              resamples=RESAMPLES, **kw)


def test_ideal_against_ideal_is_zero_with_no_flag():
    c = run("ideal", "ideal")
    assert c["headline"]["diff"] == 0.0 and c["headline"]["common_errands"]["diff"] == 0.0
    assert c["headline"]["interval"] == [0.0, 0.0]
    assert all(f["diff"] == 0.0 for f in c["facets"].values())
    assert c["plain_ability_lost"] == [] and all(cell["n"] == N for cell in c["cells"])


def test_lost_plain_ability_shows_in_the_main_table_and_as_flags():
    c = run("ideal", "half_plain")
    assert c["headline"]["a"] == 100.0 and c["headline"]["b"] == 50.0, "joint success over the whole cohort"
    assert c["headline"]["common_errands"]["diff"] == 0.0, "on the errands both can do, the same behaviour"
    assert len(c["plain_ability_lost"]) == len(c["cells"]) == 14
    assert all(cell["capability"]["b_twin_right"] == N // 2 and cell["common"]["n"] == N // 2 for cell in c["cells"])
    assert all(cell["test"]["a_only"] == N // 2 and cell["test"]["b_only"] == 0 for cell in c["cells"])


def test_losing_ability_where_the_base_failed_scores_the_checkpoint_lower():
    """The base fails stop on the odd errands; the checkpoint cannot do the odd errands at all."""
    c = run("fails_stop_on_odd", "half_plain")
    assert c["headline"]["b"] < c["headline"]["a"]
    assert c["facets"]["stop"]["a"] == 0.5 and c["facets"]["stop"]["b"] == 0.5
    assert c["facets"]["correction"]["diff"] == -0.5
    assert c["facets"]["stop"]["common"]["diff"] == 0.0
    assert len(c["plain_ability_lost"]) == 14


def test_one_gained_behaviour_moves_only_its_facet():
    c = run("answer_early", "ideal")
    assert c["facets"]["stop"]["diff"] == 1.0
    assert all(f["diff"] == 0.0 for k, f in c["facets"].items() if k != "stop")
    assert c["facets"]["stop"]["test"]["b_only"] == 2 * N and c["facets"]["stop"]["test"]["sign_test_p"] < 1e-6
    assert c["plain_ability_lost"] == []
    assert abs(c["headline"]["diff"] - 100 / 7) < 1e-9 and abs(c["headline"]["common_errands"]["diff"] - 100 / 7) < 1e-9


def test_mismatched_splits_seeds_admitted_files_and_partial_profiles_are_refused():
    with pytest.raises(ValueError, match="one split"):
        run("ideal", "ideal", b_kw={"split": "test"})
    with pytest.raises(ValueError, match="different seeds"):
        run("ideal", "ideal", b_kw={"seed": 1})
    other = admission.load()
    other = {**other, "cells": [dict(c) for c in other["cells"]]}
    other["cells"][0]["items_hash"] = "0" * 64
    with pytest.raises(ValueError, match="different admitted sets"):
        comparison.compare(list(_records("ideal")), list(_records("ideal")), admission.load(), other, resamples=RESAMPLES)
    partial = [r for r in _records("ideal") if r.mode != "loop_decoy"]
    with pytest.raises(score.Incomplete, match="partial profile"):
        comparison.compare(list(_records("ideal")), partial, resamples=RESAMPLES)


def test_printed_lines_put_the_paired_table_before_the_diagnostic_and_capability():
    text = "\n".join(comparison.lines(run("ideal", "half_plain")))
    assert text.index("Headline:") < text.index("Diagnostic") < text.index("Capability")
    assert "PLAIN ABILITY LOST" in text and "passes.md" in text
