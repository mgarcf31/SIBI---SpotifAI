from neo4j import GraphDatabase
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
import os

load_dotenv()

uri = os.getenv("NEO4J_URI", "neo4j://localhost:7687")
user = os.getenv("NEO4J_USER", "neo4j")
password = os.getenv("NEO4J_PASS", "spotify..")
DB   = os.getenv("NEO4J_DATABASE", "tracks-big")

driver = GraphDatabase.driver(uri, auth=(user, password), encrypted=False)

model = SentenceTransformer("distiluse-base-multilingual-cased-v2")

def make_description(record: dict) -> str:
    """
    Crea una descripción en texto de la canción para el embedding.
    """
    title = record["title"]
    artist = record["artist"]
    genres = ", ".join(record.get("genres") or []) or "sin género"
    energy = record.get("energy")
    danceability = record.get("danceability")
    acousticness = record.get("acousticness")
    valence = record.get("valence")
    tempo = record.get("tempo")

    return (
        f"{title} by {artist}. Genres: {genres}. "
        f"Energy {energy}, danceability {danceability}, "
        f"acousticness {acousticness}, valence {valence}, "
        f"tempo {tempo} BPM."
    )


with driver.session(database=DB) as session:
    result = session.run("""
        MATCH (t:Track)-[:BY_ARTIST]->(a:Artist)
        OPTIONAL MATCH (t)-[:HAS_GENRE]->(g:Genre)
        WITH t, a, collect(DISTINCT g.name) AS genres
        RETURN t.id AS id,
               t.title AS title,
               a.name AS artist,
               genres,
               t.energy AS energy,
               t.danceability AS danceability,
               t.acousticness AS acousticness,
               t.valence AS valence,
               t.tempo AS tempo
    """)

    records = list(result)

    for r in records:
        desc = make_description(r)
        emb = model.encode(desc).tolist()
        session.run("""
            MATCH (t:Track {id: $id})
            SET t.embedding = $emb
        """, id=r["id"], emb=emb)

print("✅ Embeddings creados y guardados en Neo4j (tracks_big).")
