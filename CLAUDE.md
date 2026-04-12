# Ghali — The Website Builder Agent

## What Ghali Does

Ghali takes qualified leads from Hamed's Google Sheet, deep-scrapes everything about each business (website, socials, Maps), then generates a stunning static website and deploys it to Vercel.

### How to run Ghali

When the user says anything like "run ghali", "wake up ghali", "ghali build sites", or any variation — run:

```bash
python3 -u run_ghali.py
```

For specific count:
```bash
python3 -u run_ghali.py 3
```

For a specific business:
```bash
python3 -u run_ghali.py "Restaurant Name"
```

### Key files

- `run_ghali.py` — CLI entry point
- `agent/orchestrator.py` — Ghali's brain (system prompt, MCP tools)
- `agent/tools/brand_scraper.py` — Deep scrape website/IG/FB/Maps
- `agent/tools/sheets_reader.py` — Read leads from Google Sheet
- `agent/tools/site_generator.py` — Write generated site files to disk
- `agent/tools/site_deployer.py` — Deploy to Vercel
- `agent/tools/seo_auditor.py` — SEO audit
- `agent/browser.py` — Playwright browser singleton
- `config.py` — Configuration
- `credentials.json` — Google service account (gitignored)

### Design rules (NON-NEGOTIABLE)

- Box/card text: max 1.5 lines
- Paragraph text: max 3 lines
- Headlines: 3-6 words, punchy
- Always use brand's real colors extracted from their existing presence
- Modern high-tech aesthetic: glassmorphism, gradients, micro-animations
- Pure HTML + CSS + vanilla JS — no frameworks
- SEO audit after every site, fix issues before final deploy

### Required sections by business category

Ahmed (the messenger agent) pitches these exact sections to clients. Ghali MUST build them so the pitch matches the product.

**Gym / Fitness:**
- Subscription packages & pricing tiers
- Trainer bios & certifications
- Class schedule
- Before/after client transformations
- Equipment & facility gallery
- Client reviews

**Restaurant / Cafe (Italian, Seafood, etc.):**
- Full menu with photos & prices
- Ambiance/interior gallery
- Customer reviews
- Location & hours
- Staff/chef intro

**Barber shop / Hair salon / Beauty salon / Spa:**
- Service list with prices
- Before & after photos
- Stylist/barber portfolios
- Client reviews
- Products they use

**Dental clinic / Medical / Veterinary / Optical:**
- Services breakdown
- Doctor credentials & experience
- Before/after cases
- Patient testimonials
- How to reach/contact

**Coffee shop / Bakery / Juice bar:**
- Menu with specialty items
- Ambiance/vibe gallery
- Customer reviews
- Location & hours

**Pet store:**
- Product categories
- Brands they carry
- Services (grooming, etc.)
- Store info & location

**General fallback:**
- Services offered & pricing
- Team/staff intro
- Customer reviews
- Location & hours
- Gallery/photos

### Required on EVERY site (all categories)
- **WhatsApp chat button** — floating button that opens `https://wa.me/<phone>` so visitors can message the business directly. Always visible, bottom-right corner.
- **Contact section** — phone number, address, Google Maps embed, and working hours

### Sheet columns (updated 2026-04-12)

Ghali reads from and writes to these columns:
- Reads: Business Name, Category, Old Website, Instagram, Facebook, LinkedIn (for scraping)
- Writes: **New Website** (the Vercel URL) and **Ready to Contact** ("Yes" when deployed)
- The old "Contacted?" column is now Ahmed's — Ghali does NOT touch it
