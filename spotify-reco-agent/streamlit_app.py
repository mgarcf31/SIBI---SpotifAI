# streamlit_app.py
import streamlit as st

from app.agent import chat_with_agent
from app.neo4j_search import get_preference_tracks, save_user_preferences

# -------------------------------------------------
# Configuración general
# -------------------------------------------------
st.set_page_config(
    page_title="SpotifAI",
    page_icon="🎧",
    layout="centered",
)

# -------------------------------------------------
# Helpers
# -------------------------------------------------
def render_agent_response(respuesta: str):
    """
    Renderiza la respuesta del agente separando
    recomendaciones y explicación si existe.
    """
    if "Explicación:" in respuesta:
        songs, explanation = respuesta.split("Explicación:", 1)

        st.markdown("### 🎵 Recomendaciones")
        st.markdown(songs.strip())

        st.markdown("---")
        st.markdown("### 💬 Por qué te pueden gustar")
        st.markdown(explanation.strip())
    else:
        st.markdown(respuesta)


# -------------------------------------------------
# Estado inicial
# -------------------------------------------------
if "page" not in st.session_state:
    st.session_state.page = "Chat"

if "user_id" not in st.session_state:
    st.session_state.user_id = "usuario1"

if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = [
        {
            "role": "assistant",
            "content": "¡Hola! Cuéntame qué tipo de música te apetece 🎶",
        }
    ]

# Prompt pendiente (para botones del sidebar)
if "pending_prompt" not in st.session_state:
    st.session_state.pending_prompt = None

# Página de preferencias
if "pref_page" not in st.session_state:
    st.session_state.pref_page = 0


# -------------------------------------------------
# Sidebar
# -------------------------------------------------
st.sidebar.title("🎵 SpotifAI")

st.session_state.page = st.sidebar.radio(
    "Ir a",
    ["Chat", "Buscar", "Configurar perfil musical"],
)

st.sidebar.markdown("---")

st.session_state.user_id = st.sidebar.text_input(
    "Tu ID de usuario",
    value=st.session_state.user_id,
)

st.sidebar.markdown("---")
st.sidebar.header("💡 Ejemplos de preguntas")

example_prompts = [
    "Quiero música tranquila para relajarme después de un día largo",
    "Dame 5 canciones pop muy conocidas",
    "Me gusta Coldplay y Keane, recomiéndame algo parecido",
    "Quiero música para estudiar sin distraerme",
    "Basándote en mis gustos, sorpréndeme",
]

for p in example_prompts:
    if st.sidebar.button(p):
        st.session_state.pending_prompt = p
        st.session_state.page = "Chat"
        st.rerun()

st.sidebar.markdown("---")
st.sidebar.caption("Neo4j + LlamaIndex + Ollama")


# -------------------------------------------------
# PAGE: CHAT
# -------------------------------------------------
if st.session_state.page == "Chat":
    st.title("💬 Chat con el recomendador")
    st.caption("Habla con el agente en lenguaje natural.")

    # Mostrar historial
    for msg in st.session_state.chat_messages:
        role = msg["role"]
        content = (msg.get("content") or "").strip()
        if not content:
            continue

        avatar = "🙂" if role == "user" else "🎧"
        with st.chat_message(role, avatar=avatar):
            if role == "assistant":
                render_agent_response(content)
            else:
                st.markdown(content)

    # Input único del chat
    prompt = st.chat_input("¿Qué te apetece escuchar?")

    # Si viene de un botón del sidebar
    if not prompt and st.session_state.pending_prompt:
        prompt = st.session_state.pending_prompt
        st.session_state.pending_prompt = None

    if prompt:
        prompt = prompt.strip()

    # No permitir mensajes vacíos
    if not prompt:
        st.stop()

    # Guardar mensaje del usuario
    st.session_state.chat_messages.append(
        {"role": "user", "content": prompt}
    )

    with st.chat_message("user", avatar="🙂"):
        st.markdown(prompt)

    # Respuesta del agente
    with st.chat_message("assistant", avatar="🎧"):
        with st.spinner("Pensando..."):
            if len(prompt) < 4 or prompt.lower() in {"hola", "hey", "hello", "buenas"}:
                respuesta = (
                    "😊 Dime qué te apetece escuchar: "
                    "un género, un estado de ánimo o un artista que te guste."
                )
            else:
                respuesta = chat_with_agent(prompt)

        render_agent_response(respuesta)

    st.session_state.chat_messages.append(
        {"role": "assistant", "content": respuesta}
    )


# -------------------------------------------------
# PAGE: BUSCAR
# -------------------------------------------------
elif st.session_state.page == "Buscar":
    st.title("🔎 Buscar canciones")
    st.markdown(
        "Describe el tipo de música que quieres y el sistema buscará canciones similares."
    )

    query = st.text_area(
        "¿Qué te apetece escuchar?",
        height=100,
        placeholder="Ej: pop suave para estudiar, tipo Ed Sheeran",
    )

    k = st.slider("Número de recomendaciones", 3, 15, 7)

    if st.button("Recomendar 🎧"):
        if not query.strip():
            st.warning("Escribe algo primero 🙂")
        else:
            with st.spinner("Buscando canciones..."):
                respuesta = chat_with_agent(query, k=k)

            render_agent_response(respuesta)


# -------------------------------------------------
# PAGE: CONFIGURAR PERFIL MUSICAL
# -------------------------------------------------
else:
    st.title("🧩 Configurar tu perfil musical")
    st.write(
        "Puntúa canciones para que el sistema entienda mejor tus gustos "
        "(0 = nada, 5 = me encanta)."
    )

    colA, colB = st.columns([3, 1])
    with colA:
        st.markdown(f"### Bloque #{st.session_state.pref_page + 1}")
    with colB:
        if st.button("Cambiar canciones 🔄"):
            st.session_state.pref_page += 1
            st.rerun()

    tracks = get_preference_tracks(
        user_id=st.session_state.user_id,
        limit=20,
        page=st.session_state.pref_page,
    )

    ratings = {}

    if not tracks:
        st.warning("No hay más canciones para mostrar.")
    else:
        for t in tracks:
            tid = t["id"]
            title = t["title"]
            artist = t["artist"]
            pop = t.get("popularity", "N/A")

            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"**{title}** – {artist} (popularidad {pop})")
            with col2:
                rating = st.slider(
                    "Puntuación",
                    0,
                    5,
                    0,
                    key=f"rating_{tid}_{st.session_state.pref_page}",
                )

            if rating > 0:
                ratings[tid] = rating

    if st.button("Guardar preferencias ✅"):
        if not ratings:
            st.warning("No has puntuado ninguna canción.")
        else:
            save_user_preferences(st.session_state.user_id, ratings)
            st.success(f"Preferencias guardadas ({len(ratings)} canciones).")
