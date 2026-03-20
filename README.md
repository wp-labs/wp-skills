# wp-skills

Product-level Codex skills for WarpParse.

This repository is for reusable skills that are not tightly coupled to a single code repository.

Current skills:

- `warpparse-log-engineering`

Repository-bound skills such as `wpl-rule-check` stay in their source repositories and are not duplicated here.

## Install A Skill

Install directly from GitHub without cloning:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/wp-labs/wp-skills/main/scripts/install-codex-skill.sh) warpparse-log-engineering
```

Set `WP_SKILLS_REF=<branch-or-tag>` first if you want a specific revision instead of `main`.

From a local checkout:

```bash
bash scripts/install-codex-skill.sh warpparse-log-engineering
```
