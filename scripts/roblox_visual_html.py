"""Render a portable, offline visual-review packet without external dependencies.

The packet core validates evidence. This module presents its verdict without
claiming that metadata eligibility establishes visual quality or user acceptance.
Only copied media paths are accepted; original paths never become browser URLs.
"""

from __future__ import annotations

import html
import json
import re
from typing import Any


_MEDIA_PATH = re.compile(r"media/[0-9a-fA-F]{64}\.(?:png|jpg|jpeg|mp4)\Z")


def _text(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _value(value: Any) -> str:
    if value is None or value == "":
        return '<span class="unknown">Not recorded</span>'
    if isinstance(value, (dict, list, tuple)):
        value = json.dumps(value, ensure_ascii=False, separators=(", ", ": "))
    return _text(value)


def _media_path(capture: dict[str, Any]) -> str:
    path = capture.get("mediaPath", "")
    if not isinstance(path, str) or not _MEDIA_PATH.fullmatch(path):
        raise ValueError("Renderer requires a copied relative media/<sha> URL.")
    return path


def _list(items: list[str], empty: str = "None recorded") -> str:
    if not items:
        return f'<p class="muted">{_text(empty)}</p>'
    return "<ul>" + "".join(f"<li>{_text(item)}</li>" for item in items) + "</ul>"


def _capture_media(capture: dict[str, Any], *, overlay: bool = False) -> str:
    path = _media_path(capture)
    label = _text(capture.get("label", capture["id"]))
    if capture["kind"] == "image":
        css = ' class="overlay-candidate"' if overlay else ""
        return f'<img{css} src="{path}" alt="{label}" loading="lazy" decoding="async">'
    return (
        f'<video src="{path}" controls preload="metadata" playsinline aria-label="{label}">'
        "Your browser cannot play this video. Open the original file below.</video>"
    )


def _capture_frame(capture: dict[str, Any], role: str) -> str:
    context = capture.get("context") or {}
    encoding = str(capture.get("format") or "Encoding unknown").upper()
    if encoding in ("JPG", "JPEG"):
        encoding = "JPEG · lossy"
    elif encoding == "PNG":
        encoding = "PNG · lossless"
    elif encoding == "MP4":
        encoding = "MP4 · playback unverified"
    dimensions = (
        f'{capture["width"]} × {capture["height"]}'
        if capture.get("width") and capture.get("height") else "Dimensions not recorded"
    )
    return (
        '<figure class="capture">'
        f'<figcaption><span class="frame-role">{_text(role)}</span>'
        f'<strong>{_text(capture.get("label", capture["id"]))}</strong>'
        f'<span class="frame-detail">{_text(context.get("captureMode") or "Capture mode unknown")}'
        f' · {_text(dimensions)} · {_text(encoding)}</span></figcaption>'
        f'<div class="media-frame">{_capture_media(capture)}</div>'
        '<div class="frame-foot">'
        f'<span>Build {_value((capture.get("build") or {}).get("id"))}</span>'
        f'<a href="{_media_path(capture)}" target="_blank" rel="noopener">Open original'
        '<span class="sr-only"> in a new tab</span> ↗</a></div></figure>'
    )


def _metadata(baseline: dict[str, Any], candidate: dict[str, Any],
              comparison: dict[str, Any]) -> str:
    differences = comparison.get("differences") or []
    if differences:
        rows = "".join(
            "<tr>"
            f'<th scope="row">{_text(row.get("field", "Unknown field"))}</th>'
            f'<td>{_value(row.get("baseline"))}</td>'
            f'<td>{_value(row.get("candidate"))}</td>'
            f'<td>{"Declared change" if row.get("declared") else "Uncontrolled difference"}</td>'
            "</tr>" for row in differences
        )
        diff_table = (
            '<div class="table-scroll"><table><caption>Recorded differences</caption>'
            '<thead><tr><th scope="col">Setting</th><th scope="col">Baseline</th>'
            '<th scope="col">Candidate</th><th scope="col">Interpretation</th></tr></thead>'
            f"<tbody>{rows}</tbody></table></div>"
        )
    else:
        diff_table = '<p class="muted">No recorded differences. Missing metadata remains a gap.</p>'

    context_keys = sorted(set((baseline.get("context") or {})) | set((candidate.get("context") or {})))
    all_rows = []
    for field in ["build.id", "build.sha256", "sha256", *context_keys]:
        def get(capture: dict[str, Any]) -> Any:
            if field.startswith("build."):
                return (capture.get("build") or {}).get(field.split(".")[1])
            if field == "sha256":
                return capture.get(field)
            return (capture.get("context") or {}).get(field)
        all_rows.append(
            f'<tr><th scope="row">{_text(field)}</th><td>{_value(get(baseline))}</td>'
            f"<td>{_value(get(candidate))}</td></tr>"
        )
    return (
        '<details class="metadata"><summary>Inspect settings &amp; artifact identity'
        f' <span class="count">{len(differences)} differences</span></summary>'
        + diff_table +
        '<div class="table-scroll"><table><caption>Recorded capture metadata</caption>'
        '<thead><tr><th scope="col">Field</th><th scope="col">Baseline</th>'
        '<th scope="col">Candidate</th></tr></thead>'
        f'<tbody>{"".join(all_rows)}</tbody></table></div>'
        '<p class="small muted">Build identity is declared. Matching settings do not prove '
        "that the game ran those bytes.</p></details>"
    )


def _comparison(comparison: dict[str, Any], captures: dict[str, dict[str, Any]],
                index: int) -> str:
    baseline = captures[comparison["baseline"]]
    candidate = captures[comparison["candidate"]]
    eligible = comparison.get("comparable") is True
    same_dimensions = bool(
        baseline.get("width") and baseline.get("height")
        and baseline.get("width") == candidate.get("width")
        and baseline.get("height") == candidate.get("height")
    )
    overlay = eligible and baseline["kind"] == candidate["kind"] == "image" and same_dimensions
    two_videos = baseline["kind"] == candidate["kind"] == "video"
    status = "Eligible for comparison" if eligible else "Evidence gaps"
    hidden = " hidden" if index else ""
    issues = comparison.get("issues") or []
    issue_panel = (
        '<aside class="gap-panel" aria-label="Comparison evidence gaps">'
        '<strong>This pair needs evidence before a controlled comparison.</strong>'
        '<details class="gap-details"><summary>'
        f'Inspect {len(issues)} evidence gap{"s" if len(issues) != 1 else ""}'
        '</summary>'
        + _list(issues, "This comparison is not eligible. Inspect the report for missing evidence.")
        + "</details></aside>"
    ) if not eligible else ""
    switcher = (
        '<div class="view-switch" role="group" aria-label="Image comparison view">'
        '<button type="button" data-view="side" aria-pressed="true">Side by side</button>'
        f'<button type="button" data-view="overlay" aria-pressed="false"'
        f'{" disabled" if not overlay else ""}>Overlay</button></div>'
    )
    overlay_content = ""
    if overlay:
        overlay_content = (
            '<div class="overlay-view" hidden>'
            '<p class="small muted">Baseline underneath · Candidate revealed from the left. '
            "Images retain their original aspect ratio.</p>"
            '<div class="overlay-frame">'
            + _capture_media(baseline) + _capture_media(candidate, overlay=True)
            + '</div><label class="slider-label">'
            f'Candidate reveal <output id="reveal-value-{index}">50%</output>'
            f'<input type="range" min="0" max="100" value="50" aria-label="Candidate reveal percentage"'
            f' aria-describedby="reveal-value-{index}"></label></div>'
        )
    motion = (
        '<div class="motion-controls"><button type="button" data-play-pair>'
        'Play both from start</button><button type="button" data-pause-pair>Pause both</button>'
        '<span class="small muted">Approximate simultaneous start; not frame-synchronized. '
        "Stepped footage cannot establish native motion.</span>"
        '<span class="play-notice small" role="status" aria-live="polite"></span></div>'
    ) if two_videos else ""
    return (
        f'<section class="comparison-panel" id="comparison-{index}"'
        f' aria-labelledby="comparison-title-{index}"{hidden}>'
        '<div class="section-eyebrow">'
        f'<span>{_text(comparison.get("purpose", "aesthetic"))} comparison</span>'
        f'<span class="status {"ready" if eligible else "gap"}">{status}</span></div>'
        f'<h2 id="comparison-title-{index}">{_text(comparison["title"])}</h2>'
        f'<p class="comparison-question">{_text(comparison["question"])}</p>'
        + issue_panel +
        '<div class="comparison-toolbar">' + switcher
        + '<span class="small muted">Original frames · no crop or pixel score</span></div>'
        '<div class="side-view">'
        + _capture_frame(baseline, "Baseline") + _capture_frame(candidate, "Candidate")
        + "</div>" + overlay_content + motion
        + ('<p class="small muted overlay-explanation">Overlay is unavailable: it requires '
           'an eligible pair of equal-sized images.</p>' if not overlay else "")
        + _metadata(baseline, candidate, comparison)
        + '<div class="pair-notes"><div><h3>Baseline notes</h3>'
        + _list(baseline.get("notes") or [])
        + '</div><div><h3>Candidate notes</h3>'
        + _list(candidate.get("notes") or [])
        + "</div></div></section>"
    )


_CSS = r"""
:root{color-scheme:light;--paper:#f6f4ed;--ink:#202b2a;--muted:#5d6965;--line:#d4dad1;--sage:#dfe8dd;--sage-ink:#345642;--cyan:#dcecf0;--amber:#f7e5ba;--amber-ink:#654719}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.55 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}button,input,summary{font:inherit}button,a,summary,input{touch-action:manipulation}button{cursor:pointer;color:inherit}a{color:#245560;text-underline-offset:3px}a:hover{color:#17383f}:focus-visible{outline:3px solid #16778b;outline-offset:4px}[hidden]{display:none!important}
.topline{padding:20px 4vw;display:flex;justify-content:space-between;gap:20px;border-bottom:1px solid var(--line);font-size:12px;letter-spacing:.1em;text-transform:uppercase}.topline a{font-size:11px}.brand{font-weight:750}.hero{padding:40px 4vw 32px;max-width:1700px;margin:auto}.eyebrow,.section-eyebrow{font-size:11px;letter-spacing:.12em;text-transform:uppercase;color:var(--muted);font-weight:700}.hero h1{font-size:clamp(34px,4.2vw,64px);line-height:1.05;letter-spacing:-.045em;font-weight:630;max-width:1100px;margin:12px 0 20px}.hero-question{font-size:clamp(17px,1.4vw,21px);max-width:950px;margin:0 0 25px}.status{display:inline-block;font-size:10px;letter-spacing:.055em;font-weight:750;text-transform:uppercase;padding:5px 9px;border-radius:3px;white-space:nowrap}.status.gap{background:var(--amber);color:var(--amber-ink)}.status.ready{background:var(--sage);color:var(--sage-ink)}.status.neutral{background:var(--cyan);color:#315662}.overview{display:flex;gap:22px;align-items:center;flex-wrap:wrap}.overview .small{border-left:1px solid var(--line);padding-left:22px}.small{font-size:12px}.muted{color:var(--muted)}.unknown{color:#765931;font-style:italic}.direction{border-top:1px solid var(--line);border-bottom:1px solid var(--line);margin-top:28px;padding:21px 0 25px;display:grid;grid-template-columns:1.15fr 1fr 1fr 1fr;gap:30px}.direction h2,.direction h3,.pair-notes h3{font-size:11px;letter-spacing:.1em;text-transform:uppercase;margin:0 0 12px}.direction p{margin:0;font-size:14px}.direction ul,.pair-notes ul{padding-left:17px;margin:0;font-size:13px}.direction li+li,.pair-notes li+li{margin-top:7px}.workspace{display:grid;grid-template-columns:220px minmax(0,1fr);gap:34px;padding:16px 4vw 48px;max-width:1700px;margin:auto}.rail{border-right:1px solid var(--line);padding-right:23px}.rail-inner{position:sticky;top:20px}.rail h2{font-size:11px;letter-spacing:.12em;text-transform:uppercase;color:var(--muted);margin:0 0 15px}.nav-button{display:block;width:100%;text-align:left;background:transparent;border:0;border-left:3px solid transparent;border-radius:0;padding:13px 10px;margin:0 0 3px}.nav-button[aria-pressed=true]{background:var(--sage);border-left-color:var(--sage-ink)}.nav-number{font-size:10px;font-weight:700;color:var(--muted);display:block;margin-bottom:5px}.nav-title{font-size:13px;line-height:1.35;font-weight:650;display:block}.nav-status{font-size:10px;display:block;margin-top:6px;color:var(--muted)}.rail-links{border-top:1px solid var(--line);margin-top:25px;padding-top:18px;display:grid;gap:10px;font-size:12px}.content{min-width:0}.section-eyebrow{display:flex;align-items:center;justify-content:space-between;gap:15px}.comparison-panel h2{font-size:clamp(25px,2.2vw,36px);line-height:1.15;letter-spacing:-.025em;margin:15px 0 12px}.comparison-question{font-size:16px;max-width:900px;margin:0 0 22px}.gap-panel{background:var(--amber);border-left:3px solid #b98227;padding:15px 18px;margin:0 0 23px;font-size:13px}.gap-panel strong{font-size:13px}.gap-panel ul{padding-left:18px;margin:9px 0 0}.gap-panel li+li{margin-top:4px}.comparison-toolbar{display:flex;align-items:center;justify-content:space-between;gap:15px;flex-wrap:wrap;margin-bottom:15px}.view-switch{display:inline-flex;border:1px solid #bec8bd;border-radius:4px;overflow:hidden}.view-switch button{background:transparent;border:0;padding:8px 13px;font-size:12px}.view-switch button[aria-pressed=true]{background:var(--ink);color:#fff}.view-switch button:disabled{cursor:not-allowed;color:#7f8781;background:#eceee7}.side-view{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:18px}.capture{margin:0;min-width:0}.capture figcaption{display:grid;grid-template-columns:auto 1fr;align-items:baseline;column-gap:9px;row-gap:4px;margin-bottom:10px}.capture figcaption strong{font-size:13px;font-weight:650;overflow-wrap:anywhere}.frame-role{font-size:10px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);font-weight:700}.frame-detail{font-size:10px;color:var(--muted);grid-column:1/-1}.media-frame{background:#dde1db;border:1px solid var(--line);line-height:0}.media-frame img,.media-frame video,.overlay-frame img{display:block;width:100%;height:auto}.media-frame video{background:#182320}.frame-foot{display:flex;justify-content:space-between;gap:8px;font-size:10px;padding:10px 0;overflow-wrap:anywhere}.frame-foot a{flex-shrink:0}.overlay-frame{position:relative;line-height:0;background:#dde1db;border:1px solid var(--line)}.overlay-frame .overlay-candidate{position:absolute;inset:0;clip-path:inset(0 50% 0 0)}.slider-label{font-size:12px;display:grid;grid-template-columns:1fr auto;gap:7px;margin:16px 0 8px}.slider-label input{grid-column:1/-1;width:100%;accent-color:#365c4a}.motion-controls{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin:12px 0 18px}.motion-controls button{border:1px solid #bdc8bb;background:var(--sage);padding:8px 12px;border-radius:4px;font-size:12px}.motion-controls .small{max-width:510px}.play-notice{flex-basis:100%;color:var(--amber-ink)}.metadata{border-top:1px solid var(--line);border-bottom:1px solid var(--line);margin:23px 0 0;padding:15px 0}.metadata summary{cursor:pointer;font-weight:650;font-size:13px}.count{font-weight:450;font-size:11px;color:var(--muted);margin-left:10px}.table-scroll{overflow-x:auto;margin-top:18px}table{border-collapse:collapse;width:100%;font-size:11px;table-layout:fixed}caption{text-align:left;font-size:12px;font-weight:650;padding:0 0 8px}td,th{text-align:left;vertical-align:top;padding:10px 12px;border-top:1px solid var(--line);overflow-wrap:anywhere}thead{background:#e8ece4}tbody th{font-weight:550;width:18%}.pair-notes{display:grid;grid-template-columns:1fr 1fr;gap:28px;padding:22px 0 8px}.lower-section{border-top:1px solid var(--line);padding-top:29px;margin-top:34px}.lower-section h2{font-size:25px;letter-spacing:-.025em;margin:0 0 12px}.gallery{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:24px 18px}.gallery .capture figcaption{display:block}.gallery .capture figcaption strong{display:block}.gallery .frame-role{display:none}.gallery .frame-detail{display:block;margin-top:4px}.gallery details{font-size:11px;margin-top:7px}.gallery details ul{padding-left:16px}.coverage-row{display:grid;grid-template-columns:1.1fr 1fr 1.6fr;gap:15px;padding:14px 0;border-top:1px solid var(--line);font-size:12px}.coverage-row strong{font-weight:650}.coverage-state{color:var(--sage-ink)}.coverage-state.missing{color:#78510e}.decision{display:grid;grid-template-columns:1fr 1fr;gap:30px}.decision h3{font-size:11px;letter-spacing:.1em;text-transform:uppercase;margin:18px 0 8px}.decision p{font-size:14px;margin:0}.decision .status{margin-bottom:6px}.footer{border-top:1px solid var(--line);padding:25px 4vw 35px;max-width:1700px;margin:auto;color:var(--muted);font-size:11px}.footer ul{padding-left:17px}.footer code{overflow-wrap:anywhere}.sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}.skip-link{position:absolute;left:10px;top:-100px;background:white;padding:10px;z-index:10}.skip-link:focus{top:10px}.empty-state{padding:22px;background:var(--amber);font-size:14px}
@media(min-width:1700px){.topline{padding-left:max(4vw,calc((100vw - 1564px)/2));padding-right:max(4vw,calc((100vw - 1564px)/2))}}
.gap-details{margin-top:7px}.gap-details summary{cursor:pointer;font-size:12px;color:var(--amber-ink)}.pair-notes,.direction,.decision,.coverage-row,.gallery details{overflow-wrap:anywhere}
@media(max-width:1050px){.direction{grid-template-columns:1fr 1fr;gap:25px}.workspace{grid-template-columns:170px minmax(0,1fr);gap:22px}.rail{padding-right:15px}.gallery{grid-template-columns:repeat(2,minmax(0,1fr))}.side-view{gap:12px}.frame-foot{flex-wrap:wrap}}
@media(max-width:720px){.topline{padding:15px 5vw}.topline>span{max-width:50%}.hero{padding:28px 5vw 18px}.hero h1{font-size:38px}.overview{gap:12px}.overview .small{border-left:0;padding-left:0}.direction{gap:22px 18px}.workspace{display:block;padding:12px 5vw 36px}.rail{border:0;padding:0 0 23px}.rail-inner{position:static}.rail nav{display:flex;overflow-x:auto;padding-bottom:4px;gap:6px}.nav-button{min-width:180px;max-width:230px;border-left:0;border-bottom:3px solid transparent;padding:11px}.nav-button[aria-pressed=true]{border-left:0;border-bottom-color:var(--sage-ink)}.rail-links{display:flex;flex-wrap:wrap;gap:15px;margin-top:12px;padding-top:12px}.side-view{grid-template-columns:1fr;gap:24px}.section-eyebrow{font-size:9px}.pair-notes,.decision{grid-template-columns:1fr;gap:20px}.coverage-row{grid-template-columns:1fr 1fr;gap:6px}.coverage-row>span:last-child{grid-column:1/-1}.footer{padding:22px 5vw}table{min-width:540px}.gallery{grid-template-columns:1fr 1fr;gap:18px 12px}.gallery .frame-foot{font-size:9px}.gallery .frame-detail{font-size:9px}}
@media(max-width:420px){.direction,.gallery{grid-template-columns:1fr}.hero h1{font-size:33px}.topline{font-size:10px}.status{white-space:normal}}
@media(prefers-reduced-motion:no-preference){button,a{transition:background-color .12s ease,color .12s ease}}
@media print{.rail,.view-switch,.motion-controls,.slider-label{display:none}.workspace{display:block}.comparison-panel[hidden]{display:block!important;break-before:page}.overlay-view{display:none!important}.side-view[hidden]{display:grid!important}.hero{padding-top:10px}.metadata{break-inside:avoid}.gallery{grid-template-columns:repeat(2,1fr)}}
"""


_JS = r"""
(() => {
  "use strict";
  const panels = Array.from(document.querySelectorAll(".comparison-panel"));
  const navigation = Array.from(document.querySelectorAll("[data-comparison]"));
  navigation.forEach(button => button.addEventListener("click", () => {
    panels.forEach(panel => {
      panel.hidden = panel.id !== button.dataset.comparison;
      if (panel.hidden) panel.querySelectorAll("video").forEach(video => video.pause());
    });
    navigation.forEach(item => item.setAttribute("aria-pressed", String(item === button)));
  }));
  panels.forEach(panel => {
    const overlay = panel.querySelector(".overlay-view");
    const side = panel.querySelector(".side-view");
    panel.querySelectorAll("[data-view]").forEach(button => button.addEventListener("click", () => {
      const showOverlay = button.dataset.view === "overlay";
      if (showOverlay && !overlay) return;
      side.hidden = showOverlay;
      if (overlay) overlay.hidden = !showOverlay;
      panel.querySelectorAll("[data-view]").forEach(item =>
        item.setAttribute("aria-pressed", String(item === button)));
    }));
    const slider = panel.querySelector('input[type="range"]');
    if (slider) slider.addEventListener("input", () => {
      const value = Math.max(0, Math.min(100, Number(slider.value)));
      panel.querySelector(".overlay-candidate").style.clipPath = `inset(0 ${100-value}% 0 0)`;
      panel.querySelector("output").textContent = `${value}%`;
    });
    const videos = Array.from(panel.querySelectorAll("video"));
    const play = panel.querySelector("[data-play-pair]");
    const pause = panel.querySelector("[data-pause-pair]");
    if (play) play.addEventListener("click", async () => {
      const notice = panel.querySelector(".play-notice");
      notice.textContent = "";
      const results = await Promise.allSettled(videos.map(async video => {
        video.pause();
        video.currentTime = 0;
        await video.play();
      }));
      if (results.some(result => result.status === "rejected"))
        notice.textContent = "A video could not start. Use its individual controls or open the original file.";
    });
    if (pause) pause.addEventListener("click", () => videos.forEach(video => video.pause()));
  });
})();
"""


def render_packet(manifest: dict[str, Any], report: dict[str, Any]) -> str:
    """Return escaped offline HTML for a validated, copied-media report."""
    captures = {capture["id"]: capture for capture in report["captures"]}
    # Validate every URL even when a capture is not used by a comparison.
    for capture in captures.values():
        _media_path(capture)
    comparisons = report.get("comparisons") or []
    ready = sum(comparison.get("comparable") is True for comparison in comparisons)
    title = _text(manifest["title"])
    direction = manifest["direction"]
    navigation = "".join(
        f'<button class="nav-button" type="button" data-comparison="comparison-{index}"'
        f' aria-controls="comparison-{index}" aria-pressed="{"true" if index == 0 else "false"}">'
        f'<span class="nav-number">{index + 1:02d} / {_text(comparison["purpose"])}</span>'
        f'<span class="nav-title">{_text(comparison["title"])}</span>'
        f'<span class="nav-status">{"Eligible" if comparison.get("comparable") else "Evidence gaps"}</span>'
        "</button>" for index, comparison in enumerate(comparisons)
    )
    panels = "".join(_comparison(comparison, captures, index)
                     for index, comparison in enumerate(comparisons))
    if not panels:
        panels = (
            '<p class="empty-state">Reference gallery only. No baseline/candidate comparisons '
            "have been supplied; this packet needs comparison evidence.</p>"
        )
    gallery = "".join(
        '<div>' + _capture_frame(capture, "Reference")
        + '<details><summary>Capture notes</summary>'
        + _list(capture.get("notes") or []) + "</details></div>"
        for capture in captures.values()
    )
    coverage = report.get("coverage") or []
    coverage_rows = "".join(
        '<div class="coverage-row">'
        f'<strong>{_text(row["label"])}</strong>'
        f'<span class="coverage-state{" missing" if not row.get("captureIds") else ""}">'
        f'{"Missing evidence" if not row.get("captureIds") else str(len(row["captureIds"])) + " capture(s) recorded"}'
        f'</span><span>{_text(row.get("note", ""))}</span></div>'
        for row in coverage
    ) or '<p class="muted">No coverage checklist was recorded.</p>'
    decisions = report.get("decisions") or manifest["decisions"]
    packet_ready = report.get("status") == "ready-for-review"
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta name="referrer" content="no-referrer">'
        f"<title>{title} · Visual workbench</title><style>{_CSS}</style></head><body>"
        '<a class="skip-link" href="#review-workspace">Skip to visual review</a>'
        '<header class="topline"><span class="brand">Roblox team / Visual workbench</span>'
        '<span>Offline evidence packet · <a href="report.json">Report JSON</a></span></header>'
        '<div class="hero"><div class="eyebrow">Art direction / Controlled iteration</div>'
        f"<h1>{title}</h1><p class=\"hero-question\">{_text(manifest['question'])}</p>"
        '<div class="overview">'
        f'<span class="status {"ready" if packet_ready else "gap"}">'
        f'{"Ready for human review" if packet_ready else "Needs evidence"}</span>'
        f'<span class="small">{ready} / {len(comparisons)} comparisons eligible</span>'
        f'<span class="small">{len(captures)} original media files</span>'
        '<span class="small muted">Quality &amp; user approval remain separate judgments.</span></div>'
        '<section class="direction" aria-label="Visual direction">'
        '<div><h2>The visual promise</h2>'
        f'<p>{_text(direction["promise"])}</p></div><div><h3>Build toward</h3>'
        + _list(direction["rules"]) + '</div><div><h3>Avoid</h3>'
        + _list(direction["avoid"]) + '</div><div><h3>Preserve</h3>'
        + _list(direction["preserve"]) + "</div></section></div>"
        '<div class="workspace" id="review-workspace"><aside class="rail"><div class="rail-inner">'
        '<h2>Review sequence</h2><nav aria-label="Comparisons">' + navigation + "</nav>"
        '<div class="rail-links"><a href="#reference-gallery">Reference gallery</a>'
        '<a href="#coverage">Coverage &amp; gaps</a><a href="#decision">Recorded decision</a>'
        '<a href="#limitations">Evidence limits</a></div></div></aside>'
        '<main class="content">' + panels
        + '<section class="lower-section" id="reference-gallery"><div class="eyebrow">Original media</div>'
        '<h2>Reference gallery</h2><p class="small muted">All supplied captures, including incomplete '
        'or unmatched evidence. Open an original for its full resolution.</p><div class="gallery">'
        + gallery + '</div></section><section class="lower-section" id="coverage">'
        '<div class="eyebrow">What the packet covers</div><h2>Coverage &amp; gaps</h2>'
        '<p class="small muted">Recorded media is coverage evidence, not a passed acceptance test.</p>'
        + coverage_rows + '</section><section class="lower-section" id="decision">'
        '<div class="eyebrow">Human judgment</div><h2>Recorded decision</h2><div class="decision">'
        '<div><span class="status neutral">' + _text(decisions["status"]) + "</span>"
        '<h3>User verdict</h3><p>' + _value(decisions.get("userVerdict")) + "</p></div>"
        '<div><h3>Next experiment</h3><p>' + _text(decisions["nextExperiment"])
        + "</p></div></div></section></main></div>"
        '<footer class="footer" id="limitations"><strong>Evidence limits</strong>'
        + _list(report.get("limits") or [], "No additional limits recorded.")
        + '<p>Eligibility checks metadata and media identity. It does not establish execution, '
        "capture provenance, beauty, performance or acceptance. The packet does not modify its evidence.</p>"
        '<p>Manifest SHA-256: <code>' + _text(report.get("manifestSha256", "Not recorded"))
        + "</code></p></footer><script>" + _JS + "</script></body></html>"
    )
