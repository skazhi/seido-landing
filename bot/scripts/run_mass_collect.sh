#!/bin/bash
# Массовый сбор результатов (на несколько часов).
# Сначала добавляет забеги, затем многократно собирает протоколы.
#
# Без RR/5верст/S95 (рекомендуется):
#   ./run_mass_collect.sh exclude
#
# С RussiaRunning (для 1000+ забегов):
#   ./run_mass_collect.sh full

set -e
cd "$(dirname "$0")/../.."
source .venv/bin/activate

MODE="${1:-exclude}"  # exclude | full
LOOPS="${2:-20}"      # количество прогонов сбора

echo "=== Массовый сбор результатов ==="
echo "Режим: $MODE, прогонов: $LOOPS"
echo ""

# 1. Добавить забеги + первый прогон сбора
echo "Шаг 1: Добавление забегов и первый прогон сбора..."
if [ "$MODE" = "exclude" ]; then
    python -m bot.scripts.discover_and_collect_protocols --skip-rr
else
    python -m bot.scripts.discover_and_collect_protocols
fi
echo ""

# 2. Дополнительные прогоны сбора
REMAINING=$((LOOPS - 1))
if [ "$REMAINING" -gt 0 ]; then
    echo "Шаг 2: Дополнительный сбор ($REMAINING прогонов)..."
    if [ "$MODE" = "exclude" ]; then
        python -m bot.scripts.collect_results --exclude-rr-5verst-s95 \
        --max-races 2000 --runc-limit 200 --raceresult-limit 100 \
        --loop "$REMAINING"
    else
        python -m bot.scripts.collect_results \
            --max-races 2000 --runc-limit 100 --raceresult-limit 100 --rr-limit 100 \
            --loop "$REMAINING"
    fi
else
    echo "Шаг 2: пропуск (достаточно одного прогона)"
fi

echo ""
echo "=== Готово ==="
