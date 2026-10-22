#!/bin/bash

LC_ALL=C
export LC_ALL

FAILURES=0
EXPECTED_LEDGER_HEADER='claim_id,chapter,section,claim_text,claim_type,risk_level,source_keys,source_version,source_date,accessed_date,status,review_by,notes'
APPROVED_DIAGRAM_FILES='ml-lifecycle.mmd
architecture-planes.mmd
system-of-record.mmd
failure-flow.mmd'
PROFILE='release'
SCRIPT_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
HANDBOOK_ROOT=$(CDPATH='' cd -- "$SCRIPT_DIR/.." && pwd)

fail() {
  FAILURES=$((FAILURES + 1))
  printf 'FAIL: %s\n' "$1"
}

pass() {
  printf 'PASS: %s\n' "$1"
}

exit_with_failures() {
  exit_status=$FAILURES
  if [ "$exit_status" -lt 1 ]; then
    exit_status=1
  elif [ "$exit_status" -gt 255 ]; then
    exit_status=255
  fi
  exit "$exit_status"
}

usage() {
  printf 'Usage: %s [--profile structure|release] [HANDBOOK_ROOT]\n' "$0"
}

relative_path() {
  case "$1" in
    "$HANDBOOK_ROOT"/*) printf '%s\n' "${1#"$HANDBOOK_ROOT"/}" ;;
    *) printf '%s\n' "$1" ;;
  esac
}

markdown_files() {
  find "$HANDBOOK_ROOT" -type f -name '*.md' -print | LC_ALL=C sort
}

maintained_content_markdown_files() {
  find "$HANDBOOK_ROOT" -type f -name '*.md' ! -path "$HANDBOOK_ROOT/scripts/*" -print | LC_ALL=C sort
}

extract_markdown_targets() {
  awk '
    function destination(raw) {
      sub(/^[[:space:]]+/, "", raw)
      if (raw ~ /^</) {
        sub(/^</, "", raw)
        sub(/>.*/, "", raw)
      } else {
        sub(/[[:space:]].*$/, "", raw)
      }
      return raw
    }
    {
      definition = $0
      if (definition ~ /^[[:space:]]*\[[^]]+\]:[[:space:]]*/) {
        sub(/^[[:space:]]*\[[^]]+\]:[[:space:]]*/, "", definition)
        target = destination(definition)
        if (target != "") {
          printf "%d\t%s\n", FNR, target
        }
      }

      remainder = $0
      while (match(remainder, /\]\([^)]*\)/)) {
        target = destination(substr(remainder, RSTART + 2, RLENGTH - 3))
        if (target != "") {
          printf "%d\t%s\n", FNR, target
        }
        remainder = substr(remainder, RSTART + RLENGTH)
      }
    }
  ' "$1"
}

heading_anchor_exists() {
  anchor_file="$1"
  wanted_anchor="$2"
  awk -v wanted="$wanted_anchor" '
    function anchor(text) {
      sub(/^#+[[:space:]]+/, "", text)
      sub(/[[:space:]]+#+[[:space:]]*$/, "", text)
      text = tolower(text)
      gsub(/[^[:alnum:] _-]/, "", text)
      gsub(/[[:space:]]+/, "-", text)
      gsub(/-+/, "-", text)
      return text
    }
    /^#+[[:space:]]+/ {
      base = anchor($0)
      candidate = base
      suffix = 1
      while (used[candidate]) {
        candidate = base "-" suffix
        suffix++
      }
      used[candidate] = 1
      if (candidate == wanted) {
        found = 1
        exit
      }
    }
    END { exit(found ? 0 : 1) }
  ' "$anchor_file"
}

is_external_or_same_document_target() {
  case "$1" in
    http://*|https://*|mailto:*|\#*|/*) return 0 ;;
    *) return 1 ;;
  esac
}

check_registered_diagrams() {
  registry="$HANDBOOK_ROOT/diagrams/chapter-01/README.md"
  [ -f "$registry" ] || return

  links=$(extract_markdown_targets "$registry")
  ml_lifecycle_count=0
  architecture_planes_count=0
  system_of_record_count=0
  failure_flow_count=0
  if [ -n "$links" ]; then
    tab=$(printf '\t')
    while IFS="$tab" read -r link_line link_target; do
      is_external_or_same_document_target "$link_target" && continue
      diagram_path=${link_target%%#*}
      diagram_path=${diagram_path%%\?*}
      case "$diagram_path" in
        ml-lifecycle.mmd)
          ml_lifecycle_count=$((ml_lifecycle_count + 1))
          occurrence_count=$ml_lifecycle_count
          ;;
        architecture-planes.mmd)
          architecture_planes_count=$((architecture_planes_count + 1))
          occurrence_count=$architecture_planes_count
          ;;
        system-of-record.mmd)
          system_of_record_count=$((system_of_record_count + 1))
          occurrence_count=$system_of_record_count
          ;;
        failure-flow.mmd)
          failure_flow_count=$((failure_flow_count + 1))
          occurrence_count=$failure_flow_count
          ;;
        *)
          fail "unapproved diagram target in diagrams/chapter-01/README.md:$link_line: $link_target"
          continue
          ;;
      esac
      if [ "$occurrence_count" -gt 1 ]; then
        fail "duplicate diagram target in diagrams/chapter-01/README.md:$link_line: $diagram_path"
        continue
      fi
      if [ ! -f "$(dirname -- "$registry")/$diagram_path" ]; then
        fail "missing required diagram file: diagrams/chapter-01/$diagram_path"
      fi
    done <<EOF
$links
EOF
  fi

  unique_count=0
  while IFS= read -r approved_diagram; do
    case "$approved_diagram" in
      ml-lifecycle.mmd) occurrence_count=$ml_lifecycle_count ;;
      architecture-planes.mmd) occurrence_count=$architecture_planes_count ;;
      system-of-record.mmd) occurrence_count=$system_of_record_count ;;
      failure-flow.mmd) occurrence_count=$failure_flow_count ;;
    esac
    if [ "$occurrence_count" -eq 0 ]; then
      fail "diagram registry missing approved target: $approved_diagram"
    else
      unique_count=$((unique_count + 1))
    fi
  done <<EOF
$APPROVED_DIAGRAM_FILES
EOF

  if [ "$unique_count" -ne 4 ]; then
    fail "diagram registry must register exactly four unique approved .mmd files (found $unique_count)"
  fi
}

check_required_files() {
  before=$FAILURES
  required_files='README.md
EDITORIAL_STATUS.md
STYLE_GUIDE.md
GLOSSARY.md
CHANGELOG.md
sources/references.md
sources/claim-ledger.csv
diagrams/chapter-01/README.md'

  while IFS= read -r required_file; do
    if [ ! -f "$HANDBOOK_ROOT/$required_file" ]; then
      fail "missing required file: $required_file"
    fi
  done <<EOF
$required_files
EOF

  if [ "$PROFILE" = 'release' ]; then
    chapter_file='chapters/01-mlops-architecture-foundations.md'
    if [ ! -f "$HANDBOOK_ROOT/$chapter_file" ]; then
      fail "missing required file: $chapter_file"
    fi
    check_registered_diagrams
  fi

  if [ "$FAILURES" -eq "$before" ]; then
    pass "required files are present for $PROFILE profile"
  fi
}

check_changelogs() {
  before=$FAILURES
  files=$(markdown_files)
  if [ -n "$files" ]; then
    while IFS= read -r markdown_file; do
      if ! grep -Fxq '## Changelog' "$markdown_file"; then
        fail "missing exact ## Changelog heading: $(relative_path "$markdown_file")"
      fi
    done <<EOF
$files
EOF
  fi
  if [ "$FAILURES" -eq "$before" ]; then
    pass 'all maintained Markdown files contain ## Changelog'
  fi
}

check_fences() {
  before=$FAILURES
  files=$(markdown_files)
  if [ -n "$files" ]; then
    while IFS= read -r markdown_file; do
      fence_count=$(awk '/^```/ { count++ } END { print count + 0 }' "$markdown_file")
      if [ $((fence_count % 2)) -ne 0 ]; then
        fail "unbalanced Markdown fence: $(relative_path "$markdown_file")"
      fi
    done <<EOF
$files
EOF
  fi
  if [ "$FAILURES" -eq "$before" ]; then
    pass 'all Markdown fences are balanced'
  fi
}

check_heading_hierarchy() {
  before=$FAILURES
  files=$(maintained_content_markdown_files)
  if [ -n "$files" ]; then
    while IFS= read -r markdown_file; do
      matches=$(awk '
        /^```/ { in_fence = !in_fence; next }
        !in_fence && /^#+[[:space:]]+/ {
          match($0, /^#+/)
          level = RLENGTH
          reason = ""
          if (level > 4) {
            reason = "heading level " level " exceeds ####"
          } else if (!seen_heading && level != 1) {
            reason = "first heading must be level 1"
          } else if (seen_heading && level > previous_level + 1) {
            reason = "heading jumps from level " previous_level " to " level
          } else if (level == 1 && h1_count > 0) {
            reason = "multiple level-1 headings"
          }
          if (reason != "") {
            printf "%d:%s\n", FNR, reason
          }
          if (level == 1) h1_count++
          previous_level = level
          seen_heading = 1
        }
      ' "$markdown_file")
      if [ -n "$matches" ]; then
        while IFS= read -r match; do
          fail "invalid heading hierarchy in $(relative_path "$markdown_file"):$match"
        done <<EOF
$matches
EOF
      fi
    done <<EOF
$files
EOF
  fi
  if [ "$FAILURES" -eq "$before" ]; then
    pass 'all maintained Markdown heading hierarchies are valid'
  fi
}

check_generated_ids() {
  before=$FAILURES
  files=$(markdown_files)
  if [ -n "$files" ]; then
    while IFS= read -r markdown_file; do
      matches=$(awk '/^```/ && /id="[^"]+"/ { printf "%d:%s\n", FNR, $0 }' "$markdown_file")
      if [ -n "$matches" ]; then
        while IFS= read -r match; do
          fail "generated fence id in $(relative_path "$markdown_file"):$match"
        done <<EOF
$matches
EOF
      fi
    done <<EOF
$files
EOF
  fi
  if [ "$FAILURES" -eq "$before" ]; then
    pass 'no generated fence identifiers found'
  fi
}

check_markers() {
  before=$FAILURES
  content_files=$(find "$HANDBOOK_ROOT" -type f ! -path "$HANDBOOK_ROOT/scripts/*" -print | LC_ALL=C sort)
  if [ -n "$content_files" ]; then
    while IFS= read -r content_file; do
      matches=$(grep -nE '(^|[^[:alnum:]_])(TODO|TBD|FIXME|VERIFY)([^[:alnum:]_]|$)' "$content_file" 2>/dev/null || true)
      if [ -n "$matches" ]; then
        while IFS= read -r match; do
          fail "unresolved marker in $(relative_path "$content_file"):$match"
        done <<EOF
$matches
EOF
      fi
    done <<EOF
$content_files
EOF
  fi
  if [ "$FAILURES" -eq "$before" ]; then
    pass 'no unresolved marker tokens found'
  fi
}

check_placeholder_text() {
  before=$FAILURES
  files=$(maintained_content_markdown_files)
  if [ -n "$files" ]; then
    while IFS= read -r markdown_file; do
      matches=$(awk '
        /^```/ { in_fence = !in_fence; next }
        !in_fence {
          lower = tolower($0)
          if (lower ~ /lorem[[:space:]]+ipsum/ ||
              lower ~ /(^|[^[:alnum:]_])(placeholder|tktk)([^[:alnum:]_]|$)/ ||
              lower ~ /coming[[:space:]]+soon/ ||
              lower ~ /content[[:space:]]+forthcoming/ ||
              lower ~ /to[[:space:]]+be[[:space:]]+(completed|written|added)/ ||
              lower ~ /insert[[:space:]]+[^.]*[[:space:]]+here/) {
            printf "%d:%s\n", FNR, $0
          }
        }
      ' "$markdown_file")
      if [ -n "$matches" ]; then
        while IFS= read -r match; do
          fail "placeholder text in $(relative_path "$markdown_file"):$match"
        done <<EOF
$matches
EOF
      fi
    done <<EOF
$files
EOF
  fi
  if [ "$FAILURES" -eq "$before" ]; then
    pass 'no unresolved placeholder text found'
  fi
}

check_banned_generic_phrases() {
  before=$FAILURES
  files=$(maintained_content_markdown_files)
  if [ -n "$files" ]; then
    while IFS= read -r markdown_file; do
      matches=$(awk '
        /^```/ { in_fence = !in_fence; next }
        !in_fence {
          lower = tolower($0)
          if (lower ~ /in today.s rapidly evolving landscape/ ||
              lower ~ /in the ever-evolving (world|landscape)/ ||
              lower ~ /it is important to note/ ||
              lower ~ /it is worth noting/ ||
              lower ~ /(^|[^[:alnum:]_])in conclusion([^[:alnum:]_]|$)/ ||
              lower ~ /(^|[^[:alnum:]_])to summarize([^[:alnum:]_]|$)/ ||
              lower ~ /as we delve into/ ||
              lower ~ /this section will (explore|discuss|cover)/ ||
              lower ~ /this comprehensive guide/ ||
              lower ~ /in the realm of/) {
            printf "%d:%s\n", FNR, $0
          }
        }
      ' "$markdown_file")
      if [ -n "$matches" ]; then
        while IFS= read -r match; do
          fail "banned generic phrase in $(relative_path "$markdown_file"):$match"
        done <<EOF
$matches
EOF
      fi
    done <<EOF
$files
EOF
  fi
  if [ "$FAILURES" -eq "$before" ]; then
    pass 'no banned generic phrases found'
  fi
}

check_unsupported_superlatives() {
  before=$FAILURES
  files=$(maintained_content_markdown_files)
  if [ -n "$files" ]; then
    while IFS= read -r markdown_file; do
      matches=$(awk '
        /^```/ { in_fence = !in_fence; next }
        !in_fence {
          lower = tolower($0)
          scan = lower
          gsub(/best-effort/, "", scan)
          gsub(/always-on/, "", scan)
          has_superlative = scan ~ /(^|[^[:alnum:]_])(best|always|never|guaranteed|latest|currently)([^[:alnum:]_]|$)/
          qualified = lower ~ /\[[^]]+\]\([^)]*\)/ ||
                      lower ~ /\[[^]]+\]\[[^]]+\]/ ||
                      lower ~ /as of [0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]/ ||
                      lower ~ /(within|for|under) (this|the) / ||
                      lower ~ /in this (handbook|chapter|section|scenario|example)/ ||
                      lower ~ /(^|[^[:alnum:]_])(when|unless|if)[[:space:]]/
          if (has_superlative && !qualified) {
            printf "%d:%s\n", FNR, $0
          }
        }
      ' "$markdown_file")
      if [ -n "$matches" ]; then
        while IFS= read -r match; do
          fail "unsupported superlative in $(relative_path "$markdown_file"):$match"
        done <<EOF
$matches
EOF
      fi
    done <<EOF
$files
EOF
  fi
  if [ "$FAILURES" -eq "$before" ]; then
    pass 'no unsupported superlatives found'
  fi
}

check_relative_links() {
  before=$FAILURES
  files=$(markdown_files)
  if [ -n "$files" ]; then
    while IFS= read -r markdown_file; do
      links=$(extract_markdown_targets "$markdown_file")
      [ -n "$links" ] || continue
      tab=$(printf '\t')
      while IFS="$tab" read -r link_line link_target; do
        is_external_or_same_document_target "$link_target" && continue

        link_path=${link_target%%#*}
        link_path=${link_path%%\?*}
        link_anchor=''
        case "$link_target" in
          *\#*)
            link_anchor=${link_target#*#}
            link_anchor=${link_anchor%%\?*}
            ;;
        esac

        resolved_path="$(dirname -- "$markdown_file")/$link_path"
        if [ ! -f "$resolved_path" ]; then
          fail "broken relative link in $(relative_path "$markdown_file"):$link_line: $link_target"
          continue
        fi
        if [ -n "$link_anchor" ] && ! heading_anchor_exists "$resolved_path" "$link_anchor"; then
          fail "missing ATX-heading anchor in $(relative_path "$markdown_file"):$link_line: $link_target"
        fi
      done <<EOF
$links
EOF
    done <<EOF
$files
EOF
  fi
  if [ "$FAILURES" -eq "$before" ]; then
    pass 'all relative Markdown links resolve'
  fi
}

check_ledger_schema() {
  before=$FAILURES
  ledger="$HANDBOOK_ROOT/sources/claim-ledger.csv"
  if [ -f "$ledger" ]; then
    IFS= read -r actual_header < "$ledger" || actual_header=''
    if [ "$actual_header" != "$EXPECTED_LEDGER_HEADER" ]; then
      fail 'claim-ledger.csv header does not match the required schema byte-for-byte'
    fi
  fi
  if [ "$FAILURES" -eq "$before" ]; then
    pass 'claim-ledger.csv header matches the required schema'
  fi
}

check_release_claims() {
  before=$FAILURES
  ledger="$HANDBOOK_ROOT/sources/claim-ledger.csv"
  chapter="$HANDBOOK_ROOT/chapters/01-mlops-architecture-foundations.md"

  if [ -f "$ledger" ]; then
    unresolved_claims=$(awk '
      function csvsplit(record, values,    count, i, char, nextchar, field, quoted) {
        count = 1
        field = ""
        quoted = 0
        for (i = 1; i <= length(record); i++) {
          char = substr(record, i, 1)
          nextchar = substr(record, i + 1, 1)
          if (char == "\"") {
            if (quoted && nextchar == "\"") {
              field = field "\""
              i++
            } else {
              quoted = !quoted
            }
          } else if (char == "," && !quoted) {
            values[count++] = field
            field = ""
          } else {
            field = field char
          }
        }
        values[count] = field
        return count
      }
      NR == 1 {
        csvsplit($0, header)
        for (i in header) position[header[i]] = i
        next
      }
      {
        for (key in row) delete row[key]
        csvsplit($0, row)
        chapter = row[position["chapter"]]
        risk = row[position["risk_level"]]
        status = row[position["status"]]
        if ((chapter == "1" || chapter == "01" || chapter == "Chapter 1") &&
            (risk == "P0" || risk == "P1") && status != "verified") {
          printf "%s\t%s\n", row[position["claim_id"]], status
        }
      }
    ' "$ledger")
    if [ -n "$unresolved_claims" ]; then
      tab=$(printf '\t')
      while IFS="$tab" read -r claim_id claim_status; do
        fail "Chapter 1 $claim_id is high-risk and not verified (status: $claim_status)"
      done <<EOF
$unresolved_claims
EOF
    fi
  fi

  if [ -f "$chapter" ]; then
    required_headings='## Reader outcomes and prerequisites
## Why production ML is a systems problem
## ML lifecycle and operational feedback loops
## Architecture planes
## MLOps capability and maturity model
## System-of-record boundaries
## Platform and product-team responsibilities
## Build, buy, and managed-service decisions
## Senior, Staff, and Principal decision scope
## Reference architecture and lifecycle flows
## Production failure case study
## Architecture decision record exercise
## Interview questions and evaluation rubric
## Key takeaways
## Glossary additions and authoritative references'
    while IFS= read -r required_heading; do
      if ! grep -Fxq "$required_heading" "$chapter"; then
        fail "Chapter 1 missing required heading: $required_heading"
      fi
    done <<EOF
$required_headings
EOF
  fi

  if [ "$FAILURES" -eq "$before" ]; then
    pass 'all Chapter 1 P0/P1 claims and required sections pass release checks'
  fi
}

if [ "${1:-}" = '--profile' ]; then
  if [ "$#" -lt 2 ]; then
    fail 'missing value for --profile'
    usage
    exit_with_failures
  fi
  PROFILE="$2"
  shift 2
fi

case "$PROFILE" in
  structure|release) ;;
  *)
    fail "unknown profile: $PROFILE"
    usage
    exit_with_failures
    ;;
esac

if [ "$#" -gt 1 ]; then
  fail 'too many arguments'
  usage
  exit_with_failures
fi

if [ "$#" -eq 1 ]; then
  HANDBOOK_ROOT=${1%/}
fi

if [ ! -d "$HANDBOOK_ROOT" ]; then
  fail "handbook root is not a directory: $HANDBOOK_ROOT"
  exit_with_failures
fi

check_required_files
check_changelogs
check_fences
check_heading_hierarchy
check_generated_ids
check_markers
check_placeholder_text
check_banned_generic_phrases
check_unsupported_superlatives
check_relative_links
check_ledger_schema

if [ "$PROFILE" = 'release' ]; then
  check_release_claims
fi

if [ "$FAILURES" -eq 0 ]; then
  pass "$PROFILE validation completed with zero failures"
  exit 0
fi

printf 'FAIL: %s validation failure(s)\n' "$FAILURES"
exit_with_failures
