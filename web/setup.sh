#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

echo "Build Tailwind CSS (docker)"

docker run --rm \
  --user "$(id -u):$(id -g)" \
  -v "$PWD":/app \
  -w /app \
  node:20-alpine \
  sh -c "npm install && npx tailwindcss -i css/tailwind.src.css -o css/tailwind.css -m"

echo "Complete!!!"
