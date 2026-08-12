---
name: verify-a-cooked-package
description: Use when cooking, packaging, or staging a packaged build, or when citing a packaged build as evidence. Covers why BUILD SUCCESSFUL does not mean the package contains the content you asked for, how to verify container contents with a positive control, and the project-named target trap.
---

# Verify a Cooked Package

This skill grants no promotion, config-write, or external-effect authority.

## When

You are cooking, packaging, or staging a packaged build, or about to cite
one as evidence. A packaged build is evidence only after you have inspected
what is inside it: `BUILD SUCCESSFUL` describes the tool's execution, not
the artifact's contents.

## The trap: a bare cook silently packages only the default map

With no explicit maps-to-cook configuration, the cook falls back to the
project's game default map — whatever that happens to be. Measured
instance: the default map was a retired preview scene; the build reported
SUCCESS, 0 errors, 565 packages, 680 MB — all from the wrong map's
reference graph, with the actual subject map absent and never mentioned in
the log. The only tells were quantitative: a shader count impossible for
the subject scene, and no shader lines for its master material.

## What to do instead

1. **Name every map explicitly** on the command line (`-map=A+B`); a
   command-line list dirties no config. Keep the game default map in the
   list even when it is not the subject — the executable boots into it —
   and select the subject map via the packaged executable's first argument.

2. **Verify the container, with a positive control.** Modern packaging
   splits payload across containers (in UE 5.x IoStore, payload lives in
   `.ucas` and the `.utoc` holds the index — a 680 MB package can show an
   11 MB `.pak`). Grep the index bytes for literal asset names — and
   **always include a needle you expect to be present**. Finding the
   control needle proves the index is greppable in plain bytes, which is
   what makes an absence meaningful; without it, zero hits is
   indistinguishable from a compressed index. Know what the index does NOT
   list (actor labels live inside map payloads) so their absence is not
   misread as a missing map.

3. **Expect the project-named target.** For a Blueprint project with code
   plugins, the build tool synthesizes targets named after the project.
   Building the generic editor target succeeds — then the cook aborts two
   stages later looking for `<Project>Editor.target`, in a tool that never
   mentions the build. The tell: the game build links `<Project>.exe`
   rather than the generic game executable.

4. **Never gate on the process exit code.** Two independent cases in one
   session: a script runner returned 0 while its own report recorded FAIL,
   and the cook returned SUCCESS for a package missing its subject map.
   Gate on the artifact and on a report the run itself wrote.

5. **Cite the real cache for derived-data claims.** Engine versions move
   their derived-data store (UE 5.x routes through Zen at a machine-level
   path; the legacy project folder stays near-empty). A cold/warm claim
   sourced from the wrong directory measures nothing.

## Record what the package is, not that it built

Name the archive for the **measured** state (`Baseline_D3D12_SM5`), never
"Baseline" — a package usually exists to be half of an A/B, and a directory
called Baseline says nothing once its counterpart exists. Record: maps
actually verified present, shader platform observed in the cook log,
package byte sizes by container, protected hashes before and after, and
the exact map list used. A package whose map list was not recorded cannot
be reproduced or compared.

## Provenance

The wrong-map SUCCESS build, the greppable-index control, and the
project-named-target abort are measured instances from one project's
Windows bring-up (2026-07-31). Generalized 2026-08-12.

## Changelog

- 2026-08-12 — Initial generalized port.
