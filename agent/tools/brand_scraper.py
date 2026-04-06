import re

from agent.browser import new_context, random_delay


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


async def deep_scrape_facebook(url: str) -> dict:
    """Deep scrape Facebook page for about info, posts, and brand content."""
    if not url:
        return {"error": "No URL provided"}

    if not url.startswith("http"):
        url = f"https://www.facebook.com/{url.lstrip('/')}/"

    result = {
        "url": url,
        "about": "",
        "cover_image": "",
        "contact_info": {"phone": "", "email": "", "address": ""},
        "services": [],
        "hours": "",
        "recent_posts": [],
        "error": None,
    }

    async with new_context() as context:
        page = await context.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=20000)
            await random_delay(2, 4)

            # Cover image
            cover = await page.query_selector('img[data-imgperflogname="profileCoverPhoto"], .cover img, img[alt*="cover"]')
            if cover:
                result["cover_image"] = (await cover.get_attribute("src")) or ""

            # About text from meta or page
            og_desc = await page.query_selector('meta[property="og:description"]')
            if og_desc:
                result["about"] = ((await og_desc.get_attribute("content")) or "").strip()

            text = await page.text_content("body") or ""

            # Phone
            phone_match = re.search(r'(?:\+\d{1,3}[\s-]?)?\(?\d{2,4}\)?[\s.-]?\d{3,4}[\s.-]?\d{3,4}', text)
            if phone_match:
                result["contact_info"]["phone"] = phone_match.group(0).strip()

            # Email
            email_match = re.search(r'[\w.+-]+@[\w-]+\.[\w.-]+', text)
            if email_match:
                result["contact_info"]["email"] = email_match.group(0)

            # Recent posts — extract text from post containers
            post_els = await page.locator('[data-ad-preview="message"], [class*="userContent"], div[dir="auto"]').all()
            for el in post_els[:6]:
                post_text = ((await el.text_content()) or "").strip()
                if post_text and 20 < len(post_text) < 500:
                    result["recent_posts"].append(post_text)

            # Hours
            hours_match = re.search(r'(?:hours|open|close|timing)[:\s]*([^\n]{10,100})', text, re.IGNORECASE)
            if hours_match:
                result["hours"] = hours_match.group(1).strip()

        except Exception as e:
            result["error"] = f"Scrape failed: {str(e)[:150]}"
        finally:
            await page.close()

    return result


async def deep_scrape_maps(business_name: str, area: str) -> dict:
    """Deep scrape Google Maps for photos, reviews, hours, and services."""
    search_term = f"{business_name} {area} Egypt"

    result = {
        "name": business_name,
        "photo_urls": [],
        "reviews": [],
        "hours": "",
        "services": [],
        "price_level": "",
        "description": "",
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

            # Photos — click Photos tab if available
            photos_tab = page.locator('button[aria-label*="Photos"], button:has-text("Photos")')
            if await photos_tab.count() > 0:
                await photos_tab.first.click()
                await random_delay(2, 3)

                # Extract photo URLs from the photos grid
                photo_els = await page.locator('img[src*="googleusercontent"], img[src*="gstatic"]').all()
                for el in photo_els[:12]:
                    src = (await el.get_attribute("src")) or ""
                    if src and "w80" not in src and "w40" not in src:
                        # Upgrade to higher resolution
                        src = re.sub(r'=w\d+-h\d+', '=w800-h600', src)
                        result["photo_urls"].append(src)

                # Go back to main listing
                await page.go_back()
                await random_delay(1, 2)

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

    return result
