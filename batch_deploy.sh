#!/bin/bash
# Batch deploy all pending sites to Vercel
# Run this when the Vercel daily deployment limit resets (100/day)
# Usage: bash batch_deploy.sh

SITES_DIR="/Users/zeyadkhaled/Desktop/ghali_the_website_builder/sites"

# List of sites to deploy (project-name : row-index pairs)
declare -A SITES=(
  ["euvc-maadi"]=126
  ["nile-vet-clinic-maadi"]=127
  ["kodak-the-spot-auc"]=130
  ["bali-studios-new-cairo"]=131
  ["jannaty-nursery-zayed"]=132
  ["the-studio-photography"]=150
  ["my-partner-vet-hospital"]=143
  ["ox-egypt"]=148
)

echo "=== Ghali Batch Deploy ==="
echo "Sites to deploy: ${#SITES[@]}"
echo ""

DEPLOYED=0
FAILED=0

for site in "${!SITES[@]}"; do
  row=${SITES[$site]}
  echo "Deploying: $site (row $row)..."

  cd "$SITES_DIR/$site"

  # Deploy to Vercel
  URL=$(vercel deploy --prod --yes 2>&1 | grep -o 'https://[^ ]*')

  if [ -n "$URL" ]; then
    echo "  SUCCESS: $URL"
    ((DEPLOYED++))
  else
    echo "  FAILED - will retry later"
    ((FAILED++))
  fi

  echo ""
done

echo "=== Summary ==="
echo "Deployed: $DEPLOYED"
echo "Failed: $FAILED"
echo ""
echo "After deploying, run Ghali again to mark leads as completed with the URLs."
