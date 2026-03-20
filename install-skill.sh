#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<EOF
Usage: $0 <skill-name> [target-dir]

Install a skill from wp-skills repository.

Arguments:
  skill-name    Name of the skill to install (e.g., warpparse-log-engineering)
  target-dir    Target directory for the skill (default: auto-detect platform)

Environment:
  WP_SKILLS_REF   Branch or tag to install from (default: main)
  WP_SKILLS_PLATFORM  Force platform: codex, claude-code, or auto (default: auto)

Examples:
  $0 warpparse-log-engineering
  $0 warpparse-log-engineering ~/.claude/skills
  WP_SKILLS_REF=v1.0.0 $0 warpparse-log-engineering
EOF
}

if [[ $# -lt 1 ]]; then
  usage
  exit 2
fi

skill_name="$1"
target_override="${2:-}"
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
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
  local archive_url=""
  local extracted_root=""
  local kind=""

  tmp_dir="$(mktemp -d "${TMPDIR:-/tmp}/wp-skills.XXXXXX")"

  for kind in heads tags; do
    archive_url="https://github.com/wp-labs/wp-skills/archive/refs/${kind}/${ref}.tar.gz"
    if curl -fsSL "$archive_url" | tar -xzf - -C "$tmp_dir" 2>/dev/null; then
      # Find the extracted directory (may have different naming)
      extracted_root=$(find "$tmp_dir" -maxdepth 1 -type d -name "wp-skills*" | head -1)
      if [[ -n "$extracted_root" ]]; then
        break
      fi
    fi
  done

  if [[ -z "$extracted_root" || ! -d "$extracted_root" ]]; then
    echo "Failed to download wp-skills archive for ref: $ref" >&2
    exit 1
  fi

  src_dir="$extracted_root/skills/$skill_name"

  if [[ ! -d "$src_dir" ]]; then
    echo "Skill source not found in downloaded archive: $src_dir" >&2
    echo "Available skills:" >&2
    ls -1 "$extracted_root/skills/" 2>/dev/null >&2 || true
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