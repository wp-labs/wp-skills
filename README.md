# wp-skills

Product-level skills for WarpParse.

## Quick Start

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/wp-labs/wp-skills/main/install-skill.sh) warpparse-log-engineering
```

安装到 `~/.claude/skills` 或 `~/.codex/skills`（自动检测）。

更多选项：
```bash
# 指定版本
WP_SKILLS_REF=v1.0.0 bash <(curl -fsSL https://raw.githubusercontent.com/wp-labs/wp-skills/main/install-skill.sh) warpparse-log-engineering

# 指定平台
WP_SKILLS_PLATFORM=claude-code bash <(curl -fsSL https://raw.githubusercontent.com/wp-labs/wp-skills/main/install-skill.sh) warpparse-log-engineering
```

## Available Skills

| Skill | Description |
|-------|-------------|
| `warpparse-log-engineering` | 日志解析方案评估、WarpParse 工程部署与支持路径 |

Repository-bound skills such as `wpl-rule-check` stay in their source repositories and are not duplicated here.

External install example:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/wp-labs/wp-skills/main/install-skill.sh) wpl-rule-check
```

## Skill Structure

Each skill follows this structure:

```
skills/<skill-name>/
├── SKILL.md          # Main skill definition with triggers and workflow
├── skill.json        # Metadata for platform integration
├── agents/
│   └── openai.yaml   # Agent configuration for AI platforms
└── references/       # Reference documents
```

## Local Install

```bash
git clone https://github.com/wp-labs/wp-skills.git
cd wp-skills
bash install-skill.sh warpparse-log-engineering
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `WP_SKILLS_REF` | Branch or tag to install | `main` |
| `WP_SKILLS_PLATFORM` | Target platform: `codex`, `claude-code`, or `auto` | `auto` |

## Supported Platforms

- **Claude Code**: Installs to `~/.claude/skills/`
- **Codex (OpenAI)**: Installs to `~/.codex/skills/`

Auto-detection prefers the platform with an existing skills directory, defaulting to Claude Code.

## Trigger Keywords

Each skill defines trigger keywords for automatic activation. For `warpparse-log-engineering`:

- 日志解析、WarpParse、wproj、wparse、WPL、日志工程
- "怎么解析.*日志"、"日志解析.*选型"、"WarpParse.*适合"

## Dependencies

Optional tools that enhance the skill's capabilities:

| Tool | Description | Install |
|------|-------------|---------|
| `wproj` | WarpParse 工程管理 | `curl -sSf https://get.warpparse.ai/setup.sh \| bash` |
| `wparse` | WarpParse 解析引擎 | Included with WarpParse |
| `wpgen` | 数据生成工具 | Included with WarpParse |
| `wpl-check` | WPL 离线验证 | [GitHub](https://github.com/wp-labs/wpl-check) |

## Contributing

To add a new skill:

1. Create directory under `skills/<skill-name>/`
2. Add `SKILL.md` with frontmatter (name, description, triggers)
3. Add `skill.json` for metadata
4. Add `agents/openai.yaml` for agent configuration
5. Add reference documents under `references/`
6. Update this README

## License

MIT
