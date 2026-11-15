"""Generate a lifetime RPG character-sheet GitHub profile header SVG."""

from __future__ import annotations

import base64
import html
import json
import math
import os
import sys
import urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

GRAPHQL_URL = "https://api.github.com/graphql"

PROFILE_QUERY = """
query($login: String!) {
  user(login: $login) {
    login
    name
    createdAt
    avatarUrl(size: 240)
    followers {
      totalCount
    }
    repositories(ownerAffiliations: OWNER, isFork: false, first: 100) {
      totalCount
      nodes {
        stargazerCount
        languages(first: 5, orderBy: {field: SIZE, direction: DESC}) {
          edges {
            size
            node {
              name
            }
          }
        }
      }
    }
  }
}
"""

CONTRIBUTIONS_WINDOW_QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      totalCommitContributions
      totalPullRequestContributions
      totalPullRequestReviewContributions
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
          }
        }
      }
    }
  }
}
"""

LANGUAGE_CLASSES = {
    "JavaScript": "ROGUE",
    "TypeScript": "ROGUE",
    "Python": "MAGE",
    "Go": "WARRIOR",
    "Rust": "WARRIOR",
    "C": "WARRIOR",
    "C++": "WARRIOR",
    "Java": "PALADIN",
    "C#": "PALADIN",
    "Kotlin": "PALADIN",
    "Ruby": "RANGER",
    "PHP": "CLERIC",
    "Swift": "MONK",
    "Dart": "MONK",
    "HTML": "BARD",
    "CSS": "BARD",
    "Shell": "ARTIFICER",
}


def graphql_request(query: str, variables: dict, token: str) -> dict:
    """Execute a GitHub GraphQL request and return the data payload."""
    payload = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    req = urllib.request.Request(
        GRAPHQL_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "github-profile-header-generator",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        body = json.loads(resp.read().decode("utf-8"))

    if "errors" in body:
        raise RuntimeError(f"GitHub GraphQL error: {body['errors']}")
    return body.get("data", {})


def iter_yearly_windows(start: datetime, end: datetime) -> list[tuple[datetime, datetime]]:
    """Split [start, end] into <= 365-day windows required by GitHub's GraphQL API."""
    windows = []
    cursor = start
    while cursor < end:
        window_end = min(cursor + timedelta(days=364), end)
        windows.append((cursor, window_end))
        cursor = window_end + timedelta(seconds=1)
    return windows


def fetch_lifetime_stats(username: str, token: str) -> tuple[dict, dict]:
    """Fetch profile metadata and aggregate lifetime contributions from account creation."""
    profile_data = graphql_request(PROFILE_QUERY, {"login": username}, token)
    user = profile_data.get("user")
    if not user:
        raise RuntimeError(f"GitHub user '{username}' not found")

    created_at = datetime.fromisoformat(user["createdAt"].replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)

    commits = 0
    prs = 0
    reviews = 0
    total_contribs = 0
    daily_counts: dict[str, int] = {}

    for win_start, win_end in iter_yearly_windows(created_at, now):
        data = graphql_request(
            CONTRIBUTIONS_WINDOW_QUERY,
            {
                "login": username,
                "from": win_start.isoformat().replace("+00:00", "Z"),
                "to": win_end.isoformat().replace("+00:00", "Z"),
            },
            token,
        )
        contrib = data["user"]["contributionsCollection"]
        commits += contrib["totalCommitContributions"]
        prs += contrib["totalPullRequestContributions"]
        reviews += contrib["totalPullRequestReviewContributions"]
        total_contribs += contrib["contributionCalendar"]["totalContributions"]
        for week in contrib["contributionCalendar"]["weeks"]:
            for day in week["contributionDays"]:
                date_key = day["date"]
                daily_counts[date_key] = max(daily_counts.get(date_key, 0), day["contributionCount"])

    lifetime = {
        "commits": commits,
        "prs": prs,
        "reviews": reviews,
        "total_contribs": total_contribs,
        "best_streak": compute_best_streak(daily_counts),
    }
    return user, lifetime


def fetch_avatar_data_uri(avatar_url: str) -> str:
    """Download the avatar and return a base64 data URI for GitHub-safe SVG embedding."""
    req = urllib.request.Request(
        avatar_url,
        headers={"User-Agent": "github-profile-header-generator"},
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        content_type = resp.headers.get("Content-Type", "image/png").split(";")[0].strip()
        encoded = base64.b64encode(resp.read()).decode("ascii")
    return f"data:{content_type};base64,{encoded}"


def compute_best_streak(daily_counts: dict[str, int]) -> int:
    """Compute the longest consecutive-day contribution streak across all recorded days."""
    best = 0
    current = 0
    prev_date: datetime | None = None
    for date_str in sorted(daily_counts):
        count = daily_counts[date_str]
        day = datetime.strptime(date_str, "%Y-%m-%d")
        if count > 0:
            if prev_date and (day - prev_date).days == 1:
                current += 1
            else:
                current = 1
            best = max(best, current)
            prev_date = day
        else:
            current = 0
            prev_date = None
    return best


def compute_top_language(repo_nodes: list[dict]) -> str:
    """Return the user's top language by total byte size across owned non-fork repos."""
    totals: Counter[str] = Counter()
    for repo in repo_nodes:
        for edge in repo.get("languages", {}).get("edges", []):
            totals[edge["node"]["name"]] += edge["size"]
    if not totals:
        return "Code"
    return totals.most_common(1)[0][0]


def scale_stat(value: int, max_reference: int) -> int:
    """Scale a raw metric onto a 1..20 RPG attribute range using log compression."""
    if value <= 0:
        return 1
    ratio = math.log1p(value) / math.log1p(max_reference)
    return max(1, min(20, round(ratio * 20)))


def compute_level_and_xp(total_xp: int) -> tuple[int, int, int]:
    """Return (level, xp_into_level, xp_for_next_level) with progressive RPG thresholds."""
    level = 1
    remaining = max(0, total_xp)
    while True:
        needed = 50 + (level - 1) * 15
        if remaining < needed:
            return level, remaining, needed
        remaining -= needed
        level += 1


def render_bar_segments(score: int, x_start: int, y: int) -> str:
    """Render 20 rounded square segments for an RPG attribute bar."""
    segments = []
    for i in range(20):
        fill = "#E52B42" if i < score else "#241D1B"
        x = x_start + i * 16
        segments.append(f'<rect x="{x}" y="{y}" width="12" height="12" rx="2" fill="{fill}"/>')
    return "\n    ".join(segments)


def render_svg(profile: dict, lifetime: dict, avatar_data_uri: str) -> str:
    """Render the lifetime RPG character-sheet SVG with the MENDEX palette."""
    raw_name = (profile.get("name") or profile["login"]).upper()
    name = html.escape(raw_name[:20])

    created_at = datetime.fromisoformat(profile["createdAt"].replace("Z", "+00:00"))
    years_on_github = max(1, (datetime.now(timezone.utc) - created_at).days // 365)

    commits = lifetime["commits"]
    prs = lifetime["prs"]
    reviews = lifetime["reviews"]
    total_contribs = lifetime["total_contribs"]
    best_streak = lifetime["best_streak"]
    followers = profile["followers"]["totalCount"]

    repo_nodes = profile["repositories"]["nodes"]
    stars = sum(n["stargazerCount"] for n in repo_nodes)
    top_lang = compute_top_language(repo_nodes)
    rpg_class = LANGUAGE_CLASSES.get(top_lang, "ADVENTURER")

    total_xp = total_contribs + prs * 5 + reviews * 4 + stars * 10
    level, xp_in_level, xp_needed = compute_level_and_xp(total_xp)
    xp_bar_width = 414
    xp_fill_width = max(8, round((xp_in_level / xp_needed) * xp_bar_width))

    attributes = [
        ("STR", scale_stat(commits, 3000), f"{commits:,} commits"),
        ("DEX", scale_stat(prs, 300), f"{prs:,} pull requests"),
        ("INT", scale_stat(reviews, 200), f"{reviews:,} reviews"),
        ("WIS", min(20, max(1, years_on_github * 3)), f"{years_on_github} years on GitHub"),
        ("CHA", scale_stat(followers, 200), f"{followers:,} followers"),
        ("CON", scale_stat(best_streak, 60), f"{best_streak} day best streak"),
    ]

    attr_rows = []
    for idx, (label, score, caption) in enumerate(attributes):
        y = 58 + idx * 42
        bars = render_bar_segments(score, x_start=384, y=y - 12)
        attr_rows.append(
            f"""  <g>
    <text x="292" y="{y}" fill="#F4EDE4" font-family="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace" font-size="18" font-weight="700">{label}</text>
    <text x="348" y="{y}" fill="#F4EDE4" font-family="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace" font-size="18" font-weight="700">{score}</text>
    {bars}
    <text x="384" y="{y + 15}" fill="#B3A79C" font-family="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace" font-size="11">{html.escape(caption)}</text>
  </g>"""
        )

    attrs_svg = "\n".join(attr_rows)
    top_lang_upper = html.escape(top_lang.upper())
    top_lang_escaped = html.escape(top_lang)

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="740" height="390" viewBox="0 0 740 390" role="img" aria-label="{name} MENDEX RPG GitHub profile">
  <defs>
    <clipPath id="avatar-clip">
      <rect x="34" y="34" width="212" height="212" rx="6"/>
    </clipPath>
  </defs>

  <rect width="740" height="390" rx="12" fill="#120E0E"/>
  <rect x="0.5" y="0.5" width="739" height="389" rx="11.5" fill="none" stroke="#3A302C"/>

  <!-- Avatar hard-shadow + frame -->
  <rect x="34" y="34" width="224" height="224" rx="8" fill="#F2B632"/>
  <rect x="28" y="28" width="224" height="224" rx="8" fill="#1A1514" stroke="#E52B42" stroke-width="2.5"/>
  <rect x="34" y="34" width="212" height="212" rx="6" fill="#F4EDE4"/>
  <image href="{avatar_data_uri}" x="34" y="34" width="212" height="212" clip-path="url(#avatar-clip)" preserveAspectRatio="xMidYMid slice"/>

  <!-- MENDEX Wordmark + Character identity -->
  <text x="28" y="282" fill="#F4EDE4" font-family="ui-sans-serif, system-ui, -apple-system, sans-serif" font-size="13" font-weight="800" letter-spacing="1.5">MENDE<tspan fill="#E52B42">X</tspan></text>
  <text x="28" y="306" fill="#F4EDE4" font-family="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace" font-size="18" font-weight="700" letter-spacing="0.5">{name}</text>
  <text x="28" y="328" fill="#F2B632" font-family="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace" font-size="12" font-weight="700">LEVEL {level} {top_lang_upper} {rpg_class}</text>
  <text x="28" y="346" fill="#B3A79C" font-family="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace" font-size="11">class from top language · {top_lang_escaped}</text>

  <!-- Attributes -->
  <text x="292" y="34" fill="#B3A79C" font-family="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace" font-size="13" font-weight="700" letter-spacing="1">ATTRIBUTES</text>
{attrs_svg}

  <!-- XP bar -->
  <text x="292" y="330" fill="#B3A79C" font-family="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace" font-size="13">XP</text>
  <text x="328" y="330" fill="#F4EDE4" font-family="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace" font-size="14" font-weight="700">LV {level} &gt; {level + 1}</text>
  <text x="706" y="330" text-anchor="end" fill="#B3A79C" font-family="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace" font-size="11">{xp_in_level} / {xp_needed} xp this level</text>
  <rect x="292" y="342" width="{xp_bar_width}" height="12" rx="4" fill="#241D1B"/>
  <rect x="292" y="342" width="{xp_fill_width}" height="12" rx="4" fill="#F2B632"/>
</svg>
"""


def main() -> int:
    username = os.environ.get("GITHUB_USERNAME") or os.environ.get("GITHUB_REPOSITORY_OWNER")
    token = os.environ.get("GITHUB_TOKEN")
    output_path = Path(os.environ.get("OUTPUT_PATH", "header.svg"))

    if not username:
        print("Error: GITHUB_USERNAME or GITHUB_REPOSITORY_OWNER must be set.", file=sys.stderr)
        return 1
    if not token:
        print("Error: GITHUB_TOKEN must be set.", file=sys.stderr)
        return 1

    profile, lifetime = fetch_lifetime_stats(username, token)
    avatar_uri = fetch_avatar_data_uri(profile["avatarUrl"])
    svg = render_svg(profile, lifetime, avatar_uri)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(svg, encoding="utf-8")
    print(f"Generated {output_path} for @{profile['login']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
