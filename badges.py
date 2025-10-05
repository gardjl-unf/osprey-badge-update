#!/u/usr/lpp/IBM/cyp/v3r13/pyz/bin/python3
# -*- coding: utf-8 -*-

"""
Update student badge cells in a given directory1.html using Credly JSON.

Usage:
    python update_directory_badges.py students.json /path/to/directory1.html

- students.json: { "Full Name": "https://www.credly.com/users/<slug>", ... }
- Validates that the HTML <title> (stripped) is:
    "Ospreys.biz Student Directory Homepages, Badges, and Certifications"
- Badge images saved to a folder RELATIVE to the HTML file:
    <html_dir>/badges/<vanity_slug>.<ext>
- Each badge links to: https://www.credly.com/badges/{id}
- Replaces the LAST <td> in the row whose FIRST <td> matches the name
"""

import json
import os
import re
import sys
import time
import html
import shutil
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import ssl

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("ERROR: beautifulsoup4 is required. Install with: pip install beautifulsoup4", file=sys.stderr)
    sys.exit(1)

# Build an SSL context that prefers a cert bundle from certifi if available.
# Allow skipping verification for quick testing via BADGES_SKIP_SSL=1 env var.
try:
    if os.environ.get('BADGES_SKIP_SSL', '') == '1':
        SSL_CONTEXT = ssl._create_unverified_context()
    else:
        import certifi
        SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except Exception:
    # Fall back to system defaults if certifi isn't available.
    if os.environ.get('BADGES_SKIP_SSL', '') == '1':
        SSL_CONTEXT = ssl._create_unverified_context()
    else:
        SSL_CONTEXT = ssl.create_default_context()

EXPECTED_TITLE = "Ospreys.biz Student Directory Homepages, Badges, and Certifications"
USER_AGENT     = "Mozilla/5.0 (OspreysBadgeUpdater/1.1)"
MAX_PAGES      = 50
IMG_HEIGHT     = 88

# Optional runtime overrides  edit here when running under JCL/USS
# If STUDENTS_PATH_OVERRIDE is empty, students.json is expected alongside this script.
# If HTML_PATH_OVERRIDE is empty, the script will require the HTML path on the command line.
STUDENTS_PATH_OVERRIDE = ""  # e.g. "/u/s990061/python_scripts/students.json"
HTML_PATH_OVERRIDE = ""      # e.g. "/u/s990061/public_html/directory1.html"

def norm_name(s: str) -> str:
    """Normalize student name for matching (collapse whitespace, casefold)."""
    return re.sub(r"\s+", " ", (s or "").strip()).casefold()

def http_get_json(url: str):
    """GET JSON with UA and simple retry."""
    for attempt in range(3):
        try:
            req = Request(url, headers={"User-Agent": USER_AGENT})
            with urlopen(req, timeout=30, context=SSL_CONTEXT) as resp:
                raw = resp.read().decode("utf-8")
            return json.loads(raw)
        except ssl.SSLError as e:
            # Give a clear hint when SSL verification or CA bundle is the problem
            print(f"SSL error when fetching {url}: {e}", file=sys.stderr)
            print("Hint: install certifi in your Python environment (pip install --user certifi)" , file=sys.stderr)
            raise
        except (HTTPError, URLError, TimeoutError) as e:
            if attempt == 2:
                raise
            time.sleep(0.7 * (attempt + 1))
    return None

def http_get_bytes(url: str):
    """GET bytes with UA and simple retry. Returns (bytes, content_type)."""
    for attempt in range(3):
        try:
            req = Request(url, headers={"User-Agent": USER_AGENT})
            with urlopen(req, timeout=30, context=SSL_CONTEXT) as resp:
                data = resp.read()
                ctype = (resp.headers.get("Content-Type") or "").lower()
            return data, ctype
        except ssl.SSLError as e:
            print(f"SSL error when fetching {url}: {e}", file=sys.stderr)
            print("Hint: install certifi in your Python environment (pip install --user certifi)", file=sys.stderr)
            raise
        except (HTTPError, URLError, TimeoutError) as e:
            if attempt == 2:
                raise
            time.sleep(0.7 * (attempt + 1))
    return b"", ""

def credly_pages(base_profile_url: str):
    """
    Yield all badge objects from https://www.credly.com/users/<slug>/badges.json?page=N
    Accept both list and {data:[...]} shapes.
    """
    base = base_profile_url.rstrip("/") + "/badges.json"
    page = 1
    while page <= MAX_PAGES:
        url = f"{base}?page={page}"
        data = http_get_json(url)
        if data is None:
            break
        if isinstance(data, list):
            badges = data
        else:
            badges = data.get("data") or data.get("badges") or []
        if not badges:
            break
        for b in badges:
            yield b
        page += 1

def normalize_img_url(u: str) -> str:
    """Normalize size segment to 110x110 (if present)."""
    if not u:
        return u
    return re.sub(r"/size/\d+x\d+/", "/size/110x110/", u)

def pick_ext_from(ctype: str, url: str) -> str:
    """Pick a safe image extension based on content-type or URL."""
    if "jpeg" in ctype:
        return ".jpg"
    if "png" in ctype:
        return ".png"
    if "webp" in ctype:
        return ".webp"
    if "gif" in ctype:
        return ".gif"
    ext = os.path.splitext(url.split("?", 1)[0])[1].lower()
    if ext in (".png", ".jpg", ".jpeg", ".webp", ".gif"):
        return ext
    return ".png"

def safe_slug(s: str) -> str:
    """Make a filesystem-safe filename base from vanity_slug."""
    s = (s or "").strip().lower()
    s = re.sub(r"[^a-z0-9._-]+", "_", s)
    return s or "badge"

def collect_badges_for_student(profile_url: str, badge_dir: Path):
    """
    Return list of dicts: { 'link', 'img_rel', 'title' }
      - link   = https://www.credly.com/badges/{id}
      - img_rel: path to image RELATIVE to HTML directory (e.g., 'badges/slug.png')
    """
    out = []
    badge_dir.mkdir(parents=True, exist_ok=True)

    for b in credly_pages(profile_url):
        bid = b.get("id")
        if not bid:
            continue
        link = f"https://www.credly.com/badges/{bid}"

        # image url (prefer per-badge, fallback to template)
        img = b.get("image_url") or (b.get("badge_template") or {}).get("image_url")
        img = normalize_img_url(img)
        if not img:
            continue

        # filename base from vanity_slug
        vanity = (b.get("badge_template") or {}).get("vanity_slug")
        fname_base = safe_slug(vanity) or f"badge_{bid}"

        # download (or refresh if changed)
        data, ctype = http_get_bytes(img)
        ext = pick_ext_from(ctype, img)
        local_path = badge_dir / f"{fname_base}{ext}"
        if not local_path.exists():
            local_path.write_bytes(data)
        else:
            if local_path.read_bytes() != data:
                local_path.write_bytes(data)

        title = b.get("name") or (b.get("badge_template") or {}).get("name") or "Badge"
        out.append({
            "link": link,
            "img_rel": local_path.name,  # relative to badge_dir; caller will prefix
            "title": title,
        })

    return out

def build_badge_block(badges, badge_path_prefix: str):
    """
    Return an HTML <p> with <a><img/></a> items.
    badge_path_prefix is the relative path from the HTML file to the badge folder (e.g., 'badges/')
    """
    cells = []
    for it in badges:
        alt = html.escape(it["title"], quote=True)
        src = f"{badge_path_prefix}{it['img_rel']}"
        # Use percentage height and width to match existing HTML (15%) so
        # inserted images match the page's style and scale with layout.
        cells.append(f'<a href="{it["link"]}"><img src="{src}" alt="{alt}" height="15%" width="15%"></a>')
    return '<p class="badges" align="left">\n  ' + "\n  ".join(cells) + "\n</p>\n"

def update_directory(html_path: Path, students_map: dict, verbose: bool = False):
    """
    For each row in the table:
      - match first <td> (name) to students_map key (case-insensitive, whitespace-collapsed)
      - replace LAST <td> inner HTML with the new badge block for that student
    Badge directory is relative to the HTML location: <html_dir>/badges
    """
    # Validate title before touching file
    soup_for_title = BeautifulSoup(html_path.read_text(encoding="utf-8-sig"), "html.parser")
    page_title = (soup_for_title.title.string if soup_for_title.title else "").strip()
    if page_title != EXPECTED_TITLE:
        raise SystemExit(
            f"Title mismatch for {html_path}.\n"
            f"Found:    '{page_title}'\n"
            f"Expected: '{EXPECTED_TITLE}'\n"
            f"(We compare with .strip(), in case the source has a trailing space.)"
        )

    # Create a timestamped backup directory for this run, so each run's
    # backup is preserved: ./backup/YYYYmmdd_HHMMSS/<original-filename>
    now = time.strftime("%Y%m%d_%H%M%S")
    backup_root = html_path.parent / "backup" / now
    backup_root.mkdir(parents=True, exist_ok=True)
    backup = backup_root / html_path.name
    shutil.copyfile(html_path, backup)

    soup = BeautifulSoup(html_path.read_text(encoding="utf-8-sig"), "html.parser")
    rows = soup.find_all("tr")

    # Resolve relative locations based on HTML file position
    html_dir   = html_path.parent
    badge_dir  = html_dir / "badges"
    # Ensure badges directory exists before any downloads/writes
    badge_dir.mkdir(parents=True, exist_ok=True)
    path_prefix = "badges/"  # src attribute will be relative to the HTML path

    # Normalize student map
    name_to_url_norm = {norm_name(k): v for k, v in students_map.items()}
    updated_count = 0

    for tr in rows:
        tds = tr.find_all("td")
        if len(tds) < 2:
            continue

        # First td is assumed to contain the student's full name
        first_td = tds[0]
        # Extract text from the first <td> and normalize it. The cell may
        # contain extra text (professor notes, titles, etc.). Try exact
        # normalized match first; if that fails, look for the longest
        # students.json key that appears as a substring in the TD text.
        td_text_raw = first_td.get_text(separator=" ", strip=True)
        name_text = norm_name(td_text_raw)
        if not name_text:
            continue

        profile_url = name_to_url_norm.get(name_text)
        substring_used = None
        if not profile_url:
            # Try substring matching: find all student keys that occur in the
            # td_text_raw (normalized), pick the longest one (best specificity)
            candidates = []
            for k_norm, url in name_to_url_norm.items():
                if k_norm in name_text:
                    candidates.append((len(k_norm), k_norm, url))
            if candidates:
                # choose the longest normalized key
                candidates.sort(reverse=True)
                _, chosen_norm, profile_url = candidates[0]
                substring_used = chosen_norm
                print(f"DEBUG: substring match used for '{td_text_raw}' -> '{chosen_norm}'")
        if not profile_url:
            continue  # name not in our JSON; skip

        # Fetch fresh badges for this student
        badges = collect_badges_for_student(profile_url, badge_dir)
        if not badges:
            # No public badges  leave cell unchanged
            continue

        # Build the new badge block HTML
        block_html = build_badge_block(badges, badge_path_prefix=path_prefix)

        # Compare new block with existing LAST <td> contents; only replace if different
        badge_td = tds[-1]
        # Normalize fragments for comparison: collapse whitespace so minor
        # formatting differences won't cause false positives.
        existing_fragment = re.sub(r"\s+", " ", ''.join(str(c) for c in badge_td.contents)).strip()
        new_fragment_soup = BeautifulSoup(block_html, "html.parser")
        new_fragment = re.sub(r"\s+", " ", ''.join(str(c) for c in new_fragment_soup.contents)).strip()

        if verbose:
            # Count fetched vs existing images for diagnostic help
            fetched_count = len(badges)
            existing_imgs = badge_td.find_all('img')
            existing_count = len(existing_imgs)
            print(f"DEBUG: student='{name_text}' fetched={fetched_count} existing={existing_count} ")
            if existing_fragment == new_fragment:
                print("DEBUG: no change (fragments equal)")

        if existing_fragment == new_fragment:
            # No change required
            continue

        # Replace LAST <td> content (Name | middle | Badges)
        badge_td.clear()
        for child in new_fragment_soup.contents:
            badge_td.append(child)

        updated_count += 1

    html_path.write_text(str(soup), encoding="utf-8")
    return updated_count, backup

def main():
    # Support both explicit overrides (useful for JCL) and a sensible
    # relative layout for local testing. Behavior:
    #  - If STUDENTS_PATH_OVERRIDE is set (non-empty), prefer it; otherwise
    #    require students.json next to the script.
    #  - If HTML_PATH_OVERRIDE is set, prefer it; otherwise look for
    #    ../public_html/directory1.html relative to the script dir.
    verbose = False
    script_dir = Path(__file__).parent.resolve()

    # No aliasing logic here — use simple override/relative defaults.

    # Resolve students.json
    if STUDENTS_PATH_OVERRIDE:
        students_json = Path(STUDENTS_PATH_OVERRIDE).expanduser().resolve()
    else:
        students_json = (script_dir / 'students.json').resolve()

    # Resolve html path
    if HTML_PATH_OVERRIDE:
        html_path = Path(HTML_PATH_OVERRIDE).expanduser().resolve()
    else:
        html_path = (script_dir.parent / 'public_html' / 'directory1.html').resolve()

    # (DEBUG prints moved below so they reflect any alias fallbacks)

    # Print final resolved paths for diagnostics
    print(f"DEBUG: final students_json='{students_json}'")
    print(f"DEBUG: final html_path='{html_path}'")

    # students.json is required
    if not students_json.exists():
        print(f"ERROR: students.json not found at '{students_json}' (required next to the script or set STUDENTS_PATH_OVERRIDE)", file=sys.stderr)
        sys.exit(1)

    # Load students
    try:
        students = json.loads(students_json.read_text(encoding='utf-8'))
    except Exception as e:
        print(f"ERROR parsing students.json: {e}", file=sys.stderr)
        sys.exit(1)
    if not isinstance(students, dict):
        print("ERROR: students.json must be an object mapping 'Full Name' -> 'Credly profile URL'", file=sys.stderr)
        sys.exit(1)

    if not html_path.exists():
        print(f"ERROR: HTML file not found at '{html_path}'", file=sys.stderr)
        sys.exit(1)

    updated, backup = update_directory(html_path, students, verbose=verbose)
    print(f"Updated {updated} row(s). Backup saved to: {backup}")

if __name__ == "__main__":
    main()
