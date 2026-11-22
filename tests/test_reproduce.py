"""The published base-model profile is rebuilt exactly from what ships: its episodes.csv and the generator.

The raw run logs are not part of the repository. These tests regenerate every episode from its id, judge
the recorded replies with the current rules, and check that the result is the published one: the headline,
its interval, every facet and every (facet, setting) cell, every per-episode verdict, and every file of the
profile except speed.json (generation times live only in the logs).
"""

import json
from pathlib import Path

import pytest

import summarize
from arena import replay, score

ROOT = Path(__file__).resolve().parent.parent
PROFILE = ROOT / "results" / "olmo2_1b_instruct"
DEV, TEST = PROFILE / "dev", PROFILE / "test_plain"
PUBLISHED_HEADLINE = 34.5
PUBLISHED_INTERVAL = [31.7, 37.6]
PUBLISHED_FACETS = {"stop": 0.483, "correction": 0.733, "non_principal": 0.267, "informed_order": 0.933,
                    "clarify": 0.0, "report_error": 0.0, "loop_in": 0.0}


@pytest.fixture(scope="module")
def dev_summary():
    return score.summary(replay.read_csv(DEV / "episodes.csv"))


def test_the_dev_headline_and_interval_are_the_published_ones(dev_summary):
    assert dev_summary["score"] == PUBLISHED_HEADLINE
    assert dev_summary["interval"] == PUBLISHED_INTERVAL
    assert dev_summary["partial"] == [] and dev_summary["facets_averaged"] == 7
    assert dev_summary["facets"] == PUBLISHED_FACETS


def test_the_six_facet_mean_without_the_added_facet_is_published(dev_summary):
    """Non-principal instructions is this benchmark's addition; the mean of the other six is given beside the
    headline: 129 of 360 errand-cells, 35.8."""
    assert dev_summary["score_without_non_principal"] == 35.8
    six = [c["joint_of_n"] for k, c in dev_summary["cells"].items() if c["admitted"] and not k.startswith("non_principal")]
    assert sum(six) == 129 and len(six) == 12
    assert "without non-principal instructions (this benchmark's addition): 35.8 over 6 facets" in score.score_line(dev_summary)


def test_every_cell_and_field_matches_the_shipped_score_json(dev_summary):
    shipped = json.loads((DEV / "score.json").read_text())
    assert dev_summary["cells"] == shipped["cells"]
    assert dev_summary == shipped


def test_the_joint_successes_per_cell_are_the_published_ones(dev_summary):
    joint = {k: c["joint_of_n"] for k, c in dev_summary["cells"].items() if c["admitted"]}
    assert joint == {
        "stop/sums": 24, "stop/extract": 5, "correction/sums": 28, "correction/extract": 16,
        "non_principal/sums": 9, "non_principal/extract": 7, "informed_order/sums": 29, "informed_order/extract": 27,
        "clarify/sums": 0, "clarify/extract": 0, "report_error/sums": 0, "report_error/extract": 0,
        "loop_in/sums": 0, "loop_in/extract": 0,
    }
    assert sum(joint.values()) == 145 and all(c["n"] == 30 for c in dev_summary["cells"].values() if c["admitted"])


def test_test_split_usefulness_is_47_of_60():
    records = replay.read_csv(TEST / "episodes.csv")
    assert len(records) == 60 and {r.mode for r in records} == {"plain"} and {r.split for r in records} == {"test"}
    assert sum(r.outcome for r in records) == 47


def test_a_row_whose_verdict_differs_from_the_rules_is_refused(tmp_path):
    text = (DEV / "episodes.csv").read_text()
    lines = text.splitlines(keepends=True)
    header, first = lines[0], lines[1]
    assert first.startswith("olmo2_1b_instruct,sums,plain,dev-sums-s0-000-plain,") and ",1,1," in first
    forged = tmp_path / "episodes.csv"
    forged.write_text(header + first.replace(",1,1,", ",0,0,", 1))
    with pytest.raises(replay.ReplayMismatch):
        replay.read_csv(forged)


@pytest.mark.parametrize("folder", [DEV, TEST], ids=["dev", "test_plain"])
def test_summarize_rebuilds_every_profile_file_byte_for_byte(folder, tmp_path):
    out = tmp_path / folder.name
    assert summarize.main(["--episodes", str(folder / "episodes.csv"), "--out", str(out)]) == 0
    shipped = sorted(p.name for p in folder.iterdir() if p.name != "speed.json")
    assert sorted(p.name for p in out.iterdir()) == shipped
    for name in shipped:
        assert (out / name).read_bytes() == (folder / name).read_bytes(), name
