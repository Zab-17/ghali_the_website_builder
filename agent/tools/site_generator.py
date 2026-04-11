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


def _detect_image_type(data: bytes) -> str | None:
    """Return canonical image extension for real image bytes, or None if not an image.

    Checks magic bytes — defends against MP4/HTML/etc. being saved as .jpg when the
    source URL is opaque (e.g. Facebook lookaside ?media_id=… returns video files for
    video posts). The Ghali Hijab Boutique incident on 2026-04-10 shipped 6 MP4s
    masquerading as .jpg because the old code only checked size > 500 bytes.
    """
    if len(data) < 12:
        return None
    # JPEG: FF D8 FF
    if data[:3] == b"\xff\xd8\xff":
        return "jpg"
    # PNG: 89 50 4E 47 0D 0A 1A 0A
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    # GIF87a / GIF89a
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    # WebP: RIFF....WEBP
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    # Anything else (MP4 'ftyp', HTML '<', SVG, etc.) — not a raster image we can use
    return None


def _download_image(url: str, dest_dir: str) -> str | None:
    """Download an image to dest_dir, returning the local filename or None on failure.

    Validates that the response body is actually a raster image (JPEG/PNG/GIF/WebP)
    via magic-byte sniffing. Rejects MP4 videos, HTML error pages, and anything else
    that the Facebook/Instagram scrapers sometimes return for image-looking URLs.
    """
    try:
        # Stable filename from URL hash so re-runs don't duplicate
        h = hashlib.md5(url.encode("utf-8")).hexdigest()[:12]

        # If we already have a file for this URL, trust it only if it's still a real image
        for existing_ext in ("jpg", "png", "gif", "webp"):
            existing = os.path.join(dest_dir, f"img_{h}.{existing_ext}")
            if os.path.exists(existing) and os.path.getsize(existing) > 1000:
                with open(existing, "rb") as f:
                    head = f.read(16)
                if _detect_image_type(head) == existing_ext:
                    return f"img_{h}.{existing_ext}"
                # Stale/corrupt (e.g. old MP4 saved as .jpg) — remove and re-download
                os.remove(existing)

        req = urllib.request.Request(url, headers={"User-Agent": _pick_ua(url), "Accept": "image/*,*/*"})
        with urllib.request.urlopen(req, timeout=15) as r:
            content_type = (r.headers.get("Content-Type") or "").lower()
            data = r.read()

        if len(data) < 500:
            return None
        # Hard reject non-image content types (video/*, text/html, etc.)
        if content_type and not content_type.startswith("image/"):
            return None

        real_ext = _detect_image_type(data)
        if real_ext is None:
            return None

        filename = f"img_{h}.{real_ext}"
        filepath = os.path.join(dest_dir, filename)
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


def _scrub_remote_image_refs(html: str, images_dir: str) -> tuple[str, int]:
    """Replace any remaining remote image src/og:image/icon references with a local
    fallback image. Runs after _localize_images — any URL still pointing off-site
    means the download failed, and shipping it would ship a broken image.

    Returns (new_html, scrubbed_count).
    """
    # Pick the first valid local image as fallback
    fallback = None
    if os.path.isdir(images_dir):
        for name in sorted(os.listdir(images_dir)):
            candidate = os.path.join(images_dir, name)
            if not os.path.isfile(candidate):
                continue
            try:
                with open(candidate, "rb") as f:
                    head = f.read(16)
                if _detect_image_type(head):
                    fallback = f"images/{name}"
                    break
            except Exception:
                continue
    if not fallback:
        return html, 0

    scrubbed = 0

    # 1) <img src="https://…"> / <img data-src="…"> — swap src only; leave <meta>/<link> href alone for a dedicated pass
    img_tag_pattern = re.compile(
        r'(<img\b[^>]*?\bsrc\s*=\s*)(["\'])(https?://[^"\']+)\2',
        re.IGNORECASE,
    )

    def _swap_img(m):
        nonlocal scrubbed
        scrubbed += 1
        return f'{m.group(1)}{m.group(2)}{fallback}{m.group(2)}'

    html = img_tag_pattern.sub(_swap_img, html)

    # 2) <meta property="og:image" content="https://…"> — same deal
    meta_og_pattern = re.compile(
        r'(<meta\b[^>]*?\bproperty\s*=\s*["\']og:image["\'][^>]*?\bcontent\s*=\s*)(["\'])(https?://[^"\']+)\2',
        re.IGNORECASE,
    )
    html = meta_og_pattern.sub(_swap_img, html)

    # 3) <link rel="icon" href="https://…">
    link_icon_pattern = re.compile(
        r'(<link\b[^>]*?\brel\s*=\s*["\'][^"\']*icon[^"\']*["\'][^>]*?\bhref\s*=\s*)(["\'])(https?://[^"\']+)\2',
        re.IGNORECASE,
    )
    html = link_icon_pattern.sub(_swap_img, html)

    return html, scrubbed


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

    # Safety net: scrub any surviving http(s) image refs in HTML files
    # (download failures would otherwise ship as broken images)
    total_scrubbed = 0
    for filename in list(processed.keys()):
        if filename.lower().endswith((".html", ".htm")):
            new_content, scrubbed = _scrub_remote_image_refs(processed[filename], images_dir)
            processed[filename] = new_content
            total_scrubbed += scrubbed

    for filename, content in processed.items():
        filepath = os.path.join(project_dir, filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True) if os.path.dirname(filepath) != project_dir else None
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

    if total_dl or total_fail or total_scrubbed:
        print(
            f"  [images] downloaded {total_dl}, failed {total_fail}, "
            f"scrubbed {total_scrubbed} stale remote refs → {images_dir}"
        )

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
