#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<EOF
Usage: $0 <skill-name> [options]

Install a skill from wp-skills repository or other supported sources.

Arguments:
  skill-name    Name of the skill to install (e.g., warpparse-log-engineering)

Options:
  --codex           Install to Codex CLI (~/.codex/skills/)
  --claude          Install to Claude Code (~/.claude/skills/)
  --all             Install to all available platforms (default)
  --dir <path>      Install to custom directory

Environment:
  WP_SKILLS_REF       Branch or tag to install from (default: main)
  WP_SKILLS_SOURCE    Custom source repo (default: wp-labs/wp-skills)

Examples:
  $0 warpparse-log-engineering
  $0 warpparse-log-engineering --claude
  $0 wpl-rule-check --all
  $0 warpparse-log-engineering --dir ~/my-skills

Supported skill sources:
  - wp-skills repo (default): warpparse-log-engineering, etc.
  - wpl-check repo: wpl-rule-check (auto-detected)
EOF
}

# Parse arguments
skill_name=""
target_dirs=()
install_all=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    --codex)
      target_dirs+=("$HOME/.codex/skills")
      shift
      ;;
    --claude)
      target_dirs+=("$HOME/.claude/skills")
      shift
      ;;
    --all)
      install_all=true
      shift
      ;;
    --dir)
      if [[ -z "${2:-}" ]]; then
        echo "Error: --dir requires a path argument" >&2
        exit 2
      fi
      target_dirs+=("$2")
      shift 2
      ;;
    -*)
      echo "Error: Unknown option $1" >&2
      usage
      exit 2
      ;;
    *)
      if [[ -z "$skill_name" ]]; then
        skill_name="$1"
      else
        echo "Error: Unexpected argument $1" >&2
        usage
        exit 2
      fi
      shift
      ;;
  esac
done

if [[ -z "$skill_name" ]]; then
  usage
  exit 2
fi

# Determine repo root
if [[ -n "${BASH_SOURCE[0]:-}" ]]; then
  repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
else
  repo_root=""
fi
src_dir=""
tmp_dir=""

cleanup() {
  if [[ -n "$tmp_dir" && -d "$tmp_dir" ]]; then
    rm -rf "$tmp_dir"
  fi
}
trap cleanup EXIT

# Auto-detect available platforms if no explicit targets
if [[ ${#target_dirs[@]} -eq 0 ]]; then
  if [[ "$install_all" == "true" ]] || [[ -z "${WP_SKILLS_PLATFORM:-}" ]]; then
    # Install to all available platforms
    [[ -d "$HOME/.codex/skills" ]] && target_dirs+=("$HOME/.codex/skills")
    [[ -d "$HOME/.claude/skills" ]] && target_dirs+=("$HOME/.claude/skills")

    # If no platform directories exist, create default
    if [[ ${#target_dirs[@]} -eq 0 ]]; then
      target_dirs+=("$HOME/.claude/skills")
    fi
  else
    # Respect WP_SKILLS_PLATFORM for backward compatibility
    case "${WP_SKILLS_PLATFORM:-auto}" in
      codex)
        target_dirs+=("$HOME/.codex/skills")
        ;;
      claude-code)
        target_dirs+=("$HOME/.claude/skills")
        ;;
      auto)
        if [[ -d "$HOME/.claude/skills" ]]; then
          target_dirs+=("$HOME/.claude/skills")
        elif [[ -d "$HOME/.codex/skills" ]]; then
          target_dirs+=("$HOME/.codex/skills")
        else
          target_dirs+=("$HOME/.claude/skills")
        fi
        ;;
      *)
        target_dirs+=("$HOME/.claude/skills")
        ;;
    esac
  fi
fi

resolve_local_src() {
  local candidate="$repo_root/skills/$skill_name"
  if [[ -d "$candidate" ]]; then
    src_dir="$candidate"
    return 0
  fi
  return 1
}

resolve_remote_src() {
  local ref="${WP_SKILLS_REF:-main}"
  local source_repo="${WP_SKILLS_SOURCE:-}"
  local skill_subdir="skills/$skill_name"

  # Auto-detect source repo based on skill name
  if [[ -z "$source_repo" ]]; then
    case "$skill_name" in
      wpl-rule-check)
        source_repo="wp-labs/wpl-check"
        skill_subdir="tools/skills/wpl-rule-check"
        ;;
      *)
        source_repo="wp-labs/wp-skills"
        skill_subdir="skills/$skill_name"
        ;;
    esac
  fi

  tmp_dir="$(mktemp -d "${TMPDIR:-/tmp}/wp-skills.XXXXXX")"

  echo "Cloning $source_repo (ref: $ref)..."
  if ! git clone --depth 1 --branch "$ref" "https://github.com/$source_repo.git" "$tmp_dir/repo" 2>/dev/null; then
    if ! git clone --depth 1 "https://github.com/$source_repo.git" "$tmp_dir/repo" 2>/dev/null; then
      echo "Failed to clone $source_repo" >&2
      exit 1
    fi
  fi

  src_dir="$tmp_dir/repo/$skill_subdir"

  if [[ ! -d "$src_dir" ]]; then
    echo "Skill not found: $skill_name" >&2
    echo "Available skills:" >&2
    ls -1 "$tmp_dir/repo/skills/" 2>/dev/null >&2 || ls -1 "$tmp_dir/repo/tools/skills/" 2>/dev/null >&2 || true
    exit 1
  fi
}

# Resolve source
if ! resolve_local_src; then
  echo "Fetching skill from GitHub (ref: ${WP_SKILLS_REF:-main})..."
  resolve_remote_src
fi

# Install to all target directories
echo ""
for target_base in "${target_dirs[@]}"; do
  dst_dir="$target_base/$skill_name"

  mkdir -p "$target_base"
  rm -rf "$dst_dir"
  cp -R "$src_dir" "$dst_dir"

  # Detect platform name for display
  platform="custom"
  case "$target_base" in
    */.codex/skills) platform="codex" ;;
    */.claude/skills) platform="claude-code" ;;
  esac

  echo "Installed: $skill_name"
  echo "Platform:  $platform"
  echo "Location:  $dst_dir"
  echo ""
done

echo "Files installed:"
find "$dst_dir" -type f 2>/dev/null | sed 's|'"$dst_dir"'||' | sed 's|^/|  - |' | head -20
if [[ $(find "$dst_dir" -type f | wc -l) -gt 20 ]]; then
  echo "  ... and more"
fi