"""Regenerate the main results table and two figures from final_results.json."""

from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import statistics
from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
THRESHOLDS = ("0.75", "0.8", "0.85", "0.9")
COLORS = ("#1d5f87", "#bf5b30", "#41916b", "#8064a2")


def font(size: int, bold: bool = False):
    name = "arialbd.ttf" if bold else "arial.ttf"
    try:
        return ImageFont.truetype(name, size)
    except OSError:
        return ImageFont.load_default()


def draw_png_figures(rows: list[dict], out_dir: Path) -> None:
    width, height = 1500, 900
    left, right, top, bottom = 130, 75, 125, 190
    chart_w, chart_h = width - left - right, height - top - bottom
    labels = ["Wikipedia", "Kazakh News", "Engime", "News summaries"]
    title_font, label_font, small_font = font(34, True), font(24), font(21)

    def axes(draw, ceiling, title, xlabel):
        draw.text((width//2, 42), title, font=title_font, fill="#17212b", anchor="ma")
        for step in range(5):
            value = ceiling * step / 4
            y = top + chart_h * (1 - step/4)
            draw.line((left, y, left+chart_w, y), fill="#dfe4e9", width=2)
            draw.text((left-15, y), f"{value:.1f}", font=small_font, fill="#333", anchor="rm")
        draw.line((left, top, left, top+chart_h), fill="#333", width=3)
        draw.line((left, top+chart_h, left+chart_w, top+chart_h), fill="#333", width=3)
        draw.text((width//2, height-30), xlabel, font=label_font, fill="#222", anchor="ma")
        draw.text((left, top-35), "Flagged records (%)", font=small_font, fill="#222", anchor="lm")

    ceiling = max(.5, max((100*max(r["character_mean_rate"]+r["character_sd_rate"], r["word_mean_rate"]+r["word_sd_rate"]) for r in rows), default=0)*1.25)
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    axes(draw, ceiling, "Residual near-duplicate flags by corpus", "Corpus")
    for idx, row in enumerate(rows):
        center = left + chart_w*(idx+.5)/4
        for offset, key, sd_key, color in ((-37,"word_mean_rate","word_sd_rate","#9aa9b2"),(8,"character_mean_rate","character_sd_rate","#1d5f87")):
            value = 100*row[key]
            y = top + chart_h*(1-value/ceiling)
            draw.rectangle((center+offset, y, center+offset+29, top+chart_h), fill=color)
            err = chart_h*100*row[sd_key]/ceiling
            draw.line((center+offset+14,y-err,center+offset+14,y+err), fill="#333", width=3)
        draw.text((center, top+chart_h+28), labels[idx], font=small_font, fill="#222", anchor="mt")
    draw.rectangle((390, height-100, 417, height-73), fill="#9aa9b2")
    draw.text((427, height-86), "Word 5-gram", font=small_font, fill="#222", anchor="lm")
    draw.rectangle((730, height-100, 757, height-73), fill="#1d5f87")
    draw.text((767, height-86), "Character 7-gram", font=small_font, fill="#222", anchor="lm")
    draw.text((width//2,height-125), "Error bars show sample SD across three runs", font=small_font, fill="#555", anchor="ma")
    image.save(out_dir / "figure_1_results.png")

    ceiling = max(.5, max((100*max(r["threshold_mean_rates"].values()) for r in rows), default=0)*1.2)
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    axes(draw, ceiling, "Threshold sensitivity of character 7-gram flags", "Jaccard threshold")
    for idx, threshold in enumerate(THRESHOLDS):
        x = left+chart_w*idx/3
        draw.text((x, top+chart_h+25), f"{float(threshold):.2f}", font=small_font, fill="#222", anchor="mt")
    for idx, row in enumerate(rows):
        points = [(left+chart_w*j/3, top+chart_h*(1-100*row["threshold_mean_rates"][t]/ceiling)) for j,t in enumerate(THRESHOLDS)]
        draw.line(points, fill=COLORS[idx], width=5)
        for x,y in points:
            draw.ellipse((x-7,y-7,x+7,y+7), fill=COLORS[idx])
        legend_x = 190+idx*315
        draw.line((legend_x,height-90,legend_x+42,height-90), fill=COLORS[idx], width=5)
        draw.text((legend_x+52,height-90), labels[idx], font=small_font, fill="#222", anchor="lm")
    image.save(out_dir / "figure_2_sensitivity.png")


def flip_p(diffs: list[float]) -> float:
    if not diffs or all(abs(v) < 1e-15 for v in diffs):
        return 1.0
    observed = abs(statistics.mean(diffs))
    null = [abs(statistics.mean(sign * v for sign, v in zip(signs, diffs)))
            for signs in itertools.product((-1, 1), repeat=len(diffs))]
    return sum(value >= observed - 1e-15 for value in null) / len(null)


def holm(values: list[float]) -> list[float]:
    ordered = sorted(enumerate(values), key=lambda pair: pair[1])
    adjusted = [0.0] * len(values)
    running = 0.0
    for rank, (idx, value) in enumerate(ordered):
        running = max(running, min(1.0, value * (len(values) - rank)))
        adjusted[idx] = running
    return adjusted


def metric(run: dict, method: str, threshold: str = "0.8") -> dict:
    return run["methods"][method]["threshold_results"][threshold]


def summarize(data: dict) -> dict:
    grouped = {}
    for run in data["results"]:
        grouped.setdefault(run["source_key"], []).append(run)
    rows = []
    for key, runs in grouped.items():
        runs.sort(key=lambda r: r["run_seed"])
        char_rates = [metric(r, "character_7")["flag_rate"] for r in runs]
        word_rates = [metric(r, "word_5")["flag_rate"] for r in runs]
        differences = [a - b for a, b in zip(char_rates, word_rates)]
        rows.append({
            "source_key": key, "source_label": runs[0]["source_label"],
            "raw_rows_total": sum(r["raw_sample"] for r in runs),
            "eligible_post_exact_total": sum(r["post_exact"] for r in runs),
            "exact_removed_total": sum(r["excluded"].get("exact_removed", 0) for r in runs),
            "character_flags_total": sum(metric(r, "character_7")["flagged_records"] for r in runs),
            "word_flags_total": sum(metric(r, "word_5")["flagged_records"] for r in runs),
            "character_mean_rate": statistics.mean(char_rates),
            "character_sd_rate": statistics.stdev(char_rates),
            "word_mean_rate": statistics.mean(word_rates),
            "word_sd_rate": statistics.stdev(word_rates),
            "difference_percentage_points": 100 * statistics.mean(differences),
            "per_run": [{"seed": r["run_seed"], "post_exact": r["post_exact"],
                         "character_flags": metric(r, "character_7")["flagged_records"],
                         "character_rate": char_rates[i],
                         "word_flags": metric(r, "word_5")["flagged_records"],
                         "word_rate": word_rates[i]} for i, r in enumerate(runs)],
            "threshold_mean_rates": {t: statistics.mean(metric(r, "character_7", t)["flag_rate"] for r in runs) for t in THRESHOLDS},
            "exact_sign_flip_p": flip_p(differences),
        })
    adjusted = holm([r["exact_sign_flip_p"] for r in rows])
    for row, value in zip(rows, adjusted):
        row["holm_adjusted_p"] = value
    return {"protocol_selection_sha256": data["protocol_selection_sha256"], "corpora": rows,
            "statistical_note": "Exact sign-flip on three paired run-level differences; minimum nonzero two-sided p is 0.25. Disjoint block samples from one corpus are not fully independent. Comparisons are exploratory and do not estimate full-corpus prevalence."}


def figure_bars(rows: list[dict]) -> str:
    labels = ["Wikipedia", "Kazakh News", "Engime", "News summaries"]
    w, h = 900, 520
    x0, y0, plotw, ploth = 92, 75, 750, 340
    maximum = max((100 * max(r["character_mean_rate"] + r["character_sd_rate"], r["word_mean_rate"] + r["word_sd_rate"]) for r in rows), default=1)
    ceiling = max(.5, maximum * 1.25)
    pieces = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
              '<rect width="100%" height="100%" fill="white"/>',
              '<text x="450" y="35" text-anchor="middle" font-family="Arial" font-size="21" font-weight="bold">Residual near-duplicate flags by corpus</text>',
              f'<line x1="{x0}" y1="{y0+ploth}" x2="{x0+plotw}" y2="{y0+ploth}" stroke="#333"/>',
              f'<line x1="{x0}" y1="{y0}" x2="{x0}" y2="{y0+ploth}" stroke="#333"/>']
    for tick in range(5):
        value = ceiling * tick / 4
        y = y0 + ploth * (1 - tick / 4)
        pieces.append(f'<line x1="{x0}" y1="{y:.1f}" x2="{x0+plotw}" y2="{y:.1f}" stroke="#e1e4e8"/>')
        pieces.append(f'<text x="{x0-9}" y="{y+5:.1f}" text-anchor="end" font-family="Arial" font-size="13">{value:.1f}</text>')
    for idx, row in enumerate(rows):
        center = x0 + plotw * (idx + .5) / 4
        for offset, key, sd, color in ((-28, "word_mean_rate", "word_sd_rate", "#9aa9b2"), (8, "character_mean_rate", "character_sd_rate", "#1d5f87")):
            rate = 100 * row[key]
            height = ploth * rate / ceiling
            x, y = center + offset, y0 + ploth - height
            pieces.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="21" height="{max(height,1):.1f}" fill="{color}"/>')
            error = ploth * 100 * row[sd] / ceiling
            pieces.append(f'<line x1="{x+10.5:.1f}" y1="{y-error:.1f}" x2="{x+10.5:.1f}" y2="{y+error:.1f}" stroke="#333"/>')
        pieces.append(f'<text x="{center:.1f}" y="{y0+ploth+25}" text-anchor="middle" font-family="Arial" font-size="13">{escape(labels[idx])}</text>')
    pieces += ['<text x="24" y="255" transform="rotate(-90 24 255)" font-family="Arial" font-size="14">Mean flagged records (%)</text>',
               '<rect x="294" y="467" width="17" height="17" fill="#9aa9b2"/><text x="318" y="481" font-family="Arial" font-size="14">Word 5-gram baseline</text>',
               '<rect x="505" y="467" width="17" height="17" fill="#1d5f87"/><text x="529" y="481" font-family="Arial" font-size="14">Character 7-gram</text>',
               '<text x="450" y="507" text-anchor="middle" font-family="Arial" font-size="12">Error bars: sample SD across three fixed block samples</text>', '</svg>']
    return "\n".join(pieces)


def figure_sensitivity(rows: list[dict]) -> str:
    w, h = 900, 520
    x0, y0, plotw, ploth = 95, 70, 720, 340
    maximum = max((100 * max(r["threshold_mean_rates"].values()) for r in rows), default=1)
    ceiling = max(.5, maximum * 1.2)
    pieces = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
              '<rect width="100%" height="100%" fill="white"/>',
              '<text x="450" y="35" text-anchor="middle" font-family="Arial" font-size="21" font-weight="bold">Threshold sensitivity of character 7-gram flags</text>',
              f'<line x1="{x0}" y1="{y0+ploth}" x2="{x0+plotw}" y2="{y0+ploth}" stroke="#333"/>',
              f'<line x1="{x0}" y1="{y0}" x2="{x0}" y2="{y0+ploth}" stroke="#333"/>']
    for tick in range(5):
        value = ceiling * tick / 4
        y = y0 + ploth * (1 - tick / 4)
        pieces.append(f'<line x1="{x0}" y1="{y:.1f}" x2="{x0+plotw}" y2="{y:.1f}" stroke="#e1e4e8"/>')
        pieces.append(f'<text x="{x0-9}" y="{y+5:.1f}" text-anchor="end" font-family="Arial" font-size="13">{value:.1f}</text>')
    for idx, t in enumerate(THRESHOLDS):
        x = x0 + plotw * idx / 3
        pieces.append(f'<text x="{x:.1f}" y="{y0+ploth+25}" text-anchor="middle" font-family="Arial" font-size="13">{float(t):.2f}</text>')
    for idx, row in enumerate(rows):
        points = [(x0 + plotw * i / 3, y0 + ploth * (1 - 100 * row["threshold_mean_rates"][t] / ceiling)) for i, t in enumerate(THRESHOLDS)]
        color = COLORS[idx]
        pieces.append('<polyline points="' + ' '.join(f'{x:.1f},{y:.1f}' for x, y in points) + f'" fill="none" stroke="{color}" stroke-width="3"/>')
        for x, y in points:
            pieces.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="{color}"/>')
        pieces.append(f'<line x1="{120+idx*190}" y1="470" x2="{155+idx*190}" y2="470" stroke="{color}" stroke-width="3"/>')
        pieces.append(f'<text x="{160+idx*190}" y="475" font-family="Arial" font-size="13">{escape(row["source_label"][:18])}</text>')
    pieces += ['<text x="24" y="255" transform="rotate(-90 24 255)" font-family="Arial" font-size="14">Mean flagged records (%)</text>',
               '<text x="455" y="454" text-anchor="middle" font-family="Arial" font-size="14">Jaccard similarity threshold</text>', '</svg>']
    return "\n".join(pieces)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=ROOT / "results" / "final_results.json")
    parser.add_argument("--out-dir", type=Path, default=ROOT / "results")
    args = parser.parse_args()
    raw_bytes = args.input.read_bytes()
    data = json.loads(raw_bytes)
    summary = summarize(data)
    summary["input_results_sha256"] = hashlib.sha256(raw_bytes).hexdigest()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (args.out_dir / "main_results.csv").open("w", encoding="utf-8", newline="") as output:
        writer = csv.writer(output)
        writer.writerow(["Corpus", "Raw rows", "Post-exact", "Exact removed", "Character flags", "Character mean %", "Character SD %", "Word flags", "Word mean %", "Word SD %", "Difference pp", "p", "Holm p"])
        for row in summary["corpora"]:
            writer.writerow([row["source_label"], row["raw_rows_total"], row["eligible_post_exact_total"], row["exact_removed_total"],
                             row["character_flags_total"], 100*row["character_mean_rate"], 100*row["character_sd_rate"],
                             row["word_flags_total"], 100*row["word_mean_rate"], 100*row["word_sd_rate"],
                             row["difference_percentage_points"], row["exact_sign_flip_p"], row["holm_adjusted_p"]])
    (args.out_dir / "figure_1_results.svg").write_text(figure_bars(summary["corpora"]), encoding="utf-8")
    (args.out_dir / "figure_2_sensitivity.svg").write_text(figure_sensitivity(summary["corpora"]), encoding="utf-8")
    draw_png_figures(summary["corpora"], args.out_dir)
    print("Wrote summary, main_results.csv and two figures in SVG and PNG")


if __name__ == "__main__":
    main()
