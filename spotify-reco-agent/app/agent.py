# app/agent.py
import os
import re
from collections import defaultdict
from dotenv import load_dotenv
from llama_index.llms.ollama import Ollama

from .neo4j_search import search_similar_tracks

# Detección de idioma
from langdetect import detect, DetectorFactory, LangDetectException
DetectorFactory.seed = 0

# ======================================================
# Configuración
# ======================================================
load_dotenv()

MODEL_NAME = os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b")
print("USANDO MODELO OLLAMA:", MODEL_NAME)

llm = Ollama(
    model=MODEL_NAME,
    temperature=0.15,
    request_timeout=60.0,
    system_prompt=(
        "Eres un recomendador musical.\n"
        "Respondes SIEMPRE en español.\n"
        "No inventes datos.\n"
        "No escribas poesía, rimas ni metáforas.\n"
        "Cuando te pidan explicación, escribe 2-3 frases normales y directas.\n"
    ),
)

# ======================================================
# Utilidades de parsing
# ======================================================
GENRE_KEYWORDS = {
    "rock": "rock",
    "pop": "pop",
    "latin": "latin",
    "reggaeton": "reggaeton",
    "reggaetón": "reggaeton",
    "indie": "indie",
    "acoustic": "acoustic",
    "metal": "metal",
    "jazz": "jazz",
    "hip hop": "hip hop",
    "hip-hop": "hip hop",
    "rap": "rap",
}

BLOCK_GENRES_DEFAULT = {
    "korean", "japanese", "turkish", "arabic",
    "cantopop", "indian", "thai", "russian",
    "brazilian", "latin jazz", "anime", "j-pop",
    "gaming", "world", "afrobeats"
}


RELAX_WORDS = {"relajar", "relajado", "relajada", "tranquila", "tranquilo", "calma", "chill", "suave", "descansar"}
STUDY_WORDS = {"estudi", "concentr", "focus", "trabajar"}
PARTY_WORDS = {"fiesta", "bail", "gym", "entren", "energ", "motivar"}


def detect_genre(user_query: str) -> str:
    q = user_query.lower()
    for word, genre in GENRE_KEYWORDS.items():
        if word in q:
            return genre
    return ""


def parse_num_songs_from_query(user_query: str, default: int = 7, max_k: int = 10) -> int:
    nums = re.findall(r"\d+", user_query)
    if not nums:
        return default
    return max(1, min(int(nums[0]), max_k))


def wants_relax(user_query: str) -> bool:
    q = user_query.lower()
    return any(w in q for w in RELAX_WORDS)


def wants_study(user_query: str) -> bool:
    q = user_query.lower()
    return any(w in q for w in STUDY_WORDS)


def wants_party(user_query: str) -> bool:
    q = user_query.lower()
    return any(w in q for w in PARTY_WORDS)


def user_allows_any_language(user_query: str) -> bool:
    q = user_query.lower()
    return any(
        x in q for x in [
            "cualquier idioma", "da igual el idioma", "en cualquier idioma",
            "me da igual el idioma", "idioma indistinto", "any language",
        ]
    )


def user_wants_only_spanish_or_english(user_query: str) -> bool:
    q = user_query.lower()
    return any(
        x in q for x in [
            "solo español", "solo espanol", "solo inglés", "solo ingles",
            "solo español o inglés", "solo espanol o ingles",
            "en español o inglés", "en espanol o ingles",
            "spanish or english",
        ]
    )

# ======================================================
# Normalización y filtros
# ======================================================
def mostly_latin(text: str, threshold: float = 0.85) -> bool:
    if not text:
        return True
    allowed_extra = set("áéíóúÁÉÍÓÚñÑüÜ¿¡")
    latin = 0
    for c in text:
        if c.isascii() or c in allowed_extra:
            latin += 1
    return (latin / len(text)) >= threshold


def normalize_artist_name(artist: str) -> str:
    if not artist:
        return ""
    parts = [p.strip().lower() for p in artist.split(",") if p.strip()]
    return parts[0] if parts else ""


def limit_tracks_per_artist(tracks: list[dict], max_per_artist: int = 2) -> list[dict]:
    counts = defaultdict(int)
    out = []
    for t in tracks:
        artist_key = normalize_artist_name(t.get("artist", ""))
        if counts[artist_key] < max_per_artist:
            out.append(t)
            counts[artist_key] += 1
    return out


# -------------------------
# Detección de idioma
# -------------------------
def detect_language(text: str) -> str | None:
    text = (text or "").strip()
    if len(text) < 8:
        return None
    try:
        return detect(text)
    except LangDetectException:
        return None


def passes_language_filter(user_query: str, title: str, artist: str) -> bool:
    if user_allows_any_language(user_query):
        return True

    text = f"{title} {artist}".strip()
    lang = detect_language(text)
    if lang is None:
        return True

    if user_wants_only_spanish_or_english(user_query):
        return lang in {"es", "en"}

    # Suave por defecto (pt a veces se confunde con es)
    return lang in {"es", "en", "pt"}


def filter_by_language_and_genre(user_query: str, tracks: list[dict]) -> list[dict]:
    filtered = []
    for t in tracks:
        title = t.get("title") or ""
        artist = t.get("artist") or ""
        combined = f"{title} {artist}"

        if not mostly_latin(combined):
            continue

        genres = [g.lower() for g in (t.get("genres") or [])]
        if any(bg in genres for bg in BLOCK_GENRES_DEFAULT):
            continue

        if not passes_language_filter(user_query, title, artist):
            continue
        # si el artista tiene caracteres raros (no latinos), fuera
        if not mostly_latin(artist, threshold=0.95):
            continue

        filtered.append(t)
    return filtered
def calm_score(track: dict, user_query: str) -> float:
    """
    Score simple: mayor => más “tranquilo”.
    Usa género y popularidad como señales.
    """
    genres = [g.lower() for g in (track.get("genres") or [])]
    pop = track.get("popularity") or 0

    score = 0.0

    # géneros típicos de calma
    calm_genres = {"lofi", "ambient", "acoustic", "chill", "study", "piano", "classical", "soul"}
    noisy_genres = {"gaming", "hardstyle", "edm", "metal", "techno", "drum and bass"}

    if any(g in calm_genres for g in genres):
        score += 3.0
    if any(g in noisy_genres for g in genres):
        score -= 3.0

    # si el usuario pide relax, favorecemos temas no “mega mainstream”
    if wants_relax(user_query):
        score += max(0.0, 1.5 - (pop / 100.0))  # cuanto menos popular, un pelín más calmado
    return score

# ======================================================
# Explicaciones seguras
# ======================================================
def safe_explanation(user_query: str, results: list[dict]) -> str:
    genre_counts = defaultdict(int)
    pops = []

    for r in results:
        for g in (r.get("genres") or []):
            genre_counts[g.lower()] += 1
        if isinstance(r.get("popularity"), (int, float)):
            pops.append(r["popularity"])

    top_genres = sorted(genre_counts.items(), key=lambda x: x[1], reverse=True)[:3]
    genres_txt = ", ".join(g for g, _ in top_genres) if top_genres else "varios estilos"
    pop_avg = int(sum(pops) / len(pops)) if pops else None

    q = user_query.lower()
    liked_artist = ("me gusta" in q) or ("me encant" in q) or ("me flipa" in q)

    if wants_relax(q):
        mood = "un ambiente tranquilo y relajado"
    elif wants_party(q):
        mood = "más energía y ritmo"
    elif wants_study(q):
        mood = "acompañar sin distraer"
    else:
        mood = "un rollo parecido a lo que buscas"

    # Si viene de “me gusta X”, sonar más natural y menos “plantilla”
    if liked_artist:
        first = f"Te he dejado temas bastante {('pegadizos y modernos' if 'pop' in genres_txt else 'en la línea de lo que sueles escuchar')}, tirando a {genres_txt}."
    else:
        first = f"La selección mantiene {mood}, con predominio de {genres_txt}."

    if pop_avg is not None:
        return f"{first} Además, la mayoría son bastante accesibles (popularidad media ~{pop_avg}), ideales para entrar rápido."
    return f"{first} Si me dices 1–2 canciones que te encanten, lo ajusto aún más."


def explanation_looks_hallucinated(text: str) -> bool:
    if not text or len(text.strip()) < 20:
        return True

    t = text.strip().lower()

    refusal_markers = [
        "lo siento", "no puedo ayudarte", "no puedo ayudar", "no tengo información",
        "no dispongo de información", "no tengo datos", "no puedo crear una explicación",
        "no puedo generar", "no estoy seguro",
    ]
    if any(m in t for m in refusal_markers):
        return True

    if "\n" in text.strip():
        return True

    if '"' in text or "“" in text or "”" in text:
        return True

    if re.search(r"\b(19|20)\d{2}\b", text):
        return True
    if "me hace sentir cómodo" in t or "del usuario" in t:
        return True


    bad_phrases = [
        "este álbum", "podrías considerar", "en este contexto",
        "según las características del grafo", "base de datos", "grafo",
        "este usuario", "su agradecimiento",
    ]
    if any(bp in t for bp in bad_phrases):
        return True

    if len(text.split()) > 60:
        return True

    return False


def sanitize_explanation(text: str, results: list[dict]) -> str:
    if not text:
        return text
    out = text
    out = re.sub(r"\bme encanta\b", "queda muy bien", out, flags=re.IGNORECASE)
    out = re.sub(r"me hace sentir cómodo", "va muy bien para desconectar", out, flags=re.IGNORECASE)
    out = re.sub(r"\bdel usuario\b", "", out, flags=re.IGNORECASE)
    out = re.sub(r"\busuario\b", "tú", out, flags=re.IGNORECASE)


    # quitar títulos y artistas si se cuelan
    for r in results:
        title = (r.get("title") or "").strip()
        artist = (r.get("artist") or "").strip()
        if title:
            out = re.sub(re.escape(title), "estas canciones", out, flags=re.IGNORECASE)
        if artist:
            out = re.sub(re.escape(artist), "ese artista", out, flags=re.IGNORECASE)

    # evitar frases raras típicas
    out = re.sub(r"\beste usuario\b", "tú", out, flags=re.IGNORECASE)
    out = re.sub(r"\s{2,}", " ", out).strip()
    return out

# ======================================================
# FUNCIÓN PRINCIPAL
# ======================================================
def chat_with_agent(user_query: str, k: int | None = None) -> str:
    cleaned = user_query.strip()

    if len(cleaned) < 4:
        return (
            "😊 Cuéntame un poco más: un género, "
            "un estado de ánimo o algún artista que te guste."
        )

    k_effective = k if k is not None else parse_num_songs_from_query(cleaned)
    genre = detect_genre(cleaned)

    raw = search_similar_tracks(
        cleaned,
        k=max(k_effective * 8, 50),
        genre_filter=genre,
    )

    if not raw:
        return "No he encontrado canciones que encajen con lo que pides 😔."

    # ✅ 1) FILTRAR primero (y SIEMPRE definir filtered)
    filtered = filter_by_language_and_genre(cleaned, raw)

    # ✅ 2) Si el filtro es demasiado estricto, usar raw
    if not filtered:
        filtered = raw

    # ✅ 3) Reordenar SOLO después de existir filtered
    if wants_relax(cleaned) or wants_study(cleaned):
        filtered = sorted(
            filtered,
            key=lambda t: calm_score(t, cleaned),
            reverse=True
        )

    # ✅ 4) Limitar por artista
    candidates = limit_tracks_per_artist(filtered, max_per_artist=2)
    if len(candidates) < k_effective:
        candidates = limit_tracks_per_artist(filtered, max_per_artist=3)

    results = candidates[:k_effective]
    if not results:
        return "No he encontrado canciones que encajen con lo que pides 😔."

    # Lista final
    lines = []
    for i, r in enumerate(results, start=1):
        genres = ", ".join(r.get("genres") or []) or "sin género"
        pop = r.get("popularity")
        pop_txt = f", popularidad {pop}" if pop is not None else ""
        lines.append(f"{i}. {r['title']} – {r['artist']} ({genres}{pop_txt})")
    lista = "\n".join(lines)

    # Explicación (fallback seguro)
    explanation = safe_explanation(cleaned, results)

    # Contexto real para el LLM (sin títulos/artistas)
    genres_set = []
    for r in results:
        for g in (r.get("genres") or []):
            if g and g not in genres_set:
                genres_set.append(g)
    genres_txt = ", ".join(genres_set[:4]) if genres_set else "varios estilos"

    pops = [r.get("popularity") for r in results if isinstance(r.get("popularity"), (int, float))]
    pop_avg = round(sum(pops) / len(pops)) if pops else None
    pop_txt = f"popularidad media ~{pop_avg}" if pop_avg is not None else "popularidad variada"

    explanation_prompt = f"""
Petición del usuario: "{cleaned}"

Contexto real de la selección:
- Estilos presentes: {genres_txt}
- Nivel de popularidad: {pop_txt}

Escribe una explicación breve en español (2 o 3 frases) de por qué esta selección le puede gustar.

REGLAS:
- Tono natural y cercano (como un amigo).
- No menciones títulos ni artistas (ni siquiera el que ha dicho el usuario).
- No digas “este usuario…”.
- No inventes hechos (años, álbumes, biografías, premios).
- Nada de poesía o frases raras.
- No hables del grafo/base de datos/modelo.
- Evita frases genéricas tipo “encaja con lo que pedías”.

FORMATO:
- 2 o 3 frases.
- Máximo 40 palabras.
Devuelve SOLO el texto.
""".strip()

    # Intento con LLM
    try:
        r = llm.complete(explanation_prompt)
        candidate = getattr(r, "text", str(r)).strip().strip('"').strip()
        if candidate and not explanation_looks_hallucinated(candidate):
            explanation = candidate
    except Exception:
        pass

    # Limpieza final
    explanation = sanitize_explanation(explanation, results)

    return f"{lista}\n\nExplicación:\n{explanation}"
