#!/bin/bash
# Run 3 Ghali instances in parallel, repeat until no leads remain.
# Usage: nohup bash run_ghali_nonstop.sh &

cd /Users/zeyadkhaled/Desktop/ghali_the_website_builder

BATCH=1
while true; do
    echo ""
    echo "========================================================"
    echo "  BATCH $BATCH — Launching 3 Ghali instances in parallel"
    echo "  $(date)"
    echo "========================================================"

    # Launch 3 instances with --instance labels for dashboard tracking
    python3 -u run_ghali.py 20 --instance A > "logs/ghali_batch${BATCH}_a.log" 2>&1 &
    PID_A=$!
    python3 -u run_ghali.py 20 --instance B > "logs/ghali_batch${BATCH}_b.log" 2>&1 &
    PID_B=$!
    python3 -u run_ghali.py 20 --instance C > "logs/ghali_batch${BATCH}_c.log" 2>&1 &
    PID_C=$!

    echo "  Instance A: PID $PID_A"
    echo "  Instance B: PID $PID_B"
    echo "  Instance C: PID $PID_C"

    # Wait for all 3 to finish
    wait $PID_A $PID_B $PID_C

    # Count how many sites were deployed this batch
    DEPLOYED_A=$(grep -c "DEPLOYED" "logs/ghali_batch${BATCH}_a.log" 2>/dev/null || true)
    DEPLOYED_B=$(grep -c "DEPLOYED" "logs/ghali_batch${BATCH}_b.log" 2>/dev/null || true)
    DEPLOYED_C=$(grep -c "DEPLOYED" "logs/ghali_batch${BATCH}_c.log" 2>/dev/null || true)
    DEPLOYED_A=${DEPLOYED_A:-0}; DEPLOYED_B=${DEPLOYED_B:-0}; DEPLOYED_C=${DEPLOYED_C:-0}
    TOTAL=$((DEPLOYED_A + DEPLOYED_B + DEPLOYED_C))

    echo ""
    echo "  Batch $BATCH done: A=$DEPLOYED_A, B=$DEPLOYED_B, C=$DEPLOYED_C — Total=$TOTAL deploys"
    echo "  $(date)"

    # If all 3 instances deployed 0 sites, the sheet is done
    if [ "$TOTAL" -eq 0 ]; then
        echo ""
        echo "========================================================"
        echo "  SHEET COMPLETE — No more leads to process!"
        echo "  $(date)"
        echo "========================================================"
        break
    fi

    BATCH=$((BATCH + 1))
    echo "  Starting next batch in 10s..."
    sleep 10
done
