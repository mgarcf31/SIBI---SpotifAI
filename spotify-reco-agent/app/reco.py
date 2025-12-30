# app/reco.py
import os
import numpy as np
from .auth import sp_client
from .graph import run, upsert_track

AUDIO_COLS = [
    "danceability","energy","valence","tempo",
    "acousticness","instrumentalness","liveness","speechiness"
]

def ingest_user(uid: str):
    """
    Descarga top tracks del usuario desde Spotify,
    guarda nodos/relaciones en Neo4j y añade audio features al Track.
    """
    sp = sp_client()
    tops = sp.current_user_top_tracks(limit=50)["items"]
    if not tops:
        return {"ok": True, "tracks": 0}

    ids = [t["id"] for t in tops]
    feats = sp.audio_features(ids)

    for t, f in zip(tops, feats):
        # upsert del track + artista
        upsert_track({
            "id": t["id"],
            "name": t["name"],
            "pop": t.get("popularity", 0),
            "artist_id": t["artists"][0]["id"],
            "artist_name": t["artists"][0]["name"],
        })
        # relación LIKE y guardado de features en el nodo Track
        run("""
        MERGE (u:User {id:$uid})
        MERGE (tr:Track {id:$tid})
        MERGE (u)-[:LIKES]->(tr)
        SET tr.features = $features
        """, {
            "uid": uid,
            "tid": t["id"],
            "features": {k: float(f[k]) if (f and f.get(k) is not None) else None for k in AUDIO_COLS}
        })

    return {"ok": True, "tracks": len(tops)}

def _cosine(a, b):
    a, b = np.array(a, dtype=float), np.array(b, dtype=float)
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(a.dot(b) / (na * nb))

def _user_profile(uid: str):
    rows = run("""
    MATCH (:User {id:$uid})-[:LIKES]->(t:Track)
    WHERE exists(t.features)
    RETURN t.features AS f
    """, {"uid": uid})
    if not rows:
        return None
    M = []
    for r in rows:
        vec = [(r["f"].get(k, 0) if r["f"] else 0) for k in AUDIO_COLS]
        M.append(vec)
    M = np.array(M, dtype=float)
    return np.nan_to_num(M, nan=0.0).mean(axis=0).tolist()

def recommend_by_features(uid: str, k: int = 20):
    """
    Baseline: similitud coseno entre el perfil promedio del usuario y tracks del grafo.
    """
    profile = _user_profile(uid)
    if profile is None:
        return []

    cands = run("""
    MATCH (t:Track) 
    WHERE exists(t.features)
    RETURN t.id AS id, t.name AS name, t.features AS f
    LIMIT 500
    """)

    scored = []
    for c in cands:
        vec = [(c["f"].get(x, 0) if c["f"] else 0) for x in AUDIO_COLS]
        scored.append((c["id"], c["name"], _cosine(profile, vec)))

    scored.sort(key=lambda x: x[2], reverse=True)
    return [{"id": i, "name": n, "score": s} for i, n, s in scored[:k]]
