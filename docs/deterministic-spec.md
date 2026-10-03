# The Signature AI Mix Lab — Deterministic Specification (mix-determinism/1)

> "Same pair, same hybrid — forever." This document makes that promise
> provable. Implemented in `code/engine.py` and mirrored in `index.html`;
> frozen test vectors in `code/qa/test_vectors.json`; automated checks in
> `code/qa/test_determinism.py` (run on every build).

## The promise

For any hybrid number N (1 ≤ N ≤ 1,000,000), the hybrid is a pure function of N.
No randomness, no stored state, no hidden inputs. Any client — this site, an
AI agent, an independent implementation — gets the same hybrid for the same N.

## Generator version vs record version

- **GENERATOR-VERSION = 1** — the algorithm that picks parents, names, and
  variants. Any algorithm change increments this and MUST be versioned and
  disclosed; old outputs remain valid under their generator version.
- **MIX-VERSION = 1** — the Hybrid Record Standard (content schema version).
  Correcting a name's spelling is a MIX-VERSION bump, not a generator bump.

## The algorithm (generator v1)

Parent pool P = 260 parent AIs (indices 0..259: 11 system, 6 persona, 243 domain)
+ 100,000 word-AI slots (indices 260..100259; populated ones resolve to words).

```
z  = N - 1
i  = z mod P                       # first parent index
q  = z div P                        # full-cycle counter
j0 = (q * 7919 + i * 104729 + 13) mod (P - 1)
j  = j0   if j0 < i
     j0+1 otherwise                 # second parent, never equals i
v  = z mod 3                        # variant: 0, 1, or 2
```

**SEED-ALGORITHM = identity**: the seed IS the hybrid number N.

**Formal seed string**: `MIX-{N:06d}-V{variant}-FORGE1`
(e.g. `MIX-000001-V0-FORGE1`).

**PARENT-ORDER-RULE = positional**: the parents are ordered — index A first,
index B second. (A,B) ≠ (B,A); the pair is NOT commutative. The normalized
parent pair is `JAH-AI-…-…… x JAH-AI-…-……` in position order.

**Hybrid type**: variant 0 → "Logic-led fusion" (parent A dominant),
variant 1 → "Soul-led fusion" (parent B dominant), variant 2 → "True 50/50 fusion".

## Hashing

- **Hash algorithm**: SHA-256.
- **CONTENT-HASH** = SHA-256 of the canonical JSON of the record: keys sorted,
  compact separators (`,`, `:`), UTF-8. STATUS and CONTENT-HASH itself are
  excluded (status is a retrieval label, not record content).
- **SEED hash (seed_hash)**: SHA-256 of the formal seed string (labeling only).

## Statuses

- **ARCHIVED** — N ≤ seeded count: the record is stored in `data/mixes/` chunks.
- **COMPUTED-ON-DEMAND** — N > seeded count: computed live, nothing stored.
  Never call an on-demand computation an archived record.
- **NOT-YET-SEEDED** — reserved for pipeline use.
- **INVALID** — N outside 1..1,000,000. Never forge outside the range.

## Frozen test vectors

`code/qa/test_vectors.json` pins N ∈ {1, 2, 6500, 13000, 13001, 1000000}
with parents, name, variant, seed, and content hash. The build gate
`test_determinism.py` re-verifies the Python engine AND the JavaScript mirror
against them — any drift fails the build.

## Cross-check parity

The JS engine in `index.html` (lines ~235–310) is formula-identical to
`code/engine.py`. Both produce the same records on every test vector
(verified by the node parity harness in the determinism suite).

## Change history

- v1 (2026-10-03): formalization of the existing algorithm. No behavior change.
