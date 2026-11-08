#!/usr/bin/env bash
# NaukariPro autonomy healthcheck — timers, linger, recent cycles, board_health KPI.
set -euo pipefail
WORKSPACE="${WORKSPACE:-$(cd "$(dirname "$0")/.." && pwd)}"
cd "$WORKSPACE"

echo "=== NaukariPro Autonomy Health ==="
echo "host=$(hostname) time=$(date) sha=$(git rev-parse --short HEAD 2>/dev/null || echo unknown)"
echo
echo "--- linger ---"
loginctl show-user "$(whoami)" -p Linger 2>/dev/null || true
echo
echo "--- timers ---"
systemctl --user list-timers --all --no-pager 2>/dev/null | grep -E 'naukaripro|NEXT' || true
echo
echo "--- unit active ---"
for u in naukaripro-agy.timer naukaripro-ingest.timer naukaripro-label.timer \
         naukaripro-digest.timer naukaripro-learn.timer naukaripro-mutate.timer; do
  printf '%-32s %s\n' "$u" "$(systemctl --user is-active "$u" 2>/dev/null || echo missing)"
done
echo
echo "--- agy service ---"
systemctl --user show naukaripro-agy.service -p ActiveState -p SubState -p MainPID --no-pager 2>/dev/null || true
echo
echo "--- board_health KPI ---"
if [ -x .venv/bin/python ]; then
  .venv/bin/python - <<'PY'
from naukari_pro.aggregation.storage import AggregationStore
s = AggregationStore()
print(s.registry_kpi())
print("healthy_ids", s.healthy_boards()[:12])
PY
fi
echo
echo "--- recent agy history ---"
tail -n 20 logs/agy_schedule_history.log 2>/dev/null || echo "(no history yet)"
echo "=== done ==="
