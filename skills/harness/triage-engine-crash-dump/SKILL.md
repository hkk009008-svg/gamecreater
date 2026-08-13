---
name: triage-engine-crash-dump
description: Triage Unreal Engine crash dumps (XML breadcrumbs, minidumps, and callstacks) generated during headless captures or live sessions. Use to rapidly distinguish GPU TDR/device-removed errors from CPU null pointers and Blueprint infinite loops.
---

# Triage Engine Crash Dump

When Unreal Engine crashes during a headless run or live session, it writes crash context to `<ProjectRoot>/Saved/Crashes/` and `<ProjectRoot>/Saved/Logs/`. Guessing root causes from exit codes alone wastes hours on irrelevant theories.

## When

1. A headless launch (`UnrealEditor-Cmd.exe`) crashes with non-zero exit code or sudden process termination.
2. The user reports a hard freeze, GPU driver timeout, or crash dialog.
3. Diagnosing intermittent access violations (`0xC0000005`) or assertion failures (`check()`, `ensure()`).

## Triage Order

### 1. Locate the Latest Crash Folder
In `<ProjectRoot>/Saved/Crashes/crashinfo_.../`:
- `CrashContext.runtime-xml`: Primary structured XML summary (contains engine version, command line, crash reason, callstack symbols, and GPU device state).
- `CrashReportClient.log`: Client logging output.
- `<ProjectName>.log`: Full engine log leading up to the fatal frame.

### 2. Classify the Failure Class

| Failure Class | Diagnostic Signature | Typical Cause & Remedy |
| :--- | :--- | :--- |
| **GPU TDR / Device Removed** | `DXGI_ERROR_DEVICE_REMOVED`, `HRESULT: 0x887A0006`, `D3D12 device hung` | Heavy compute shader, infinite loop in Niagara emitter, ray tracing DXR timeout. Reduce shadow/RT cvars or increase Windows TdrDelay. |
| **CPU Null Pointer / AV** | `Exception 0xC0000005`, `Read address 0x0000000000000000` | Uninitialized component pointer, unlinked object reference, or accessed null Class Default Object. |
| **Assertion Macro Hit** | `Fatal error: [File:.../AssertionMacros.h] [Line: ...] ensure() / check() failed` | Explicit engine invariant violated (e.g. unregistered render resource, invalid bone transform index). |
| **Stack Overflow / Cyclic Loop** | `0xC00000FD`, recursive Blueprint function callstack | Infinite event cascade (e.g. OnRep calling server RPC which triggers OnRep). |

### 3. Extract the Decisive Callstack Line
Filter the callstack down to the highest frame inside your project's modules, plugins, or script functions. Ignore low-level driver or kernel frames (`nvwgf2um64.dll`, `ntdll.dll`).

## Provenance

DXR ray-tracing GPU device hung faults (2026-08): Headless capture runs timed out and crashed due to heavy DXR compute shader passes on uninitialized lumen scene assets.

## Changelog

- 2026-08-14 — Authored for automated engine crash dump and callstack triage.
