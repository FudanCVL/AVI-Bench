#!/bin/bash
# Run AVIBench inference. By default runs all 15 tasks sequentially; can be
# scoped to a subset via the TASKS env var or CLI args.
#
# Each task runs as a separate process for fault isolation.
#
# Usage:
#   bash run_all.sh                                # all tasks (uses default API model)
#   TASKS="ASQA AVC AVR" bash run_all.sh
#   bash run_all.sh ASQA AVC AVR                   # same effect
#
# Override knobs via env var, e.g.:
#   MODEL_PATH=gemini-2.5-flash MODEL_LABEL=gemini-2.5-flash \
#   OPENAI_API_KEY=... OPENAI_BASE_URL=https://your-gateway/v1 \
#   bash run_all.sh
#
# Available tasks:
#   perception : AMIC VMIC AVL AVM
#   understand : VAR AVR AVC
#   reasoning  : AVH VAH AVQA AVLG
#   sensation  : ASQA VSQA_I VSQA_V AVSQA

set -e
cd "$(dirname "$0")"

# ---- Configurable (env-var with defaults) ----
PYTHON="${PYTHON:-python}"
MODEL_PATH="${MODEL_PATH:-gemini-2.5-pro}"
MODEL_LABEL="${MODEL_LABEL:-gemini-2.5-pro}"
DATA_ROOT="${DATA_ROOT:-./data/levels}"
OUTPUT_DIR="${OUTPUT_DIR:-./eval/user_outputs}"
CONCURRENCY="${CONCURRENCY:-1}"
EXTRA_ARGS="${EXTRA_ARGS:-}"

# ---- Task list: CLI args > TASKS env > default 15 tasks ----
ALL_TASKS="ASQA VSQA_I VSQA_V AVSQA AMIC VMIC AVL AVM VAR AVR AVC AVH VAH AVQA AVLG"
if [ $# -gt 0 ]; then
    SELECTED_TASKS="$*"
elif [ -n "${TASKS:-}" ]; then
    SELECTED_TASKS="$TASKS"
else
    SELECTED_TASKS="$ALL_TASKS"
fi

echo "============================================================"
echo "  AVIBench inference"
echo "  CUDA_VISIBLE_DEVICES = $CUDA_VISIBLE_DEVICES"
echo "  PYTHON      = $PYTHON"
echo "  MODEL_PATH  = $MODEL_PATH"
echo "  MODEL_LABEL = $MODEL_LABEL"
echo "  DATA_ROOT   = $DATA_ROOT"
echo "  OUTPUT_DIR  = $OUTPUT_DIR"
echo "  CONCURRENCY = $CONCURRENCY"
echo "  TASKS       = $SELECTED_TASKS"
echo "============================================================"

run_task() {
    echo ""
    echo "============================================================"
    echo ">>> Running task: $1"
    echo "============================================================"
    $PYTHON run.py \
        --model_path "$MODEL_PATH" \
        --model_label "$MODEL_LABEL" \
        --tasks "$1" \
        --data_root "$DATA_ROOT" \
        --output_dir "$OUTPUT_DIR" \
        --concurrency "$CONCURRENCY" \
        $EXTRA_ARGS
}

for t in $SELECTED_TASKS; do
    run_task "$t"
done

echo ""
echo "============================================================"
echo ">>> All requested tasks finished."
echo "============================================================"
