#!/usr/bin/env bash
set -u
set -o pipefail

# Run all experiment tests sequentially and capture logs (Bash version)
# Usage: ./run_all_tests.sh

LOG_DIR="logs"
rm -r "$LOG_DIR" 2>/dev/null || true # idempotent cleanup
mkdir -p "$LOG_DIR"
COMBINED="$LOG_DIR/all_tests.log"
CSV="$LOG_DIR/stats.csv"

# Simple CLI: support --dry-run
DRY_RUN=0
while [ "$#" -gt 0 ]; do
  case "$1" in
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --help)
      echo "Usage: $0 [--dry-run]"
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

SCRIPTS=(
  "test_consistency.py"
      "test_partitioning.py"
      "test_availability.py"
)

declare -A EXIT_CODES

THREADS=(1   8  32)
LOCALS=(1   8  32  128)

echo "timestamp,phase,test,thread_count,local_test_count,exit_code,result,reason,logfile" > "$CSV"
echo "=== All runs started at $(date) ===" | tee -a "$COMBINED"

run_and_record() {
  local phase="$1"; shift
  local tcount="$1"; shift
  local lcount="$1"; shift
  local script="$1"; shift

  local name
  name=$(basename "$script" .py)
  local logfile="$LOG_DIR/${name}_t${tcount}_l${lcount}.log"

  if [ "$DRY_RUN" -eq 1 ]; then
    echo "DRY-RUN: would run $script (phase=$phase t=$tcount l=$lcount)" | tee -a "$COMBINED"
    local rc=0
    # write a CSV entry marking this as dry-run
    reason="skipped"
    result="dry-run"
    printf "%s,%s,%s,%s,%s,%s,%s,%s,%s\n" "$(date --rfc-3339=seconds)" "$phase" "$(basename "$script" .py)" "$tcount" "$lcount" "" "$result" "\"$reason\"" "$logfile" >> "$CSV"
    EXIT_CODES["${name}_t${tcount}_l${lcount}"]=$rc
    return 0
  else
    echo "--- Resetting cluster before running $script (t=$tcount l=$lcount) ---" | tee -a "$logfile" "$COMBINED"
    docker compose -f docker-compose.yaml down >> "$logfile" 2>&1 || true
    rm -rf /mnt/redis1/* /mnt/redis2/* /mnt/redis3/* >> "$logfile" 2>&1 || true
    mkdir -p /mnt/redis1 /mnt/redis2 /mnt/redis3 >> "$logfile" 2>&1 || true
    docker compose -f docker-compose.yaml up -d --force-recreate >> "$logfile" 2>&1
    docker cp create_and_test_cluster.sh redis-node-1:/create_cluster.sh >> "$logfile" 2>&1 || true
    docker exec redis-node-1 sh -c "chmod +x /create_cluster.sh && /create_cluster.sh" >> "$logfile" 2>&1 || true

    echo "=== Running: python3 -u $script --thread-count $tcount --local-test-count $lcount at $(date) ===" | tee -a "$logfile" "$COMBINED"
    python3 -u "$script" --thread-count "$tcount" --local-test-count "$lcount" >> "$logfile" 2>&1 || true
    local rc=$?
  fi

  # Determine reason: search for known failure markers
  local reason
  if [ "$rc" -eq 0 ]; then
    reason="ok"
    result="ok"
  else
    result="fail"
    reason=$(grep -m1 -E "No, the cluster|No, the cluster did not|Key:|No, the cluster is not" "$logfile" || true)
    if [ -z "$reason" ]; then
      reason=$(tail -n 20 "$logfile" | tr '\n' ' ' | sed -e 's/"/""/g' -e 's/^\s*//')
    fi
  fi

  # CSV-escape reason
  reason="$(printf "%s" "$reason" | sed 's/"/""/g')"
  printf "%s,%s,%s,%s,%s,%d,%s,%s,%s\n" "$(date --rfc-3339=seconds)" "$phase" "$name" "$tcount" "$lcount" "$rc" "$result" "\"$reason\"" "$logfile" >> "$CSV"

  echo "--- Log from $script (rc=$rc) ---" >> "$COMBINED"
  cat "$logfile" >> "$COMBINED"
  EXIT_CODES["${name}_t${tcount}_l${lcount}"]=$rc
}

# Keep track of which combinations we've already run to avoid duplicates
declare -A SEEN

phase="both_varied"
for t in "${THREADS[@]}"; do
  for l in "${LOCALS[@]}"; do
    key="t${t}_l${l}"
    if [ -z "${SEEN[$key]:-}" ]; then
      for script in "${SCRIPTS[@]}"; do
        run_and_record "$phase" "$t" "$l" "$script"
      done
      SEEN[$key]=1
    fi
  done
done

echo "Summary exit codes:" | tee -a "$COMBINED"
any_failed=0
for k in "${!EXIT_CODES[@]}"; do
  echo "- $k: ${EXIT_CODES[$k]}" | tee -a "$COMBINED"
  if [ "${EXIT_CODES[$k]}" -ne 0 ]; then
    any_failed=1
  fi
done


if [ "$any_failed" -ne 0 ]; then
  echo "One or more tests failed. See $COMBINED and $CSV for details." | tee -a "$COMBINED"
  exit 1
else
  echo "All runs completed successfully. Logs available in $LOG_DIR and stats in $CSV" | tee -a "$COMBINED"
  exit 0
fi

