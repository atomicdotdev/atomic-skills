---
name: triage-review
description: Review a change-set before its changes are promoted between views. Use this whenever you need to decide what to insert from one view into another, narrate what a change-set does and why, review whether an intent's acceptance criteria are genuinely satisfied by the recorded changes, judge a candidate change-set, or check for staleness and open remediations before promotion. Driven by `atomic triage review --json` (whose `walkthrough` groups the changes into ordered semantic layers); you read the walkthrough to author a provenance-backed narrative review — intent → memory → change — surfacing critical risks and blockers, then investigate the findings, review the actual code, and record your verdict as a review intent (`kind: review`) that `reviews` the work — authored and attested under your own identity (ideally a different model than the author), so promoting into a shared view requires an independent, completed review.
---

# Reviewing an Intent (Code Triage)

In Atomic the code is **already in the graph** by the time you review it — a draft
view already sees it. So review is not "should these diffs be applied" (a pull
request). It is **triage**: deciding which change references should be inserted
(promoted) from one view into another, and confirming the intent that motivated
them is genuinely satisfied.

The review is its own **review intent** (`kind: review`) that `reviews` the work
intent — authored and attested by *you, the reviewer*, not an edit to the
author's intent. Its acceptance criteria are your review checklist; a flaw you
find is an `unmet` review criterion. Because you sign it under your own identity
(ideally a different model than the author), it is an **independent** review —
and promoting the work into a *shared* view requires exactly that: a `done`,
non-author review covering the changed intents (`UNREVIEWED_CHANGE` blocks
otherwise). The author's self-attested `done` on the work intent is an earlier,
separate bar. The triage report you work from is a reproducible projection,
discarded after you act on it.

## The two commands

| Command | Answers |
|---------|---------|
| `atomic triage candidates <feature> --into <target> [--json]` | Which changes would land if I promote `feature` into `target`? (only-in-feature + dependency closure + baggage) |
| `atomic triage review <feature> --into <target> [--json]` | The full report: verdict, findings, the intents/criteria those changes fulfil, provenance, and a content-addressed triage reference. |

`--json` is your worklist. Start there.

## The report is your worklist

`atomic triage review <feature> --into <target> --json` returns one model:

- **`verdict`** — `ready` \| `blocked` \| `stale` (precedence: blocked > stale > ready).
- **`inputs`** — `feature`, `target`, `view_merkle` (the pinned Merkle — you will
  reuse this when you record verification), `candidate_changes`, `closure_additions`.
- **`intents[]`** — each reached intent's `why`, gate `conforms`, and its
  `criteria[]`. A criterion with `judgment_required: true` is one the gate cleared
  for *presence* but that needs your *content* judgment.
- **`changes[]`** — each candidate change's `message`, `modifies`, `coverage`,
  the real per-file `diff`, and compact `provenance` (which agent/session/turn).
- **`findings[]`** — the failures, each with `code`, `severity`, `focus` (a node
  id), `message`, and often a `suggested_query` to investigate it.
- **`walkthrough[]`** — the candidate modifications grouped into **ordered
  semantic layers** (foundations first): each layer has a `title` (the module),
  a `rationale`, its `files`, the `tasks`/`criteria` it advances, the `changes`
  that land there, and `depends_on` (earlier layers it builds on). This is the
  **reading order** — the spine of your narrative.
- **`reference`** — `urn:atomic:triage:<blake3>`, the content hash of this report
  over its pinned inputs.

The gate enforces that evidence *exists*; it never grades the prose. **Your job is
the content judgment it deliberately leaves to you.**

## Narrate the change first (the walkthrough story)

Before the line-by-line judgment, open your review with a **narrative review**: a
plain-language story of what this change-set *is* and *why it exists*, told in the
walkthrough's reading order. This is **not** a pull-request description invented
from the diff — it is assembled from **signed vault facts**, so every sentence
traces to a node id: an intent's `why`, an attested **memory**, a **change**
message/provenance. Atomic supplies the facts; you supply the prose and the
judgment. This is the LLM-authored annotation the deterministic report deliberately
leaves to the reviewer — it is never baked into the report itself.

### Gather the story facts

The `--json` report already carries the `walkthrough`, `intents[]` (with `why`),
and `changes[]` (with `message` + `provenance`). The one thing it does not embed
is the **memories** the author distilled while doing the work — pull those per
reached intent:

```bash
# The attested decisions/lessons/constraints the author derived FROM this intent.
# wasDerivedFrom edges point memory:<id> → intent:<UID>.
atomic query neighbors intent:<intent-UID> -d 1 --json   # find memory:<id> via prov:wasDerivedFrom
atomic memory show <memory-id>                           # read the decision/lesson in the author's words
atomic change <hash> -p                                  # the change's reasoning + provenance
```

For the human-facing version of the same story, `atomic triage review <feature>
--into <target> --html <view>` renders the walkthrough as an ordered chapter tour;
`--walkthrough` prints the bounded text form. Your narrative is the *review* of
that tour.

### The narrative shape — intent → memory → change → review

Walk `walkthrough[]` in order (foundations first). Produce:

1. **Overview** — one paragraph: what the change-set accomplishes end-to-end, the
   `verdict`, and the headline count of blockers and risks.
2. **Per layer (a chapter)**, in reading order — for each, weave the four beats:
   - **Intent (the why):** the motivating intent's `why` — why this work exists.
   - **Memory (the reasoning):** each attested memory the author derived —
     *decision* (chose X over Y), *lesson* (a corrective learning), *constraint*
     (a rule discovered) — in their own words, **cited by memory id**. This is
     the thinking behind the code that a diff can never show.
   - **Change (the what):** the change `message`(s), the files touched, and the
     `provenance` (which agent/model/session produced it).
   - **Narrative review (your synthesis):** does the code deliver the why? Name
     **critical risk factors**, **blocking findings** (`severity: block` on this
     layer's changes/criteria), scope or `:::constraint` concerns, and anything a
     memory reveals as a known trade-off, shortcut, or assumption to challenge.
3. **Risk & blocker summary** — a bulleted list: every `block` finding, plus
   `STALE_TRIAGE` / `UNREVIEWED_CHANGE` / `SCOPE_OUT_BREACH` / `BLAST_UNREVIEWED`
   and any risk *you* surfaced, each tied to its **layer + source id** and a
   recommended action.

Every claim cites its source (`urn:atomic:intent:…`, `memory:…`, change hash) so
the narrative is auditable, not vibes. The risks you name here become the
acceptance criteria on your review intent (below) — the narrative *is* the plan
for the rest of the review.

> A memory that fails to load, or an unenriched KG, just means fewer beats — the
> story degrades gracefully; it never blocks the review.

## The review loop

### 1. Get the report and narrate the change
```bash
atomic triage review <feature> --into <target> --json
```
Read the `walkthrough` and author the **narrative review** (intent → memory →
change → review) per the section above — pulling each reached intent's derived
memories with `atomic query neighbors intent:<UID> -d 1 --json` +
`atomic memory show`. Lead your review with this story; the risks and blockers it
surfaces are the agenda for the steps that follow.

### 2. Investigate every blocking finding and every `judgment_required` criterion
Use the read-only skills — do not guess:
- `code-intelligence` (`atomic vault query neighbors|callers|code|entities`) to see
  the blast radius and structure. Run each finding's `suggested_query`.
- `atomic-vcs` (`atomic change <hash> -p`, `atomic diff --word-diff`) to read the
  actual edits and the reasoning that produced them.

### 2b. Review the actual code — not just the linkage
The report and findings check *linkage* (does the work trace to a why, are
criteria evidenced, is anything out of scope). They do **not** judge whether the
code is any good. That is your job, and it is the core of the review. For every
candidate change, read the real diff and look for smells:

```bash
atomic change <hash>              # message + files + hunk summary (what & why)
atomic change <hash> --show-hunks # per-hunk detail
atomic diff -c <hash> --word-diff # token-level edits (CRDT semantic diff)
```

Review each change for: correctness and edge cases; security (injection, secrets,
unsafe blocks, missing authz); error handling and resource cleanup; concurrency;
duplication and dead code; naming and clarity; **missing or weak tests**;
performance regressions; and adherence to the intent's `:::constraint`s. Use
`--word-diff` for token-level review — it shows exactly which tokens changed, not
just which lines.

A smell is not automatically a blocking finding — classify it:
- It means an **acceptance criterion isn't really met** → leave that criterion
  `unmet` and say why (do not record a passing verification).
- It **violates a `:::constraint` or scope** → treat it as blocking; the change
  needs rework before promotion.
- It's a **minor nit** → note it in your review summary; it need not block.

### 3. Create your review intent
The review is *your own* intent, not an edit to the author's work intent. Scaffold
it:
```bash
atomic intent new --review <work-intent-id>
```
This sets `kind: review` and adds `:::ref{to=<work-intent> edge=reviews}`. Its
acceptance criteria are your **review checklist** — e.g. "no security flaws in the
static-file handler", "tests cover the rate-limit path", "AC-2 is genuinely met".
Write one criterion per thing you must establish.

### 4. Run the checks and record the verdict on the review intent
Run whatever the review requires (tests, `npm run serve`, the specific exploit).
Record each result as a **verification record** on the matching review criterion,
pinning `observedAtMerkle` to the report's `inputs.view_merkle`. Mark a criterion
`met` only when it genuinely holds; a flaw you find leaves its criterion `unmet`
with the reason. Edit the review intent's `.vault/` file with your **file-editing
tool** (never bash/sed):

```md
:::acceptance-criterion{#<review-UID>-ac-1 status=met requiredKinds=e2e}
No path traversal in the static-file handler.
::verification{kind=e2e outcome=pass scope=ac observedAtMerkle=<view_merkle> observation=curl --path-as-is /%2e%2e%2fserver.ts now 404s}
:::
```

Then attest the review **under your own identity** — ideally a *different model*
than the author, which is what makes it independent:
```bash
atomic vault sync                       # persist your edits into the vault db
atomic intent validate <review-ID>      # gate: a met criterion needs a passing
                                        # record per required kind (EvidenceShape)
atomic intent attest <review-ID>        # sign it under YOUR did; done only if it conforms
```
A review with any `unmet` criterion is not `done` → the work it reviews is not
`ready`. The gate rejects a `met` criterion lacking a passing record — you cannot
check a box without proof.

### 5. Recommend the outcome
The work intent is `ready` to promote when your review intent is **`done`,
attested, by a non-author identity**, and no blocking findings remain.
`UNREVIEWED_CHANGE` blocks promotion into a *shared* view until that independent
review exists (advisory for draft→draft). Recommend the insert; do not create or
switch views yourself. If findings block, report them and handle any flaw per the
rule below.

## Findings and what to do

| `code` | Severity | What it means / your move |
|--------|----------|---------------------------|
| `ORPHAN_CHANGE` | block | A candidate change traces to no intent. Find its intent or question why it's promoting. |
| `GATE_VIOLATION` | block | The intent doesn't conform. Read the message; fix the intent's structure/evidence. |
| `MET_AC_NO_EVIDENCE` | block | A criterion is `met` without a passing required-kind record. Run the check and attach it, or un-mark it. |
| `SCOPE_OUT_BREACH` | block | A change touches a file the intent declared scope-out. Split it out or widen scope. |
| `UNMET_AC_WITH_CANDIDATE` | warn | A candidate claims to satisfy an unmet criterion — judge the diff (step 3). |
| `BAGGAGE_DEP` | warn | A closure dependency lands that no intent covers. Confirm it's intended baggage. |
| `STALE_TRIAGE` | warn | The intent's substance drifted after `done` was granted — its `done` lapsed. Re-review against the current state. |
| `OPEN_REMEDIATION` | info | Promoted code has a `remediates`-linked intent in flight. Non-blocking; track it. |
| `UNREVIEWED_CHANGE` | block →shared / warn draft | No independent, completed review covers this intent's changes. Author + attest a `kind: review` intent under a *different* identity that `reviews` it. |

## When you find a flaw

Whether you fix it in place or open a new intent depends on **insertion state**, not
severity:

- **Flaw found pre-insert (still in the draft view):** leave the relevant review
  criterion `unmet` (so the review isn't `done` and the work isn't `ready`); a fix
  change lands in the same view (author or follow-up), then re-run `triage review`
  and re-attest the review. **No remediation intent** — the code just needs to
  catch up before promotion.
- **Flaw found post-insert (already in a shared view):** the change is in
  collaborative history; you cannot walk it back. Create a **new intent** that
  `remediates` the original (author it with `:::ref{to=<original-intent> edge=remediates}`),
  with a **fresh acceptance criterion** whose `requiredKinds` includes the check
  that would have caught the flaw (promote the manual test to an automated one).
  It surfaces on the original as a non-blocking `OPEN_REMEDIATION`.

## Worked examples

### How a change links to an intent (the join)

Triage links a change to an intent through a **shared `file:` node**: a change's
`MODIFIES` edge and a task's `TOUCHES` edge must point at the *same* file path.
You create the `TOUCHES` edge by giving a task a `::file-ref` leaf:

```md
:::task{#<UID>-1 criteria=<UID>-ac-1}
Add the rate limiter to the auth middleware.
::file-ref{path=src/auth/middleware.rs}
:::
```

Now any change that modifies `src/auth/middleware.rs` is "covered" by this
intent. The path must match **exactly** — full repo-relative path,
case-sensitive. `middleware.rs` will NOT meet `src/auth/middleware.rs`.

**`::file-ref` vs `:::ref`** — do not confuse them:
- `::file-ref{path=…}` is a `::` **leaf inside a `:::task`** (or `:::scope-out`).
  It links task → file, which is how a change gets attributed to an intent.
- `:::ref{to=… edge=…}` is a `:::` **container** declaring intent → intent links
  (`depends`, `blockedBy`, `remediates`). It has nothing to do with change
  attribution.

### A clean review

```bash
atomic triage review empty-rose-5779 --into dev --json
```

Read `findings[]` and each intent's `criteria[]`. For a `judgment_required`
criterion, inspect the change and run its `requiredKinds` checks, then record the
verdict (see "The review loop"):

```bash
atomic change <hash> -p           # the reasoning behind the change
atomic diff --word-diff <file>    # the precise edits
cargo test                        # or whatever the criterion requires
```

### The narrative review (intent → memory → change)

Given a report whose `walkthrough` orders two layers — `storage` (foundation)
then `cli` (entry point) — the opening of your review reads like:

> **Overview.** `feature-view-filter → dev` promotes 6 changes across 2 layers.
> Verdict: **blocked** — 1 blocking finding, 1 risk to flag.
>
> **Layer 1 — storage (foundation).**
> *Why* (`urn:atomic:intent:01J…A2`): "status must not surface files from other
> views." *Reasoning* (`memory:01J…m1`, decision): the author chose a
> change-filter over copying edges "because insert stays O(1) metadata-only."
> *What* (`AB12…`, agent `claude-opus`): adds the `VIEW_CHANGES` filter to
> `tables.rs` + `txn/write/view.rs`. *Review:* delivers the why, but
> `memory:01J…m1` admits the filter is unbounded — **risk:** large ancestor
> chains re-scan on every `status`; no test covers the deep-chain case.
>
> **Layer 2 — cli (builds on storage).**
> *Why* / *what:* surfaces the flag in `run.rs` (`CD34…`). *Review:* thin
> wiring; the **blocking** `UNREVIEWED_CHANGE` here just means no independent
> review exists yet — which is what you are about to fix.
>
> **Risks & blockers.**
> - `block` `UNREVIEWED_CHANGE` → layer cli → author this review under a
>   different identity.
> - risk (deep-chain re-scan) → layer storage, from `memory:01J…m1` → add a
>   perf criterion / test before promotion.

Each beat cites the intent, memory, or change it came from, so the story is
auditable. Then continue into the code-level review (step 2) with those risks as
your checklist.

### Fixing `ORPHAN_CHANGE`

`ORPHAN_CHANGE` means a candidate change reaches no intent. Triage reads the
change's modified files directly from the change, so the **finding names the
paths for you** — e.g. “candidate change modifies [src/foo.rs] but no intent's
task touches those files.” The fix is to make an intent's task `TOUCHES` one of
those exact paths:

```bash
# 1. Which intent should own this work? Check its tasks' file-refs match reality.
atomic vault query neighbors file:src/foo.rs -d 2 --json   # any incoming TOUCHES from a task?

# 2. Fix: add a matching file-ref to a task on the owning intent (edit the
#    intent's .vault file with your file tool). The path must match the finding
#    EXACTLY — full repo-relative path, case-sensitive.
```
```md
:::task{#<UID>-1 criteria=<UID>-ac-1}
Whatever this change does.
::file-ref{path=src/foo.rs}
:::
```
```bash
# 3. Persist and re-triage:
atomic vault sync
atomic triage review empty-rose-5779 --into dev   # the change now links
```

The exact-path match is the usual culprit: `foo.rs` will NOT meet `src/foo.rs`.
If the change is genuinely unrelated to any intent, that is the finding doing its
job — either author the intent that explains it, or question why it is promoting.
(Note: `atomic vault query enrich` is still worth running for the entity-level
`BLAST_UNREVIEWED` finding, which uses `DEFINES`/`CALLS` edges — but change→intent
attribution no longer depends on it.)

### Clearing `STALE_TRIAGE`

`STALE_TRIAGE` is a **warn** (it does not block). It means the intent was granted
`done`, then its reviewable **definition** changed — an acceptance criterion's
text or its `requiredKinds` — so the pin recorded at grant time no longer matches.
Clear it one of two ways:

- **Re-grant done** to re-pin at the current substance: `atomic intent update <id> --status done`.
- **Revert** the definition change so the substance matches the original pin.

Adding a **verification record** does NOT trigger this — records are review state,
not definition. So: set `requiredKinds` when you *author* the criterion (before
granting done), record verifications during review, and **mark `done` last**, after
all definition edits. That ordering avoids the churn entirely.

## Rules

- **Open with the narrative, grounded in facts.** Lead the review with the
  intent → memory → change story in walkthrough order. It is LLM-authored prose,
  but every claim cites a signed source (intent `why`, `memory:<id>`, change
  hash) — never invent rationale the vault does not support.
- **The review is the intent's own state.** You do not create a memory or a "review"
  record — you advance acceptance criteria with evidence and attest the intent.
- **Presence is the gate's job; content is yours.** Judge whether the diff genuinely
  satisfies the criterion; the gate only checks that a passing record exists.
- **A checked box needs proof.** Never flip a criterion to `met` without running its
  required verifications and attaching a passing record for each required kind.
- **Pin to the reported merkle.** Use the report's `inputs.view_merkle` for
  `observedAtMerkle` so the evidence is anchored to the exact state you reviewed.
- **Edit intent files with your file tool, then `atomic vault sync`.** Never edit the
  vault with bash/sed. Do **not** run `atomic add`/`atomic record` — the plugin
  records at turn end.
- **Do not create or switch views.** Recommend the promotion; the insert is a gated
  step outside the session.
- **Insertion state decides the flaw path.** Pre-insert → same intent; post-insert →
  a new `remediates`-linked intent with a fresh, stronger criterion.

## Related skills

- `code-intelligence` — investigate findings and blast radius (`atomic vault query …`).
- `atomic-vcs` — read the diffs and provenance behind each change (`atomic change -p`,
  `atomic diff --word-diff`).
- `atomic-vault` — the intent/acceptance-criterion lifecycle you write the verdict into.
- `decision-record` — capture any durable insight the review produced as a memory.
