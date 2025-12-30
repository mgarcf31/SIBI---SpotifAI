# app/neo4j_search.py
import os
from neo4j import GraphDatabase
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

load_dotenv()

URI = os.getenv("NEO4J_URI", "neo4j://localhost:7687")
USER = os.getenv("NEO4J_USER", "neo4j")
PASS = os.getenv("NEO4J_PASS", "testtest")
DB   = os.getenv("NEO4J_DATABASE", "tracks")

# Conexión a Neo4j (sin cifrado si es Desktop local)
driver = GraphDatabase.driver(URI, auth=(USER, PASS), encrypted=False)

# Mismo modelo que usaste para generar los embeddings
embed_model = SentenceTransformer("distiluse-base-multilingual-cased-v2")


def search_similar_tracks(prompt: str, k: int = 10, genre_filter: str = ""):
    """
    Dado un texto tipo 'indie tranquilo para estudiar', busca canciones similares
    usando el índice vectorial track_embedding_index.
    """
    q_vec = embed_model.encode(prompt).tolist()

    cypher = """
    CALL db.index.vector.queryNodes('track_embedding_index', $k*2, $vec)
    YIELD node, score
    OPTIONAL MATCH (node)-[:BY_ARTIST]->(a:Artist)
    OPTIONAL MATCH (node)-[:HAS_GENRE]->(g:Genre)
    WITH node, score, a, collect(DISTINCT g.name) AS genres
    WHERE $genre = ''
        OR ANY(gname IN genres WHERE toLower(gname) CONTAINS toLower($genre))
    RETURN node.id          AS id,
           node.title       AS title,
           coalesce(a.name,'') AS artist,
           genres           AS genres,
           node.popularity  AS popularity,
           score
    ORDER BY score DESC
    LIMIT $k
    """

    with driver.session(database=DB) as session:
        rows = session.run(cypher, vec=q_vec, k=k, genre=genre_filter).data()
    return rows


def get_sample_tracks(limit: int = 20):
    """
    Devuelve canciones relativamente conocidas para configurar el perfil.
    Priorizamos por popularidad y luego aleatorizamos un poco.
    """
    cypher = """
    MATCH (t:Track)-[:BY_ARTIST]->(a:Artist)
    WHERE t.popularity IS NOT NULL
    WITH t, a
    ORDER BY t.popularity DESC, rand()   // primero populares, luego aleatorio
    RETURN t.id   AS id,
           t.title AS title,
           a.name AS artist,
           t.popularity AS popularity
    LIMIT $limit
    """
    with driver.session(database=DB) as session:
        return session.run(cypher, limit=limit).data()


def save_user_preferences(user_id: str, ratings: dict):
    """
    Guarda en Neo4j las valoraciones del usuario.
    ratings: dict { track_id (str) -> rating (int 0-5) }
    Crea (:User {id:user_id})-[:LIKES {rating:...}]->(:Track)
    """
    cypher = """
    MERGE (u:User {id: $user_id})
    WITH u
    UNWIND $pairs AS pr
    MATCH (t:Track {id: pr.id})
    MERGE (u)-[r:LIKES]->(t)
    SET r.rating = pr.rating
    """

    # track_id ahora es string (id de Spotify), NO lo convertimos a int
    pairs = [{"id": str(tid), "rating": int(r)} for tid, r in ratings.items()]
    if not pairs:
        return

    with driver.session(database=DB) as session:
        session.run(cypher, user_id=user_id, pairs=pairs)
def get_preference_tracks(user_id: str, limit: int = 20, page: int = 0):
    """
    Devuelve un bloque de canciones para que el usuario configure su perfil.
    - Ordenadas por popularidad (más conocidas primero)
    - Paginadas: 'page' controla qué bloque de 20 se devuelve
    - Evita géneros que el propio usuario ha puntuado mal (< 3 de media)
    """
    with driver.session(database=DB) as session:
        # 1) Géneros que el usuario suele valorar MAL
        dislike_result = session.run(
            """
            MATCH (u:User {id: $user_id})-[r:LIKES]->(t:Track)-[:HAS_GENRE]->(g:Genre)
            WITH g.name AS genre, avg(r.rating) AS avg_rating
            WHERE avg_rating < 3
            RETURN collect(genre) AS disliked_genres
            """,
            user_id=user_id,
        ).single()

        disliked_genres = dislike_result["disliked_genres"] if dislike_result and dislike_result["disliked_genres"] else []

        # 2) Canciones populares, evitando esos géneros
        tracks = session.run(
            """
            MATCH (t:Track)-[:BY_ARTIST]->(a:Artist)
            OPTIONAL MATCH (t)-[:HAS_GENRE]->(g:Genre)
            WITH t, a, collect(DISTINCT g.name) AS genres
            WHERE t.popularity IS NOT NULL
              AND (
                size(genres) = 0 OR
                NONE(gn IN genres WHERE gn IN $disliked_genres)
              )
            RETURN t.id        AS id,
                   t.title     AS title,
                   a.name      AS artist,
                   t.popularity AS popularity,
                   genres      AS genres
            ORDER BY t.popularity DESC, t.id ASC
            SKIP $skip
            LIMIT $limit
            """,
            disliked_genres=disliked_genres,
            skip=page * limit,
            limit=limit,
        ).data()

    return tracks
def artist_exists(name: str) -> bool:
    cypher = """
    MATCH (a:Artist)
    WHERE toLower(a.name) CONTAINS toLower($name)
    RETURN count(a) > 0 AS exists
    """
    with driver.session(database=DB) as session:
        rec = session.run(cypher, name=name).single()
    return rec["exists"] if rec else False