# atomic-skills

[Atomic VCS](https://atomic.dev) canonical skills and workflow instructions.

This is the single source of truth for the Atomic agent workflow body (`AGENTS.md`) and the on-demand skills every Atomic-aware agent loads. It is consumed by all 12 agent integration packages ([atomic-opencode](https://github.com/atomicdotdev/atomic-opencode), [atomic-claude](https://github.com/atomicdotdev/atomic-claude), [atomic-codex](https://github.com/atomicdotdev/atomic-codex), etc.) via `[skills-source]` in their `atomic-integration.toml` manifests.

> **Definitive source:** this repository lives on Atomic storage. The GitHub repo is a mirror. The CLI clones it into `~/.atomic/integrations/atomic-skills/repo` (shared cache) on every `atomic agent enable`.

## What's in here

```
atomic-skills/
├── AGENTS.md                          # vendor-neutral workflow body
├── atomic-integration.toml            # declares the skills (below)
└── skills/
    ├── atomic-vault/SKILL.md          # intent lifecycle, vault commands, memory operations
    ├── atomic-vcs/SKILL.md            # read-only VCS: status, log, change, diff
    ├── code-intelligence/SKILL.md     # knowledge graph + content search (replaces grep)
    ├── intent-builder/SKILL.md        # how to author structured intents
    ├── decision-record/SKILL.md       # capture durable insights as attestable memories
    └── triage-review/SKILL.md         # review change-sets before cross-view promotion
```

### AGENTS.md

The canonical, vendor-neutral agent workflow body. It establishes:

1. **"You use Atomic VCS, not git."** — the agent uses Atomic CLI commands instead of git.
2. **The intent-first workflow.** — every unit of work becomes a directive-based intent (`:::why`, `:::acceptance-criterion`, `:::task`) that must validate and attest.
3. **"Do NOT run `atomic add` or `atomic record`."** — hooks record automatically with provenance.
4. **Point at the skills.** — `atomic-vault`, `atomic-vcs`, `code-intelligence`, etc.

Each plugin delivers this body to the agent through one of two paths:

- **Bundled agent** (OpenCode, Claude, Kilo, Pi): The plugin ships a frontmatter template (`agents/atomic.md.frontmatter`). At install time, the CLI stitches the frontmatter + this `AGENTS.md` body together via `[agent-definition]` in the plugin manifest. The user picks the "Atomic" agent in their IDE.
- **Repo-level AGENTS.md** (all agents): `atomic agent enable --agents-md` copies this `AGENTS.md` into the repo root. Every agent in that repo gets the workflow automatically — no agent picking. If the repo already has an `AGENTS.md`, the installer appends the canonical content with a `---` separator, preserving the user's project-specific content.

### Skills

Skills are on-demand reference documents the agent loads when a task calls for them (kept out of the always-on prompt to save context). Every Atomic agent pulls the same skills from this package so that behavior is identical no matter which agent the user runs.

| Skill | Description |
|-------|-------------|
| `atomic-vault` | Intent lifecycle, vault CLI commands, memory operations |
| `atomic-vcs` | Read-only VCS inspection: `status`, `log`, `change -p`, `diff` |
| `code-intelligence` | Knowledge graph + content search (replaces grep/find) |
| `intent-builder` | How to author structured, conforming intents |
| `decision-record` | Capture durable insights as attestable memories at turn end |
| `triage-review` | Review change-sets before cross-view promotion |

## How it works

### Skills are declared, not globbed

The `atomic-integration.toml` in this package explicitly declares each skill via `[[declared-skill]]` entries:

```toml
[[declared-skill]]
name = "atomic-vault"

[[declared-skill]]
name = "triage-review"
```

When a plugin's manifest has a `[skills]` block with `install = "all"`, the installer:

1. Clones this package into the shared cache (`~/.atomic/integrations/atomic-skills/repo`) — **always**, on every `atomic agent enable`, so new skills are picked up immediately.
2. Reads this manifest to get the declared skill list.
3. For each declared skill, copies `skills/{name}/SKILL.md` to the plugin's `dst_pattern` (formatted with `{name}`).

The CLI reads the manifest — it never scans the filesystem.

### Adding a new skill

1. Create `skills/<skill-name>/SKILL.md` with the skill content.
2. Add one `[[declared-skill]]` entry to `atomic-integration.toml`:
   ```toml
   [[declared-skill]]
   name = "<skill-name>"
   ```
3. Commit and push.

That's it. Every plugin that has `[skills] install = "all"` will pick up the new skill automatically on next `atomic agent enable`. Zero plugin manifest changes.

### Updating an existing skill

Edit the `SKILL.md` file, commit, push. Every plugin gets the update on next install — the CLI always re-clones the cache to get latest.

### Updating AGENTS.md

Edit `AGENTS.md`, commit, push. The canonical body flows to:
- **Bundled-agent plugins**: stitched into the agent file at install time (frontmatter + body).
- **Repo-level installs**: copied/merged into the repo's `AGENTS.md` via `--agents-md`.

No plugin repo changes needed.

## How plugins consume this package

A plugin's `atomic-integration.toml` declares:

```toml
[skills-source]
package = "atomic-skills"

[skills]
install = "all"
dst_pattern = "~/.config/opencode/skills/{name}/SKILL.md"

[[repo-file]]
src = "AGENTS.md"
dst = "AGENTS.md"

# For bundled-agent plugins only:
[agent-definition]
src = "agents/atomic.md.frontmatter"
body_from = "atomic-skills:AGENTS.md"
slot = "~/.config/opencode/agents/atomic.md"
```

- `[skills-source]` — names this package as the shared cache.
- `[skills]` — `install = "all"` reads the declared skills from this package's manifest; `dst_pattern` formats the per-vendor destination path with `{name}`.
- `[[repo-file]]` — installs `AGENTS.md` into the repo root (when the user opts in via `--agents-md`).
- `[agent-definition]` — stitches the plugin's frontmatter + this package's `AGENTS.md` body into the vendor's agent slot.

Vendors with flat skill layouts (Cline: `Workflows/{name}.md`, agy: `plugin/skills/{name}.md`) use a flat `.md` filename in `dst_pattern` instead of `{name}/SKILL.md`.

## Building a new agent integration

See the [Adding a New AI Agent to Atomic](https://github.com/atomicdotdev/atomic/blob/dev/docs/adding-agents.md) guide in the atomic repo for the full walkthrough: hook adapters, manifest fields, plugins vs hooks manifests, the test harness, and the checklist.

## License

Dual-licensed under MIT and Apache 2.0.
