#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

echo "Npm requirements"
npm install

echo "Build Tailwind"
npx tailwindcss -i css/tailwind.src.css -o css/tailwind.css -m

echo "Complete!!!"
