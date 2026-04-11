#!/bin/bash
# Rebuild every Ghali site (except Kian) with the skill + fixed localizer.
# Logs to logs/rebuild_<slug>.log per site, and a master rebuild_all.log.

cd "$(dirname "$0")"
mkdir -p logs

MASTER_LOG="logs/rebuild_all.log"
echo "═══════════════════════════════════════════════════════" > "$MASTER_LOG"
echo "  Ghali bulk rebuild started: $(date)" >> "$MASTER_LOG"
echo "═══════════════════════════════════════════════════════" >> "$MASTER_LOG"

# slug → original business name (best-effort title-case)
# These are the sites currently in sites/ minus the Kian variants.
declare -a SITES=(
  "911 Dental Clinic"
  "Air Gym Elite Heliopolis"
  "Angel Beauty Salon Sheikh Zayed"
  "Bells Restaurant Maadi"
  "Calisto Restaurant Cafe"
  "Capelli Hair Salon"
  "Clams and Claws Maadi"
  "Cuts Barber Shop"
  "D Cappuccino Nasr City"
  "Dr Hani Saber Pharmacy"
  "Dr Rania Pharmacy"
  "Edrak Clinics"
  "Elite Gym Heliopolis"
  "Elle Salon Sheikh Zayed"
  "Fitness House"
  "Gastrocare Clinic New Cairo"
  "Golds Gym Heliopolis"
  "Hani Nouh Pharmacy"
  "Health Care City"
  "Hookah Tagamo3"
  "Island Gym"
  "Joes Barber Shop"
  "Klinics Dr Karim Fahmy Dental"
  "Lacasa Barber Shop"
  "Massive Cafe Bakery"
  "Massive Cafe Bakery Nasr City"
  "Mo Bistro"
  "Princess Cafe Restaurant"
  "Reform Dental Center"
  "Revolt Fitness"
  "RX Fitness"
  "Saraya Care Pharmacy"
  "Tetouan Spa New Cairo"
  "The Clinic Healthcare City"
  "The Clinic Medical Center"
  "Twenty Grams Specialty Coffee"
  "Umami"
  "Your Gym Ladies New Cairo"
)

TOTAL=${#SITES[@]}
COUNT=0

for name in "${SITES[@]}"; do
  COUNT=$((COUNT + 1))
  slug=$(echo "$name" | tr '[:upper:]' '[:lower:]' | tr ' ' '_')
  log="logs/rebuild_${slug}.log"

  echo "" >> "$MASTER_LOG"
  echo "[$COUNT/$TOTAL] $(date '+%H:%M:%S') ▶ $name" >> "$MASTER_LOG"

  # Run Ghali for this business — captures stdout+stderr to per-site log
  python3 -u run_ghali.py "$name" > "$log" 2>&1
  exit_code=$?

  if [ $exit_code -eq 0 ]; then
    # Extract the deployed URL from the log if present
    url=$(grep -oE 'https://[a-z0-9-]+\.vercel\.app' "$log" | tail -1)
    echo "[$COUNT/$TOTAL] ✅ DONE  $name  →  $url" >> "$MASTER_LOG"
  else
    echo "[$COUNT/$TOTAL] ❌ FAILED $name  (exit $exit_code, see $log)" >> "$MASTER_LOG"
  fi
done

echo "" >> "$MASTER_LOG"
echo "═══════════════════════════════════════════════════════" >> "$MASTER_LOG"
echo "  Ghali bulk rebuild finished: $(date)" >> "$MASTER_LOG"
echo "═══════════════════════════════════════════════════════" >> "$MASTER_LOG"
