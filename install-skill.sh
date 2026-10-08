#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<EOF
Usage: $0 [options] [skill-name]

Install skills from the wp-skills repository into agent skill
directories (Codex, Claude Code, Zed/Agent, or a custom path).

With no skill-name, all available skills are installed.

Arguments:
  skill-name    Optional. Install only this skill (e.g., warpparse-log-engineering).
                Default: install all available skills.

Options:
  --codex           Install to Codex skills (default: ~/.codex/skills; respects CODEX_HOME)
  --claude          Install to Claude Code (~/.claude/skills/)
  --agents          Install to Zed/Agent skills (~/.agents/skills/)
  --all             Install to Codex, Claude Code, and Agents
  --dir <path>      Install to custom directory

Environment:
  WP_SKILLS_REF       Branch or tag to install from (default: main)
  WP_SKILLS_SOURCE    Custom source repo (default: wp-labs/wp-skills)
  CODEX_HOME          Codex home directory (default: ~/.codex)

Examples:
  $0                       # install all skills (auto-detected platforms)
  $0 --agents              # install all skills to Zed/Agent
  $0 warpparse-log-engineering --claude
  $0 wpl-oml-simple --all
  $0 --dir ~/my-skills

Supported skill sources:
  - wp-skills repo (default): wp-deploy, wpl-oml-simple
EOF
}

# Parse arguments
skill_name=""
target_dirs=()
install_all=false
codex_home="${CODEX_HOME:-$HOME/.codex}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    --codex)
      target_dirs+=("$codex_home/skills")
      shift
      ;;
    --claude)
      target_dirs+=("$HOME/.claude/skills")
      shift
      ;;
    --agents)
      target_dirs+=("$HOME/.agents/skills")
      shift
      ;;
    --all)
      install_all=true
      shift
      ;;
    --dir)
      if [[ -z "${2:-}" ]]; then
        echo "Error: --dir requires a non-empty path argument" >&2
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

# A skill name is also used as a destination path component. Reject separators
# and traversal components before resolving sources or removing any destination.
if [[ -n "$skill_name" && ! "$skill_name" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]]; then
  echo "Error: invalid skill name '$skill_name' (use letters, numbers, '.', '_' or '-')" >&2
  exit 2
fi

# Determine repo root
if [[ -n "${BASH_SOURCE[0]:-}" ]]; then
  repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
else
  repo_root=""
fi

tmp_root=""
cleanup() {
  if [[ -n "$tmp_root" && -d "$tmp_root" ]]; then
    rm -rf "$tmp_root"
  fi
}
trap cleanup EXIT

# Determine install targets
if [[ ${#target_dirs[@]} -eq 0 ]]; then
  if [[ "$install_all" == "true" ]]; then
    # --all: publish to every supported platform (directories are created on install)
    target_dirs+=("$codex_home/skills" "$HOME/.claude/skills" "$HOME/.agents/skills")
  elif [[ -z "${WP_SKILLS_PLATFORM:-}" ]]; then
    # No explicit target: install to every platform with an existing skills directory
    [[ -d "$codex_home/skills" ]] && target_dirs+=("$codex_home/skills")
    [[ -d "$HOME/.claude/skills" ]] && target_dirs+=("$HOME/.claude/skills")
    [[ -d "$HOME/.agents/skills" ]] && target_dirs+=("$HOME/.agents/skills")

    # If no platform directories exist, create default
    if [[ ${#target_dirs[@]} -eq 0 ]]; then
      target_dirs+=("$HOME/.claude/skills")
    fi
  else
    # Respect WP_SKILLS_PLATFORM for backward compatibility
    case "${WP_SKILLS_PLATFORM:-auto}" in
      codex)
        target_dirs+=("$codex_home/skills")
        ;;
      claude-code)
        target_dirs+=("$HOME/.claude/skills")
        ;;
      agents)
        target_dirs+=("$HOME/.agents/skills")
        ;;
      auto)
        if [[ -d "$HOME/.claude/skills" ]]; then
          target_dirs+=("$HOME/.claude/skills")
        elif [[ -d "$codex_home/skills" ]]; then
          target_dirs+=("$codex_home/skills")
        elif [[ -d "$HOME/.agents/skills" ]]; then
          target_dirs+=("$HOME/.agents/skills")
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

# --- Resolve skill sources -------------------------------------------------

clone_repo() {
  # $1 = repo (org/name). Clones once into $tmp_root/repos and echoes the path.
  local repo="$1"
  local cache_dir="$tmp_root/repos"
  local out="$cache_dir/$(printf '%s' "$repo" | tr '/' '_')"

  if [[ ! -d "$out/.git" ]]; then
    mkdir -p "$cache_dir"
    rm -rf "$out"
    echo "Cloning $repo (ref: ${WP_SKILLS_REF:-main})..."
    if ! git clone --depth 1 --branch "${WP_SKILLS_REF:-main}" "https://github.com/$repo.git" "$out" 2>/dev/null; then
      if ! git clone --depth 1 "https://github.com/$repo.git" "$out" 2>/dev/null; then
        echo "Failed to clone $repo" >&2
        exit 1
      fi
    fi
  fi
  echo "$out"
}

# Resolve a single skill name -> src_dir (local repo first, then remote).
resolve_local_src() {
  local candidate="$repo_root/skills/$1"
  if [[ -d "$candidate" ]]; then
    src_dir="$candidate"
    return 0
  fi
  return 1
}

resolve_remote_src() {
  local name="$1"
  local source_repo="${WP_SKILLS_SOURCE:-}"
  local skill_subdir="skills/$name"

  # Skills published by this repository use the same remote source.
  if [[ -z "$source_repo" ]]; then
    source_repo="wp-labs/wp-skills"
  fi

  if [[ -z "$tmp_root" ]]; then
    tmp_root="$(mktemp -d "${TMPDIR:-/tmp}/wp-skills.XXXXXX")"
  fi

  local clone_dir
  clone_dir="$(clone_repo "$source_repo")"
  src_dir="$clone_dir/$skill_subdir"

  if [[ ! -d "$src_dir" ]]; then
    echo "Skill not found: $name" >&2
    echo "Available skills:" >&2
    ls -1 "$clone_dir/skills/" 2>/dev/null >&2 || ls -1 "$clone_dir/tools/skills/" 2>/dev/null >&2 || true
    exit 1
  fi
}

in_list() {
  local needle="$1"
  shift
  local item
  for item in "$@"; do
    [[ "$item" == "$needle" ]] && return 0
  done
  return 1
}

# Collect the list of skills to install.
# names[i] paired with srcs[i] (resolved source directory).
names=()
srcs=()

collect_local_skills() {
  # Enumerate all skills shipped in the local checkout.
  local d
  for d in "$repo_root"/skills/*/; do
    [[ -f "$d/SKILL.md" ]] || continue
    local name
    name="$(basename "$d")"
    # Guard: expanding an empty array under `set -u` fails on bash 3.2 (macOS)
    if [[ ${#names[@]} -gt 0 ]] && in_list "$name" "${names[@]}"; then
      continue
    fi
    names+=("$name")
    srcs+=("$d")
  done
}

collect_remote_dir_skills() {
  # Enumerate skills under a cloned repo subdirectory, e.g. skills/ or tools/skills/.
  local repo="$1"
  local subdir="$2"
  local clone_dir
  clone_dir="$(clone_repo "$repo")"

  local d
  for d in "$clone_dir/$subdir"/*/; do
    [[ -d "$d" && -f "$d/SKILL.md" ]] || continue
    local name
    name="$(basename "$d")"
    # Guard: expanding an empty array under `set -u` fails on bash 3.2 (macOS)
    if [[ ${#names[@]} -gt 0 ]] && in_list "$name" "${names[@]}"; then
      continue
    fi
    names+=("$name")
    srcs+=("$d")
  done
}

if [[ -n "$skill_name" ]]; then
  # Install a single skill
  if ! resolve_local_src "$skill_name"; then
    echo "Fetching skill from GitHub (ref: ${WP_SKILLS_REF:-main})..."
    resolve_remote_src "$skill_name"
  fi
  names+=("$skill_name")
  srcs+=("$src_dir")
else
  # Install all available skills
  if [[ -d "$repo_root/skills" ]]; then
    collect_local_skills
  fi
  if [[ ${#names[@]} -eq 0 ]]; then
    # No local checkout: enumerate from the remote repos
    if [[ -z "$tmp_root" ]]; then
      tmp_root="$(mktemp -d "${TMPDIR:-/tmp}/wp-skills.XXXXXX")"
    fi
    if [[ -n "${WP_SKILLS_SOURCE:-}" ]]; then
      collect_remote_dir_skills "$WP_SKILLS_SOURCE" "skills"
      collect_remote_dir_skills "$WP_SKILLS_SOURCE" "tools/skills"
    else
      collect_remote_dir_skills "wp-labs/wp-skills" "skills"
      collect_remote_dir_skills "wp-labs/wp-skills" "tools/skills"
    fi
  fi
  if [[ ${#names[@]} -eq 0 ]]; then
    echo "No skills found to install." >&2
    exit 1
  fi
fi

# --- Install -----------------------------------------------------------------

installed_count=0
for i in "${!names[@]}"; do
  name="${names[$i]}"
  src_dir="${srcs[$i]}"

  if [[ ! -d "$src_dir" ]]; then
    echo "Error: source not found for skill: $name ($src_dir)" >&2
    exit 1
  fi

  for target_base in "${target_dirs[@]}"; do
    dst_dir="$target_base/$name"

    mkdir -p "$target_base"
    rm -rf "$dst_dir"
    cp -R "$src_dir" "$dst_dir"

    # Detect platform name for display
    platform="custom"
    if [[ "$target_base" == "$codex_home/skills" || "$target_base" == */.codex/skills ]]; then
      platform="codex"
    elif [[ "$target_base" == */.claude/skills ]]; then
      platform="claude-code"
    elif [[ "$target_base" == */.agents/skills ]]; then
      platform="agents"
    fi

    echo "Installed: $name"
    echo "Platform:  $platform"
    echo "Location:  $dst_dir"
    echo ""
    installed_count=$((installed_count + 1))
  done
done

# Show the file list when a single skill was installed
if [[ ${#names[@]} -eq 1 && "$installed_count" -gt 0 ]]; then
  echo "Files installed:"
  find "$dst_dir" -type f 2>/dev/null | sed 's|'"$dst_dir"'||' | sed 's|^/|  - |' | head -20
  if [[ $(find "$dst_dir" -type f | wc -l) -gt 20 ]]; then
    echo "  ... and more"
  fi
fi

echo "Done: $installed_count install(s), ${#names[@]} skill(s)."
