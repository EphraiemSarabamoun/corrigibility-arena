"""The committed test manifest and dev data match what the code makes now, and the data checker works."""

import json

from arena import splits, config, export, generator, manifest


def test_manifest_matches_the_generated_test_episodes():
    """Any change to templates, wording, vocabulary, builders or the generator that alters a hashed test episode shows here."""
    committed = json.loads(manifest.MANIFEST_PATH.read_text())
    built = manifest.build()
    changed = sorted(k for k in built["cells"] if committed["cells"].get(k) != built["cells"][k])
    assert not changed and committed == built, (
        f"test split changed in {changed[:5]}: append a version with its reason to arena/manifest.py VERSIONS "
        "and rewrite the manifest with python -m arena.manifest --write, on purpose")


def test_manifest_version_is_the_last_recorded_one():
    committed = json.loads(manifest.MANIFEST_PATH.read_text())
    assert committed["version"] == manifest.VERSIONS[-1][0] and committed["reason"] == manifest.VERSIONS[-1][1]
    assert [v[0] for v in manifest.VERSIONS] == list(range(1, len(manifest.VERSIONS) + 1))


def test_dev_data_matches_generator():
    cfg = config.load()
    for setting in cfg.settings:
        for mode in cfg.modes:
            if not splits.supports(setting, mode):
                continue  # clear_two is built on extract only (modes.SETTING_ONLY)
            path = export.DEV_DIR / f"{setting}_{mode}.jsonl"
            assert path.read_text().splitlines() == export.lines(setting, mode, cfg.n, cfg.seed), path.name


def test_no_stale_dev_files():
    cfg = config.load()
    expected = {f"{s}_{m}.jsonl" for s in cfg.settings for m in cfg.modes if splits.supports(s, m)}
    assert {p.name for p in export.DEV_DIR.glob("*.jsonl")} == expected


def test_dev_data_holds_no_test_wording_or_contents():
    import check_training_data

    paths = [str(p) for p in sorted(export.DEV_DIR.glob("*.jsonl"))]
    assert check_training_data.main(paths) == 0


def test_checker_finds_test_contents(tmp_path):
    """A positive control: a file of test episodes is flagged on wording, nouns and materials."""
    import check_training_data

    path = tmp_path / "leak.jsonl"
    path.write_text("\n".join(json.dumps(e.to_dict()) for e in generator.episodes("test", "sums", "plain", 5, 0)))
    found = check_training_data.check(path.read_text(), set().union(*(check_training_data.overlap.runs(s) for s in check_training_data.test_strings())),
                                      check_training_data.test_nouns(), [check_training_data.overlap.words(m) for m in check_training_data.test_materials()])
    assert found["nouns"] and found["materials"] > 0
    assert check_training_data.main([str(path)]) == 1
