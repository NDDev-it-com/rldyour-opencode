#!/usr/bin/env bash
# rldyour-lsps install script
# Brew-first LSP dependency installation
set -euo pipefail

echo "=== rldyour-lsps brew-first install ==="
echo ""

if ! command -v brew >/dev/null 2>&1; then
  echo "Error: Homebrew is required. Install from https://brew.sh"
  exit 1
fi

echo "Installing brew-managed packages..."
brew install --quiet \
  go \
  gopls \
  shellcheck \
  vscode-langservers-extracted \
  docker-language-server \
  taplo \
  marksman \
  2>/dev/null || {
    echo "Some packages may already be installed (this is fine)."
  }

# Qt QML support (optional)
if command -v qmlls >/dev/null 2>&1; then
  echo "qmlls already available."
elif brew list qtdeclarative >/dev/null 2>&1; then
  echo "qtdeclarative already installed."
else
  read -p "Install Qt QML support (qtdeclarative, qtlanguageserver)? [y/N] " -n 1 -r
  echo
  if [[ $REPLY =~ ^[Yy]$ ]]; then
    brew install --quiet qtdeclarative qtlanguageserver 2>/dev/null || true
  fi
fi

# npm-based LSPs (managed separately, not via brew)
echo ""
echo "npm-managed LSPs (install manually if needed):"
echo "  npm install -g pyright typescript-language-server yaml-language-server bash-language-server"
echo "  pipx install ruff  # or: pip install ruff"

# Rust analyzer (via rustup if available)
if command -v rustup >/dev/null 2>&1; then
  echo ""
  echo "Installing rust-analyzer via rustup..."
  rustup component add rust-src rust-analyzer 2>/dev/null || true
fi

# Dart SDK check
if command -v dart >/dev/null 2>&1; then
  echo ""
  echo "Dart SDK available: $(dart --version 2>&1 | head -1)"
else
  echo ""
  echo "Note: Dart SDK not found. Install from https://dart.dev/get-dart for Dart/Flutter LSP support."
fi

echo ""
echo "Running health check..."
"$(dirname "$0")/check_lsps.sh"