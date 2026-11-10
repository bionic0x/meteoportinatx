#!/usr/bin/env bash
# Run LOCALLY after authenticating `gh auth login` (GitHub CLI)
set -euo pipefail
cd "$(dirname "$0")/.."
if ! command -v gh >/dev/null 2>&1; then
  echo "Install GitHub CLI first: https://cli.github.com/" >&2
  exit 1
fi
if ! gh auth status >/dev/null 2>&1; then
  echo "First run: gh auth login" >&2
  exit 1
fi
if ! git rev-parse --git-dir >/dev/null 2>&1; then
  git init -b main
fi
git add .
if ! git diff --cached --quiet; then
  git commit -m 'feat: initial MeteoPortinatx & Pirineo Nowcast 0.3.0 release'
fi
# Private by default: user can change visibility in GitHub settings.
# A repository will only be created when this script is run by its owner.
gh repo create bionic0x/meteoportinatx --private --source . --remote origin --push
