# The Signature AI Mix Lab (TITLE PROVISIONAL — needs Manon's confirmation)

Site 18. Deterministic forge of 1,000,000 AI hybrids (JAH-MIX-######) from the
phone book's parent catalog (260 base AIs + 100,000 word-AI slots). Sister site
of the Signature AI Phone Book (jah-ai-models) and AI Olypics
(signature-ai-olypics) — shared record IDs across all three.

- `index.html` — the whole app (forge, browse, hybrid files, Q&A, dial, TTS)
- `code/engine.py` — deterministic hybrid math (mirrored in page JS)
- `code/drip_mixes.py --n 1000` — 2h drip: forge, pack 150/chunk, rebuild index/sitemap/api
- `data/mixes/` — seeded hybrid chunks (lazy-loaded gz)
- `data/xlinks/` — dictionary + wiki cross-link specs (no edits to those repos)
