#!/usr/bin/env bash
# Install the pinned toolchain from .tool-versions onto a CI agent (Linux x86_64).
# Idempotent: a tool already on PATH at the pinned version is left alone.
# Usage: tools/ci-install-tools.sh [BIN_DIR]   (default: ~/.local/bin)
# Ported from platform-infra's hardened skeleton (version_ok, SIGPIPE-safe)
# + automation-poc-alert's uv stanza. This repo pins only 3 tools: gitleaks,
# just, uv (Python toolchain via uv — no tofu/conftest/cue/bats here).
#
# SIGPIPE hazard (exit 141) under `set -o pipefail`: early-exit readers like
# `... | grep -q` or `... | head -1` close the pipe while the writer is still
# writing. Version checks therefore capture output with $() (reads to EOF)
# — never head/grep -q.
#
# uv install: UV_INSTALL_DIR pins the binary into the cached BIN_DIR (the
# installer otherwise defaults to ~/.local/bin, escaping the CI cache);
# UV_NO_MODIFY_PATH=1 stops the installer from touching shell rc files on
# the ephemeral CI agent.
set -euo pipefail
cd "$(dirname "$0")/.."

BIN_DIR="${1:-$HOME/.local/bin}"
mkdir -p "$BIN_DIR"
export PATH="$BIN_DIR:$PATH"

ver() { awk -v tool="$1" '$1 == tool {print $2}' .tool-versions; }

# version_ok <needle> <cmd...> — true when the command runs and its full
# output contains <needle>. $() consumes the whole stream: no SIGPIPE.
version_ok() {
  local needle="$1" out
  shift
  out="$("$@" 2>/dev/null || true)"
  [[ "$out" == *"$needle"* ]]
}

GITLEAKS_V="$(ver gitleaks)"
if ! { command -v gitleaks >/dev/null && version_ok "${GITLEAKS_V}" gitleaks version; }; then
  curl -fsSL "https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_V}/gitleaks_${GITLEAKS_V}_linux_x64.tar.gz" \
    | tar -xz -C /tmp gitleaks
  install /tmp/gitleaks "$BIN_DIR/gitleaks"
fi

JUST_V="$(ver just)"
if ! { command -v just >/dev/null && version_ok "${JUST_V}" just --version; }; then
  curl -fsSL "https://github.com/casey/just/releases/download/${JUST_V}/just-${JUST_V}-x86_64-unknown-linux-musl.tar.gz" \
    | tar -xz -C /tmp just
  install /tmp/just "$BIN_DIR/just"
fi

UV_V="$(ver uv)"
if ! { command -v uv >/dev/null && version_ok "${UV_V}" uv --version; }; then
  # The VAR=val prefix only binds to the command it directly precedes; in a
  # pipeline that's `sh` (the reader), not `curl` (the writer) — so the vars
  # go here, not on curl's line.
  curl -LsSf "https://astral.sh/uv/${UV_V}/install.sh" \
    | UV_INSTALL_DIR="$BIN_DIR" UV_NO_MODIFY_PATH=1 sh
fi

echo "toolchain ready in ${BIN_DIR}:"
echo "gitleaks $(gitleaks version)"
just --version
uv --version
