#!/usr/bin/env bash
# rldyour-lsps health check
# Verifies language server commands are available and project prerequisites exist
set -euo pipefail

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m'

missing=0
warnings=0
project_path="${1:-.}"

echo "=== rldyour-lsps health check ==="
echo "Project: $(cd "$project_path" 2>/dev/null && pwd || echo "$project_path")"
echo ""

check_cmd() {
  local name="$1"
  local cmd="$2"
  shift 2
  local desc="$*"

  if command -v "$cmd" >/dev/null 2>&1; then
    printf "  ${GREEN}OK${NC}   %-30s %s\n" "$name" "$(command -v "$cmd")"
  else
    # Check common alternative paths
    local found=false
    for alt in "/opt/homebrew/bin/$cmd" "/usr/local/bin/$cmd"; do
      if [ -x "$alt" ]; then
        printf "  ${GREEN}OK${NC}   %-30s %s\n" "$name" "$alt"
        found=true
        break
      fi
    done
    if [ "$found" = "false" ]; then
      printf "  ${RED}MISS${NC} %-30s %s\n" "$name" "$desc"
      missing=$((missing + 1))
    fi
  fi
}

echo "--- Language servers ---"
check_cmd "pyright" "pyright-langserver" "npm/pipx: pyright"
check_cmd "ruff" "ruff" "pipx/brew: ruff"
check_cmd "typescript" "typescript-language-server" "npm: typescript-language-server"
check_cmd "rust-analyzer" "rust-analyzer" "rustup component: rust-analyzer"
check_cmd "dart" "dart" "Dart SDK 3.9+"
check_cmd "gopls" "gopls" "brew/go: gopls"
check_cmd "clangd" "clangd" "brew: clangd"
check_cmd "yaml-ls" "yaml-language-server" "npm: yaml-language-server"
check_cmd "bash-ls" "bash-language-server" "npm: bash-language-server"
check_cmd "shellcheck" "shellcheck" "brew: shellcheck"
check_cmd "html-ls" "vscode-html-language-server" "npm: vscode-langservers-extracted"
check_cmd "css-ls" "vscode-css-language-server" "npm: vscode-langservers-extracted"
check_cmd "json-ls" "vscode-json-language-server" "npm: vscode-langservers-extracted"
check_cmd "docker-ls" "docker-language-server" "brew: docker-language-server"
check_cmd "taplo" "taplo" "brew/cargo: taplo"
check_cmd "marksman" "marksman" "brew: marksman"

# Conditional: qmlls only if .qml files exist
if find "$project_path" -name "*.qml" -print -quit 2>/dev/null | grep -q .; then
  check_cmd "qmlls" "qmlls" "brew: qtlanguageserver"
fi

echo ""
echo "--- Project prerequisites ---"

check_prereq() {
  local name="$1"
  shift
  for file in "$@"; do
    if [ -f "$project_path/$file" ]; then
      printf "  ${GREEN}OK${NC}   %s\n" "$name ($file)"
      return
    fi
  done
  printf "  ${YELLOW}WARN${NC} %-30s %s\n" "$name" "not found"
  warnings=$((warnings + 1))
}

check_prereq "Python config" "pyproject.toml" "pyrightconfig.json" "setup.py" "setup.cfg"
check_prereq "TypeScript config" "tsconfig.json" "jsconfig.json"
check_prereq "Rust manifest" "Cargo.toml"
check_prereq "Dart manifest" "pubspec.yaml" "analysis_options.yaml"
check_prereq "Go workspace" "go.mod" "go.work"
check_prereq "C/C++ compile DB" "compile_commands.json"
check_prereq "Docker" "Dockerfile" "docker-compose.yml" "docker-compose.yaml" "docker-bake.hcl"

echo ""
if [ "$missing" -eq 0 ] && [ "$warnings" -eq 0 ]; then
  printf "${GREEN}All checks passed.${NC}\n"
  exit 0
elif [ "$missing" -eq 0 ]; then
  printf "${YELLOW}0 missing, %d warnings.${NC}\n" "$warnings"
  exit 0
else
  printf "${RED}%d missing, %d warnings.${NC}\n" "$missing" "$warnings"
  exit 1
fi