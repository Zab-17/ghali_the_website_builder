import os
import json
import re
import hashlib
import urllib.request

import config


_GOOGLEBOT_UA = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
_BROWSER_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"

# URLs that either require Googlebot UA or frequently 403 when embedded
_UA_NEEDED = ("lookaside.fbsbx.com", "fbcdn.net", "cdninstagram.com")


def _pick_ua(url: str) -> str:
    return _GOOGLEBOT_UA if any(d in url for d in _UA_NEEDED) else _BROWSER_UA


def _download_image(url: str, dest_dir: str) -> str | None:
    """Download an image to dest_dir, returning the local filename or None on failure."""
    try:
        ext_match = re.search(r'\.(jpe?g|png|webp|gif)(\?|$)', url, re.IGNORECASE)
        ext = ext_match.group(1).lower() if ext_match else "jpg"
        if ext == "jpeg":
            ext = "jpg"
        # Stable filename from URL hash so re-runs don't duplicate
        h = hashlib.md5(url.encode("utf-8")).hexdigest()[:12]
        filename = f"img_{h}.{ext}"
        filepath = os.path.join(dest_dir, filename)
        if os.path.exists(filepath) and os.path.getsize(filepath) > 1000:
            return filename
        req = urllib.request.Request(url, headers={"User-Agent": _pick_ua(url), "Accept": "image/*,*/*"})
        with urllib.request.urlopen(req, timeout=15) as r:
            data = r.read()
        if len(data) < 500:
            return None
        with open(filepath, "wb") as f:
            f.write(data)
        return filename
    except Exception:
        return None


def _localize_images(html: str, images_dir: str) -> tuple[str, int, int]:
    """Find all remote image URLs in HTML, download them, rewrite src paths.
    Returns (new_html, downloaded_count, failed_count)."""
    # Match src="...", data-*="...", srcset="...", poster="...", and url(...) for image URLs.
    # Covers both extensioned URLs and Facebook lookaside (no extension).
    attr_pattern = re.compile(
        r'((?:src|data-[\w-]+|srcset|poster)\s*=\s*|url\()(["\']?)(https?://[^\s"\')]+?\.(?:jpe?g|png|webp|gif)[^\s"\')]*)\2',
        re.IGNORECASE,
    )
    lookaside_pattern = re.compile(
        r'((?:src|data-[\w-]+|srcset|poster)\s*=\s*|url\()(["\']?)(https?://lookaside\.fbsbx\.com/[^\s"\')]+)\2',
        re.IGNORECASE,
    )
    googleusercontent_pattern = re.compile(
        r'((?:src|data-[\w-]+|srcset|poster)\s*=\s*|url\()(["\']?)(https?://[a-z0-9.-]*googleusercontent\.com/[^\s"\')]+)\2',
        re.IGNORECASE,
    )

    os.makedirs(images_dir, exist_ok=True)
    url_to_local: dict[str, str] = {}
    downloaded, failed = 0, 0

    def _process(match):
        nonlocal downloaded, failed
        attr_or_url = match.group(1)  # e.g. 'src=', 'data-lightbox=', 'url('
        quote = match.group(2)
        url = match.group(3)
        if url in url_to_local:
            local = url_to_local[url]
        else:
            local = _download_image(url, images_dir)
            if local:
                url_to_local[url] = local
                downloaded += 1
            else:
                failed += 1
                return match.group(0)  # leave original
        return f'{attr_or_url}{quote}images/{local}{quote}'

    html = attr_pattern.sub(_process, html)
    html = lookaside_pattern.sub(_process, html)
    html = googleusercontent_pattern.sub(_process, html)
    return html, downloaded, failed


def write_site_files(project_name: str, files: dict[str, str]) -> str:
    """Write generated site files to disk, downloading remote images locally.

    Remote images (especially Facebook lookaside URLs, which require Googlebot UA)
    are downloaded into an `images/` subfolder and the HTML is rewritten to reference
    them as local paths. This prevents broken images in the deployed site.
    """
    project_dir = os.path.join(config.SITES_DIR, project_name)
    os.makedirs(project_dir, exist_ok=True)
    images_dir = os.path.join(project_dir, "images")

    # Pre-process any HTML / CSS file to localize remote images
    processed: dict[str, str] = {}
    total_dl, total_fail = 0, 0
    for filename, content in files.items():
        if filename.lower().endswith((".html", ".htm", ".css")):
            new_content, dl, fail = _localize_images(content, images_dir)
            processed[filename] = new_content
            total_dl += dl
            total_fail += fail
        else:
            processed[filename] = content

    for filename, content in processed.items():
        filepath = os.path.join(project_dir, filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True) if os.path.dirname(filepath) != project_dir else None
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

    if total_dl or total_fail:
        print(f"  [images] downloaded {total_dl}, failed {total_fail} → {images_dir}")

    return project_dir


def read_site_file(project_name: str, filename: str) -> str:
    """Read a generated site file back for editing."""
    filepath = os.path.join(config.SITES_DIR, project_name, filename)
    if not os.path.exists(filepath):
        return f"File not found: {filepath}"
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


def slugify(name: str) -> str:
    """Convert a business name to a URL-safe slug."""
    slug = name.lower().strip()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    return slug.strip('-')[:50]
