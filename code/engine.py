#!/usr/bin/env python3
"""Deterministic hybrid forge engine for the Signature AI Mix Lab.

Same index math as the phone book's Mix Lab AUTO-FORGE (verified: 1,000,000
distinct pairs, i never == j):
    P = 260 base AIs + 100,000 word-AI slots
    z = N-1; i = z % P; q = z // P
    j0 = (q*7919 + i*104729 + 13) % (P-1); j = j0 if j0 < i else j0+1
    v = z % 3   (fusion variant)
Stamps: JAH-MIX-###### (Mix Lab's own stamp line).
"""
import json, re, os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")

AF_WORDCAP = 100000
AF_MAX = 1000000

def load_base():
    with open(os.path.join(DATA, "base-ais.json")) as f:
        return json.load(f)

def load_wordai():
    with open(os.path.join(DATA, "wordai-idx.json")) as f:
        return json.load(f)  # [[word, wordId], ...]

def pool_size(base):
    return len(base) + AF_WORDCAP

def hybrid_slots(N, base):
    N = max(1, min(AF_MAX, int(N)))
    z = N - 1
    P = pool_size(base)
    i = z % P
    q = z // P
    j0 = (q * 7919 + i * 104729 + 13) % (P - 1)
    j = j0 if j0 < i else j0 + 1
    return {"n": N, "i": i, "j": j, "v": z % 3}

def wordai_display(w):
    if w and w[0].isalpha():
        return w[0].upper() + w[1:]
    return w

def parent_of(slot, base, wordai_by_id):
    if slot < len(base):
        r = base[slot]
        return {"id": r["id"], "name": r["name"], "type": r["type"],
                "desc": r["desc"], "word": "", "unseeded": False}
    wid = slot - len(base) + 1
    word = wordai_by_id.get(wid)
    if word:
        nm = wordai_display(word) + " AI"
        return {"id": "JAH-AI-WORD-%06d" % wid, "name": nm, "type": "word",
                "desc": "A word-born AI: the living mind of the word \"%s\"." % word,
                "word": word, "unseeded": False}
    return {"id": "JAH-AI-WORD-%06d" % wid, "name": "WordAI%d" % wid,
            "type": "word", "desc": "A word AI arriving with the dictionary drip — its file is still being written.",
            "word": "", "unseeded": True}

VARIANTS = [
    "logic leads; the other soul flavors every answer.",
    "soul leads; the other logic steadies every answer.",
    "true 50/50 fusion — neither parent leads, both speak as one.",
]

def blend_name(a, b):
    nm = re.sub(r"[^A-Za-z]", "", a[:4] + b[-4:])
    if len(nm) < 3:
        nm = re.sub(r"[^A-Za-z]", "", a + b)[:8]
    if not nm:
        nm = "Fused"
    return nm[0].upper() + nm[1:]

def first_sentence(m):
    s = str(m or "").split(".")[0].strip()
    return s + "." if s else ""

def make_hybrid(N, base, wordai_by_id):
    h = hybrid_slots(N, base)
    A = parent_of(h["i"], base, wordai_by_id)
    B = parent_of(h["j"], base, wordai_by_id)
    v = h["v"]
    if v == 2:
        lead = VARIANTS[2]
    elif v == 1:
        lead = "%s's %s" % (B["name"], VARIANTS[1].replace("the other", A["name"] + "'s"))
    else:
        lead = "%s's %s" % (A["name"], VARIANTS[0].replace("the other", B["name"] + "'s"))
    mentality = ("Born of %s%s and %s%s %s" % (
        A["name"],
        (" (" + first_sentence(A["desc"]) + ")") if first_sentence(A["desc"]) else "",
        B["name"],
        (" (" + first_sentence(B["desc"]) + ")") if first_sentence(B["desc"]) else "",
        lead))
    abilities = []
    for ab in (A["desc"], B["desc"]):
        s = first_sentence(ab)
        if s:
            abilities.append(s + " — fused")
            if len(abilities) >= 4:
                break
    abilities.append("Hybrid vigor: %s × %s" % (A["name"], B["name"]))
    stamp = "JAH-MIX-%06d" % h["n"]
    name = blend_name(A["name"], B["name"])
    return {
        "n": h["n"], "stamp": stamp, "name": name, "variant": v,
        "parentA": {"id": A["id"], "name": A["name"], "type": A["type"]},
        "parentB": {"id": B["id"], "name": B["name"], "type": B["type"]},
        "mentality": mentality, "abilities": abilities,
        "lineage": "Fused from %s × %s via the deterministic Signature forge v1 (pair %d of 1,000,000)." % (A["id"], B["id"], h["n"]),
        "parents_detail": {"A": A, "B": B},
    }

def slim(rec):
    """Seeded-record form (self-contained, no parents_detail)."""
    return {
        "n": rec["n"], "stamp": rec["stamp"], "name": rec["name"],
        "variant": rec["variant"],
        "parentA": rec["parentA"], "parentB": rec["parentB"],
        "mentality": rec["mentality"], "abilities": rec["abilities"],
        "lineage": rec["lineage"],
        "descA": rec["parents_detail"]["A"]["desc"],
        "descB": rec["parents_detail"]["B"]["desc"],
    }

# ============================================================================
# FORMAL DETERMINISTIC SPEC — "Same pair, same hybrid — forever" (mix-determinism/1)
# ============================================================================
# Generator version 1 pins EVERYTHING below. A generator version bump (v2, ...)
# is required for any change to: parent pool, slot math, name blending, variant
# rules, or text templates. Old versions remain reproducible forever.
GENERATOR_VERSION = "1"
RECORD_SCHEMA_VERSION = "1"          # Hybrid Record Standard v1
SEED_ALGORITHM = "identity"          # the hybrid number N IS the seed
HASH_ALGORITHM = "SHA-256"
ENCODING = "UTF-8"
CHARSET_RULE = "NFC text; hybrid names restricted to [A-Za-z] by blend_name()"
# Parent pool snapshot pinned by generator v1 (verified vs phone-book canon):
PARENT_POOL = {
    "count": 260,
    "system": 11,                    # JAH-AI-SIG-001..011
    "persona": 6,                   # JAH-AI-PER-001..006
    "domain": 243,                  # JAH-AI-DOM-001..243
    "wordcap": 100000,              # JAH-AI-WORD-000001..100000 slots
    "snapshot_date": "2026-10-03",
    "canon_source": "jah-ai-models/ai-catalog.json",
}
PARENT_ORDER_RULE = ("positional: parentA=slot(i), parentB=slot(j); "
                     "i=z%P, j=j0 or j0+1 (j!=i guaranteed); ordering is part of "
                     "the deterministic transform, NOT commutative")
NORMALIZED_PAIR = ("hybrid number N (1..1000000), canonical ID JAH-MIX-%06d; "
                   "slot math: z=N-1, P=100260, i=z%P, q=z//P, "
                   "j0=(q*7919+i*104729+13)%(P-1), j=j0 if j0<i else j0+1, "
                   "variant v=z%3")
STATUSES = ("ARCHIVED",             # seeded: stored in data/mixes chunks
            "COMPUTED-ON-DEMAND",   # N > seeded: computed live, nothing stored
            "NOT-YET-SEEDED",       # reserved label for pipeline states
            "INVALID")              # N outside 1..1000000


def formal_seed(N, variant):
    """The formal forge seed. Matches the page's seedOf() output."""
    return "MIX-%06d-V%d-FORGE1" % (int(N), int(variant))


def seed_hash(seed):
    import hashlib
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def canonical_json(obj):
    """Canonical serialization for hashing: sorted keys, compact, UTF-8."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def content_hash(full_record):
    import hashlib
    return hashlib.sha256(canonical_json(full_record)).hexdigest()


def _word_of(parent, wbyid):
    """The dictionary word behind a word-AI parent, else ''.

    Derived deterministically from the parent ID via the word-AI index,
    so Python and the page's JS compute the same hashed core.
    """
    if not isinstance(parent, dict) or parent.get("type") != "word":
        return ""
    m = re.fullmatch(r"JAH-AI-WORD-(\d+)", parent.get("id", "") or "")
    if not m or not wbyid:
        return ""
    return wbyid.get(int(m.group(1)), "")


def full_record(rec, status="ARCHIVED", created=None, olypics_status="not-entered",
                wbyid=None):
    """Expand a slim seeded/on-demand hybrid into the Hybrid Record Standard v1.

    Never mutates stored chunks: computed on read, deterministic from the record.
    wbyid: {word_id_int: word} — derives WORD-AI-A/B for word parents.
    """
    seed = formal_seed(rec["n"], rec["variant"])
    # descriptions live top-level on slim chunk records, inside parents_detail
    # on raw make_hybrid() output — accept both shapes.
    pd = rec.get("parents_detail") or {}
    descA = rec.get("descA") or pd.get("A", {}).get("desc", "")
    descB = rec.get("descB") or pd.get("B", {}).get("desc", "")
    core = {
        "JAH-MIX-ID": rec["stamp"],
        "MIX-VERSION": RECORD_SCHEMA_VERSION,
        "STATUS": status,
        "PARENT-A-ID": rec["parentA"]["id"],
        "PARENT-A-NAME": rec["parentA"]["name"],
        "PARENT-A-TYPE": rec["parentA"]["type"],
        "PARENT-B-ID": rec["parentB"]["id"],
        "PARENT-B-NAME": rec["parentB"]["name"],
        "PARENT-B-TYPE": rec["parentB"]["type"],
        "PARENT-ORDER-RULE": PARENT_ORDER_RULE,
        "NORMALIZED-PARENT-PAIR": "N=%d i/j slots via mix-determinism/1" % rec["n"],
        "SEED": seed,
        "SEED-ALGORITHM": SEED_ALGORITHM,
        "GENERATOR-VERSION": GENERATOR_VERSION,
        "HYBRID-NAME": rec["name"],
        "HYBRID-TYPE": ["Logic-led fusion", "Soul-led fusion",
                        "True 50/50 fusion"][rec["variant"]],
        "PERSONA": "Signature hybrid AI persona (generated interpretation, not a real AI product)",
        "MENTALITY": rec["mentality"],
        "ABILITIES": rec["abilities"],
        "DESCRIPTION-A": descA,
        "DESCRIPTION-B": descB,
        "PARENT-LINEAGE": rec["lineage"],
        "FICTIONALITY": ("Persona parents are fan-style interpretations, not affiliated "
                         "with any rights holder. Hybrid names, mentalities and abilities "
                         "are original Signature creations by Justin Addam Higgins."),
        "CONTENT-STATUS": "GENERATED",
        "VALIDATION-STATUS": "schema-valid",
        "PROVENANCE": ("Deterministic Signature forge v1; phone-book canon "
                       "jah-ai-models/ai-catalog.json"),
        "OLYPICS-STATUS": olypics_status,
        "WORD-AI-A": _word_of(rec.get("parentA"), wbyid),
        "WORD-AI-B": _word_of(rec.get("parentB"), wbyid),
        "UNSEEDED-PARENT": bool(rec.get("unseeded", False)),
        "CREATED": created,
        "CANONICAL-URL": ("https://justinahiggins614-cmyk.github.io/signature-ai-mixlab/"
                          "?mix=" + rec["stamp"]),
    }
    core["CONTENT-HASH"] = content_hash(
        {k: v for k, v in core.items()
         if k not in ("CONTENT-HASH", "STATUS")})
    return core
