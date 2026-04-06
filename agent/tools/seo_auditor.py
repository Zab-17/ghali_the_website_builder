import re

from agent.browser import new_context, random_delay


async def audit_seo(html_content: str = "", url: str = "") -> dict:
    """Audit a page for SEO issues.

    Can audit from raw HTML string or by visiting a URL.

    Returns:
        Dict with issues list, score, and recommendations.
    """
    issues = []
    checks = {
        "title": False,
        "meta_description": False,
        "h1": False,
        "h1_single": False,
        "heading_hierarchy": False,
        "img_alt": True,
        "semantic_html": False,
        "og_tags": False,
        "canonical": False,
        "structured_data": False,
        "viewport": False,
        "lang_attr": False,
    }

    html = html_content

    # If URL provided and no HTML, fetch it
    if url and not html:
        async with new_context() as context:
            page = await context.new_page()
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                await random_delay(1, 2)
                html = await page.content()
            except Exception as e:
                return {"error": f"Could not load URL: {str(e)[:100]}", "issues": [], "score": 0}
            finally:
                await page.close()

    if not html:
        return {"error": "No HTML content to audit", "issues": [], "score": 0}

    html_lower = html.lower()

    # Title tag
    title_match = re.search(r'<title[^>]*>([^<]+)</title>', html, re.IGNORECASE)
    if title_match:
        title_text = title_match.group(1).strip()
        checks["title"] = True
        if len(title_text) < 20:
            issues.append({"severity": "medium", "issue": "Title tag is too short (< 20 chars)", "fix": "Make title 50-60 characters with primary keyword"})
        elif len(title_text) > 65:
            issues.append({"severity": "low", "issue": "Title tag is too long (> 65 chars)", "fix": "Trim to 50-60 characters"})
    else:
        issues.append({"severity": "critical", "issue": "Missing <title> tag", "fix": "Add a descriptive title tag with primary keyword"})

    # Meta description
    meta_desc = re.search(r'<meta\s+name=["\']description["\']\s+content=["\']([^"\']*)["\']', html, re.IGNORECASE)
    if not meta_desc:
        meta_desc = re.search(r'<meta\s+content=["\']([^"\']*?)["\']\s+name=["\']description["\']', html, re.IGNORECASE)
    if meta_desc:
        desc = meta_desc.group(1).strip()
        checks["meta_description"] = True
        if len(desc) < 50:
            issues.append({"severity": "medium", "issue": "Meta description too short", "fix": "Write 120-160 character description with keywords"})
        elif len(desc) > 165:
            issues.append({"severity": "low", "issue": "Meta description too long", "fix": "Trim to 120-160 characters"})
    else:
        issues.append({"severity": "critical", "issue": "Missing meta description", "fix": "Add meta description with primary keyword and call to action"})

    # H1 tag
    h1_matches = re.findall(r'<h1[^>]*>.*?</h1>', html, re.IGNORECASE | re.DOTALL)
    if h1_matches:
        checks["h1"] = True
        if len(h1_matches) == 1:
            checks["h1_single"] = True
        else:
            issues.append({"severity": "medium", "issue": f"Multiple H1 tags found ({len(h1_matches)})", "fix": "Use exactly one H1 tag per page"})
    else:
        issues.append({"severity": "critical", "issue": "Missing H1 tag", "fix": "Add one H1 tag with the primary keyword"})

    # Heading hierarchy (h1 before h2 before h3)
    heading_order = re.findall(r'<(h[1-6])', html_lower)
    if heading_order:
        checks["heading_hierarchy"] = all(
            int(heading_order[i][1]) <= int(heading_order[i+1][1]) + 1
            for i in range(len(heading_order) - 1)
        )
        if not checks["heading_hierarchy"]:
            issues.append({"severity": "low", "issue": "Heading hierarchy is not sequential", "fix": "Use headings in order: H1 → H2 → H3"})

    # Image alt tags
    imgs_total = re.findall(r'<img\s[^>]*>', html, re.IGNORECASE)
    imgs_no_alt = [img for img in imgs_total if 'alt=' not in img.lower() or 'alt=""' in img.lower()]
    if imgs_no_alt:
        checks["img_alt"] = False
        issues.append({"severity": "medium", "issue": f"{len(imgs_no_alt)}/{len(imgs_total)} images missing alt text", "fix": "Add descriptive alt text to all images"})

    # Semantic HTML
    semantic_tags = ["<header", "<main", "<footer", "<section", "<nav"]
    found_semantic = sum(1 for tag in semantic_tags if tag in html_lower)
    if found_semantic >= 3:
        checks["semantic_html"] = True
    else:
        issues.append({"severity": "medium", "issue": "Insufficient semantic HTML", "fix": "Use <header>, <main>, <section>, <footer>, <nav>"})

    # Open Graph tags
    og_tags = re.findall(r'<meta\s+property=["\']og:', html, re.IGNORECASE)
    if len(og_tags) >= 3:
        checks["og_tags"] = True
    else:
        issues.append({"severity": "medium", "issue": "Missing or incomplete Open Graph tags", "fix": "Add og:title, og:description, og:image, og:url"})

    # Canonical URL
    if 'rel="canonical"' in html_lower or "rel='canonical'" in html_lower:
        checks["canonical"] = True
    else:
        issues.append({"severity": "low", "issue": "Missing canonical URL", "fix": "Add <link rel=\"canonical\" href=\"...\">"})

    # Structured data (JSON-LD)
    if '"@type"' in html or "'@type'" in html:
        checks["structured_data"] = True
    else:
        issues.append({"severity": "medium", "issue": "No structured data (JSON-LD)", "fix": "Add LocalBusiness schema with name, address, phone, hours"})

    # Viewport meta
    if 'name="viewport"' in html_lower or "name='viewport'" in html_lower:
        checks["viewport"] = True
    else:
        issues.append({"severity": "critical", "issue": "Missing viewport meta tag", "fix": "Add <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">"})

    # Lang attribute
    if 'lang=' in html_lower[:200]:
        checks["lang_attr"] = True
    else:
        issues.append({"severity": "low", "issue": "Missing lang attribute on <html>", "fix": "Add lang=\"en\" to the <html> tag"})

    # Calculate score (0-100)
    passed = sum(1 for v in checks.values() if v)
    total = len(checks)
    score = int((passed / total) * 100)

    return {
        "score": score,
        "checks": checks,
        "issues": issues,
        "critical_count": sum(1 for i in issues if i["severity"] == "critical"),
        "medium_count": sum(1 for i in issues if i["severity"] == "medium"),
        "low_count": sum(1 for i in issues if i["severity"] == "low"),
        "error": None,
    }
