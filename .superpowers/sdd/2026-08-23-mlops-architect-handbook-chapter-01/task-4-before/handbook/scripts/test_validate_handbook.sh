#!/bin/bash

VALIDATOR_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
VALIDATOR="$VALIDATOR_DIR/validate_handbook.sh"
TEST_TMP=$(mktemp -d "${TMPDIR:-/tmp}/handbook-validator.XXXXXX") || exit 1
trap 'rm -rf "$TEST_TMP"' EXIT HUP INT TERM

assert_pass() {
  description="$1"
  shift
  if output=$("$@" 2>&1); then
    printf 'PASS: %s\n' "$description"
  else
    printf 'FAIL: %s\n%s\n' "$description" "$output"
    return 1
  fi
}

assert_fail_contains() {
  description="$1"
  expected="$2"
  shift 2
  if output=$("$@" 2>&1); then
    printf 'FAIL: %s - command unexpectedly passed\n' "$description"
    return 1
  fi
  if printf '%s\n' "$output" | grep -Fq "$expected"; then
    printf 'PASS: %s\n' "$description"
  else
    printf 'FAIL: %s - missing output: %s\n%s\n' "$description" "$expected" "$output"
    return 1
  fi
}

write_changelog_document() {
  document_path="$1"
  document_title="$2"
  {
    printf '# %s\n\n' "$document_title"
    printf 'Fixture content.\n\n'
    printf '## Changelog\n\n'
    printf '### 2026-08-23\n\n'
    printf -- '- Created test fixture.\n'
  } > "$document_path"
}

make_valid_fixture() {
  fixture_root="$1"
  mkdir -p "$fixture_root/chapters" "$fixture_root/sources" \
    "$fixture_root/diagrams/chapter-01" "$fixture_root/scripts"

  write_changelog_document "$fixture_root/README.md" "Handbook"
  write_changelog_document "$fixture_root/EDITORIAL_STATUS.md" "Editorial Status"
  write_changelog_document "$fixture_root/STYLE_GUIDE.md" "Style Guide"
  write_changelog_document "$fixture_root/GLOSSARY.md" "Glossary"
  write_changelog_document "$fixture_root/CHANGELOG.md" "Handbook Changelog"
  write_changelog_document "$fixture_root/sources/references.md" "References"

  {
    printf '# Chapter 1 Diagrams\n\n'
    printf -- '- [ML lifecycle](fig-01-ml-lifecycle.mmd)\n'
    printf -- '- [Architecture planes](fig-02-architecture-planes.mmd)\n'
    printf -- '- [System of record](fig-03-systems-of-record.mmd)\n'
    printf -- '- [Failure flow](fig-04-failure-propagation.mmd)\n'
    printf -- '- [Architecture section](../../chapters/01-mlops-architecture-foundations.md#architecture-planes)\n\n'
    printf '## Changelog\n\n### 2026-08-23\n\n- Created registry.\n'
  } > "$fixture_root/diagrams/chapter-01/README.md"

  printf 'flowchart LR\n  A --> B\n' > "$fixture_root/diagrams/chapter-01/fig-01-ml-lifecycle.mmd"
  printf 'flowchart LR\n  A --> B\n' > "$fixture_root/diagrams/chapter-01/fig-02-architecture-planes.mmd"
  printf 'flowchart LR\n  A --> B\n' > "$fixture_root/diagrams/chapter-01/fig-03-systems-of-record.mmd"
  printf 'flowchart LR\n  A --> B\n' > "$fixture_root/diagrams/chapter-01/fig-04-failure-propagation.mmd"

  {
    printf '# MLOps Architecture Foundations: From ML Lifecycle to Enterprise Platform Strategy\n\n'
    printf '## Reader outcomes and prerequisites\n\nFixture content.\n\n'
    printf '## Why production ML is a systems problem\n\nFixture content.\n\n'
    printf '## ML lifecycle and operational feedback loops\n\nFixture content.\n\n'
    printf '## Architecture planes\n\nFixture content.\n\n'
    printf '## MLOps capability and maturity model\n\nFixture content.\n\n'
    printf '## System-of-record boundaries\n\nFixture content.\n\n'
    printf '## Platform and product-team responsibilities\n\nFixture content.\n\n'
    printf '## Build, buy, and managed-service decisions\n\nFixture content.\n\n'
    printf '## Senior, Staff, and Principal decision scope\n\nFixture content.\n\n'
    printf '## Reference architecture and lifecycle flows\n\nFixture content.\n\n'
    printf '## Production failure case study\n\nFixture content.\n\n'
    printf '## Architecture decision record exercise\n\nFixture content.\n\n'
    printf '## Interview questions and evaluation rubric\n\nFixture content.\n\n'
    printf '## Key takeaways\n\nFixture content.\n\n'
    printf '## Glossary additions and authoritative references\n\nFixture content.\n\n'
    printf '## Changelog\n\n### 2026-08-23\n\n- Created fixture chapter.\n'
  } > "$fixture_root/chapters/01-mlops-architecture-foundations.md"

  {
    printf '%s\n' 'claim_id,chapter,section,claim_text,claim_type,risk_level,source_keys,source_version,source_date,accessed_date,status,review_by,notes'
    printf '%s\n' 'CH01-C001,1,Reader outcomes,Fixture claim,architectural synthesis,P1,REF-001,1.0,2026-08-23,2026-08-23,verified,reviewer,Fixture row'
  } > "$fixture_root/sources/claim-ledger.csv"
}

test_failures=0

fixture="$TEST_TMP/structure-pass"
make_valid_fixture "$fixture"
assert_pass "complete minimal fixture passes structure" \
  "$VALIDATOR" --profile structure "$fixture" || test_failures=$((test_failures + 1))

fixture="$TEST_TMP/missing-file"
make_valid_fixture "$fixture"
rm "$fixture/GLOSSARY.md"
assert_fail_contains "missing required file is named" "GLOSSARY.md" \
  "$VALIDATOR" --profile structure "$fixture" || test_failures=$((test_failures + 1))

fixture="$TEST_TMP/unbalanced-fence"
make_valid_fixture "$fixture"
printf '\n```text\nunclosed\n' >> "$fixture/README.md"
assert_fail_contains "unbalanced fence names affected file" "README.md" \
  "$VALIDATOR" --profile structure "$fixture" || test_failures=$((test_failures + 1))

fixture="$TEST_TMP/generated-id"
make_valid_fixture "$fixture"
printf '\n%s\n%s\n%s\n' '```text id="generated"' 'content' '```' >> "$fixture/README.md"
assert_fail_contains "generated fence identifier fails" 'id="generated"' \
  "$VALIDATOR" --profile structure "$fixture" || test_failures=$((test_failures + 1))

fixture="$TEST_TMP/marker"
make_valid_fixture "$fixture"
printf '\nTODO: resolve fixture content.\n' >> "$fixture/README.md"
assert_fail_contains "unresolved marker fails" "TODO" \
  "$VALIDATOR" --profile structure "$fixture" || test_failures=$((test_failures + 1))

fixture="$TEST_TMP/broken-link"
make_valid_fixture "$fixture"
printf '\n[Broken](missing.md)\n' >> "$fixture/README.md"
assert_fail_contains "broken relative link names target" "missing.md" \
  "$VALIDATOR" --profile structure "$fixture" || test_failures=$((test_failures + 1))

fixture="$TEST_TMP/malformed-ledger"
make_valid_fixture "$fixture"
printf 'claim_id,chapter,status\n' > "$fixture/sources/claim-ledger.csv"
assert_fail_contains "malformed ledger header fails" "claim-ledger.csv" \
  "$VALIDATOR" --profile structure "$fixture" || test_failures=$((test_failures + 1))

fixture="$TEST_TMP/unverified-claim"
make_valid_fixture "$fixture"
{
  printf '%s\n' 'claim_id,chapter,section,claim_text,claim_type,risk_level,source_keys,source_version,source_date,accessed_date,status,review_by,notes'
  printf '%s\n' 'CH01-C001,1,Reader outcomes,Fixture claim,architectural synthesis,P1,REF-001,1.0,2026-08-23,2026-08-23,unverified,reviewer,Fixture row'
} > "$fixture/sources/claim-ledger.csv"
assert_fail_contains "unverified P0 or P1 Chapter 1 claim fails release" "CH01-C001" \
  "$VALIDATOR" --profile release "$fixture" || test_failures=$((test_failures + 1))

fixture="$TEST_TMP/missing-changelog"
make_valid_fixture "$fixture"
printf '# References\n\nFixture content.\n' > "$fixture/sources/references.md"
assert_fail_contains "maintained Markdown requires changelog" "sources/references.md" \
  "$VALIDATOR" --profile structure "$fixture" || test_failures=$((test_failures + 1))

fixture="$TEST_TMP/release-pass"
make_valid_fixture "$fixture"
assert_pass "complete release fixture passes release" \
  "$VALIDATOR" --profile release "$fixture" || test_failures=$((test_failures + 1))

fixture="$TEST_TMP/exit-boundary"
make_valid_fixture "$fixture"
mkdir -p "$fixture/defects"
defect_number=1
while [ "$defect_number" -le 256 ]; do
  printf '# Defect %s\n' "$defect_number" > "$fixture/defects/defect-$defect_number.md"
  defect_number=$((defect_number + 1))
done
assert_fail_contains "256 accumulated defects retain a non-zero exit" "FAIL: 256 validation failure(s)" \
  "$VALIDATOR" --profile structure "$fixture" || test_failures=$((test_failures + 1))

fixture="$TEST_TMP/duplicate-diagrams"
make_valid_fixture "$fixture"
{
  printf '# Chapter 1 Diagrams\n\n'
  printf -- '- [ML lifecycle 1](fig-01-ml-lifecycle.mmd)\n'
  printf -- '- [ML lifecycle 2](fig-01-ml-lifecycle.mmd)\n'
  printf -- '- [ML lifecycle 3](fig-01-ml-lifecycle.mmd)\n'
  printf -- '- [ML lifecycle 4](fig-01-ml-lifecycle.mmd)\n\n'
  printf '## Changelog\n\n### 2026-08-23\n\n- Created duplicate registry.\n'
} > "$fixture/diagrams/chapter-01/README.md"
assert_fail_contains "duplicate diagram targets fail release" "duplicate diagram target" \
  "$VALIDATOR" --profile release "$fixture" || test_failures=$((test_failures + 1))

fixture="$TEST_TMP/wrong-diagrams"
make_valid_fixture "$fixture"
printf 'flowchart LR\n' > "$fixture/diagrams/chapter-01/wrong-one.mmd"
printf 'flowchart LR\n' > "$fixture/diagrams/chapter-01/wrong-two.mmd"
printf 'flowchart LR\n' > "$fixture/diagrams/chapter-01/wrong-three.mmd"
printf 'flowchart LR\n' > "$fixture/diagrams/chapter-01/wrong-four.mmd"
{
  printf '# Chapter 1 Diagrams\n\n'
  printf -- '- [Wrong one](wrong-one.mmd)\n'
  printf -- '- [Wrong two](wrong-two.mmd)\n'
  printf -- '- [Wrong three](wrong-three.mmd)\n'
  printf -- '- [Wrong four](wrong-four.mmd)\n\n'
  printf '## Changelog\n\n### 2026-08-23\n\n- Created wrong registry.\n'
} > "$fixture/diagrams/chapter-01/README.md"
assert_fail_contains "unapproved diagram targets fail release" "unapproved diagram target" \
  "$VALIDATOR" --profile release "$fixture" || test_failures=$((test_failures + 1))

fixture="$TEST_TMP/reference-link"
make_valid_fixture "$fixture"
printf '\n[Guide][guide]\n\n[guide]: missing-reference.md\n' >> "$fixture/README.md"
assert_fail_contains "broken reference-style link names target" "missing-reference.md" \
  "$VALIDATOR" --profile structure "$fixture" || test_failures=$((test_failures + 1))

fixture="$TEST_TMP/duplicate-heading-anchor"
make_valid_fixture "$fixture"
printf '\n## Repeated heading\n\nFirst.\n\n## Repeated heading\n\nSecond.\n' >> "$fixture/GLOSSARY.md"
printf '\n[Second heading](GLOSSARY.md?view=full#repeated-heading-1)\n' >> "$fixture/README.md"
assert_pass "duplicate heading suffix anchor resolves" \
  "$VALIDATOR" --profile structure "$fixture" || test_failures=$((test_failures + 1))

fixture="$TEST_TMP/invalid-heading-hierarchy"
make_valid_fixture "$fixture"
printf '\n##### Skipped heading level\n' >> "$fixture/README.md"
assert_fail_contains "invalid heading hierarchy fails" "invalid heading hierarchy" \
  "$VALIDATOR" --profile structure "$fixture" || test_failures=$((test_failures + 1))

fixture="$TEST_TMP/placeholder-phrase"
make_valid_fixture "$fixture"
printf '\n[PLACEHOLDER]\n' >> "$fixture/README.md"
assert_fail_contains "placeholder phrase fails" "placeholder text" \
  "$VALIDATOR" --profile structure "$fixture" || test_failures=$((test_failures + 1))

fixture="$TEST_TMP/generic-phrase"
make_valid_fixture "$fixture"
printf "\nIn today's rapidly evolving landscape, platform choices matter.\n" >> "$fixture/README.md"
assert_fail_contains "banned generic phrase fails" "banned generic phrase" \
  "$VALIDATOR" --profile structure "$fixture" || test_failures=$((test_failures + 1))

fixture="$TEST_TMP/unqualified-superlative"
make_valid_fixture "$fixture"
printf '\nThis architecture is best.\n' >> "$fixture/README.md"
assert_fail_contains "unqualified superlative fails" "unsupported superlative" \
  "$VALIDATOR" --profile structure "$fixture" || test_failures=$((test_failures + 1))

fixture="$TEST_TMP/unbalanced-tilde-fence"
make_valid_fixture "$fixture"
printf '\n~~~markdown\nunclosed example\n' >> "$fixture/README.md"
assert_fail_contains "unbalanced tilde fence names affected file" "README.md" \
  "$VALIDATOR" --profile structure "$fixture" || test_failures=$((test_failures + 1))

fixture="$TEST_TMP/fenced-reference-definition"
make_valid_fixture "$fixture"
printf '\n%s\n%s\n%s\n' '````markdown' '[guide]: missing-backtick.md' '````' >> "$fixture/README.md"
printf '\n~~~markdown\n[guide]: missing-tilde.md\n~~~\n' >> "$fixture/README.md"
assert_pass "reference definitions inside fences are ignored" \
  "$VALIDATOR" --profile structure "$fixture" || test_failures=$((test_failures + 1))

fixture="$TEST_TMP/fenced-only-heading"
make_valid_fixture "$fixture"
printf '\n~~~~markdown\n## Fenced only heading\n~~~~\n' >> "$fixture/GLOSSARY.md"
printf '\n[Fenced heading](GLOSSARY.md#fenced-only-heading)\n' >> "$fixture/README.md"
assert_fail_contains "ATX heading inside fence does not create anchor" "missing ATX-heading anchor" \
  "$VALIDATOR" --profile structure "$fixture" || test_failures=$((test_failures + 1))

fixture="$TEST_TMP/fenced-duplicate-heading"
make_valid_fixture "$fixture"
printf '\n## Repeated fenced heading\n\n~~~markdown\n## Repeated fenced heading\n~~~\n\n## Repeated fenced heading\n' >> "$fixture/GLOSSARY.md"
printf '\n[False suffix](GLOSSARY.md#repeated-fenced-heading-2)\n' >> "$fixture/README.md"
assert_fail_contains "fenced ATX heading does not shift duplicate suffixes" "missing ATX-heading anchor" \
  "$VALIDATOR" --profile structure "$fixture" || test_failures=$((test_failures + 1))

fixture="$TEST_TMP/placeholder-policy"
make_valid_fixture "$fixture"
printf '\nPlaceholder text is forbidden in publication content.\n' >> "$fixture/README.md"
assert_pass "placeholder policy prose passes" \
  "$VALIDATOR" --profile structure "$fixture" || test_failures=$((test_failures + 1))

if [ "$test_failures" -ne 0 ]; then
  printf 'FAIL: %s validator test(s) failed\n' "$test_failures"
  exit 1
fi

printf 'PASS: all 24 validator tests passed\n'
