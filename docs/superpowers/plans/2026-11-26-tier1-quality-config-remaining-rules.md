# Tier 1 Quality Config: Remaining Rules Implementation Plan

> **For agentic workers:** Execute the tasks in order. Steps use checkbox (`- [ ]`) syntax; tick each one when it's done. Rule rows are numbered **R1–R33** and decisions **D1–D6**, and tasks refer to them by number. If a step contradicts the code you find, stop and report the mismatch. Don't improvise.

**Goal:** Move every remaining hard-coded Tier 1 dimension deduction (Efficiency, Discoverability, Correctness) into `src/skillevaluator/config/quality-default.yaml`. With no custom file, scores and findings must stay the same, except for the `finding_id` changes D3 allows.

**Starting point:** `main` at `914c15c` (#611 merged as `0f3d980`). Reliability is already fully in YAML (`expected_headers`, `error_handling`). The unmerged branch `origin/claude/quality-config-efficiency` already has the table refactor plus all Efficiency and Discoverability rules, written before #611's review. Cherry-pick from it; don't rebase it.

**Out of scope:** dimension weights, grade bands, the pass bar (`QUALITY_DEFAULT_MIN_SCORE`), `QUALITY_CHARS_PER_TOKEN`, per-rule severity, and the `expected_headers` parser. Leave all of these as they are.

---

## Global Constraints

Follow the pattern set by #213, #336 and #611.

1. Each rule moves `points`, `message`, `suggestion` and the data that defines what it looks for (word lists, thresholds, markers, extensions).
2. **Severity stays in code.** So do matching algorithms (regexes, skill-type detection, the instruction-section extraction) and the directory lists used for skill-type detection (`EXECUTABLE_SKILL_DIRS`, `QUALITY_RESOURCE_DIRS`).
3. **Option C:** the instruction headings `## Instructions` / `## Usage` (`quality_score.py:896-904`) stay in code. No `headings` setting.
4. `points: 0` turns a rule off. When it is 0, the call site must skip `dim.deduct()`, as `reserved_name` does (`quality_score.py:597`). This matters most for error-level rules, because an error finding fails the run.
5. A custom file overlays the packaged values sparsely: an omitted key keeps the packaged value, and a list replaces the packaged list.
6. The packaged YAML must list every rule with every key.
7. Preserve current behavior even where it's odd. Note any oddity in a YAML comment, and fix nothing in this plan.
8. Computed values are appended to the configured message as `"{message}: {value}"`, the #611 format (see D3).
9. Each PR adds one CHANGELOG entry under Unreleased. It must say that the packaged `quality_config` digest changes, list any `finding_id` changes, and say that scores are unchanged.
10. Docs live in `docs/tier1-reference.mdx`. The branch's edits target `docs/tier1-validation.mdx`; don't apply them there.
11. Sign off commits (`git commit -s`). Push only the working branch. Open each PR as a draft.

## Decisions (defaults; change them here before executing)

| # | Decision | Default | Rows |
|---|---|---|---|
| D1 | Three rules can never fire, because skill-type detection already guarantees the condition is false | Move them as they are, add a YAML comment saying they can't fire, and record them for the follow-up list. Don't delete them. | R22, R23, R28 |
| D2 | Two rules have no suggestion today | Allow `suggestion: null` in rule sections; null means the finding gets no suggestion. Don't invent text. | R23, R29 |
| D3 | Some messages have a computed value in the middle | Move the value to the end: `"{message}: {value}"`. Accept the new `finding_id`s and list them in the CHANGELOG. | R13, R14, R18, R19, R29, R31 |
| D4 | `## Purpose` duplicates the `expected_headers` mechanism | Keep it as its own Discoverability rule with a `heading` setting. | R12 |
| D5 | The examples markers also set the `has_examples` metric | Set `has_examples` from the configured markers whatever `points` is. | R15 |
| D6 | Author and tags are emitted by one loop with generated text | Split them into two rules, each with fixed message and suggestion text equal to today's generated strings. | R32, R33 |

## Rule Inventory

Columns:
- **Code** is a `src/skillevaluator/validators/quality_score.py` line on `main`.
- **Settings** lists the YAML keys besides `points`/`message`/`suggestion`.
- **Source:** `branch` means the rule already exists on `origin/claude/quality-config-efficiency`; `new` means write it.

### Efficiency (`efficiency:`): 7 rules, all from the branch

| # | Rule id | Code | Pts / sev | Settings | Source | Notes |
|---|---|---|---|---|---|---|
| R1 | `line_repetition` | 886-894 | 10 / info | `min_unique_ratio: 0.7` (float) | branch | Needs `_validate_ratio` (on the branch). Counts frontmatter lines too; note it, don't fix it. |
| R2 | `action_verbs` | 905-912 | 15 / warning | `terms` | branch | **Remove the `headings` key (option C).** |
| R3 | `list_format` | 914-920 | 5 / info | `markers: ["- ", "1.", "* "]` | branch | **Remove the `headings` key (option C).** |
| R4 | `corporate_language` | 922-930 | 5 / info | `terms` | branch | Scans the whole file, code blocks included. Note it. |
| R5 | `vague_reference_filename` | 935-945 | 5 / info | `terms`, `min_chars: 4` | branch | `isdigit()` stays in code. The filename is appended. |
| R6 | `nested_references` | 948-958 | 10 / warning | none | branch | Zero-setting rule (`PlainRule`). The filename is appended. |
| R7 | `non_doc_reference` | 962-972 | 5 / info | `suffixes` | branch | Needs `_validate_suffixes` (on the branch). Matching is case-sensitive. |

### Discoverability (`discoverability:`): 7 rules, all from the branch

| # | Rule id | Code | Pts / sev | Settings | Source | Notes |
|---|---|---|---|---|---|---|
| R8 | `missing_trigger` | 744-751 | 10 / info | `terms` | branch | |
| R9 | `vague_words` | 753-760 | 15 / warning | `terms` | branch | |
| R10 | `first_or_second_person` | 762-769 | 15 / warning | `terms` | branch | |
| R11 | `broad_description` | 772-780 | 5 / info | `over_chars: 100`, `terms`, `negative_terms` | branch | Three settings in one rule; the AND/NOT logic stays in code. |
| R12 | `purpose_section` | 782-783 | 5 / info | `heading: "## Purpose"` | branch | D4. |
| R13 | `name_too_short` | 785-791 | 10 / warning | `min_chars: 5` | branch | D3: the name is appended. Checks the folder name, not the frontmatter name. |
| R14 | `name_convention` | 793-799 | 10 / warning | none | branch | D3. The regex stays in code. |

### Correctness (`correctness:`): 19 rules, all new

| # | Rule id | Code | Pts / sev | Settings | Source | Notes |
|---|---|---|---|---|---|---|
| R15 | `examples` | 515-518 | 5 / info | `markers: ["```", "Example:", "**Example:**"]`, `heading: "## Examples"` | new | D5. Two settings. |
| R16 | `windows_paths` | 521-527 | 10 / warning | `dirs: [scripts, references, assets]` | new | Build the regex from `dirs` in code, escaping each entry. |
| R17 | `readme_reference` | 537-544 | 5 / warning | none | new | `README.md` is what the rule is about, so it stays in code. |
| R18 | `xml_frontmatter_field` | 562-584 | 15 / **error** | none | new | D3: the field name is appended. Keep the `break`: only the first field is reported. |
| R19 | `name_format` | 588-594 | 15 / **error** | none | new | D3. The regex `^[a-z0-9-]+$` stays in code. |
| R20 | `name_xml` | 605 | 15 / **error** | none | new | |
| R21 | `description_xml` | 608 | 15 / **error** | none | new | |
| R22 | `scripts_dir_missing` | 630-636 | 25 / **error** | none | new | D1: can never fire. |
| R23 | `scripts_dir_empty` | 626-628 | 10 / warning | none | new | D1 and D2: can never fire, `suggestion: null`. The message already names the extensions; keep it as written. |
| R24 | `scripts_table` | 637-643 | 10 / warning | `markers: ["## Available Scripts", "| Script |"]` | new | |
| R25 | `run_script` | 644-650 | 10 / warning | `markers: ["run_script"]` | new | The exemption for Node-only skills stays in code. |
| R26 | `lib_pyproject` | 656-662 | 10 / warning | none | new | `pyproject.toml` stays in code. |
| R27 | `lib_api_docs` | 663-669 | 10 / warning | none | new | The detection regexes (`_has_api_documentation`) stay in code. |
| R28 | `lib_module_missing` | 670-676 | 15 / warning | none | new | D1: can never fire. |
| R29 | `lib_resource_docs` | 678-687 | 5 / info | `terms: [template, asset, design, style, css, html, resource]` | new | D2 and D3: `suggestion: null`, and the directory list is appended. |
| R30 | `resource_docs` | 689-697 | 10 / warning | `terms` (same 7 words) | new | Give it its own copy of the list. Don't share it with R29. |
| R31 | `guide_min_lines` | 699-707 | 15 / warning | `min_lines: 20` | new | D3: the line count is appended. Frontmatter and code-fence lines count; note it. |
| R32 | `spec_author` | 987-998 | 5 / warning | none | new | D6. Message: `SKILL_SPEC recommended field missing: 'metadata.author'`. |
| R33 | `spec_tags` | 987-998 | 5 / warning | none | new | D6. Message: `SKILL_SPEC recommended field missing: 'metadata.tags'`. |

---

## Task 0: Set up

- [ ] 0.1 `git fetch origin main claude/quality-config-efficiency`.
- [ ] 0.2 Create the working branch from `origin/main`.
- [ ] 0.3 Install dev dependencies: `python3 -m pip install -e '.[all,dev]'`, or `uv sync --all-extras`.
- [ ] 0.4 Confirm the baseline is green: run `python3 -m pytest tests/test_quality_config.py tests/validators/test_quality_score.py tests/test_metrics_reference_docs.py -q` and `python3 -m ruff check src tests`. Record any failures that already exist before changing anything.

## Task 1 (PR 1): Table refactor plus Efficiency, rows R1–R7

- [ ] 1.1 `git cherry-pick d18d380`, which lets a rule have zero or more settings. Resolve the conflict in `_RULE_SECTIONS` using the dict form, and keep `main`'s `_validate_reserved_terms` for `correctness.reserved_name`.
- [ ] 1.2 `git cherry-pick 6e3ed40 5445f3d`. Resolve the conflicts:
  - **`quality_config.py`:** keep the branch's new validators (`_validate_ratio`, `_validate_headings`, `_validate_suffixes`, `_validate_terms`, `_validate_markers`).
  - **`error_handling` entries:** may use either `main`'s or the branch's helper spelling, as long as behavior is identical.
  - **`CHANGELOG.md` and the docs files:** take `main`'s version. You'll rewrite them in steps 1.5–1.6.
- [ ] 1.3 Option C, for R2 and R3:
  - Delete `headings` from `action_verbs` and `list_format` in the YAML, the `_RULE_SECTIONS` table and the TypedDicts.
  - Restore the in-code heading tuple at the section extraction.
  - Delete `_validate_headings` if it's now unused. R12 uses `_normalize_heading` directly, so check that first.
  - Delete the tests that cover `headings`.
- [ ] 1.4 Check the code against #611's review decisions:
  - (a) The `token_budget` long text stays in `suggestion`, not `message`. Compare the YAML with `0f3d980`.
  - (b) The description length limits are checked independently, never with `elif`.
  - (c) The `reserved_name` validator is unchanged.
- [ ] 1.5 Docs:
  - Add an R1–R7 subsection under the `efficiency` section of `docs/tier1-reference.mdx`, following the existing `token_budget` text.
  - Update the Efficiency row of `docs/metrics-reference.mdx:457` if the wording changed.
  - Make sure `tests/test_metrics_reference_docs.py` reads the points from config.
- [ ] 1.6 CHANGELOG entry, per Global Constraint 9. There are no `finding_id` changes for R1–R7, since the filename was already appended.
- [ ] 1.7 Add a test that `load_quality_config()` with no file gives the same deductions as before for a fixture that triggers all seven rules. Also add a test that `points: 0` silences each one.
- [ ] 1.8 Run the commands from step 0.4, then commit, push, and open a draft PR.

## Task 2 (PR 2): Discoverability, rows R8–R14

- [ ] 2.1 `git cherry-pick 28d25fa 4b9c342 357ea10` onto PR 1. Expect real conflicts in 8 files.
- [ ] 2.2 In `quality_score.py`, keep `main`'s independent `description_too_short` / `description_too_long` checks. Bring in only the new R8–R14 call sites.
- [ ] 2.3 Keep the branch's cross-field check (`min_chars` ≤ `max_chars`) only if it raises a clear `QualityConfigError` naming both locations. Otherwise drop it and note that.
- [ ] 2.4 D3 for R13 and R14: confirm the folder name is appended as `"{message}: '{name}'"`, and list both `finding_id` changes in the CHANGELOG.
- [ ] 2.5 D4 for R12: the deduction stays in Discoverability. Add a YAML comment that listing `## Purpose` in `expected_headers` as well deducts twice.
- [ ] 2.6 Do the docs, CHANGELOG and test steps as in 1.5–1.7, then step 1.8.

## Task 3 (PR 3): Correctness, rows R15–R33

- [ ] 3.1 **Loader, for D2:** let a rule section accept `suggestion: null`.
  - `_validate_text` stays strict for strings; null is allowed only for `suggestion`.
  - The packaged file must still declare the key.
  - Add tests that null loads, that a custom file can set a string, and that an empty string is still rejected.
- [ ] 3.2 Add `correctness` table entries and TypedDicts for R15–R33, using the settings in the inventory.
  - New validators: `dirs` for R16, a list of plain directory names with no slashes; and `min_lines` for R31, using `_validate_positive_int`.
  - Reuse the existing validators for `terms`, `markers` and `heading`.
- [ ] 3.3 Add the YAML blocks for R15–R33 to `quality-default.yaml`, with text copied exactly from the current code.
  - Where D3 applies, remove the value from the message and add a comment saying the code appends it.
  - Add the D1 comment to R22, R23 and R28.
- [ ] 3.4 Convert the call sites one group per commit. Every site reads the config and skips the deduction when `points` is 0.
  - (a) `_check_correctness`: R15–R17.
  - (b) `_check_frontmatter_correctness`: R18–R21. These are error-level, so test that `points: 0` produces no HIGH finding.
  - (c) `_check_type_specific`: R22–R31.
  - (d) `_check_spec_fields`: R32 and R33. Split the loop into two config-driven checks.
- [ ] 3.5 D5: `has_examples` follows the configured `markers` even when `points` is 0. Add a test for it.
- [ ] 3.6 Fix the docs test that counts literal `deduct` amounts in `_check_type_specific` (around line 514 of `tests/test_metrics_reference_docs.py`) so it reads the config. Then add an assertion, like the one for Reliability, that `_check_correctness`, `_check_frontmatter_correctness`, `_check_type_specific` and `_check_spec_fields` no longer contain literal deduction amounts.
- [ ] 3.7 Write the docs: a `correctness` subsection in `docs/tier1-reference.mdx` for each rule group, covering `suggestion: null`, the D1 note and the D3 appended values.
- [ ] 3.8 CHANGELOG: note the digest change, and list the `finding_id` changes for R18, R19, R29 and R31.
- [ ] 3.9 Write the regression test: a fixture for each skill type (script-based, lib-based, resource-based, guide-only, hybrid) scores the same before and after.
- [ ] 3.10 Run step 1.8.

## Task 4: Final check

- [ ] 4.1 `grep -n "dim.deduct(\s*[0-9]" src/skillevaluator/validators/quality_score.py`, and likewise for `qs.correctness.deduct(` with a literal number, must return nothing.
- [ ] 4.2 Every rule key in `quality-default.yaml` must have a matching subsection in `docs/tier1-reference.mdx`.
- [ ] 4.3 Run the full suite: `python3 -m pytest -q` and `python3 -m ruff check src tests`.

## Follow-up issues (file them; don't fix them in these PRs)

- **Crash:** quality scoring crashes when `references` is a regular file. `quality_score.py:934` checks `exists()`, then `:964` calls `iterdir()`, which raises `NotADirectoryError`.
- **Rules that can never fire:** R22, R23 and R28. Decide whether to delete them.
- **Three different name checks disagree:** `quality_score.py:588`, `:793` and `constants.py:128` (the schema). `my_skill--` passes the quality checks and fails the schema.
- **Out-of-date docs:** `docs/metrics-reference.mdx:464` says ".py or .sh", but `.mjs`, `.cjs` and `.js` also count.
- **Instruction-section quirks:** `## Instructions for setup`, `### Instructions` or a trailing space empties the section, and `## Usage` is then never tried (`quality_score.py:896-904`).
- **Digest:** a custom-config digest doesn't identify the packaged version underneath it.

## Estimate

| Task | Hours |
|---|---|
| 0 Setup | 0.5 |
| 1 Refactor + Efficiency (R1–R7) | 5–6 |
| 2 Discoverability (R8–R14) | 5–7 |
| 3 Correctness (R15–R33) | 10–12 |
| 4 Final check | 1 |
