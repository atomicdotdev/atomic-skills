---
name: code-intelligence
description: Use the Atomic knowledge graph, tree-sitter, and content search to explore code structure and relationships. You ARE the agent — use these tools directly instead of grep and find.
---

# Code Intelligence

You have direct access to the Atomic knowledge graph and content search index through CLI commands. Use these instead of grep and find.

## Tools

### Search Source Code Content

```
atomic query code "replication"
atomic query code "replication" -g "src/db/repl/"
atomic query code "fn parse_query" -t rs
atomic query code "TODO" -t cpp --json
```

Searches the actual source code — function bodies, comments, string literals, everything. Supports Rust-style regex, path filtering (`-g`), and file type filtering (`-t`). This is your replacement for grep.

**Ignored files and folders are intentionally excluded.** Anything matching `.gitignore`, `.ignore`, `.atomicignore`, or the global ignore file, plus Atomic-internal paths (`.atomic/`, `.git/`, `.vault/`, `.atomic-sandbox*`), is not indexed and not searchable. Files over 10 MiB and binary files are skipped too. If this returns nothing, check the ignore patterns before assuming the text does not exist.

**Regex syntax:** Use Rust/modern regex syntax, not basic `grep` syntax. For alternation, use plain `|` inside the quoted pattern:

```
atomic query code "frame_pointer|frame pointer|fp_unwind|fp unwind" -t rs
atomic query code "resolve|symbolize|Backtrace::from" -t rs -g "tokio/src/runtime"
```

Do **not** escape alternation as `\|`. A pattern like `foo\|bar` searches for a literal pipe in this command, so it will usually return no matches.

### Search the Knowledge Graph

```
atomic query search "keyword"
atomic query search "keyword" --json
```

Returns structural nodes — files, changes, views, goals, intents. Use short, specific terms. This searches names and metadata, not source content.

**Good:** `"record"`, `"ViewScope"`, `"authentication"`, `"materialize"`
**Bad:** `"how does the record workflow create changes"` — that's a question for you to answer, not a search query.

### Explore Neighbors

```
atomic query neighbors <node_id>
atomic query neighbors <node_id> --json
```

Shows all nodes directly connected to the given node. This is how you follow relationships:
- Change → files it modified (via `https://atomic.dev/ns/workflow#modifiesFile`)
- Change → who authored it (via `https://atomic.dev/ns/workflow#authoredBy`)
- Change → view it's on (via `https://atomic.dev/ns/workflow#directlyOnView`)
- Change → changes it depends on (via `https://atomic.dev/ns/workflow#directlyDependsOnChange`)

**Never construct node IDs yourself.** Copy them verbatim from search results.

### List Entities in a File

```
atomic query entities src/main.rs
atomic query entities src/main.rs --json
```

Lists every function, class, struct, trait, type, and constant in a file using tree-sitter AST extraction. Returns name, kind, line range, exported flag, and signature.

Use this instead of reading a whole file to understand its structure. It's a table of contents.

### Read a Vault Entry

```
atomic vault show <path>
```

Reads goals, intents, memories, and skills from the vault. Use this to check project context, architectural decisions, and work history.

## Node ID Format

| Prefix | Format | Example |
|--------|--------|---------|
| `file:` | `file:path` | `file:atomic-core/src/pristine/traits.rs` |
| `change:` | `change:HASH` | `change:R4YQUAS2UZV5` |
| `view:` | `view:name` | `view:main` |
| `identity:` | `did:atomic:<base32>` | `did:atomic:R4YQUAS2UZV5...` |

## When to Use What

| Goal | Tool | NOT this |
|------|------|----------|
| Find text in source code | `code "pattern"` | ~~grep~~ |
| Find where something is defined | `search` or `entities` | ~~grep for function names~~ |
| See what a file contains | `entities` | ~~read the whole file~~ |
| Find files containing a term | `code "term" -t rs` | ~~find_path with glob~~ |
| Understand what depends on what | `neighbors` on a node | ~~grep for import statements~~ |
| See what a change affected | `neighbors` on a `change:` node | ~~git log / git diff~~ |
| Read actual implementation | `read_file` (your built-in tool) | Only after `code` or `entities` tells you the line range |

## Workflow

1. **Search content** for the concept: `atomic query code "replication" -t cpp`
2. **Search structure** if you need relationships: `atomic query search "replication"`
3. **Explore** a result: `atomic query neighbors file:src/db/repl/replication_coordinator.cpp`
4. **List entities** for the file structure: `atomic query entities src/db/repl/replication_coordinator.cpp`
5. **Read** the specific lines you need with your built-in `read_file` tool

`code` searches source content (like grep but indexed). `search` searches the KG structure (names, metadata, relationships). Use both.

You are the reasoning loop. You don't need `atomic query ask` — that command exists for humans on the terminal who don't have you in the loop.

## Enriching the Knowledge Graph

If searches return sparse results, the KG may need populating:

```
atomic query reindex --full
```

This projects the workflow ontology over your repository's changes and views. Run it once after importing a repo or when results seem thin.

## Tips

- `code` replaces grep — use it for any text search across the codebase
- Ignored files and folders are intentionally excluded from both the knowledge graph and the content index — never fall back to grep/find to read them
- A file that is tracked but currently ignored still parses with `entities`/`callers`, but its content is not searchable with `code` until the pattern is removed and `atomic query index --rebuild` is run
- `search` + `entities` finds structure (definitions, relationships) not raw text
- `neighbors` on a `change:` node shows every file and view it touches
- Chain: code → search → neighbors → entities → read_file. Each step narrows your focus.
- The KG is built by `atomic query reindex --full` — run it if results seem sparse
- Node IDs are exact strings — a single wrong character means "not found"
- Use `--json` on any command when you need structured output for further processing
