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
