# 0019. The tutor's material index is pgvector, in the same database

Date: 2026-09-18
Status: accepted

## Context
The dashboard tutor could recall a doctor's own history — consultations,
debriefs, what they had read — and could not answer the question they actually
ask it: "how do I safety-net chest pain?" Its `search_material` tool returned
"not available in this deployment", which is an honest answer and not a useful
one. Answering it means retrieving passages of the study material by meaning,
which means embeddings and a vector index.

b2c already does this with Pinecone: `management_text_utils.py` chunks a
summary, an embedding goes to a Pinecone namespace, and search comes back with
ids to look up. So the default was to port that, and the question was whether
to.

Two things argued against carrying it over. The first is that the corpus is
small — the platform library and the published media are thousands of passages,
not millions of documents — and a dedicated vector database is built for a
problem two or three orders of magnitude larger than the one we have. The
second is that a second datastore has a second outage, a second bill, a second
set of credentials, and its own idea of what is published. The index in b2c
drifted from the database repeatedly: an item unpublished in Postgres stayed in
Pinecone, and search went on returning it.

Against that, Postgres is not a vector database and never will be. IVFFlat
recall is approximate, the index has to be rebuilt as the corpus grows, and
there is no managed tier to hand the problem to when it stops fitting.

## Decision
The tutor's material index is **pgvector, in the same database as everything
else**, behind `core.ports.MaterialIndex`.

Three consequences follow, and they are the actual decision:

**The index is written in the same transaction as the rows it describes.** A
re-index that fails half way leaves no half-indexed document. The drift that
happened in b2c is not a bug we fixed here; it is a state the schema cannot
reach.

**The exam filter is a `WHERE`, not a post-filter.** A doctor may only be read
out of material they hold. Filtering after retrieval would throw away the best
passages and return worse ones, or nothing — and getting it wrong reads out
material somebody has not bought. In SQL it is one clause, applied before the
ordering, and `tests/repository/test_material_index.py` plants the nearest
passage in an exam the learner does not hold to prove it.

**The port is the exit.** `MaterialIndex` names passages, a corpus and an exam
filter — not Postgres. The day the corpus is large enough that IVFFlat recall
is the constraint, a second adapter is one module, and the fake in
`tests/support/fakes.py` is what every test above the boundary already uses.

Two smaller choices go with it. The `pgvector` Python package is **not** a
dependency: the extension does the work, the column type is thirty lines in
`vector_column.py`, and the one query that needs the distance operator writes
it out. And the chunker is a byte-for-byte port of b2c's, pinned by an oracle —
where a chunker cuts decides what the tutor can quote, and moving a boundary
changes the answer to a clinical question with no diff anywhere near it.

`docs/OPEN-QUESTIONS.md` M-3 asked which vector index. This answers it for the
tutor. The media slice's own `VectorIndex` — whole items by id, for its search
box — is left alone; it is a different shape, and adopting this adapter for it
is a separate decision with a separate migration.

## Consequences
The database now needs the `vector` extension, so the local compose file and
the test container are pinned to `pgvector/pgvector:pg16` rather than stock
Postgres. That is a real cost: a contributor with an existing container has to
let it be recreated, and any deployment target must offer the extension.

Embeddings are `text-embedding-3-small` at 1536 dimensions, and the column's
width is DDL. Changing the model means re-embedding everything, so the model is
named in `embedder.py` as a constant rather than a setting — a setting that
disagreed with the migration would be a setting that cannot be set.

Re-indexing is nightly plus an admin route, not on publish. Embedding the whole
library takes minutes and costs money; an author who cannot wait has a button.

A deployment with no `OPENAI_API_KEY` has no index, and `build_material_index`
returns `None` rather than an empty one. The tutor then says it cannot look
something up, instead of saying the material does not cover it — two claims
that a spoken answer delivers with equal confidence, and only one of which is
true.
