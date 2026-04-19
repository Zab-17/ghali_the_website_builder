#!/bin/bash
# Batch deploy all pending sites to Vercel
# Run this once the Vercel daily limit resets (100 deploys/day)

SITES_DIR="/Users/zeyadkhaled/Desktop/ghali_the_website_builder/sites"

PROJECTS=(
  "ahl-alraya-syrian"
  "crimson-bar-grill"
  "pawsitive-vet-clinic"
  "pets-choice-hospital-maadi"
  "harmony-vet-clinic-maadi"
  "go-vet-maadi"
  "euvc-vet-maadi"
  "nile-vet-clinic-maadi"
  "kodak-new-cairo-studio"
  "kodak-the-spot-auc"
  "bali-studios-new-cairo"
  "jannaty-nursery-zayed"
  "cherries-preschool-zayed"
  "cute-kids-academy-zayed"
  "venti-coffee-new-cairo"
  "benzi-car-new-cairo"
  "50-wash-hub-new-cairo"
  "dai-pescatori-maadi"
  "candy-smile-center-heliopolis"
)

echo "Deploying ${#PROJECTS[@]} sites to Vercel..."
echo "============================================"

for project in "${PROJECTS[@]}"; do
  dir="$SITES_DIR/$project"
  if [ -f "$dir/index.html" ]; then
    echo ""
    echo "Deploying: $project"
    cd "$dir"
    url=$(vercel deploy --yes --prod 2>&1 | grep -o 'https://[^ ]*')
    if [ -n "$url" ]; then
      echo "  DEPLOYED: $url"
    else
      echo "  FAILED - check Vercel limits"
      break
    fi
  else
    echo "SKIP: $project (no index.html found)"
  fi
done

echo ""
echo "Done! Run 'python3 -u run_ghali.py' to update the Google Sheet with deployed URLs."
