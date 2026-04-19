#!/bin/bash
# Auto-retry deploy for jannaty-support-services
# Will attempt every 5 minutes until success

PROJECT_DIR="/Users/zeyadkhaled/Desktop/ghali_the_website_builder/sites/jannaty-support-services"
LOG="/Users/zeyadkhaled/Desktop/ghali_the_website_builder/logs/jannaty_deploy.log"
mkdir -p "$(dirname "$LOG")"

echo "[$(date)] Starting deploy retry loop..." >> "$LOG"

for i in $(seq 1 20); do
    echo "[$(date)] Attempt $i..." >> "$LOG"
    OUTPUT=$(cd "$PROJECT_DIR" && vercel deploy --yes --prod 2>&1)
    echo "$OUTPUT" >> "$LOG"
    
    if echo "$OUTPUT" | grep -q "vercel.app"; then
        URL=$(echo "$OUTPUT" | grep -oE 'https://[a-z0-9-]+\.vercel\.app' | head -1)
        echo "[$(date)] SUCCESS! Deployed at: $URL" >> "$LOG"
        echo "$URL"
        exit 0
    fi
    
    echo "[$(date)] Failed, waiting 5 minutes..." >> "$LOG"
    sleep 300
done

echo "[$(date)] All attempts exhausted." >> "$LOG"
exit 1
