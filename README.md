# Ghali — AI Website Builder Agent

Ghali is one of three AI agents that form an automated web design agency. He takes qualified business leads and builds stunning, production-ready websites — then deploys them to Vercel in minutes.

## How the Agency Works

I built three AI agents that work together as an automated web design agency targeting small businesses in Cairo:

1. **[Hamed](https://github.com/Zab-17/hamed)** — scouts Google Maps for businesses without websites and qualifies them as leads
2. **Ghali** (this repo) — deep-scrapes everything about each business, then generates and deploys a cinematic website
3. **[Ahmed](https://github.com/Zab-17/ahmed_the_messenger)** — pitches the finished website to the business owner via WhatsApp

I monitor all three through a [live dashboard](https://github.com/Zab-17/agents_dashboard) and only step in when a client responds with interest.

## What Ghali Does

For each lead, Ghali:

1. **Scrapes everything** — website, Instagram, Facebook (via mbasic for no login wall), and Google Maps using Playwright
2. **Extracts brand identity** — colors from images (ColorThief), logo, tone of voice, services, menu items, reviews, hours, contact info
3. **Generates a cinematic website** — pure HTML/CSS/JS with 24 design elements: preloader, word-by-word hero animation, parallax, glassmorphism, infinite marquees, stat counters, lightbox gallery, AI chatbot with real business data, and more
4. **Downloads all images locally** — three safety layers ensure zero broken images in production
5. **Deploys to Vercel** — instant live URL, marked in the Google Sheet for Ahmed to pitch

## Architecture

Built on the **Claude Agent SDK** — same pattern as Hamed and Ahmed:

- `agent/orchestrator.py` — Ghali's system prompt and MCP tool definitions
- `agent/tools/brand_scraper.py` — Playwright-based deep scraping (website, IG, FB, Maps)
- `agent/tools/site_generator.py` — file writing with 3-layer image safety (download, scrub, validate)
- `agent/tools/site_deployer.py` — Vercel CLI deployment
- `agent/tools/sheets_reader.py` — Google Sheets integration for lead management
- `agent/tools/seo_auditor.py` — SEO scoring and issue detection
- `config.py` — configuration

## Design Playbook

Every site ships with a cinematic design language inspired by $10k agency work:

- Playfair Display + Inter typography pairing
- Brand colors extracted from the business's actual visual presence
- Word-by-word hero reveal with staggered animations
- Optional Genesis-style inline image carousel hero
- Infinite keyword marquee + gallery marquee strips
- Glassmorphism location cards with Google Maps embeds
- AI chatbot with category-specific knowledge base
- WhatsApp floating button for instant contact
- Full responsive design with hamburger nav on mobile

## Running Ghali

```bash
# Single lead
python3 run_ghali.py

# Batch
python3 run_ghali.py 10

# Specific business
python3 run_ghali.py "Restaurant Name"

# 3 parallel instances until sheet is done
bash run_ghali_nonstop.sh
```

Requires: `ANTHROPIC_API_KEY` in `.env`, Google service account `credentials.json`, Vercel CLI authenticated.

## Built By

Zeyad Khaled — Computer Engineering, American University in Cairo
