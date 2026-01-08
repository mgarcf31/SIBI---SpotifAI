# 🎧 SIBI – SpotifAI

**SpotifAI** es un proyecto académico que implementa un **agente recomendador de música basado en IA**, capaz de generar recomendaciones personalizadas a partir de consultas en lenguaje natural y de las preferencias del usuario.

El sistema **no depende de Spotify ni de APIs propietarias**. Utiliza **datasets abiertos**, **una base de datos en grafo (Neo4j)** y **modelos de lenguaje locales**, priorizando el control, la explicabilidad y el valor académico.

---

## 🏗️ Arquitectura

- **Neo4j**  
  Base de datos en grafo para modelar canciones, artistas y géneros.  
  Incluye búsqueda por similitud mediante **embeddings vectoriales**.

- **Embeddings semánticos**  
  Generados con `distiluse-base-multilingual-cased-v2` para representar canciones y consultas del usuario.

- **LLM local (Ollama + LlamaIndex)**  
  Modelo local (por defecto `qwen2.5:0.5b`) para interpretar la intención del usuario y generar explicaciones breves y controladas.

- **Streamlit**  
  Interfaz web con:
  - Chat conversacional
  - Búsqueda estructurada
  - Configuración del perfil musical

---

## 📂 Estructura del proyecto


spotify-reco-agent/

│

├── app/

│ ├── agent.py # Lógica del agente conversacional

│ ├── neo4j_search.py # Consultas y filtros en Neo4j

│ ├── reco.py # Reglas de recomendación

│ ├── graph.py # Esquema del grafo

│

├── scripts/

│ ├── graph.py # Creación del grafo desde CSV

│ └── embed_tracks.py # Generación de embeddings

│

├── streamlit_app.py # Interfaz web

├── .env.example # Variables de entorno de ejemplo

├── requirements.txt

|

README.md

|

spotifAi.pdf # presentación en pdf

|

enlace-al-video-drive.txt # documento de teto con elnace al video en Drive

|

memoriaSpotifAI.pdf # memoria del proyecto en pdf
  
---

## ⚙️ Requisitos

- Python 3.10+
- Neo4j (con soporte de índices vectoriales)
- Ollama instalado localmente
- Modelo descargado en Ollama (`qwen2.5:0.5b` por defecto)

---
## 📊 Dataset

Este proyecto utiliza datasets musicales abiertos (por ejemplo, Spotify / Kaggle).

El dataset **no se incluye en el repositorio** por motivos de tamaño y licencia.
Solo se utiliza durante la fase de creación del grafo en Neo4j.

Puedes usar cualquier dataset que contenga:
- Canciones
- Artistas
- Géneros
- Popularidad (opcional)

Los scripts `graph.py` y `embed_tracks.py` se encargan de transformar estos datos en la base de datos.

---

## 🔧 Configuración

1. Crear entorno virtual:
```bash
python -m venv .venv
.venv\Scripts\activate    # Windows
```

2. Instalar dependencias:
```bash
pip install -r requirements.txt
```

3. Configurar variables de entorno:
```bash
cp .env.example .env
```

Editar .env:
```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
OLLAMA_MODEL=qwen2.5:0.5b
```


---

## 🧠 Preparación de la base de datos

Ejecutar una sola vez:
```bash
python scripts/graph.py
python scripts/embed_tracks.py
```
Esto crea el grafo y los índices vectoriales en Neo4j.

---

## ▶️ Ejecución de la aplicación
```bash
streamlit run streamlit_app.py
```

la aplicación estará disponible en: http://localhost:8501

---

## 🎯 Funcionalidades principales

- Recomendación musical en lenguaje natural
- Control explícito de:
- Idioma
- Popularidad
- Diversidad de artistas
- Explicaciones breves y controladas (sin alucinaciones)
- Perfil musical con valoraciones persistentes
- Interfaz conversacional clara

---

## 🔐 Seguridad y privacidad
- No se almacenan datos sensibles
- No se envía información a servicios externos
- Modelos ejecutados localmente
- Sanitización y control de respuestas del LLM

---

## 🚀 Tecnologías utilizadas

Python · Neo4j · Streamlit · Ollama · LlamaIndex · Sentence Transformers

---

## 📎 Material adicional
El repositorio incluye:
- Código fuente completo
- README
- Memoria del proyecto
- Presentación (PPTX)
- Vídeo de la presentación y de la aplicación
