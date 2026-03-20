#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 || $# -gt 2 ]]; then
  echo "Usage: $0 <skill-name> [codex-home]" >&2
  exit 2
fi

skill_name="$1"
codex_home="${2:-$HOME/.codex}"
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
dst_dir="$codex_home/skills/$skill_name"
src_dir=""
tmp_dir=""

cleanup() {
  if [[ -n "$tmp_dir" && -d "$tmp_dir" ]]; then
    rm -rf "$tmp_dir"
  fi
}

trap cleanup EXIT

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
    if curl -fsSL "$archive_url" | tar -xzf - -C "$tmp_dir"; then
      extracted_root="$tmp_dir/wp-skills-$ref"
      break
    fi
  done

  if [[ -z "$extracted_root" || ! -d "$extracted_root" ]]; then
    echo "failed to download wp-skills archive for ref: $ref" >&2
    exit 1
  fi

  src_dir="$extracted_root/skills/$skill_name"

  if [[ ! -d "$src_dir" ]]; then
    echo "skill source not found in downloaded archive: $src_dir" >&2
    exit 1
  fi
}

if ! resolve_local_src; then
  resolve_remote_src
fi

mkdir -p "$(dirname "$dst_dir")"
rm -rf "$dst_dir"
cp -R "$src_dir" "$dst_dir"

echo "installed $skill_name -> $dst_dir"
