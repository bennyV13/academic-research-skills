---
name: ars-cache-invalidate
description: >-
  Use this skill to invalidate the persistent academic verification cache for a
  specific citation key or reset the entire verification cache store.
---

# ARS Cache Invalidate

Invalidates the persistent verification cache for one or more citation keys, forcing the next pipeline run to re-verify metadata and retrieval live against Crossref, OpenAlex, Semantic Scholar, and arXiv.

## When to Use

- When a cited paper's publication status or metadata has changed (e.g. preprint gained a formal DOI).
- When a cached verification verdict is suspected to be stale or erroneous.

## Execution

Execute the invalidation script using `run_command` as a single-line command:

```bash
python3 scripts/ars_cache_invalidate.py <citation_key>
```

To invalidate all cached entries, remove the database file:

```bash
rm -f ~/.cache/ars/verification.db
```
