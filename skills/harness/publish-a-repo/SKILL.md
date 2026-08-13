---
name: publish-a-repo
description: Take a private repo public without publishing what a tree scrub can never see — the whole exposable surface (every blob on every ref, commit identities, platform surfaces), the identity rewrite with its tree-equality proof, the ordering that keeps each step reversible, and the grant that records the decision. Use before any visibility flip, first public push, or "make it public".
---

# Publish a Repo

This skill grants no push, visibility-change, or history-rewrite
authority; every one of those is a separately authorized act, and the
visibility flip itself is irreversible in effect the moment a crawler
sees the repo.

## When

The user says "make it public", or a first push targets a public remote.
"Scrub is clean" is a claim about a tree; publishing exposes a surface.
The paid instance (2026-08-13): a scrub that had swept every blob on
every rev was clean, and the user's personal Gmail was still one flip
away from every commit page, clone, and .patch URL — riding the
author/committer field of all six commits, a channel no tree scrub can
see. Four independent auditors each flagged it; nothing else did.

## The surface is bigger than the tree

Audit ALL of it before the flip, each with a fired positive control:

- **Every blob on every remote-reachable ref** — history is permanent
  after the flip; a fixture deleted at tip (`someone@example.com`,
  removed by a later commit) stays publicly reachable in its old blob
  forever. Decide per finding: fixture-on-reserved-domain is info; real
  data is a rewrite.
- **Commit metadata** — author/committer names, emails, timezones on
  every commit. The scrub structurally cannot see this channel.
- **Ref inventory** — `ls-remote`: every branch and tag flips together;
  an audit of main alone is an audit of one ref.
- **Platform surfaces** — description, issues, releases, wiki state,
  Actions workflows (public logs, fork PRs). Enumerate via the API, not
  assumption.
- **The instrument itself** — run the repo's own scrub on the EXACT tree
  the remote holds (archive it out), not the working tree; local commits
  ahead of origin make those different objects.

## The ordering keeps every step reversible until the flip

1. **Bundle backup first** — `git bundle create ... --all`, verified,
   outside the repo. The rewrite is destructive; the bundle is the
   rollback (`back-up-before-a-destructive-write`).
2. **Rewrite while still private** — identity to the platform noreply
   (`ID+user@users.noreply.github.com`). Prove trees byte-identical
   pre/post (`git log --format=%T` pairwise) — metadata only. Prove the
   old identity's absence with the same grep that finds it 2N times in
   the pre-rewrite refs (a zero needs its fired control).
3. **Force-push the rewritten remote-equivalent, still private** — lease
   pinned to the expected old tip; push only the commits the remote
   already had, keeping local-ahead work local.
4. **Verify through the platform's own API** — the commit payloads the
   public will be served, not your local view.
5. **Flip, then verify visibility** — and only then record the standing
   grant (the push-guard's grant file), so the guard's exception list
   matches exactly what the user authorized.
6. **Pin the identity for the future** — repo-local `user.email` to the
   noreply, so the next commit cannot reintroduce the address.

## Evidence rules

Every "clean" in the audit names its fired control (a planted secret the
sweep caught, a synthetic email through the same pipeline). The flip
claim cites the API response, not the CLI's silence. The rewrite claim
cites the tree-equality diff and the old→new sha map — other records
referencing the old shas go stale at that moment; name them.

## Provenance

The gamecreater public flip (2026-08-13): four-auditor pre-flip sweep,
content clean on all revs with fired controls, personal Gmail found only
in commit metadata; noreply rewrite with byte-identical trees; blocked
until the user chose rewrite-then-flip; verified PUBLIC via API.

## Changelog

- 2026-08-13 — Authored from the public-flip arc's inbox entry
  ("publishing exposes a surface").
