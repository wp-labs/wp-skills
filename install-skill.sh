#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<EOF
Usage: $0 <skill-name> [target-dir]

Install a skill from wp-skills repository or other supported sources.

Arguments:
  skill-name    Name of the skill to install (e.g., warpparse-log-engineering)
  target-dir    Target directory for the skill (default: auto-detect platform)

Environment:
  WP_SKILLS_REF   Branch or tag to install from (default: main)
  WP_SKILLS_PLATFORM  Force platform: codex, claude-code, or auto (default: auto)
  WP_SKILLS_SOURCE   Custom source repo URL (default: wp-labs/wp-skills)

Examples:
  $0 warpparse-log-engineering
  $0 warpparse-log-engineering ~/.claude/skills
  WP_SKILLS_REF=v1.0.0 $0 warpparse-log-engineering

Supported skill sources:
  - wp-skills repo (default): warpparse-log-engineering, etc.
  - wpl-check repo: wpl-rule-check (auto-detected)
EOF
}

if [[ $# -lt 1 ]]; then
  usage
  exit 2
fi

skill_name="$1"
target_override="${2:-}"

# Determine repo root: use BASH_SOURCE if available, otherwise assume remote execution
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

detect_platform() {
  local platform="${WP_SKILLS_PLATFORM:-auto}"

  if [[ "$platform" != "auto" ]]; then
    echo "$platform"
    return
  fi

  # Auto-detect based on existing directories
  if [[ -d "$HOME/.claude/skills" ]]; then
    echo "claude-code"
  elif [[ -d "$HOME/.codex/skills" ]]; then
    echo "codex"
  else
    # Default to claude-code as it's more common
    echo "claude-code"
  fi
}

get_target_dir() {
  if [[ -n "$target_override" ]]; then
    echo "$target_override/$skill_name"
    return
  fi

  local platform
  platform=$(detect_platform)

  case "$platform" in
    codex)
      echo "$HOME/.codex/skills/$skill_name"
      ;;
    claude-code)
      echo "$HOME/.claude/skills/$skill_name"
      ;;
    *)
      echo "$HOME/.claude/skills/$skill_name"
      ;;
  esac
}

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
    # If ref is a commit hash, clone main first then checkout
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

# Main
if ! resolve_local_src; then
  echo "Fetching skill from GitHub (ref: ${WP_SKILLS_REF:-main})..."
  resolve_remote_src
fi

dst_dir=$(get_target_dir)

mkdir -p "$(dirname "$dst_dir")"
rm -rf "$dst_dir"
cp -R "$src_dir" "$dst_dir"

platform=$(detect_platform)
echo ""
echo "Installed: $skill_name"
echo "Platform:  $platform"
echo "Location:  $dst_dir"
echo ""
echo "Files installed:"
find "$dst_dir" -type f | sed 's|'"$dst_dir"'||' | sed 's|^/|  - |'