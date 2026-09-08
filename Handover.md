# Doc_Bot — Handover

## What got done this session

### Replace path — COMPLETE and PROVEN LIVE
The open ticket from last session is closed. `process_one_file` now has a four-branch
status contract, every branch verified by forcing it, not just reasoned:

- **`stored`** — happy path. Also proved the SHRINK case: ingested a doc at 55 chunks,
  deleted a section, re-ingested → landed at exactly 54. No orphans, no doubling.
  This is the case that would have exposed an upsert-only bug. delete-by-doc_id handled it.
- **`embedding_error`** — embed throws; delete never runs; old version fully intact. Safe/retry.
  (Only branch not force-tested — it's the simplest, low risk.)
- **`deletion_error`** — delete throws; add never runs; old version intact; other docs untouched. Safe/retry. FORCED, confirmed.
- **`storage_error`** — delete succeeded, add failed → this doc_id goes to 0, other docs
  untouched. The honest empty-hole state. FORCED, confirmed count==0 for the doc.

**Ordering invariant, now enforced by structure not luck:**
embed (riskiest, network) runs FIRST, before the destructive delete. delete runs OUTSIDE
the add-try, so the storage_error message ("document is now empty") is always true when it
fires. Every SAFE failure leaves old data untouched; the only path that reaches
deleted-but-empty is the one loud escalate-to-admin branch.

**Why delete, not upsert:** upsert only touches ids it writes, so a shrinking doc leaves
orphan rows (`_54`+). `delete(where={"doc_id": doc_id})` wipes ALL rows for the doc
regardless of count/ids. That's non-negotiable — proven by the 55→54 test.

### Cross-document isolation — proven (bonus)
During testing the collection held 4 docs simultaneously. Forcing a failure on one doc
left all others at their exact counts. doc_id-scoped delete gives the core of cross-doc
scoping for free — the thing previously filed as "deliberately not built."

### Store cleanup — done
- Deleted junk `original.docx` (1-chunk doc, recognized, not needed) via one-time REPL
  `chunk_collection.delete(where={"doc_id": "original.docx"})`.
- Reclaimed the orphaned on-disk `doc_summaries` collection via
  `chroma_client.delete_collection("doc_summaries")` — it DID exist, now gone.
- Current store contents (verified via Counter):
  mentor-mp-advanced-user-guide.pdf: 4427
  MCal_User_Guide.md: 3588
  Instructions for AOI in Program.pdf: 114
  MCal_CQ_Bot_User_Guide_v2.docx: 54

### Dead code swept
- Deleted `summarize` / `version_check` (commented-out).
- Removed `from tracemalloc import start` (config.py) — stray; the `start` names in
  embed_texts/chunker are local, unaffected.
- Removed `llm` and `llm_embed` from ingest.py's import line — both dead THERE
  (summarize gone; embed_texts lives in config.py and holds llm_embed itself).
  NOTE: `llm` is still DEFINED in config.py and ALIVE — router.py's answer_question uses it. Do not remove the definition.
- Verified `summary_collection` / `DUPLICATE_THRESHOLD` are already gone from config.py
  (handover was stale on this — checked the file, not the note).
- Removed debug scaffolding from inside process_one_file: the heading-print loop and the
  dead `for c in chunks: body = ...` loop. Function is now production-shaped.

## OPEN — pick up here in the morning

### 1. Finish the __main__ CLI (small, in progress)
Decided: `__main__` becomes a CLI entry point, since running `python ingest.py` is the
ONLY ingest path until the Power App front end exists. Target shape:

```python
if __name__ == "__main__":
    import sys
    result = process_one_file(sys.argv[1])
    print(result)
```

Then `python ingest.py "path/to/file.pdf"` ingests any named file — no editing between runs.
Beau was mid-learning `sys.argv` when we stopped (argv[0]=script name, argv[1]=first real arg).
DECISIONS STILL TO MAKE:
  - bare `argv[1]` (raw IndexError if you forget the path) vs a one-line usage guard. It's
    your personal tool right now — your call.
  - Confirm understood: process_one_file wants a PATH, not a doc_id. It does
    os.path.basename() for the id and passes the whole thing to extract_text. The bare
    filenames worked only because the files sat in the working dir. CLI + future Power App
    must both pass real paths.

### 2. The real production caller (next build after CLI)
Power App front end: manager uploads a file, presses a button. Something server-side
(Flow / API endpoint) must:
  (a) save the uploaded file to a path,
  (b) call process_one_file(path),
  (c) read the returned `status` and show the manager the right message:
      stored → "done"; embedding_error/deletion_error → "retry, nothing lost";
      storage_error → "this doc is now empty, alert admin".
The four-status contract was built EXACTLY so this caller can do (c). It's ready and
waiting for its consumer.

## DEFERRED / watch items
- **Ingest latency** — ~7 min for the 4,427-chunk manual at 2s/batch. The UX problem from
  the start. Future optimization: bigger batches, probe the embed endpoint's real RPM
  ceiling. Not urgent until the Power App makes latency user-visible.
- **4,427 chunks for one manual** — table-heavy doc shreds into thousands of atomic rows.
  By design, but the real driver of ingest cost. Sanity-check nothing's inflating it.
- **embedding_error branch** — never force-tested (only one of the four). Low risk, but if
  you want completeness, force it once.

## Standing principles (unchanged)
- Don't tune knobs against hypotheticals — act on real query misses only.
- Replace-always is correct FOR THIS PROJECT: re-upload by a human IS the change signal;
  no separate change-detection needed. (Pressure-tested this session, held.)
- Verify live over reasoned-correct — this session's whole value was forcing the branches
  and reading real counts, not trusting the reasoning. The 8130 "mystery" dissolved the
  moment we ran the Counter.
- Honest miss beats silent staleness — the entire replace-path failure design follows from this.

## Working method
Design before code. Beau writes the code; Jarvis hints/Socratic, catches bugs, doesn't
write it. Brutally honest mentor — challenge decisions that work against the project.
Recurring bug traps: indentation-as-control-flow (#1); variable-name drift; package-vs-
import name confusion; chained-transform bugs; function-boundary confusion.