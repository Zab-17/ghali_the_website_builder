import re
import io
import urllib.request
from urllib.parse import urlparse, urlunparse

from agent.browser import new_context, random_delay

try:
    from colorthief import ColorThief
    _HAS_COLORTHIEF = True
except ImportError:
    _HAS_COLORTHIEF = False


def _rgb_to_hex(rgb: tuple) -> str:
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def extract_palette_from_images(image_urls: list, max_images: int = 4) -> dict:
    """Download images and extract a dominant-color palette. Returns hex colors."""
    palette = {"primary": "", "secondary": "", "accent": "", "background": "", "text": ""}
    if not _HAS_COLORTHIEF or not image_urls:
        return palette

    all_colors = []
    for url in image_urls[:max_images]:
        if not url or not url.startswith("http"):
            continue
        try:
            # Facebook lookaside URLs require Googlebot UA to serve images
            ua = (
                "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
                if "facebook.com" in url or "fbsbx.com" in url or "fbcdn" in url
                else "Mozilla/5.0 (compatible; GhaliBot/1.0)"
            )
            req = urllib.request.Request(url, headers={"User-Agent": ua})
            with urllib.request.urlopen(req, timeout=8) as r:
                data = r.read()
            ct = ColorThief(io.BytesIO(data))
            dominant = ct.get_color(quality=5)
            pal = ct.get_palette(color_count=5, quality=5)
            all_colors.append(dominant)
            all_colors.extend(pal)
        except Exception:
            continue

    if not all_colors:
        return palette

    # Dedupe while keeping order
    seen = set()
    uniq = []
    for c in all_colors:
        key = (c[0] // 20, c[1] // 20, c[2] // 20)
        if key not in seen:
            seen.add(key)
            uniq.append(c)

    # Sort by saturation+brightness heuristic to pick vibrant primary
    def score(c):
        r, g, b = c
        mx, mn = max(c), min(c)
        sat = (mx - mn) / mx if mx else 0
        bright = mx / 255
        return sat * 0.7 + bright * 0.3

    vibrant = sorted(uniq, key=score, reverse=True)
    if len(vibrant) >= 1:
        palette["primary"] = _rgb_to_hex(vibrant[0])
    if len(vibrant) >= 2:
        palette["secondary"] = _rgb_to_hex(vibrant[1])
    if len(vibrant) >= 3:
        palette["accent"] = _rgb_to_hex(vibrant[2])

    # Pick darkest for background, lightest for text (or vice versa)
    by_brightness = sorted(uniq, key=lambda c: sum(c))
    palette["background"] = _rgb_to_hex(by_brightness[0])
    palette["text"] = _rgb_to_hex(by_brightness[-1])
    return palette


async def deep_scrape_website(url: str) -> dict:
    """Deep scrape a website for all content, colors, fonts, images, and structure."""
    if not url:
        return {"error": "No URL provided", "content": {}}

    if not url.startswith("http"):
        url = f"https://{url}"

    result = {
        "url": url,
        "title": "",
        "meta_description": "",
        "headings": [],
        "paragraphs": [],
        "services": [],
        "contact_info": {"phone": "", "email": "", "address": ""},
        "hours": "",
        "team_members": [],
        "testimonials": [],
        "image_urls": [],
        "logo_url": "",
        "colors": {"primary": "", "secondary": "", "accent": "", "background": "", "text": ""},
        "fonts": [],
        "error": None,
    }

    async with new_context() as context:
        page = await context.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=20000)
            await random_delay(2, 4)

            # Title and meta
            result["title"] = await page.title() or ""
            meta_desc = await page.query_selector('meta[name="description"]')
            if meta_desc:
                result["meta_description"] = (await meta_desc.get_attribute("content")) or ""

            # Extract all headings
            for tag in ["h1", "h2", "h3"]:
                els = await page.locator(tag).all()
                for el in els[:10]:
                    text = (await el.text_content() or "").strip()
                    if text and len(text) < 200:
                        result["headings"].append({"tag": tag, "text": text})

            # Extract paragraphs
            p_els = await page.locator("p").all()
            for el in p_els[:20]:
                text = (await el.text_content() or "").strip()
                if text and len(text) > 20:
                    result["paragraphs"].append(text)

            # Extract list items (often services)
            li_els = await page.locator("li").all()
            services = []
            for el in li_els[:30]:
                text = (await el.text_content() or "").strip()
                if text and 5 < len(text) < 150:
                    services.append(text)
            result["services"] = services

            # Extract images
            img_els = await page.locator("img[src]").all()
            for el in img_els[:15]:
                src = (await el.get_attribute("src")) or ""
                if src and not src.startswith("data:") and len(src) > 10:
                    if not src.startswith("http"):
                        src = url.rstrip("/") + "/" + src.lstrip("/")
                    result["image_urls"].append(src)

            # Logo detection — img in header or with logo-like attributes
            logo = await page.query_selector('header img, img[class*="logo"], img[alt*="logo"], img[id*="logo"], .logo img')
            if logo:
                logo_src = (await logo.get_attribute("src")) or ""
                if logo_src:
                    if not logo_src.startswith("http"):
                        logo_src = url.rstrip("/") + "/" + logo_src.lstrip("/")
                    result["logo_url"] = logo_src

            # Extract colors from computed styles
            colors = await page.evaluate("""() => {
                const body = document.body;
                const header = document.querySelector('header, nav, .header, .navbar');
                const btn = document.querySelector('button, .btn, a.btn, [class*="button"]');
                const h1 = document.querySelector('h1');

                function getColor(el, prop) {
                    if (!el) return '';
                    return getComputedStyle(el)[prop] || '';
                }

                return {
                    background: getColor(body, 'backgroundColor'),
                    text: getColor(body, 'color'),
                    primary: getColor(header, 'backgroundColor') || getColor(btn, 'backgroundColor'),
                    secondary: getColor(btn, 'backgroundColor') || getColor(header, 'backgroundColor'),
                    accent: getColor(btn, 'color') || getColor(h1, 'color'),
                };
            }""")
            result["colors"] = colors

            # Extract fonts
            fonts = await page.evaluate("""() => {
                const body = getComputedStyle(document.body).fontFamily || '';
                const h1 = document.querySelector('h1');
                const heading = h1 ? getComputedStyle(h1).fontFamily : '';
                return { body: body, heading: heading || body };
            }""")
            result["fonts"] = fonts

            # Contact info extraction
            html = await page.content()
            html_text = await page.text_content("body") or ""

            # Email
            email_match = re.search(r'[\w.+-]+@[\w-]+\.[\w.-]+', html)
            if email_match:
                result["contact_info"]["email"] = email_match.group(0)

            # Phone
            phone_match = re.search(r'(?:\+\d{1,3}[\s-]?)?\(?\d{2,4}\)?[\s.-]?\d{3,4}[\s.-]?\d{3,4}', html_text)
            if phone_match:
                result["contact_info"]["phone"] = phone_match.group(0).strip()

            # Address — look for common patterns
            addr_el = await page.query_selector('[class*="address"], [class*="location"], address')
            if addr_el:
                result["contact_info"]["address"] = ((await addr_el.text_content()) or "").strip()[:200]

            # Operating hours
            hours_el = await page.query_selector('[class*="hour"], [class*="schedule"], [class*="timing"]')
            if hours_el:
                result["hours"] = ((await hours_el.text_content()) or "").strip()[:300]

        except Exception as e:
            result["error"] = f"Scrape failed: {str(e)[:150]}"
        finally:
            await page.close()

    return result


async def deep_scrape_instagram(url: str) -> dict:
    """Deep scrape Instagram profile for bio, posts, images, and brand identity."""
    if not url:
        return {"error": "No URL provided"}

    if not url.startswith("http"):
        url = f"https://www.instagram.com/{url.lstrip('@/')}/"

    result = {
        "url": url,
        "bio": "",
        "profile_image": "",
        "post_count": "",
        "follower_count": "",
        "post_captions": [],
        "post_images": [],
        "error": None,
    }

    async with new_context() as context:
        page = await context.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=20000)
            await random_delay(2, 4)

            content = await page.content()

            if "Sorry, this page" in content or "Page Not Found" in content:
                result["error"] = "Page not found"
                return result

            # Bio text
            bio_el = await page.query_selector('div.-vDIg span, section > main header section > div > span')
            if bio_el:
                result["bio"] = ((await bio_el.text_content()) or "").strip()

            # Fallback bio: look in meta description
            if not result["bio"]:
                meta = await page.query_selector('meta[property="og:description"]')
                if meta:
                    desc = (await meta.get_attribute("content")) or ""
                    result["bio"] = desc.strip()

            # Profile image
            og_img = await page.query_selector('meta[property="og:image"]')
            if og_img:
                result["profile_image"] = (await og_img.get_attribute("content")) or ""

            # Stats from meta or page text
            text = await page.text_content("body") or ""
            followers_match = re.search(r'([\d,.]+[KkMm]?)\s*[Ff]ollowers', text)
            posts_match = re.search(r'([\d,.]+)\s*[Pp]osts', text)
            if followers_match:
                result["follower_count"] = followers_match.group(1)
            if posts_match:
                result["post_count"] = posts_match.group(1)

            # Post images — first 6 visible posts
            post_imgs = await page.locator('article img[src]').all()
            for img in post_imgs[:6]:
                src = (await img.get_attribute("src")) or ""
                if src:
                    result["post_images"].append(src)

            # Post captions from alt text on images
            for img in post_imgs[:6]:
                alt = (await img.get_attribute("alt")) or ""
                if alt and "photo" not in alt.lower()[:20]:
                    result["post_captions"].append(alt[:300])

        except Exception as e:
            result["error"] = f"Scrape failed: {str(e)[:150]}"
        finally:
            await page.close()

    return result


import html as _html
import asyncio as _asyncio

_GOOGLEBOT_UA = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"


def _fetch_fb_html(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": _GOOGLEBOT_UA})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode("utf-8", errors="ignore")


def _unescape(s: str) -> str:
    if not s:
        return ""
    # HTML entities (&#x200f; etc.) — handles unicode correctly in one pass
    return _html.unescape(s).strip()


def _scrape_facebook_sync(url: str) -> dict:
    """Sync scraper using Googlebot UA against www.facebook.com.
    FB serves crawler-friendly SSR HTML with meta tags, photos, and content."""
    if not url.startswith("http"):
        url = f"https://www.facebook.com/{url.lstrip('/')}"
    parsed = urlparse(url)
    slug = parsed.path.strip("/").split("/")[0] if parsed.path else ""
    canon = urlunparse(("https", "www.facebook.com", f"/{slug}", "", "", ""))

    result = {
        "url": url,
        "slug": slug,
        "name": "",
        "about": "",
        "category": "",
        "cover_image": "",
        "profile_image": "",
        "logo_url": "",
        "photo_urls": [],
        "menu_photo_urls": [],
        "contact_info": {"phone": "", "phone2": "", "email": "", "address": "", "website": ""},
        "branches": [],
        "services": [],
        "hours": "",
        "recent_posts": [],
        "palette": {},
        "error": None,
    }

    try:
        raw = _fetch_fb_html(canon)
    except Exception as e:
        result["error"] = f"Fetch failed: {str(e)[:150]}"
        return result

    # ── Meta tags ──
    m = re.search(r'property="og:title"\s+content="([^"]+)"', raw)
    if m:
        result["name"] = _unescape(m.group(1)).split("|")[0].strip()
    m = re.search(r'property="og:description"\s+content="([^"]+)"', raw)
    if m:
        result["about"] = _unescape(m.group(1))[:500]
    m = re.search(r'property="og:image"\s+content="([^"]+)"', raw)
    if m:
        img = _unescape(m.group(1))
        # FB og:image = the page's profile picture = the business's logo
        result["profile_image"] = img
        result["logo_url"] = img
        result["cover_image"] = img

    # ── Category (restaurant, cafe, etc.) ──
    m = re.search(r'"category_name":"([^"]+)"', raw)
    if m:
        result["category"] = _unescape(m.group(1))
    else:
        # Fallback: look for "Restaurant", "Cafe", etc. in og:description or title
        for cat in ["Restaurant", "Cafe", "Café", "Clinic", "Salon", "Gym", "Bakery", "Shop", "Store"]:
            if cat.lower() in (result["about"] + result["name"]).lower():
                result["category"] = cat
                break

    # ── Phones ──
    phones = set()
    for pat in [r'\+?20[\s-]?1\d{9}', r'\b01\d{9}\b', r'\b19\d{3}\b']:
        for p in re.findall(pat, raw):
            phones.add(p)
    phones_list = sorted(phones)
    if phones_list:
        result["contact_info"]["phone"] = phones_list[0]
    if len(phones_list) > 1:
        result["contact_info"]["phone2"] = phones_list[1]

    # ── Email ──
    m = re.search(r'[\w.+-]+@[\w-]+\.(?:com|net|org|io|co)(?:\.[a-z]{2})?', raw)
    if m and "facebook" not in m.group(0):
        result["contact_info"]["email"] = m.group(0)

    # ── External website ──
    m = re.search(r'"website":"(https?:\\?/\\?/[^"]+)"', raw)
    if m:
        site = m.group(1).replace("\\/", "/")
        if "facebook.com" not in site:
            result["contact_info"]["website"] = site

    # ── Address / Branches ──
    # Look for "branch:" patterns (common for multi-location restaurants)
    branch_matches = re.finditer(r'([A-Z][a-zA-Z ]{3,30})\s*branch\s*:?\s*-?\s*([^\n\\]{10,150})', raw)
    _seen_branches = set()
    for bm in branch_matches:
        area = _unescape(bm.group(1)).strip()
        addr = _unescape(bm.group(2)).strip()
        key = (area.lower(), addr[:60].lower())
        if area and addr and key not in _seen_branches and len(result["branches"]) < 5:
            _seen_branches.add(key)
            result["branches"].append({"area": area, "address": addr[:200]})
    if result["branches"]:
        first = result["branches"][0]
        result["contact_info"]["address"] = f"{first['area']}: {first['address']}"

    # Fallback: look for street + city pattern
    if not result["contact_info"]["address"]:
        m = re.search(r'(\d{1,4}[^\n\\]{5,80}(?:Street|St\.|Road|Rd\.)[^\n\\]{0,60}(?:Cairo|Egypt|Nasr City|Heliopolis|Maadi|Zayed)[^\n\\]{0,40})', raw)
        if m:
            result["contact_info"]["address"] = _unescape(m.group(1))[:200]

    # ── Hours ──
    m = re.search(r'(\d{1,2}\s*(?:AM|PM|am|pm)\s*(?:to|-)\s*\d{1,2}\s*(?:AM|PM|am|pm))', raw)
    if m:
        result["hours"] = m.group(1)

    # ── Photos (lookaside URLs) ──
    lookaside = re.findall(r'https://lookaside\.fbsbx\.com/lookaside/crawler/media/\?media_id=\d+', raw)
    seen = set()
    for u in lookaside:
        if u not in seen:
            seen.add(u)
            result["photo_urls"].append(u)

    # Also grab any fbcdn direct image URLs
    fbcdn = re.findall(r'https://[a-z.-]+fbcdn\.net/[^"\s\\]+\.(?:jpg|png|webp)[^"\s\\]*', raw)
    for u in fbcdn:
        if u not in seen and "emoji" not in u and "rsrc" not in u:
            seen.add(u)
            result["photo_urls"].append(u)

    # ── Menu photos — heuristic: first N photos from a restaurant contain menu ──
    # FB doesn't tag menu photos in SSR. We use all photos; Ghali can pick visually.
    if result["category"] and any(k in result["category"].lower() for k in ["restaurant", "cafe", "café", "food"]):
        # Keep first 6 photos as menu candidates
        result["menu_photo_urls"] = result["photo_urls"][:6]

    # ── Recent posts — look for message fields in JSON blobs ──
    post_matches = re.findall(r'"message":\{"text":"([^"]{30,600})"', raw)
    import json as _json
    for pm in post_matches[:8]:
        try:
            txt = _json.loads(f'"{pm}"')
        except Exception:
            txt = _unescape(pm)
        txt = (txt or "").strip()
        if txt and txt not in result["recent_posts"]:
            result["recent_posts"].append(txt)

    # ── Image-derived palette ──
    palette_sources = []
    if result["cover_image"]:
        palette_sources.append(result["cover_image"])
    palette_sources.extend(result["photo_urls"][:4])
    result["palette"] = extract_palette_from_images(palette_sources, max_images=5)

    return result


async def deep_scrape_facebook(url: str) -> dict:
    """Deep scrape a Facebook page using Googlebot UA.

    FB serves crawler-friendly SSR HTML to Googlebot containing real photos,
    phones, addresses, category, and post content. No login wall, no JS.
    Returns: name, about, category, photo_urls, menu_photo_urls, contact_info
    (phone/email/address/website), branches, hours, recent_posts, palette.
    """
    if not url:
        return {"error": "No URL provided"}
    try:
        return await _asyncio.to_thread(_scrape_facebook_sync, url)
    except Exception as e:
        return {"error": f"Scrape failed: {str(e)[:200]}", "url": url}



async def deep_scrape_maps(business_name: str, area: str) -> dict:
    """Deep scrape Google Maps for photos, reviews, hours, and services."""
    search_term = f"{business_name} {area} Egypt"

    result = {
        "name": business_name,
        "photo_urls": [],
        "menu_photo_urls": [],
        "reviews": [],
        "hours": "",
        "services": [],
        "price_level": "",
        "description": "",
        "palette": {},
        "error": None,
    }

    async with new_context() as context:
        page = await context.new_page()
        try:
            url = f"https://www.google.com/maps/search/{search_term.replace(' ', '+')}?hl=en"
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await random_delay(2, 4)

            # Accept cookies
            try:
                btn = page.locator("button:has-text('Accept all')")
                if await btn.count() > 0:
                    await btn.click()
                    await random_delay(1, 2)
            except Exception:
                pass

            # Click first result
            first_link = page.locator('a[href*="/maps/place/"]').first
            if await first_link.count() > 0:
                await first_link.click()
                await random_delay(2, 4)

            # Wait for detail panel
            try:
                await page.wait_for_selector('.DUwDvf, .fontHeadlineLarge', timeout=5000)
            except Exception:
                pass

            # Description / editorial summary
            desc_el = await page.query_selector('.PYvSYb, [class*="editorial"]')
            if desc_el:
                result["description"] = ((await desc_el.text_content()) or "").strip()

            # Hours
            hours_el = await page.query_selector('[data-item-id="oh"], [aria-label*="hour"]')
            if hours_el:
                hours_text = (await hours_el.get_attribute("aria-label")) or (await hours_el.text_content()) or ""
                result["hours"] = hours_text.strip()[:500]

            # Price level
            price_el = await page.query_selector('[aria-label*="Price"]')
            if price_el:
                result["price_level"] = ((await price_el.get_attribute("aria-label")) or "").strip()

            # Photos — click Photos tab and try to separate Menu from general
            photos_tab = page.locator('button[aria-label*="Photos"], button:has-text("Photos")')
            if await photos_tab.count() > 0:
                try:
                    await photos_tab.first.click()
                    await random_delay(2, 3)

                    # Try to click the "Menu" sub-tab inside Photos
                    menu_tab = page.locator('button:has-text("Menu"), div[role="tab"]:has-text("Menu")')
                    menu_seen = set()
                    if await menu_tab.count() > 0:
                        try:
                            await menu_tab.first.click()
                            await random_delay(1, 2)
                            menu_imgs = await page.locator('img[src*="googleusercontent"]').all()
                            for el in menu_imgs[:12]:
                                src = (await el.get_attribute("src")) or ""
                                if src and "w80" not in src and "w40" not in src:
                                    src = re.sub(r'=w\d+-h\d+', '=w1200-h900', src)
                                    if src not in menu_seen:
                                        menu_seen.add(src)
                                        result["menu_photo_urls"].append(src)
                            # Navigate back to All photos
                            all_tab = page.locator('button:has-text("All"), div[role="tab"]:has-text("All")')
                            if await all_tab.count() > 0:
                                await all_tab.first.click()
                                await random_delay(1, 2)
                        except Exception:
                            pass

                    # General photos
                    photo_els = await page.locator('img[src*="googleusercontent"], img[src*="gstatic"]').all()
                    for el in photo_els[:20]:
                        src = (await el.get_attribute("src")) or ""
                        if src and "w80" not in src and "w40" not in src:
                            src = re.sub(r'=w\d+-h\d+', '=w1200-h900', src)
                            if src not in result["photo_urls"] and src not in menu_seen:
                                result["photo_urls"].append(src)
                except Exception:
                    pass

            # Reviews — click Reviews tab
            reviews_tab = page.locator('button[aria-label*="Reviews"], button:has-text("Reviews")')
            if await reviews_tab.count() > 0:
                await reviews_tab.first.click()
                await random_delay(2, 3)

                review_els = await page.locator('.MyEned .wiI7pd').all()
                if not review_els:
                    review_els = await page.locator('[class*="review"] span[class*="text"], .rsqaWe').all()

                for el in review_els[:8]:
                    review_text = ((await el.text_content()) or "").strip()
                    if review_text and len(review_text) > 15:
                        result["reviews"].append(review_text[:400])

            # Services / amenities
            service_els = await page.locator('[data-item-id*="service"], [class*="amenity"], li[class*="service"]').all()
            for el in service_els[:15]:
                text = ((await el.text_content()) or "").strip()
                if text:
                    result["services"].append(text)

        except Exception as e:
            result["error"] = f"Scrape failed: {str(e)[:150]}"
        finally:
            await page.close()

    # Image-derived palette from Maps photos
    palette_sources = list(result["menu_photo_urls"][:2]) + list(result["photo_urls"][:3])
    result["palette"] = extract_palette_from_images(palette_sources, max_images=5)

    return result
