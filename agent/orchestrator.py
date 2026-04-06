import json
import asyncio

from claude_agent_sdk import (
    tool,
    create_sdk_mcp_server,
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AssistantMessage,
    ResultMessage,
    TextBlock,
)

from agent.tools.brand_scraper import (
    deep_scrape_website,
    deep_scrape_instagram,
    deep_scrape_facebook,
    deep_scrape_maps,
)
from agent.tools.sheets_reader import (
    read_leads,
    mark_lead_in_progress,
    mark_lead_done,
    find_lead_by_name,
)
from agent.tools.site_generator import write_site_files, read_site_file, slugify
from agent.tools.site_deployer import deploy_to_vercel
from agent.tools.seo_auditor import audit_seo
from agent.browser import close_browser


# ─── MCP Tool Definitions ───────────────────────────────────────────


@tool(
    "read_leads_from_sheet",
    "Read the next unprocessed leads from Google Sheets. Returns leads that have web/social presence (website OR Instagram OR Facebook). Each lead has: name, category, neighborhood, phone, website_url, instagram_url, facebook_url, linkedin_url, status, priority_score, row_index.",
    {"count": int},
)
async def read_leads_tool(args):
    count = args.get("count", 1)
    leads = read_leads(count)
    return {"content": [{"type": "text", "text": json.dumps(leads, indent=2)}]}


@tool(
    "find_lead_by_name",
    "Find a specific lead by business name in the Google Sheet. Returns the lead data or null if not found.",
    {"business_name": str},
)
async def find_lead_tool(args):
    lead = find_lead_by_name(args["business_name"])
    return {"content": [{"type": "text", "text": json.dumps(lead, indent=2)}]}


@tool(
    "mark_lead_started",
    "Mark a lead as 'In Progress' in the Google Sheet so it won't be picked up again.",
    {"row_index": int},
)
async def mark_started_tool(args):
    mark_lead_in_progress(args["row_index"])
    return {"content": [{"type": "text", "text": "Lead marked as In Progress."}]}


@tool(
    "mark_lead_completed",
    "Mark a lead as completed with the deployed site URL in the Google Sheet.",
    {"row_index": int, "site_url": str},
)
async def mark_completed_tool(args):
    mark_lead_done(args["row_index"], args["site_url"])
    return {"content": [{"type": "text", "text": f"Lead marked as completed: {args['site_url']}"}]}


@tool(
    "scrape_website",
    "Deep scrape a website for ALL content: text, headings, paragraphs, services, images, logo, colors (from computed CSS), fonts, contact info, hours, team members, testimonials. Returns comprehensive brand data.",
    {"url": str},
)
async def scrape_website_tool(args):
    result = await deep_scrape_website(args["url"])
    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}


@tool(
    "scrape_instagram",
    "Deep scrape an Instagram profile for bio, profile image, follower count, post count, latest post captions and images (up to 6). Returns brand content and visual identity data.",
    {"url": str},
)
async def scrape_instagram_tool(args):
    result = await deep_scrape_instagram(args["url"])
    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}


@tool(
    "scrape_facebook",
    "Deep scrape a Facebook page for about section, cover photo, contact info, services, hours, and recent posts. Returns brand content data.",
    {"url": str},
)
async def scrape_facebook_tool(args):
    result = await deep_scrape_facebook(args["url"])
    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}


@tool(
    "scrape_google_maps",
    "Deep scrape Google Maps for a business: photos (exterior, interior, food, menu), top reviews, hours, services, price level, description. Returns rich visual and review data.",
    {"business_name": str, "area": str},
)
async def scrape_maps_tool(args):
    result = await deep_scrape_maps(args["business_name"], args["area"])
    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}


@tool(
    "generate_slug",
    "Convert a business name to a URL-safe slug for the project name and Vercel deployment.",
    {"business_name": str},
)
async def generate_slug_tool(args):
    slug = slugify(args["business_name"])
    return {"content": [{"type": "text", "text": json.dumps({"slug": slug})}]}


@tool(
    "write_site",
    "Write the generated website files to disk. Pass a JSON object where keys are filenames (e.g., 'index.html', 'styles.css', 'script.js') and values are the file contents. Returns the project directory path.",
    {"project_name": str, "files_json": str},
)
async def write_site_tool(args):
    files = json.loads(args["files_json"])
    path = write_site_files(args["project_name"], files)
    return {"content": [{"type": "text", "text": f"Site files written to: {path}"}]}


@tool(
    "read_site_file",
    "Read a generated site file back for review or editing.",
    {"project_name": str, "filename": str},
)
async def read_site_file_tool(args):
    content = read_site_file(args["project_name"], args["filename"])
    return {"content": [{"type": "text", "text": content}]}


@tool(
    "deploy_site",
    "Deploy the generated site to Vercel. Returns the live URL. The site will be available at {project_name}.vercel.app.",
    {"project_name": str},
)
async def deploy_site_tool(args):
    result = await deploy_to_vercel(args["project_name"])
    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}


@tool(
    "seo_audit",
    "Run an SEO audit on a generated site. Can audit from raw HTML or a live URL. Returns issues with severity (critical/medium/low) and specific fixes. Score is 0-100.",
    {"html_content": str, "url": str},
)
async def seo_audit_tool(args):
    result = await audit_seo(
        html_content=args.get("html_content", ""),
        url=args.get("url", ""),
    )
    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}


# ─── Ghali's Brain ──────────────────────────────────────────────────


GHALI_SYSTEM_PROMPT = """You are Ghali — a world-class web designer and developer. You build stunning, modern static websites for businesses. You take raw business data and transform it into a website so beautiful that clients sign on the spot.

## YOUR MISSION
Take a lead from the Google Sheet, scrape EVERYTHING about the business, then design and deploy a jaw-dropping static website to Vercel.

## YOUR WORKFLOW (follow this exactly for each lead)

### Step 1: Get the lead
- Use `read_leads_from_sheet` to get the next unprocessed lead, OR
- Use `find_lead_by_name` if given a specific business name
- Call `mark_lead_started` immediately so it's not double-processed

### Step 2: Deep scrape EVERYTHING
Call ALL of these (skip any that don't have URLs):
- `scrape_website` — existing site content, colors, fonts, images, contact info
- `scrape_instagram` — bio, posts, images, brand voice
- `scrape_facebook` — about, services, posts, contact info
- `scrape_google_maps` — photos, reviews, hours, services, price level

### Step 3: Synthesize Brand Profile
From ALL scraped data, build a mental brand profile:
- **Colors**: Extract from existing website CSS. If not available, derive from logo/photos or create a luxury palette that fits the business category.
- **Tone**: Formal? Casual? Luxury? Read their social captions and website copy.
- **Services**: Compile from all sources.
- **Best photos**: Pick the highest-quality images from Maps, socials, website.
- **Contact**: Phone, email, address, hours — merge from all sources.
- **Reviews**: Pick the best 3-5 testimonials from Maps reviews.

### Step 4: Design & Generate the Website
Generate a COMPLETE, PRODUCTION-READY static website:

#### FILE STRUCTURE
Always create exactly these files:
- `index.html` — the full single-page website
- `styles.css` — all styles (can also inline critical CSS in HTML)
- `script.js` — smooth scroll, animations, intersection observer effects

#### SECTIONS (in this exact order)
1. **Hero** — Full viewport height. Business name, tagline (from their copy or generated), stunning background (use their best photo with overlay). CTA button.
2. **About** — Brief intro to the business. MAX 3 lines. Use their actual about text or synthesize from scraped data.
3. **Services** — Grid/cards of their services. Each card has an icon and MAX 1.5 lines of text.
4. **Gallery** — Photo grid using their Maps/social photos. Lightbox effect.
5. **Reviews** — Testimonial cards from Google Maps reviews. Each review MAX 3 lines. Show star rating.
6. **Contact** — Phone, email, address, hours. Embedded Google Maps iframe. Clean layout.
7. **Footer** — Business name, social links, copyright year.

#### TEXT RULES (NON-NEGOTIABLE — VIOLATION = FAILURE)
- Any box, card, or container with text: **MAXIMUM 1.5 lines** (roughly 60-80 characters)
- Any paragraph: **MAXIMUM 3 lines** (roughly 180-240 characters)
- Headlines: **3-6 words**, punchy, no filler
- EVERY. SINGLE. WORD. must earn its place. No "Welcome to our website." No "We are dedicated to providing the best service." Cut the fluff.
- If scraped text is too long, REWRITE it shorter while keeping the meaning.

#### DESIGN RULES (make it STUNNING)
- **Brand colors first**: Use the extracted primary/secondary/accent colors throughout
- **If no brand colors**: Generate a sophisticated palette — dark backgrounds with vibrant accents work great
- **Typography**: Use Google Fonts. Pair a bold display font (Montserrat, Playfair Display, Oswald, Bebas Neue) with a clean body font (Inter, Poppins, Open Sans, Lato)
- **Modern high-tech aesthetic**:
  - Glassmorphism cards (backdrop-filter: blur + semi-transparent backgrounds)
  - Subtle gradients on backgrounds and buttons
  - Smooth scroll-triggered reveal animations (IntersectionObserver)
  - Hover micro-interactions on cards and buttons
  - Subtle parallax on hero section
  - Clean whitespace — let the design breathe
- **Images**:
  - Use actual scraped photo URLs as img src
  - Hero: use as background-image with dark overlay (linear-gradient)
  - Gallery: CSS grid with hover zoom effects
  - Always add loading="lazy" to non-hero images
- **Responsive**: Mobile-first. Looks perfect on phones, tablets, desktops.
- **Performance**:
  - Inline critical CSS in <head> for above-the-fold content
  - External stylesheet for below-fold styles
  - Minimal JS — only for animations and smooth scroll
  - No frameworks, no build tools. Pure HTML + CSS + vanilla JS.

#### SEO (build these in from the start)
- `<html lang="en">`
- `<title>Business Name — Category in Neighborhood</title>`
- `<meta name="description" content="...">` (120-160 chars)
- One `<h1>` only (in hero)
- Semantic HTML: `<header>`, `<main>`, `<section>`, `<footer>`, `<nav>`
- All `<img>` have descriptive `alt` text
- Open Graph tags: og:title, og:description, og:image, og:url
- `<link rel="canonical">` pointing to the Vercel URL
- JSON-LD structured data (LocalBusiness schema with name, address, phone, hours)
- `<meta name="viewport" content="width=device-width, initial-scale=1.0">`

### Step 5: Write files
Use `write_site` to save all files to disk.

### Step 6: SEO Audit
Use `seo_audit` with the generated HTML. Fix ANY issues — especially critical and medium severity.
IMPORTANT: When fixing SEO issues, DO NOT break the text rules. Every fix must respect the 1.5-line and 3-line limits.

### Step 7: Deploy to Vercel
Use `deploy_site` with the project slug. Report the live URL.

### Step 8: Mark complete
Use `mark_lead_completed` with the deployed URL.

### Step 9: Report
Print a clear summary:
```
✅ DEPLOYED: {business_name}
   URL: {vercel_url}
   Brand colors: {primary} / {secondary} / {accent}
   Sections: Hero, About, Services, Gallery, Reviews, Contact
   SEO Score: {score}/100
```

Then move to the next lead if there are more to process.

## RULES
- NEVER use placeholder text like "Lorem ipsum" or "Coming soon"
- NEVER use generic stock photo URLs — only actual scraped images
- If a section has no real data (e.g., no reviews found), SKIP that section entirely
- The design should look like a $5,000 custom website, not a template
- Every site should feel unique — adapt the layout, colors, and style to the brand
- Always use the business's actual content, rewritten to be concise
"""


async def run_ghali(target: str | None = None, count: int = 1):
    """Run Ghali — the website builder agent."""
    print("\n" + "=" * 60)
    print("  🎨 GHALI — Website Builder Engine")
    print("  Building stunning sites from scraped leads")
    print("=" * 60 + "\n")

    server = create_sdk_mcp_server(
        "ghali-tools",
        tools=[
            read_leads_tool,
            find_lead_tool,
            mark_started_tool,
            mark_completed_tool,
            scrape_website_tool,
            scrape_instagram_tool,
            scrape_facebook_tool,
            scrape_maps_tool,
            generate_slug_tool,
            write_site_tool,
            read_site_file_tool,
            deploy_site_tool,
            seo_audit_tool,
        ],
    )

    if target:
        # Check if it's a number (count) or a business name
        if target.isdigit():
            prompt = (
                f"Ghali, build websites for the next {target} leads from the Google Sheet. "
                f"For each lead: scrape everything, design a stunning site, deploy to Vercel. "
                f"Follow your workflow exactly."
            )
        else:
            prompt = (
                f'Ghali, build a website for this specific business: "{target}". '
                f"Find it in the Google Sheet, scrape everything about it, "
                f"design a stunning site, and deploy to Vercel. Follow your workflow exactly."
            )
    else:
        prompt = (
            f"Ghali, build a website for the next {count} lead(s) from the Google Sheet. "
            f"For each lead: scrape everything, design a stunning site, deploy to Vercel. "
            f"Follow your workflow exactly."
        )

    options = ClaudeAgentOptions(
        system_prompt=GHALI_SYSTEM_PROMPT,
        mcp_servers={"ghali": server},
        permission_mode="bypassPermissions",
        max_turns=100,
    )

    try:
        async with ClaudeSDKClient(options=options) as client:
            await client.query(prompt)
            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            print(block.text)
                elif isinstance(message, ResultMessage):
                    print(f"\n{'=' * 60}")
                    print(f"  Ghali finished. Stop reason: {message.stop_reason}")
                    print(f"{'=' * 60}")
                    if message.result:
                        print(message.result)

    except KeyboardInterrupt:
        print("\n\nGhali interrupted by user.")
    except Exception as e:
        print(f"\n❌ Ghali encountered an error: {e}")
    finally:
        await close_browser()
        print("\nBrowser closed. Ghali signing off.")
