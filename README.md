# wp-skills

Product-level skills for WarpParse.

## Quick Start

```bash
curl -sSf https://get.warpparse.ai/inst-x.sh | bash -s -- wp-skills
```

安装到 `~/.claude/skills` 或 `~/.codex/skills`（自动检测）。



## Available Skills

| Skill | Description |
|-------|-------------|
| `wp-deploy` | WarpParse 的 source/sink、wpgen、wp-monitor 与联调部署配置指导 |
| `wpl-rule-check` | 根据日志样本编写 WPL/OML，并通过 wpl-check 验证 |
| `warpparse-log-engineering` | 日志解析方案评估、WarpParse 工程部署与支持路径 |



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
bash install-skill.sh wp-deploy
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `WP_SKILLS_REF` | Branch or tag to install | `main` |
| `WP_SKILLS_PLATFORM` | Target platform: `codex`, `claude-code`, or `auto` | `auto` |

## Versioning

Repository release version is recorded in `version.txt`.

Recommended release flow:

1. Update `version.txt`
2. Commit the change to `main`
3. Create a matching tag: `v<version>`
4. Push the tag to GitHub

Example:

```bash
echo 0.1.1 > version.txt
git add version.txt
git commit -m "chore: release v0.1.1"
git tag v0.1.1
git push origin main
git push origin v0.1.1
```

GitHub Actions will validate that the pushed tag matches `version.txt` and then create the release automatically.

## Supported Platforms

- **Claude Code**: Installs to `~/.claude/skills/`
- **Codex (OpenAI)**: Installs to `~/.codex/skills/`

Auto-detection prefers the platform with an existing skills directory, defaulting to Claude Code.

## Trigger Keywords

Each skill defines trigger keywords for automatic activation. For `wp-deploy`:

- WarpParse 部署、source、sink、connector、wpgen、wp-monitor、联调、观测
- "怎么部署.*WarpParse"、"怎么接.*wpgen"、"怎么把.*链路跑起来"

## Dependencies

Optional tools that enhance the skill's capabilities:

| Tool | Description | Install |
|------|-------------|---------|
| `wproj` | WarpParse 工程管理 | `curl -sSf https://get.warpparse.ai/setup.sh \| bash` |
| `wparse` | WarpParse 解析引擎 | Included with WarpParse |
| `wpgen` | 数据生成工具 | Included with WarpParse |
| `wpl-check` | WPL 离线验证 | [GitHub](https://github.com/wp-labs/wpl-check) |

## Configuration Generation

Generated WarpParse project configuration should use `wproj` as the standard path. Do not hand-assemble equivalent `conf/`, `connectors/`, `topology/`, or `models/knowledge/` files for a new generated project.

Initialize a local project:

```bash
wproj init --work-root .
wproj check --work-root . --what all --fail-fast
```

Initialize from a remote project source:

```bash
wproj init --work-root . --repo <repo-url> --version <version>
wproj check --work-root . --what all --fail-fast
```

Update or regenerate remote-backed configuration:

```bash
wproj conf update --work-root . --group models --version <version>
wproj conf update --work-root . --group infra --version <version>
wproj check --work-root . --what all --fail-fast
```

Skill-generated deployment documentation should include the exact `wproj` command used so the same configuration can be regenerated and validated consistently.

## Validation Workflow

Generated workflows should use `wpgen` for sample replay and test data injection. Do not generate ad hoc sender scripts for this step.

```bash
wpgen conf check --work-root "$(pwd)"
wpgen sample --work-root "$(pwd)" -n 10000 -s 1000 --stat 3 -p
```

Generated deployment workflows should actively deploy `wp-monitor` by default. Do not stop at "wp-monitor can be started later" unless Docker, ports, or image pulls are actually blocked and the failure evidence is included.

A standard observable deployment includes:

- `warp-parse`
- `victoria-metrics`
- `victoria-logs`
- `wp-monitor`

Minimum monitor-side checks:

```bash
docker compose version
docker info
docker compose up -d victoria-metrics victoria-logs wp-monitor
docker compose ps
docker compose logs wp-monitor
curl -fsS http://localhost:8428/health
curl -fsS http://localhost:9428/health
curl -fsS http://localhost:18080
```

Then open `http://localhost:18080` and inspect source input, parse success/error counts, misses, sink output, and pipeline health.

Final generated output must include a `wp-monitor` closure status:

- Deployment status: deployed or not deployed
- Access URL, usually `http://localhost:18080`
- Whether source, parse, miss, and sink data are visible
- If not deployed or not verified, state that the business pipeline is complete but the monitoring closure is incomplete

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
