---
name: atomic-validate
description: Verifies an Atomic agent turn was recorded with AI provenance — clean status, signed change with an Attestation block (vendor, tokens, session), plus deterministic troubleshooting when nothing records. Use to check or debug Atomic's agent-integration recording.
---

# Atomic Validate (Agent Skill)

You are the validator. Your job: prove that an AI agent turn was recorded as a
signed Atomic change with AI provenance. Read-only checks first, report before
diagnosing, and never mutate without explicit consent.

**Prerequisite:** the OpenCode agent integration is enabled (`atomic agent
enable`, CLI >= 0.12.0) and a real agent turn ran inside an Atomic repo —
otherwise there is nothing to validate.

## Validation contract

- **Check-before-act:** run the read-only checks first; report the result
  before moving on.
- **Consent before mutation:** every state-changing step (re-running a turn,
  re-running `atomic agent enable`, upgrading anything) needs an explicit yes.
- **Deterministic fixes first:** work the troubleshooting table top to bottom;
  improvise only when the user asks for troubleshooting help.
- **Report a receipt:** state pass/fail and the evidence — what you checked
  and what it showed.

## 1. Check the provenance (read-only)

```bash
cd /tmp/test-atomic
atomic status -s           # clean — HELLO.md is already recorded
atomic log -n 2            # newest change's message is the test prompt
atomic change              # shows an Attestation block
```

**Success** = the newest recorded change's message is the test prompt and its
`Attestation` block names the vendor and token counts (model may read
`unknown` for some providers) and an opencode session (`ses_…`) — recorded
with zero manual commands. For the subagent path, also confirm
`.atomic/sessions/ses_*.json` exists and its `turn_count` grew. Report this
to the user as the receipt that the plugin works.

## 2. Troubleshoot if nothing recorded

Deterministic fixes first (work the table top to bottom); only improvise when
the user asks for troubleshooting help.

| Symptom | Diagnosis | Fix |
|---------|-----------|-----|
| `opencode run` fails with a provider/model error | No model connection | v1: connect a model (`opencode auth login` or provider API key) or pass `--model provider/model`; v2: pick a free built-in model (no login needed) |
| No `.atomic/sessions/ses_*.json` after the turn | Plugin never loaded | v1: check the `"plugin"` key in `~/.config/opencode/opencode.json` (written by `atomic agent enable`); v2: confirm the file sits in `~/.config/opencode/plugins/`. Check `~/.local/share/opencode/log/opencode.log` for `loading plugin` |
| Plugin loaded, turn ran, still nothing | Session directory is not an Atomic repo — the plugin records only sessions whose directory has `.atomic` | Re-run the turn from inside the Atomic repo, or `atomic init` the current project |
| `~/.config/opencode/…/.atomic/hook-errors.log` exists (in the project) | A hook shell-out failed | Read it; most common: `atomic` not on the PATH that OpenCode spawned with — restart OpenCode after the path phase, or reinstall so hooks find it |
| `.atomic/hook-errors.log` shows `exit 143` on `stop` after a v2 `--standalone` run | Pre-fix plugin (integration < 1.1.1): `opencode run --standalone` tore down the process tree and killed the in-flight Stop recording. Fresh installs from storage already include the fix, so hitting this means an old install — or a different teardown bug | Re-run `atomic agent enable` (from a repo) to pull the fixed integration package (>= 1.1.1), confirm the plugin file changed, then rerun the turn |
| Session file shows the turn (`turn_count` grew) but `atomic log` is empty | Rare deferred-publication race in the Atomic CLI: the change recorded but its publication to the view log was deferred | Run one more tiny turn (or any `atomic agent hooks` call) — the deferred change then publishes and both turns appear in `atomic log`. Do not re-init or delete anything |
| Every turn recorded twice | OpenCode v1 older than 1.18.29 | Upgrade OpenCode — old v1 builds register the plugin through both export styles |
| `opencode` was already running when the plugin was installed | Current session may predate the plugin | v2 hot-reloads; v1 needs a restart. A standalone `opencode run --auto` against the project sidesteps this entirely |
