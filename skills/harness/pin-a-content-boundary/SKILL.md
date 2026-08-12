---
name: pin-a-content-boundary
description: Draw a repo's tracked/untracked line as an allowlist and prove the leaf stages. Covers why a leaf re-include stages zero files with no error, why git status cannot see unprotected work, LFS ordering that has no in-place fix, and an allowlisted directory admitting a binary you never chose. Use before the first commit in a new repo, and whenever work moves into a new part of the tree.
---

# Pin a Content Boundary

This skill grants no commit, push, force-push, history-rewrite, or
repository-visibility authority.

## When

You are about to write a `.gitignore` naming the big directories you do not
want, then commit. That shape is one forgotten line from a multi-gigabyte
commit and the forgetting is silent: in the originating corpus, ~46 GB of
purchased vendor content arrived over two days and required **zero** ignore
edits only because the file was an allowlist. Invert the default: `/*` at
the root, re-include by name, and prove each leaf stages before you believe
it.

```bash
head -15 .gitignore                          # /* is the first non-comment rule
git check-ignore -v <admitted>/probe         # must exit 1, printing nothing
git status --short --untracked-files=all     # must print 0 lines
```

## A leaf re-include stages nothing while its parent stays excluded

**Git never consults a negation inside an excluded directory** — it stops
descending, so the re-include is not overridden, it is never read. Proved
with two throwaway repos of identical content:

```
# NAIVE    /*  !.gitignore  !a/b/c/
git add -A; git ls-files  →  .gitignore                    # 0 source files
# CORRECT  /*  !.gitignore  !a/  a/*  !a/b/  a/b/*  !a/b/c/
git add -A; git ls-files  →  .gitignore  a/b/c/keep.py     # a/b/skip.bin still out
```

The naive form stages zero files, exits 0, and warns about nothing. Every
level between the root and an admitted directory gets its own un-exclude
line plus an `X/*` re-exclusion; the terminal directory gets no `/*` line,
and that absence is what admits its subtree. Distinguish excluded from
admitted with `git check-ignore -v` — it names the winning rule by line
number and works on paths that do not exist yet.

## Allowlisting a directory is permanent consent for whatever lands in it later

Measured: an allowlisted subtree with no re-exclusion admitted a
325 KB map file a build script later wrote — untracked *and unignored*, so
the next `git add -A` sweeps it in, and the LFS route makes it permanent on
the server even after deletion. Terminal allowlists belong on hand-authored
trees; never on a directory a run can fill.

## Under an allowlist new work is ignored, not untracked, so status sees nothing

An irreplaceable instrument corpus sat outside version control for six
days and surfaced only by accident — `git status -uall` printed zero lines
throughout, **correctly**, because ignored is not untracked. Distinguish
"nothing new" from "nothing visible" with the inverse sweep: list every
directory holding source files and zero tracked files
(`comm -13 <(git ls-files | xargs -n1 dirname | sort -u) <(find . -name
'*.py' -o -name '*.md' | xargs -n1 dirname | sort -u)`). Anything it prints
is a candidate incident, and because the failure is silent this sweep runs
on a schedule, not on a trigger. Match the extension list to what your
corpus is actually made of, or the detector reports clean while missing
everything.

## The binary routing file must be in the commit before the first binary

`.gitattributes` LFS routes must exist before the first large binary
lands: binaries do not delta, so each write of a half-gigabyte asset stores
another full copy, and a binary committed before the filter is a raw blob
in history forever — the only fix is a history rewrite plus force push, and
uploaded LFS objects stay uploaded. Verify with
`git cat-file -s HEAD:<asset>` — ~130 bytes is a pointer, hundreds of
megabytes is a raw commit. A scripts-only repo deliberately carrying no
LFS is correct — until the day before the first large binary, not the day
after.

## Track the means of production and the written record, never the output

The measured shape that works: scripts, docs, manifests — a few dozen MB
from which everything else regenerates — with renders, exports, caches,
and vendor content out. On the asset side the rule inverts: track only
what a script cannot rebuild, and size each admission before making it. If
a render or intermediate extension appears in the tracked-extension census
above single digits, the boundary has already slipped.

## Commit and push are separate acts, and a one-disk commit is not backed up

`git log --oneline origin/main..main | wc -l` — a non-zero answer is that
many commits of irreplaceable work existing on exactly one disk: the
same incident as a backup inside the system that can destroy it, one level
up. Quote the number in checkpoint reports; the push itself stays a
separately authorized act.

## Before you say the corpus is tracked

- [ ] `/*` is the first non-comment rule, `!.gitignore` the second.
- [ ] Every level between root and each admitted directory has its own
      un-exclude line; terminal directories carry no `/*`.
- [ ] `git check-ignore -v <admitted>/probe` exits 1 for every admitted
      tree, on probe paths that need not exist.
- [ ] `git status --short --untracked-files=all` prints zero lines.
- [ ] The inverse sweep prints nothing, and it is scheduled, not
      remembered.
- [ ] `.gitattributes` LFS routes are committed before the first binary;
      `git lfs ls-files | wc -l` equals the tracked binary count.
- [ ] The ignore header records the tracked byte total **with its date**.
- [ ] `origin/main..main` count is quoted in the report.

Whether tracked vendor-derived content may be *published* is a separate
ruling resting on license text; this skill decides what `git ls-files`
returns, never what is visible. A visibility change is an irreversible,
separately authorized act.

Related: `verify-a-cooked-package` for what a built package contains once
the boundary decides what ships; `back-up-before-a-destructive-write` for
why the boundary must exist before scripts write.

## Provenance

The 46 GB silent vendor arrival, the zero-files leaf re-include, the
six-day invisible corpus, and the LFS arithmetic are measured instances
from two single-machine repos (2026-08). Generalized 2026-08-12.

## Changelog

- 2026-08-12 — Initial generalized port.
