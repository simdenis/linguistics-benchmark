#!/usr/bin/env bash
set -euo pipefail

# A practical free/open lineup for Apple Silicon (M1 Pro 16GB).
# Change these as you like.
MODELS=(
  "qwen2.5:7b"
  "llama3.1:8b"
  "mistral:7b"
  "phi3:mini"
  "gemma2:9b"
)

for m in "${MODELS[@]}"; do
  echo "Pulling $m"
  ollama pull "$m"
done
