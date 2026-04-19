#!/bin/bash
# Deploy Candy Smile Center when Vercel rate limit clears
cd /Users/zeyadkhaled/Desktop/ghali_the_website_builder/sites/candy-smile-center
echo "Deploying Candy Smile Center to Vercel..."
vercel deploy --yes --prod 2>&1
echo ""
echo "If successful, run:"
echo "  python3 -c \"from agent.tools.sheets_reader import mark_lead_completed; import asyncio; asyncio.run(mark_lead_completed(140, '<PASTE_URL_HERE>'))\""
