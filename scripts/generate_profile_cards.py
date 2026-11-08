"""Generate self-contained profile SVGs from public GitHub data (stdlib only)."""

import json
import os
from collections import Counter
from datetime import datetime, timezone
from html import escape
from pathlib import Path
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

USERNAME = "CrazyStudent13"
ROOT = Path(__file__).resolve().parents[1]


def get(path):
    headers = {"User-Agent": "CrazyStudent13-profile-cards", "Accept": "application/vnd.github+json"}
    if os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]
    for attempt in range(3):
        try:
            with urlopen(Request("https://api.github.com" + path, headers=headers), timeout=30) as response:
                return json.load(response)
        except (HTTPError, URLError, TimeoutError):
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)


def text(x, y, value, size=14, color="#e4e2e2"):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}">{escape(str(value))}</text>'


def card(title, description, body, footer):
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="480" height="240" viewBox="0 0 480 240" role="img" aria-labelledby="title desc">'
        f'<title id="title">{escape(title)}</title><desc id="desc">{escape(description)}</desc>'
        '<rect x="0.5" y="0.5" width="479" height="239" rx="12" fill="#141321" stroke="#45415c"/>'
        '<g font-family="Segoe UI,Arial,sans-serif">'
        + text(24, 36, title, 20, "#fe428e")
        + body
        + text(24, 222, footer, 11, "#aaa6bc")
        + '</g></svg>\n'
    )


def main():
    user = get(f"/users/{USERNAME}")
    repos = []
    page = 1
    while True:
        batch = get(f"/users/{USERNAME}/repos?type=owner&per_page=100&page={page}")
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    # Public original repositories only; forks would inflate language totals.
    originals = [repo for repo in repos if not repo["fork"] and not repo["private"]]
    languages = Counter()
    for repo in originals:
        languages.update(get(f'/repos/{repo["full_name"]}/languages'))

    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    stats = [
        ("Public repositories", user["public_repos"]),
        ("Stars earned (original repos)", sum(r["stargazers_count"] for r in originals)),
        ("Forks (original repos)", sum(r["forks_count"] for r in originals)),
        ("Followers", user["followers"]),
    ]
    body = ''.join(text(24, 76 + i * 36, label) + text(405, 76 + i * 36, f"{value:,}", 16, "#f8d847") for i, (label, value) in enumerate(stats))
    stats_svg = card(f"{USERNAME}'s GitHub Stats", "; ".join(f"{k}: {v}" for k, v in stats), body, f"Public data | Updated {date} UTC")

    top = languages.most_common(5)
    total = sum(languages.values())
    colors = ["#f1e05a", "#3178c6", "#41b883", "#e34c26", "#a97bff"]
    body = ''
    for i, ((name, count), color) in enumerate(zip(top, colors)):
        y = 67 + i * 29
        share = count / total
        body += text(24, y, name, 12) + text(394, y, f"{share:.1%}", 12)
        body += f'<rect x="24" y="{y + 5}" width="430" height="6" rx="3" fill="#302c44"/>'
        body += f'<rect x="24" y="{y + 5}" width="{430 * share:.2f}" height="6" rx="3" fill="{color}"/>'
    if not top:
        body = text(24, 100, "No public language data yet")
    languages_svg = card("Most Used Languages", "Language share by bytes across public non-fork repositories", body, f"Public non-fork repos | By bytes | {date} UTC")

    # Fetch and validate both cards before replacing either previous snapshot.
    output = ROOT / "profile-stats"
    cards = {"stats.svg": stats_svg, "top-langs.svg": languages_svg}
    for svg in cards.values():
        ET.fromstring(svg)
    output.mkdir(exist_ok=True)
    for name, svg in cards.items():
        temporary = output / (name + ".tmp")
        temporary.write_text(svg, encoding="utf-8")
        temporary.replace(output / name)
    print(f"Generated two cards from {len(originals)} public original repositories.")


if __name__ == "__main__":
    main()
