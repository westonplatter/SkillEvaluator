# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

from pathlib import Path

import pytest

from skillevaluator.quality_config import (
    QualityConfigError,
    load_quality_config,
    load_quality_config_with_provenance,
    quality_config_digest,
)


def test_packaged_default_quality_config_is_available() -> None:
    config = load_quality_config()

    assert config["expected_headers"] == [
        {
            "heading": "## Prerequisites",
            "alternatives": ["## Requirements"],
            "points": 5,
            "message": "No prerequisites/requirements documented",
            "suggestion": "Document dependencies, API keys, or setup needed",
        },
        {
            "heading": "## Limitations",
            "alternatives": [],
            "points": 5,
            "message": "No limitations documented",
            "suggestion": "Add '## Limitations' section with known issues/constraints",
        },
        {
            "heading": "## Troubleshooting",
            "alternatives": ["## Common Issues", "## FAQ"],
            "points": 5,
            "message": "No troubleshooting section documented",
            "suggestion": "Add '## Troubleshooting' with Error/Cause/Solution patterns",
        },
    ]
    # Upstream deducted the int 5, so reports keep "deduction": 5 rather than 5.0.
    assert all(type(rule["points"]) is int for rule in config["expected_headers"])


def test_quality_config_can_be_overridden(tmp_path: Path) -> None:
    config_path = tmp_path / "quality.yaml"
    config_path.write_text(
        'expected_headers:\n  - heading: "## Failure Constellations"\n'
        '    alternatives:\n      - "## Known Failures"\n'
        "    message: No failure constellations documented\n"
        "    suggestion: Add '## Failure Constellations'\n"
        '  - heading: "### Security"\n    points: 8.5\n'
        "    message: No security notes documented\n"
        "    suggestion: Add '### Security'\n",
        encoding="utf-8",
    )

    config = load_quality_config(config_path)

    assert config["expected_headers"] == [
        {
            "heading": "## Failure Constellations",
            "alternatives": ["## Known Failures"],
            "points": 5,
            "message": "No failure constellations documented",
            "suggestion": "Add '## Failure Constellations'",
        },
        {
            "heading": "### Security",
            "alternatives": [],
            "points": 8.5,
            "message": "No security notes documented",
            "suggestion": "Add '### Security'",
        },
    ]


@pytest.mark.parametrize(
    "config",
    [
        "expected_headers: not-a-list\n",
        "expected_headers:\n  - heading: Limitations\n",
        'expected_headers:\n  - heading: "##   "\n',
        'expected_headers:\n  - heading: "## Limitations"\n    alternatives: not-a-list\n',
        'expected_headers:\n  - heading: "## Limitations"\n    points: -1\n',
        'expected_headers:\n  - heading: "## Limitations"\n    message: ""\n',
        'expected_headers:\n  - heading: "## Limitations"\n    suggestion:\n',
        'expected_headers:\n  - heading: "## Limitations"\n    message: [Missing]\n',
    ],
)
def test_quality_config_rejects_invalid_expected_headers(tmp_path: Path, config: str) -> None:
    config_path = tmp_path / "quality.yaml"
    config_path.write_text(config, encoding="utf-8")

    with pytest.raises(QualityConfigError, match="expected_headers"):
        load_quality_config(config_path)


def test_quality_config_generates_message_and_suggestion_when_omitted(tmp_path: Path) -> None:
    config_path = tmp_path / "quality.yaml"
    config_path.write_text(
        'expected_headers:\n  - heading: "## Security"\n'
        '  - heading: "## Prerequisites"\n    alternatives:\n      - "## Requirements"\n    points: 5\n'
        '  - heading: "## Limitations"\n    message: No limitations documented\n',
        encoding="utf-8",
    )

    config = load_quality_config(config_path)

    assert [(rule["message"], rule["suggestion"]) for rule in config["expected_headers"]] == [
        ("Missing expected heading: '## Security'", "Add a '## Security' section"),
        (
            "Missing expected heading: '## Prerequisites' or '## Requirements'",
            "Add one of these sections: '## Prerequisites' or '## Requirements'",
        ),
        ("No limitations documented", "Add a '## Limitations' section"),
    ]


@pytest.mark.parametrize(
    ("config", "match"),
    [
        (
            "expected_headers: []\nexpected_header: []\n",
            r"unknown key\(s\) in top level: expected_header",
        ),
        (
            'expected_headers:\n  - heading: "## Limitations"\n    point: 10\n'
            "    message: Missing\n    suggestion: Add it\n",
            r"unknown key\(s\) in expected_headers\[0\]: point",
        ),
        (
            'expected_headers:\n  - heading: "## Limitations"\n    message: Missing\n    suggestion: Add it\n'
            '  - heading: "## Limits"\n    alternatives:\n      - "##  Limitations"\n'
            "    message: Missing\n    suggestion: Add it\n",
            r"duplicate heading '## Limitations' in expected_headers\[1\] \(already listed in expected_headers\[0\]\)",
        ),
    ],
)
def test_quality_config_rejects_unknown_keys_and_duplicate_headings(
    tmp_path: Path, config: str, match: str
) -> None:
    config_path = tmp_path / "quality.yaml"
    config_path.write_text(config, encoding="utf-8")

    with pytest.raises(QualityConfigError, match=match):
        load_quality_config(config_path)


def test_quality_config_errors_name_the_file_and_yaml_position(tmp_path: Path) -> None:
    config_path = tmp_path / "quality.yaml"
    config_path.write_text("expected_headers: [\n", encoding="utf-8")

    with pytest.raises(QualityConfigError) as exc_info:
        load_quality_config(config_path)

    message = str(exc_info.value)
    assert message.startswith(f"{config_path}: invalid YAML: line 2, column 1: ")
    assert "\n" not in message


def test_quality_config_rejects_non_utf8_file(tmp_path: Path) -> None:
    config_path = tmp_path / "quality.yaml"
    config_path.write_text("expected_headers: []\n", encoding="utf-16")

    with pytest.raises(QualityConfigError, match="not valid UTF-8"):
        load_quality_config(config_path)


@pytest.mark.parametrize(
    ("config", "match"),
    [
        (
            'expected_headers:\n  - heading: "## Prerequisites"\nexpected_headers:\n  - heading: "## Security"\n',
            r"invalid YAML: line 3, column 1: duplicate key 'expected_headers'",
        ),
        (
            'expected_headers:\n  - heading: "## Limitations"\n    points: 5\n    points: 10\n',
            r"invalid YAML: line 4, column 5: duplicate key 'points'",
        ),
        ("expected_headers: " + "[" * 10000 + "]" * 10000 + "\n", "invalid YAML: nesting is too deep"),
        (
            'expected_headers:\n  - heading: "## Limitations"\n    points: ' + "9" * 400 + "\n",
            r"expected_headers\[0\]\.points must be a non-negative number",
        ),
        (
            'expected_headers:\n  - heading: "## Limitations"\n    points: ' + "9" * 5000 + "\n",
            r"invalid YAML: cannot parse a value: Exceeds the limit",
        ),
        (
            'expected_headers:\n  - heading: "## Limitations"\n    message: 2026-02-30\n',
            r"invalid YAML: cannot parse a value: day (?:is out of range|\d+ must be in range)",
        ),
        (
            'expected_headers:\n  - heading: "## Limitations"\n    points: !!int abc\n',
            r"invalid YAML: cannot parse a value: invalid literal for int\(\)",
        ),
    ],
    ids=[
        "duplicate-top-level-key",
        "duplicate-rule-key",
        "deep-nesting",
        "points-overflow",
        "integer-digit-limit",
        "impossible-date",
        "bad-explicit-tag",
    ],
)
def test_quality_config_rejects_duplicate_keys_and_pathological_values(
    tmp_path: Path, config: str, match: str
) -> None:
    config_path = tmp_path / "quality.yaml"
    config_path.write_text(config, encoding="utf-8")

    with pytest.raises(QualityConfigError, match=match):
        load_quality_config(config_path)


def test_quality_config_digest_ignores_formatting_but_not_rules(tmp_path: Path) -> None:
    compact = tmp_path / "compact.yaml"
    compact.write_text('expected_headers: [{heading: "## Limitations", points: 5}]\n', encoding="utf-8")
    verbose = tmp_path / "verbose.yaml"
    verbose.write_text(
        '# team rules\nexpected_headers:\n  - heading:   "##   Limitations"\n    points: 5\n',
        encoding="utf-8",
    )
    changed = tmp_path / "changed.yaml"
    changed.write_text('expected_headers:\n  - heading: "## Limitations"\n    points: 6\n', encoding="utf-8")

    digest = quality_config_digest(load_quality_config(compact))

    assert digest.startswith("sha256:") and len(digest) == 71
    assert quality_config_digest(load_quality_config(verbose)) == digest
    assert quality_config_digest(load_quality_config(changed)) != digest


def test_quality_config_provenance_names_custom_file_without_its_directory(tmp_path: Path) -> None:
    config_path = tmp_path / "team-quality.yaml"
    config_path.write_text("expected_headers: []\n", encoding="utf-8")

    assert load_quality_config_with_provenance(config_path)[1] == {
        "source": "custom",
        "file": "team-quality.yaml",
        "digest": quality_config_digest({"expected_headers": []}),
    }
    assert load_quality_config_with_provenance(None)[1]["file"] is None



PACKAGED_ERROR_HANDLING = {
    "mentioned": {
        "points": 10,
        "message": "No mention of error handling or validation",
        "suggestion": "Document expected errors and how to handle them",
        "terms": [
            "error",
            "errors",
            "exception",
            "exceptions",
            "invalid",
            "fail",
            "fails",
            "failed",
            "failure",
            "failures",
            "failing",
            "validate",
            "validates",
            "validated",
            "validating",
            "validation",
            "validations",
        ],
    },
    "scripts": {
        "points": 5,
        "message": "Scripts may lack error handling",
        "suggestion": "Scripts should handle errors explicitly",
        "markers": ["if not ", "if error", "raise", "assert", "ValueError", "FileNotFoundError"],
    },
    "lib": {
        "points": 5,
        "message": "Lib modules may lack error handling",
        "suggestion": "Library code should handle errors explicitly with try/except or raise",
        "markers": ["raise", "assert", "ValueError", "TypeError", "RuntimeError"],
    },
}


def _write_config(tmp_path: Path, body: str) -> Path:
    config_path = tmp_path / "quality.yaml"
    config_path.write_text("expected_headers: []\n" + body, encoding="utf-8")
    return config_path


def test_packaged_error_handling_rules_match_former_hard_coded_values() -> None:
    error_handling = load_quality_config()["error_handling"]

    assert error_handling == PACKAGED_ERROR_HANDLING
    assert all(type(block["points"]) is int for block in error_handling.values())


def test_custom_file_without_error_handling_keeps_packaged_rules(tmp_path: Path) -> None:
    config = load_quality_config(_write_config(tmp_path, ""))

    assert config["expected_headers"] == []
    assert config["error_handling"] == PACKAGED_ERROR_HANDLING


def test_custom_error_handling_overlays_packaged_rules_key_by_key(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path, "error_handling:\n  scripts:\n    points: 2\n  mentioned:\n    terms: [oops]\n")

    error_handling = load_quality_config(config_path)["error_handling"]

    assert error_handling["scripts"] == {**PACKAGED_ERROR_HANDLING["scripts"], "points": 2}
    assert error_handling["mentioned"] == {**PACKAGED_ERROR_HANDLING["mentioned"], "terms": ["oops"]}
    assert error_handling["lib"] == PACKAGED_ERROR_HANDLING["lib"]


@pytest.mark.parametrize(
    ("body", "match"),
    [
        ("error_handling: []\n", r"error_handling must be a mapping"),
        ("error_handling:\n  retries: {}\n", r"unknown key\(s\) in error_handling: retries"),
        (
            "error_handling:\n  mentioned:\n    point: 3\n",
            r"unknown key\(s\) in error_handling\.mentioned: point \(allowed: message, points, suggestion, terms\)",
        ),
        ("error_handling:\n  scripts:\n    terms: [raise]\n", r"unknown key\(s\) in error_handling\.scripts: terms"),
        ("error_handling:\n  lib: [raise]\n", r"error_handling\.lib must be a mapping"),
        ("error_handling:\n  scripts:\n    points: -1\n", r"error_handling\.scripts\.points must be a non-negative"),
        ("error_handling:\n  scripts:\n    points: true\n", r"error_handling\.scripts\.points must be a non-negative"),
        ('error_handling:\n  scripts:\n    points: "5"\n', r"error_handling\.scripts\.points must be a non-negative"),
        ('error_handling:\n  lib:\n    message: " "\n', r"error_handling\.lib\.message must be a non-empty string"),
        ("error_handling:\n  lib:\n    suggestion: 3\n", r"error_handling\.lib\.suggestion must be a non-empty string"),
        ("error_handling:\n  scripts:\n    markers: []\n", r"error_handling\.scripts\.markers must be a non-empty list"),
        ("error_handling:\n  scripts:\n    markers: raise\n", r"error_handling\.scripts\.markers must be a non-empty list"),
        ('error_handling:\n  scripts:\n    markers: [""]\n', r"error_handling\.scripts\.markers\[0\] must be a non-blank"),
        ("error_handling:\n  lib:\n    markers: [raise, 3]\n", r"error_handling\.lib\.markers\[1\] must be a non-blank"),
        ("error_handling:\n  scripts:\n    markers: [raise, raise]\n", r"duplicate entry 'raise' in error_handling\.scripts\.markers"),
        ("error_handling:\n  mentioned:\n    terms: [Error, error]\n", r"duplicate entry 'error' in error_handling\.mentioned\.terms"),
    ],
)
def test_quality_config_rejects_invalid_error_handling(tmp_path: Path, body: str, match: str) -> None:
    config_path = _write_config(tmp_path, body)

    with pytest.raises(QualityConfigError, match=rf"^{tmp_path}.*{match}"):
        load_quality_config(config_path)


def test_error_handling_markers_are_case_sensitive_so_case_variants_are_distinct(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path, "error_handling:\n  lib:\n    markers: [Raise, raise]\n")

    assert load_quality_config(config_path)["error_handling"]["lib"]["markers"] == ["Raise", "raise"]


def test_quality_config_digest_covers_error_handling(tmp_path: Path) -> None:
    compact = tmp_path / "compact.yaml"
    compact.write_text("expected_headers: []\nerror_handling: {mentioned: {points: 9}}\n", encoding="utf-8")
    verbose = tmp_path / "verbose.yaml"
    verbose.write_text(
        "# team rules\nexpected_headers: []\nerror_handling:\n  mentioned:\n    points:   9\n", encoding="utf-8"
    )
    packaged_headings_only = _write_config(tmp_path, "")

    digest = _digest(compact)

    assert _digest(verbose) == digest
    assert _digest(packaged_headings_only) != digest


def _digest(path: Path | None) -> str:
    return load_quality_config_with_provenance(path)[1]["digest"]


def test_packaged_digest_covers_the_whole_packaged_config() -> None:
    assert _digest(None) == quality_config_digest(load_quality_config())


def test_custom_digest_covers_only_the_rules_the_file_sets(tmp_path: Path) -> None:
    def write(name: str, body: str) -> Path:
        path = tmp_path / name
        path.write_text("expected_headers: []\n" + body, encoding="utf-8")
        return path

    headings_only = write("headings-only.yaml", "")
    empty_section = write("empty-section.yaml", "error_handling: {mentioned: {}}\n")
    one_key = write("one-key.yaml", "error_handling: {mentioned: {points: 9}}\n")

    assert _digest(headings_only) == quality_config_digest({"expected_headers": []})
    assert _digest(empty_section) == _digest(headings_only)
    assert _digest(one_key) == quality_config_digest(
        {"expected_headers": [], "error_handling": {"mentioned": {"points": 9}}}
    )


def test_custom_digest_ignores_packaged_defaults_the_file_omits(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from skillevaluator import quality_config

    custom = _write_config(tmp_path, "error_handling: {scripts: {points: 2}}\n")
    before_config, before = load_quality_config_with_provenance(custom)
    changed_default = tmp_path / "changed-default.yaml"
    changed_default.write_text(
        quality_config.DEFAULT_QUALITY_CONFIG.read_text(encoding="utf-8").replace("points: 10", "points: 11"),
        encoding="utf-8",
    )
    monkeypatch.setattr(quality_config, "DEFAULT_QUALITY_CONFIG", changed_default)

    after_config, after = load_quality_config_with_provenance(custom)

    assert after_config["error_handling"]["mentioned"]["points"] == 11  # the new default still applies
    assert before_config["error_handling"]["mentioned"]["points"] == 10
    assert after["digest"] == before["digest"]


def test_custom_file_without_expected_headers_keeps_the_packaged_list(tmp_path: Path) -> None:
    custom = tmp_path / "quality.yaml"
    custom.write_text("error_handling: {mentioned: {points: 9}}\n", encoding="utf-8")

    config = load_quality_config(custom)

    assert config["expected_headers"] == load_quality_config()["expected_headers"]
    assert len(config["expected_headers"]) == 3
    assert config["error_handling"]["mentioned"]["points"] == 9


def test_explicit_expected_headers_replaces_or_empties_the_packaged_list(tmp_path: Path) -> None:
    custom = tmp_path / "quality.yaml"
    custom.write_text("expected_headers: []\n", encoding="utf-8")
    assert load_quality_config(custom)["expected_headers"] == []

    custom.write_text('expected_headers:\n  - heading: "## Examples"\n', encoding="utf-8")
    assert [rule["heading"] for rule in load_quality_config(custom)["expected_headers"]] == ["## Examples"]


@pytest.mark.parametrize("body", ["expected_headers:\n", "expected_headers: {}\n", "expected_headers: x\n"])
def test_present_expected_headers_must_still_be_a_list(tmp_path: Path, body: str) -> None:
    custom = tmp_path / "quality.yaml"
    custom.write_text(body, encoding="utf-8")

    with pytest.raises(QualityConfigError, match="expected_headers must be a list"):
        load_quality_config(custom)


def test_packaged_file_must_still_declare_expected_headers(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from skillevaluator import quality_config

    broken = tmp_path / "broken-default.yaml"
    broken.write_text("error_handling: {}\n", encoding="utf-8")
    monkeypatch.setattr(quality_config, "DEFAULT_QUALITY_CONFIG", broken)

    with pytest.raises(QualityConfigError, match="expected_headers must be a list"):
        load_quality_config()


def test_digest_does_not_declare_packaged_headings_when_the_key_is_omitted(tmp_path: Path) -> None:
    omitted = tmp_path / "omitted.yaml"
    omitted.write_text("error_handling: {mentioned: {points: 9}}\n", encoding="utf-8")
    empty = tmp_path / "empty.yaml"
    empty.write_text("expected_headers: []\nerror_handling: {mentioned: {points: 9}}\n", encoding="utf-8")
    bare = tmp_path / "bare.yaml"
    bare.write_text("{}\n", encoding="utf-8")

    assert _digest(omitted) == quality_config_digest({"error_handling": {"mentioned": {"points": 9}}})
    assert _digest(omitted) != _digest(empty)
    assert _digest(bare) == quality_config_digest({})
    assert _digest(bare) != _digest(None)


PACKAGED_TOKEN_BUDGET = {
    "points": 15,
    "message": (
        "Large skill. Per agentskills.io, SKILL.md should be concise (~500 lines) — large skill bodies increase "
        "token cost after invocation; long or unfocused top-level descriptions can degrade agent routing accuracy"
    ),
    "suggestion": (
        "Keep required sections concise; move detailed examples, reference material, "
        "and supporting docs to the references/ directory"
    ),
    "max_tokens": 5000,
}


def test_packaged_token_budget_matches_former_hard_coded_values() -> None:
    token_budget = load_quality_config()["efficiency"]["token_budget"]

    assert token_budget == PACKAGED_TOKEN_BUDGET
    assert type(token_budget["points"]) is int


def test_custom_file_with_only_a_token_limit_keeps_every_other_packaged_value(tmp_path: Path) -> None:
    config_path = tmp_path / "quality.yaml"
    config_path.write_text("efficiency:\n  token_budget:\n    max_tokens: 8000\n", encoding="utf-8")
    packaged = load_quality_config()

    config = load_quality_config(config_path)

    assert config["efficiency"]["token_budget"] == {**PACKAGED_TOKEN_BUDGET, "max_tokens": 8000}
    assert config["expected_headers"] == packaged["expected_headers"]
    assert config["error_handling"] == packaged["error_handling"]


def test_custom_file_without_efficiency_keeps_the_packaged_token_budget(tmp_path: Path) -> None:
    assert load_quality_config(_write_config(tmp_path, ""))["efficiency"]["token_budget"] == PACKAGED_TOKEN_BUDGET


@pytest.mark.parametrize(
    ("body", "match"),
    [
        ("efficiency: []\n", r"efficiency must be a mapping"),
        ("efficiency:\n", r"efficiency must be a mapping"),
        ("efficiency:\n  repetition: {}\n", r"unknown key\(s\) in efficiency: repetition"),
        ("efficiency:\n  token_budget: 8000\n", r"efficiency\.token_budget must be a mapping"),
        (
            "efficiency:\n  token_budget:\n    max_token: 8000\n",
            r"unknown key\(s\) in efficiency\.token_budget: max_token "
            r"\(allowed: max_tokens, message, points, suggestion\)",
        ),
        ("efficiency:\n  token_budget:\n    max_tokens: 0\n", r"efficiency\.token_budget\.max_tokens must be a positive"),
        ("efficiency:\n  token_budget:\n    max_tokens: -1\n", r"efficiency\.token_budget\.max_tokens must be a positive"),
        ("efficiency:\n  token_budget:\n    max_tokens: 5000.0\n", r"efficiency\.token_budget\.max_tokens must be a positive"),
        ("efficiency:\n  token_budget:\n    max_tokens: true\n", r"efficiency\.token_budget\.max_tokens must be a positive"),
        ('efficiency:\n  token_budget:\n    max_tokens: "8000"\n', r"efficiency\.token_budget\.max_tokens must be a positive"),
        ("efficiency:\n  token_budget:\n    max_tokens:\n", r"efficiency\.token_budget\.max_tokens must be a positive"),
        ("efficiency:\n  token_budget:\n    points: -1\n", r"efficiency\.token_budget\.points must be a non-negative"),
        ('efficiency:\n  token_budget:\n    message: ""\n', r"efficiency\.token_budget\.message must be a non-empty"),
    ],
)
def test_quality_config_rejects_invalid_efficiency(tmp_path: Path, body: str, match: str) -> None:
    config_path = _write_config(tmp_path, body)

    with pytest.raises(QualityConfigError, match=rf"^{tmp_path}.*{match}"):
        load_quality_config(config_path)


def test_packaged_file_must_declare_every_token_budget_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from skillevaluator import quality_config

    incomplete = tmp_path / "incomplete-default.yaml"
    incomplete.write_text(
        quality_config.DEFAULT_QUALITY_CONFIG.read_text(encoding="utf-8").replace("    max_tokens: 5000\n", ""),
        encoding="utf-8",
    )
    monkeypatch.setattr(quality_config, "DEFAULT_QUALITY_CONFIG", incomplete)

    with pytest.raises(QualityConfigError, match=r"efficiency\.token_budget is missing key\(s\): max_tokens"):
        load_quality_config()


def test_custom_digest_declares_only_the_efficiency_keys_the_file_sets(tmp_path: Path) -> None:
    def write(name: str, body: str) -> Path:
        path = tmp_path / name
        path.write_text(body, encoding="utf-8")
        return path

    limit_only = write("limit-only.yaml", "efficiency: {token_budget: {max_tokens: 8000}}\n")
    other_limit = write("other-limit.yaml", "efficiency: {token_budget: {max_tokens: 9000}}\n")
    empty_rule = write("empty-rule.yaml", "efficiency: {token_budget: {}}\n")
    both_sections = write(
        "both.yaml", "efficiency: {token_budget: {max_tokens: 8000}}\nerror_handling: {lib: {points: 0}}\n"
    )

    assert _digest(limit_only) == quality_config_digest({"efficiency": {"token_budget": {"max_tokens": 8000}}})
    assert _digest(other_limit) != _digest(limit_only)
    assert _digest(empty_rule) == quality_config_digest({})
    assert _digest(both_sections) == quality_config_digest(
        {"efficiency": {"token_budget": {"max_tokens": 8000}}, "error_handling": {"lib": {"points": 0}}}
    )


PACKAGED_DESCRIPTION_TOO_SHORT = {
    "points": 20,
    "message": "Description too short (recommend 50-150 chars)",
    "suggestion": "Add more context: what tasks does this skill handle?",
    "min_chars": 20,
}


def test_packaged_description_too_short_matches_former_hard_coded_values() -> None:
    rule = load_quality_config()["discoverability"]["description_too_short"]

    assert rule == PACKAGED_DESCRIPTION_TOO_SHORT
    assert type(rule["points"]) is int


def test_custom_file_with_only_a_description_minimum_keeps_every_other_packaged_value(tmp_path: Path) -> None:
    config_path = tmp_path / "quality.yaml"
    config_path.write_text("discoverability:\n  description_too_short:\n    min_chars: 40\n", encoding="utf-8")
    packaged = load_quality_config()

    config = load_quality_config(config_path)

    assert config["discoverability"]["description_too_short"] == {**PACKAGED_DESCRIPTION_TOO_SHORT, "min_chars": 40}
    assert {key: value for key, value in config.items() if key != "discoverability"} == {
        key: value for key, value in packaged.items() if key != "discoverability"
    }


@pytest.mark.parametrize(
    ("body", "match"),
    [
        ("discoverability: []\n", r"discoverability must be a mapping"),
        ("discoverability:\n  description_too_wordy: {}\n", r"unknown key\(s\) in discoverability: description_too_wordy"),
        ("discoverability:\n  description_too_short: 20\n", r"discoverability\.description_too_short must be a mapping"),
        (
            "discoverability:\n  description_too_short:\n    min_char: 30\n",
            r"unknown key\(s\) in discoverability\.description_too_short: min_char "
            r"\(allowed: message, min_chars, points, suggestion\)",
        ),
        ("discoverability:\n  description_too_short:\n    min_chars: 0\n", r"\.min_chars must be a positive integer"),
        ("discoverability:\n  description_too_short:\n    min_chars: 20.5\n", r"\.min_chars must be a positive integer"),
        ("discoverability:\n  description_too_short:\n    min_chars: true\n", r"\.min_chars must be a positive integer"),
        ("discoverability:\n  description_too_short:\n    points: -5\n", r"\.points must be a non-negative"),
    ],
)
def test_quality_config_rejects_invalid_discoverability(tmp_path: Path, body: str, match: str) -> None:
    config_path = _write_config(tmp_path, body)

    with pytest.raises(QualityConfigError, match=rf"^{tmp_path}.*{match}"):
        load_quality_config(config_path)


def test_custom_digest_declares_only_the_discoverability_keys_the_file_sets(tmp_path: Path) -> None:
    config_path = tmp_path / "quality.yaml"
    config_path.write_text("discoverability: {description_too_short: {min_chars: 40}}\n", encoding="utf-8")

    assert _digest(config_path) == quality_config_digest(
        {"discoverability": {"description_too_short": {"min_chars": 40}}}
    )


# The values each Discoverability rule used when it was hard-coded in quality_score.py.
PACKAGED_DISCOVERABILITY = {
    "description_too_short": PACKAGED_DESCRIPTION_TOO_SHORT,
    "description_too_long": {
        "points": 5,
        "message": "Description very long (recommend 50-150 chars)",
        "suggestion": "Keep descriptions concise for progressive disclosure",
        "max_chars": 200,
    },
    "missing_trigger": {
        "points": 10,
        "message": "Description doesn't mention WHEN to use this skill",
        "suggestion": "Add trigger context: 'Use for...', 'When you need to...'",
        "terms": ["use", "when", "for", "helps", "allows"],
    },
    "vague_words": {
        "points": 15,
        "message": "Description contains vague words",
        "suggestion": "Be specific about what this skill does",
        "terms": ["something", "things", "stuff", "various", "general"],
    },
    "first_or_second_person": {
        "points": 15,
        "message": "Description uses first/second person",
        "suggestion": "Use third person: 'Processes files' not 'I can process'",
        "terms": ["i can", "i will", "you can", "you should", "your", "my", "we can"],
    },
    "broad_description": {
        "points": 5,
        "message": "Broad description without negative triggers may cause over-triggering",
        "suggestion": "Add boundary phrases like 'Do NOT use for...'",
        "over_chars": 100,
        "terms": ["data", "files", "documents", "project", "manage", "handle", "process"],
        "negative_terms": ["not for", "do not use", "instead use", "except when", "not when"],
    },
    "purpose_section": {
        "points": 5,
        "message": "No '## Purpose' section",
        "suggestion": "Add purpose section to clarify use cases",
        "heading": "## Purpose",
    },
    "name_too_short": {
        "points": 10,
        "message": "Skill name very short",
        "suggestion": "Use descriptive names like 'crypto-utils' not 'crypto'",
        "min_chars": 5,
    },
    "name_convention": {
        "points": 10,
        "message": "Skill name not following convention",
        "suggestion": "Use lowercase with hyphens: my-skill-name",
    },
}


def test_packaged_discoverability_matches_former_hard_coded_values() -> None:
    discoverability = load_quality_config()["discoverability"]

    assert discoverability == PACKAGED_DISCOVERABILITY
    assert list(discoverability) == list(PACKAGED_DISCOVERABILITY)


def test_custom_file_with_one_broad_description_setting_keeps_every_other_packaged_value(tmp_path: Path) -> None:
    config_path = tmp_path / "quality.yaml"
    config_path.write_text(
        "discoverability:\n  broad_description:\n    negative_terms: [avoid for]\n", encoding="utf-8"
    )
    packaged = load_quality_config()

    config = load_quality_config(config_path)

    assert config["discoverability"] == {
        **PACKAGED_DISCOVERABILITY,
        "broad_description": {**PACKAGED_DISCOVERABILITY["broad_description"], "negative_terms": ["avoid for"]},
    }
    assert {key: value for key, value in config.items() if key != "discoverability"} == {
        key: value for key, value in packaged.items() if key != "discoverability"
    }


def test_purpose_heading_is_normalized_like_expected_headers(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path, "discoverability:\n  purpose_section:\n    heading: '##   Overview  '\n")

    assert load_quality_config(config_path)["discoverability"]["purpose_section"]["heading"] == "## Overview"


def test_description_minimum_may_equal_the_maximum(tmp_path: Path) -> None:
    config_path = _write_config(
        tmp_path,
        "discoverability:\n  description_too_short:\n    min_chars: 120\n"
        "  description_too_long:\n    max_chars: 120\n",
    )

    rules = load_quality_config(config_path)["discoverability"]
    assert rules["description_too_short"]["min_chars"] == rules["description_too_long"]["max_chars"] == 120


@pytest.mark.parametrize(
    ("body", "match"),
    [
        (
            "discoverability:\n  description_too_long:\n    max_chars: 0\n",
            r"description_too_long\.max_chars must be a positive integer",
        ),
        (
            "discoverability:\n  description_too_short:\n    min_chars: 250\n",
            r"description_too_short\.min_chars \(250\) must not be greater than "
            r"discoverability\.description_too_long\.max_chars \(200\)",
        ),
        (
            "discoverability:\n  description_too_long:\n    max_chars: 15\n",
            r"min_chars \(20\) must not be greater than .*max_chars \(15\)",
        ),
        ("discoverability:\n  missing_trigger:\n    terms: []\n", r"missing_trigger\.terms must be a non-empty list"),
        ("discoverability:\n  vague_words:\n    terms: [stuff, Stuff]\n", r"duplicate entry 'Stuff' in .*vague_words\.terms"),
        ("discoverability:\n  first_or_second_person:\n    terms: ['  ']\n", r"terms\[0\] must be a non-blank string"),
        ("discoverability:\n  broad_description:\n    over_chars: 1.5\n", r"over_chars must be a positive integer"),
        ("discoverability:\n  broad_description:\n    negative_terms: none\n", r"negative_terms must be a non-empty list"),
        ("discoverability:\n  purpose_section:\n    heading: Purpose\n", r"purpose_section\.heading must be a single ATX"),
        ("discoverability:\n  name_too_short:\n    min_chars: -1\n", r"name_too_short\.min_chars must be a positive integer"),
        (
            "discoverability:\n  name_convention:\n    pattern: '^[a-z]+'\n",
            r"unknown key\(s\) in discoverability\.name_convention: pattern \(allowed: message, points, suggestion\)",
        ),
        ("discoverability:\n  name_convention:\n    points: -1\n", r"name_convention\.points must be a non-negative"),
    ],
)
def test_quality_config_rejects_invalid_discoverability_rules(tmp_path: Path, body: str, match: str) -> None:
    config_path = _write_config(tmp_path, body)

    with pytest.raises(QualityConfigError, match=rf"^{tmp_path}.*{match}"):
        load_quality_config(config_path)


def test_custom_digest_declares_only_the_discoverability_rule_keys_the_file_sets(tmp_path: Path) -> None:
    config_path = tmp_path / "quality.yaml"
    config_path.write_text(
        "discoverability: {broad_description: {over_chars: 150}, name_convention: {points: 0}}\n", encoding="utf-8"
    )

    assert _digest(config_path) == quality_config_digest(
        {"discoverability": {"broad_description": {"over_chars": 150}, "name_convention": {"points": 0}}}
    )


PACKAGED_RESERVED_NAME = {
    "points": 15,
    "message": "Name contains reserved word",
    "suggestion": "Remove reserved words from skill name",
    "terms": ["anthropic", "claude"],
}


def test_packaged_reserved_name_matches_former_hard_coded_values() -> None:
    rule = load_quality_config()["correctness"]["reserved_name"]

    assert rule == PACKAGED_RESERVED_NAME
    assert type(rule["points"]) is int


def test_custom_file_with_only_reserved_terms_keeps_every_other_packaged_value(tmp_path: Path) -> None:
    config_path = tmp_path / "quality.yaml"
    config_path.write_text("correctness:\n  reserved_name:\n    terms: [acme]\n", encoding="utf-8")
    packaged = load_quality_config()

    config = load_quality_config(config_path)

    assert config["correctness"]["reserved_name"] == {**PACKAGED_RESERVED_NAME, "terms": ["acme"]}
    assert {key: value for key, value in config.items() if key != "correctness"} == {
        key: value for key, value in packaged.items() if key != "correctness"
    }


@pytest.mark.parametrize(
    ("body", "match"),
    [
        ("correctness: []\n", r"correctness must be a mapping"),
        ("correctness:\n  name_format: {}\n", r"unknown key\(s\) in correctness: name_format"),
        ("correctness:\n  reserved_name: [acme]\n", r"correctness\.reserved_name must be a mapping"),
        (
            "correctness:\n  reserved_name:\n    words: [acme]\n",
            r"unknown key\(s\) in correctness\.reserved_name: words \(allowed: message, points, suggestion, terms\)",
        ),
        ("correctness:\n  reserved_name:\n    terms: []\n", r"correctness\.reserved_name\.terms must be a non-empty list"),
        ("correctness:\n  reserved_name:\n    terms: acme\n", r"correctness\.reserved_name\.terms must be a non-empty list"),
        ('correctness:\n  reserved_name:\n    terms: [" "]\n', r"correctness\.reserved_name\.terms\[0\] must be a non-blank"),
        (
            "correctness:\n  reserved_name:\n    terms: [Acme, acme]\n",
            r"duplicate entry 'acme' in correctness\.reserved_name\.terms",
        ),
        ("correctness:\n  reserved_name:\n    points: -1\n", r"correctness\.reserved_name\.points must be a non-negative"),
    ],
)
def test_quality_config_rejects_invalid_correctness(tmp_path: Path, body: str, match: str) -> None:
    config_path = _write_config(tmp_path, body)

    with pytest.raises(QualityConfigError, match=rf"^{tmp_path}.*{match}"):
        load_quality_config(config_path)


def test_custom_digest_declares_only_the_correctness_keys_the_file_sets(tmp_path: Path) -> None:
    config_path = tmp_path / "quality.yaml"
    config_path.write_text("correctness: {reserved_name: {terms: [acme]}}\n", encoding="utf-8")

    assert _digest(config_path) == quality_config_digest({"correctness": {"reserved_name": {"terms": ["acme"]}}})


# The values each Efficiency rule used when it was hard-coded in quality_score.py.
PACKAGED_EFFICIENCY = {
    "token_budget": PACKAGED_TOKEN_BUDGET,
    "line_repetition": {
        "points": 10,
        "message": "High line repetition detected",
        "suggestion": "Remove duplicate instructions or use references",
        "min_unique_ratio": 0.7,
    },
    "action_verbs": {
        "points": 15,
        "message": "Instructions lack clear action verbs",
        "suggestion": "Use imperative: 'Use run_script with...', 'Call activate_skill...'",
        "headings": ["## Instructions", "## Usage"],
        "terms": ["use", "call", "run", "execute", "pass", "set", "add", "mark", "update", "keep"],
    },
    "list_format": {
        "points": 5,
        "message": "Instructions not in list format",
        "suggestion": "Use bullet points or numbered steps for clarity",
        "headings": ["## Instructions", "## Usage"],
        "markers": ["- ", "1.", "* "],
    },
    "corporate_language": {
        "points": 5,
        "message": "Uses complex/corporate language",
        "suggestion": "Use simple, direct language: 'use' not 'utilize'",
        "terms": ["utilize", "facilitate", "leverage", "paradigm", "synergy"],
    },
    "vague_reference_filename": {
        "points": 5,
        "message": "Non-descriptive filename",
        "suggestion": "Use descriptive names: 'form_validation_rules.md' not 'doc2.md'",
        "terms": ["doc", "file", "data", "info", "misc", "temp"],
        "min_chars": 4,
    },
    "nested_references": {
        "points": 10,
        "message": "Deeply nested references",
        "suggestion": "Keep references one level deep from SKILL.md",
    },
    "non_doc_reference": {
        "points": 5,
        "message": "Non-doc file in references/",
        "suggestion": "Code belongs in scripts/, data in assets/. references/ is for .md docs.",
        "suffixes": [".py", ".sh", ".json", ".csv", ".yaml", ".yml", ".toml"],
    },
}


def test_packaged_efficiency_matches_former_hard_coded_values() -> None:
    efficiency = load_quality_config()["efficiency"]

    assert efficiency == PACKAGED_EFFICIENCY
    assert list(efficiency) == list(PACKAGED_EFFICIENCY)


def test_custom_file_with_one_list_format_setting_keeps_every_other_packaged_value(tmp_path: Path) -> None:
    config_path = tmp_path / "quality.yaml"
    config_path.write_text("efficiency:\n  list_format:\n    headings: ['## Steps']\n", encoding="utf-8")
    packaged = load_quality_config()

    config = load_quality_config(config_path)

    assert config["efficiency"] == {
        **PACKAGED_EFFICIENCY,
        "list_format": {**PACKAGED_EFFICIENCY["list_format"], "headings": ["## Steps"]},
    }
    assert {key: value for key, value in config.items() if key != "efficiency"} == {
        key: value for key, value in packaged.items() if key != "efficiency"
    }


def test_instruction_headings_are_normalized_like_expected_headers(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path, "efficiency:\n  action_verbs:\n    headings: ['##  Steps  ', '### How to']\n")

    assert load_quality_config(config_path)["efficiency"]["action_verbs"]["headings"] == ["## Steps", "### How to"]


@pytest.mark.parametrize("ratio", [1, 0.5, 0.01])
def test_repetition_ratio_accepts_numbers_above_zero_up_to_one(tmp_path: Path, ratio: float) -> None:
    config_path = _write_config(tmp_path, f"efficiency:\n  line_repetition:\n    min_unique_ratio: {ratio}\n")

    assert load_quality_config(config_path)["efficiency"]["line_repetition"]["min_unique_ratio"] == ratio


@pytest.mark.parametrize(
    ("body", "match"),
    [
        ("efficiency:\n  line_repetition:\n    min_unique_ratio: 0\n", r"min_unique_ratio must be a number greater than 0"),
        ("efficiency:\n  line_repetition:\n    min_unique_ratio: 1.5\n", r"min_unique_ratio must be a number greater than 0"),
        ("efficiency:\n  line_repetition:\n    min_unique_ratio: true\n", r"min_unique_ratio must be a number greater than 0"),
        ("efficiency:\n  line_repetition:\n    min_unique_ratio: .nan\n", r"min_unique_ratio must be a number greater than 0"),
        ("efficiency:\n  action_verbs:\n    headings: []\n", r"action_verbs\.headings must be a non-empty list"),
        ("efficiency:\n  action_verbs:\n    headings: [Usage]\n", r"action_verbs\.headings\[0\] must be a single ATX"),
        (
            "efficiency:\n  list_format:\n    headings: ['## Usage', '##  Usage']\n",
            r"duplicate entry '## Usage' in efficiency\.list_format\.headings",
        ),
        ("efficiency:\n  action_verbs:\n    terms: [Run, run]\n", r"duplicate entry 'run' in efficiency\.action_verbs\.terms"),
        ("efficiency:\n  list_format:\n    markers: []\n", r"list_format\.markers must be a non-empty list"),
        ("efficiency:\n  corporate_language:\n    terms: leverage\n", r"corporate_language\.terms must be a non-empty list"),
        (
            "efficiency:\n  vague_reference_filename:\n    min_chars: 0\n",
            r"vague_reference_filename\.min_chars must be a positive integer",
        ),
        ("efficiency:\n  non_doc_reference:\n    suffixes: [py]\n", r"suffixes\[0\] must be one file suffix"),
        ("efficiency:\n  non_doc_reference:\n    suffixes: [.tar.gz]\n", r"suffixes\[0\] must be one file suffix"),
        ("efficiency:\n  non_doc_reference:\n    suffixes: [.py, .py]\n", r"duplicate entry '\.py'"),
        (
            "efficiency:\n  nested_references:\n    max_depth: 2\n",
            r"unknown key\(s\) in efficiency\.nested_references: max_depth \(allowed: message, points, suggestion\)",
        ),
    ],
)
def test_quality_config_rejects_invalid_efficiency_rules(tmp_path: Path, body: str, match: str) -> None:
    config_path = _write_config(tmp_path, body)

    with pytest.raises(QualityConfigError, match=rf"^{tmp_path}.*{match}"):
        load_quality_config(config_path)


def test_custom_digest_declares_only_the_efficiency_rule_keys_the_file_sets(tmp_path: Path) -> None:
    config_path = tmp_path / "quality.yaml"
    config_path.write_text(
        "efficiency: {line_repetition: {min_unique_ratio: 0.5}, nested_references: {points: 0}}\n", encoding="utf-8"
    )

    assert _digest(config_path) == quality_config_digest(
        {"efficiency": {"line_repetition": {"min_unique_ratio": 0.5}, "nested_references": {"points": 0}}}
    )
