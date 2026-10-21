# Offline publication-content audit

Phase 2 adds a repeatable audit of selected local Git content. It reads Git
object bytes rather than treating the current working copy as the content that
will be shared. It reuses the existing scrub rule loader, text decoding and line
cap, with explicit encoding/coverage checks and retained findings.

This tool does not authorize a push, change visibility, rewrite history, fetch,
upload or change audited source, index, refs, objects or configuration. Only the
explicit new report is written under the harness; when auditing this harness,
that is an intentionally created ignored file. It is not wired into a hook or an
automatic release gate. The existing visibility preflight remains a separate
check. A clean result is bounded evidence about the chosen sources and terms.

## Choose the source explicitly

Run from the harness root and choose one source mode:

```powershell
python scripts/publication_audit.py --repo . --tree HEAD --out team/audit-tree-r1.local.json
python scripts/publication_audit.py --repo . --index --out team/audit-index-r1.local.json
python scripts/publication_audit.py --repo . --refs --out team/audit-refs-r1.local.json
```

| Mode | Included | Outside that selection |
|---|---|---|
| `--tree REV` | The resolved immutable tree's full paths and blob bytes | Commit/tag identities, earlier history, unstaged/untracked files |
| `--index` | Stage-zero index paths and their actual blob IDs/bytes | Working-copy substitutions and untracked files; unresolved merges refuse |
| `--refs` | Current local refs and HEAD, reachable unique objects, commit/tag payloads, full historical paths and ref names | Remote server refs or hosting surfaces, other clones, reflogs and unreachable objects |

Local remote-tracking refs are local records; this command does not refresh
them. A secret deleted from the current tree can still be found in selected
reachable history. Selection identities are pinned and checked again after
collection. A moving selection refuses rather than silently combining versions.
This is a non-atomic read, not a filesystem freeze.

History collection samples the shallow boundary before and after traversal and
also checks each raw commit's canonical parent headers against the collected
commit objects. Missing parents remain coverage gaps even if a transient
shallow marker disappeared before the final sample. Replacement/graft views
and lazy fetching are disabled for these inspection commands.

The generic term file is always selected. Add explicitly available local tiers
when the audit needs project/account-specific rules:

```powershell
python scripts/publication_audit.py --repo . --index --local-terms scrub_terms.local.txt --out team/audit-index-local-r1.local.json
```

No local tier is inferred from an absent file. Reports identify generic-only
versus generic-plus-explicit-local scope and hash the loaded tiers. A missing,
unreadable, empty or malformed requested tier is an error. Terms are trusted
Python regular expressions or literals in the existing scrub format. The line
cap is not a CPU-time bound on a pathological expression.

## Read the result and the coverage together

| Result | Exit | Meaning |
|---|---:|---|
| `CLEAN_WITHIN_SCOPE` | 0 | Selected, supported content was scanned with the declared terms and produced no findings |
| `FINDINGS` | 1 | Findings remain; inspect their exact source and rule identities |
| `INCOMPLETE` | 2 | Coverage has gaps, whether or not findings were also retained |
| `ERROR` | 2 | Input, collection, scanning, disposition or output could not complete correctly |

Binary or invalid text, truncated lines, shallow history and external payloads
cannot silently become a clean result. LFS pointer text and symlink targets can
be scanned as Git data, but their referenced payloads are not fetched or followed.
Submodule content is outside the parent repository's bytes. Commit and tag
payloads include identity/message material; matching an intentionally public
identity still produces a finding for review.

Collection has declared object/path/byte quotas and per-command wait limits.
These bound accepted results and waits, not operating-system memory allocation
or arbitrary filesystem stalls. A quota failure refuses instead of reporting an
empty scan. No detector here establishes the absence of an unknown secret,
license restriction or sensitive information that its terms do not describe.

The initial collector defaults are 20,000 objects, 4 MiB per object, 64 MiB total
payload, 50,000 expanded path entries and 20 seconds per Git command. A sanitized
failure code such as `object_size_limit` identifies a refused collection. Keep
the failure; a separately scoped budget or binary-asset investigation is needed
when the selected repository exceeds these limits.

For an explicitly scoped investigation, the existing CLI accepts
`--max-object-bytes` (up to 134217728), `--max-total-bytes` (up to 167772160) and
`--max-line-chars` (up to 1048576). Values must be positive integers; the object
budget cannot exceed the effective total budget. Defaults stay unchanged.
Requested and effective budgets are recorded in the report and scan identity.
Invalid limits refuse before collection. For example:

```powershell
python scripts/publication_audit.py --repo . --refs --local-terms scrub_terms.local.txt --max-object-bytes 134217728 --max-total-bytes 167772160 --max-line-chars 8192 --out team/audit-refs-expanded-r1.local.json
```

Retain the earlier quota/truncation refusal and the expanded report. Increasing
a cap does not classify findings or make an opaque archive scan complete. This
tool scans the archive's Git blob as bytes; inspecting its members and embedded
Git bundles requires a separate bounded assessment.

Finding bodies retain object/source identity, rule identity, line number and
match fingerprint/hash instead of raw matched text or source snippets. Hashes
are not anonymization. Paths, ref/selection names, term paths and human rationale
can still contain sensitive metadata. Keep reports local. The CLI writes only a
new `*.local.json` below this harness's `team/` directory and refuses replacement
or redirected paths; it never writes a report into the bound game project.

## Classify findings without erasing them

Inspect the underlying exact Git bytes privately. Retain the original report,
then create a local disposition file with its `scanIdentity` and exact finding
fingerprints:

```json
{
  "schemaVersion": 1,
  "scanIdentity": "copy-from-the-raw-report",
  "entries": [
    {
      "fingerprint": "copy-from-a-finding",
      "classification": "synthetic-fixture",
      "rationale": "Describe the inspected source and evidence without copying secrets."
    }
  ]
}
```

Allowed labels are `synthetic-fixture`, `baseline-existing`, `action-required`
and `reviewed-reference`. Labels are reviewer declarations, not automatic proof,
waivers or authorization. Establish a baseline claim against actual prior Git
bytes. Do not split or hide a test value simply to evade a detector.

Repeat the same audit with `--dispositions FILE` and a fresh output filename.
Unknown/duplicate fingerprints, duplicate JSON keys and stale scan identities
refuse. All raw findings remain; `rawScanResult` stays recorded even when a bad
disposition makes the overall result `ERROR`. Classifying every finding does not
change `FINDINGS` to `CLEAN_WITHIN_SCOPE` or remove coverage gaps.

## Verify the mechanism

```powershell
python -B -m unittest tests.test_publication_git tests.test_publication_scan tests.test_publication_audit
```

Controls use disposable repositories and the real saved CLI. They distinguish
staged content from a harmless working-copy decoy, deleted historical content
from the current tree, nested historical paths, encoded text, missing terms,
coverage gaps, status disagreement and invalid dispositions. Keep failure and
reversion receipts. A report or matching hash alone is not evidence of a passing
scan, human acceptance, host activation, safe publication or actual Game reuse.
