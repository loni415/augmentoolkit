#!/bin/bash

# ------------------------------------------------------------
# Augmentoolkit local launcher (HPC-safe, no venv management)
# ASSUMES: vllm environment is already activated
# ------------------------------------------------------------

MODEL_TYPE="normal"
TENSOR_PARALLELISM=1

# ----------------------------
# Argument parsing
# ----------------------------
while [[ $# -gt 0 ]]; do
  case $1 in
    --tensor-parallelism)
      TENSOR_PARALLELISM="$2"
      shift 2
      ;;
    -h|--help)
      echo "Usage: $0 [normal|small|MODEL_PATH] [--tensor-parallelism N]"
      exit 0
      ;;
    *)
      MODEL_TYPE="$1"
      shift
      ;;
  esac
done

echo "Starting Augmentoolkit services"
echo "Model type: $MODEL_TYPE"
echo "Tensor parallelism: $TENSOR_PARALLELISM"

# ----------------------------
# Move to script directory
# ----------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1
echo "Running in directory: $SCRIPT_DIR"

# ----------------------------
# HPC cache redirection
# ----------------------------
export SCRATCH_BASE="/scratch/$USER"

export HF_HOME="$SCRATCH_BASE/hf"
export XDG_CACHE_HOME="$SCRATCH_BASE/.cache"
export TORCH_HOME="$SCRATCH_BASE/torch"
export TORCHINDUCTOR_CACHE_DIR="$SCRATCH_BASE/torch_inductor"
export VLLM_CACHE_DIR="$SCRATCH_BASE/vllm"
export VLLM_TORCH_COMPILE_CACHE_DIR="$SCRATCH_BASE/vllm_torch_compile"

mkdir -p \
  "$HF_HOME" \
  "$XDG_CACHE_HOME" \
  "$TORCH_HOME" \
  "$TORCHINDUCTOR_CACHE_DIR" \
  "$VLLM_CACHE_DIR" \
  "$VLLM_TORCH_COMPILE_CACHE_DIR"

echo "HPC cache locations:"
echo "  HF_HOME = $HF_HOME"
echo "  XDG_CACHE_HOME = $XDG_CACHE_HOME"
echo "  TORCH_HOME = $TORCH_HOME"

# ----------------------------
# Sanity check environment
# ----------------------------
echo "Python in use: $(which python)"
python - <<'PY'
import torch, sys
print("Python:", sys.version.split()[0])
print("Torch:", torch.__version__)
print("CUDA available:", torch.cuda.is_available())
PY

# ----------------------------
# Start Valkey / Redis (if needed)
# ----------------------------
VALKEY_PID=""
if [ -z "$REDIS_HOST" ]; then
  if command -v valkey-server &>/dev/null; then
    echo "Starting valkey-server..."
    valkey-server > helper_process_logs/valkey.log 2>&1 &
    VALKEY_PID=$!
    sleep 3
  fi
fi

# ----------------------------
# Model selection
# ----------------------------
if [ "$MODEL_TYPE" = "normal" ]; then
  MODEL_NAME="Heralax/Augmentoolkit-DataSpecialist-v0.1"
elif [ "$MODEL_TYPE" = "small" ]; then
  MODEL_NAME="Heralax/Augmentoolkit-DataSpecialist-gptqmodel-4bit"
else
  MODEL_NAME="$MODEL_TYPE"
fi

echo "Using model: $MODEL_NAME"

# ----------------------------
# Start vLLM server
# ----------------------------
mkdir -p helper_process_logs
LLAMA_LOG="helper_process_logs/vllm.log"

echo "Starting vLLM server on port 8082..."
vllm serve "$MODEL_NAME" \
  --port 8082 \
  --tensor-parallel-size "$TENSOR_PARALLELISM" \
  --gpu-memory-utilization 0.85 \
  --max-model-len 8192 \
  > "$LLAMA_LOG" 2>&1 &

LLAMA_SERVER_PID=$!
sleep 6

if ! kill -0 $LLAMA_SERVER_PID &>/dev/null; then
  echo "ERROR: vLLM failed to start"
  echo "See $LLAMA_LOG"
  exit 1
fi

echo "vLLM running (PID $LLAMA_SERVER_PID)"

# ----------------------------
# Start Huey worker
# ----------------------------
echo "Starting Huey worker..."
huey_consumer tasks.huey > helper_process_logs/huey.log 2>&1 &
HUEY_PID=$!
sleep 2

# ----------------------------
# Start FastAPI backend
# ----------------------------
echo "Starting FastAPI backend on port 8000..."
python -m uvicorn api:app --host 0.0.0.0 --port 8000 \
  > helper_process_logs/uvicorn.log 2>&1 &
UVICORN_PID=$!
sleep 2

# ----------------------------
# Frontend
# ----------------------------
cd atk-interface || exit 1
npm install
npm run build

npx serve -s dist --listen 5173 > ../helper_process_logs/frontend.log 2>&1 &
SERVE_PID=$!

echo ""
echo "=============================================="
echo "Augmentoolkit is running"
echo "  vLLM API:      http://localhost:8082"
echo "  Backend API:   http://localhost:8000"
echo "  Web UI:        http://localhost:5173"
echo "=============================================="
echo ""
echo "Press Ctrl+C to stop all services."

wait