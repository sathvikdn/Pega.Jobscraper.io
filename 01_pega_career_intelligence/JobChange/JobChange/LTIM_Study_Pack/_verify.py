"""Structural checker for the LTIM study pack. Run: python _verify.py"""
import html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CHAPTERS = {
    "ch01_ltimindtree_pega_practice.html": 7000,
    "ch02_pega_customer_service.html": 8000,
    "ch03_constellation_react.html": 9000,
}
FORBIDDEN = ["Mondelez", "Lighthouse partner"]
problems = []


def fail(message):
    problems.append(message)
    print("FAIL:", message)


css_text = (ROOT / "assets" / "sourcebook.css").read_text(encoding="utf-8")
css_classes = set(re.findall(r"\.([A-Za-z][\w-]*)", css_text))


def strip_text(source):
    body = re.sub(r"<(script|style)[\s\S]*?</\1>", " ", source)
    body = re.sub(r"<[^>]+>", " ", body)
    return html.unescape(body)


def check_file(name):
    path = ROOT / name
    source = path.read_text(encoding="utf-8")
    ids = set(re.findall(r'\sid="([^"]+)"', source))
    stats = {}

    for anchor in re.findall(r'href="#([^"]*)"', source):
        if anchor not in ids:
            fail(f"{name}: anchor #{anchor} has no matching id")

    for target in re.findall(r'href="([^"#][^"]*)"', source):
        if re.match(r"^(https?:|mailto:)", target):
            continue
        file_part = target.split("#")[0]
        if not (ROOT / file_part).resolve().exists():
            fail(f"{name}: cross-file link {target} does not resolve")

    for value in re.findall(r'class="([^"]*)"', source):
        for cls in value.split():
            if cls not in css_classes:
                fail(f"{name}: class '{cls}' not in sourcebook.css")

    if re.search(r"<style", source, re.I):
        fail(f"{name}: contains <style>")
    if re.search(r"\sstyle\s*=", source, re.I):
        fail(f"{name}: contains style= attribute")
    if re.search(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]", source):
        fail(f"{name}: contains emoji/pictograph")
    for word in FORBIDDEN:
        if word.lower() in source.lower():
            fail(f"{name}: forbidden string '{word}'")

    stats["qa"] = len(re.findall(r'class="qa"', source))
    stats["answer"] = len(re.findall(r'class="answer"', source))
    stats["flow"] = len(re.findall(r'class="flow"', source))
    stats["warning"] = len(re.findall(r'class="warning"', source))
    stats["words"] = len(strip_text(source).split())

    sections = re.findall(r"<section[^>]*\sid=\"([^\"]+)\"", source)
    stats["sections"] = len(sections) + 0
    return source, ids, stats


def main():
    all_stats = {}
    for name, target_words in CHAPTERS.items():
        source, ids, stats = check_file(name)
        all_stats[name] = stats
        n_sections = stats["sections"]
        if not 6000 <= stats["words"] <= 9500:
            fail(f"{name}: word count {stats['words']} outside 6000-9500")
        if not 14 <= stats["qa"] <= 18:
            fail(f"{name}: qa count {stats['qa']} outside 14-18")
        if stats["answer"] < 3:
            fail(f"{name}: answer count {stats['answer']} < 3")
        if stats["flow"] < 2:
            fail(f"{name}: flow count {stats['flow']} < 2")

        tiles = re.findall(r"<div><strong>([^<]+)</strong><span>([^<]+)</span></div>", source)
        tile_map = {label: value for value, label in tiles}
        if tile_map.get("Sections") != str(n_sections):
            fail(f"{name}: Sections tile {tile_map.get('Sections')} != actual {n_sections}")
        if tile_map.get("Interview Q&amp;A") != str(stats["qa"]):
            fail(f"{name}: Q&A tile {tile_map.get('Interview Q&amp;A')} != actual {stats['qa']}")

        toc_block = source.split('<div class="toc">')[1].split("</div>")[0]
        toc_entries = re.findall(r'<a href="#([^"]+)">(\d+\.[\dR]+)\s+([^<]+)', toc_block)
        if len(toc_entries) != n_sections:
            fail(f"{name}: TOC has {len(toc_entries)} entries, file has {n_sections} sections")
        for anchor, number, title in toc_entries:
            heading = re.search(
                r'<section id="%s"[^>]*>\s*<h2>([^<]+)' % re.escape(anchor), source
            )
            if not heading:
                fail(f"{name}: no h2 for TOC anchor {anchor}")
                continue
            heading_text = html.unescape(heading.group(1)).strip()
            toc_text = html.unescape(f"{number} {title}").strip()
            if not heading_text.lower().startswith(toc_text.lower()):
                fail(f"{name}: TOC '{toc_text}' != heading '{heading_text}'")

        nav_ok = re.search(r"</section>\s*<div class=\"chapnav\">.*?</div>\s*</main>", source, re.S)
        if not nav_ok:
            fail(f"{name}: chapnav not between last </section> and </main>")

    index_source, _, _ = check_file("index.html")
    total_qa = sum(s["qa"] for s in all_stats.values())
    tile = dict((l, v) for v, l in re.findall(r"<div><strong>([^<]+)</strong><span>([^<]+)</span></div>", index_source))
    if tile.get("Interview Q&amp;A") != str(total_qa):
        fail(f"index: Q&A tile {tile.get('Interview Q&amp;A')} != total {total_qa}")
    for name, stats in all_stats.items():
        if f"{stats['sections']} sections" not in index_source:
            fail(f"index: section count {stats['sections']} for {name} not shown")

    print()
    for name, stats in all_stats.items():
        print(name, stats)
    print("Total Q&A:", total_qa)
    print("RESULT:", "OK" if not problems else f"{len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
