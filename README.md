# 🎧 SIBI---SpotifAI
Este proyecto implementa un **agente recomendador de música** basado en **Inteligencia Artificial**, capaz de sugerir canciones personalizadas a partir de consultas en lenguaje natural y de las preferencias del usuario.

El sistema no depende directamente de Spotify, sino que utiliza **datasets abiertos**, **modelos de lenguaje** y una **base de datos en grafo**, lo que permite mayor flexibilidad y control sobre el proceso de recomendación.

---

## 🏗️ Arquitectura
- **Neo4j**
  Base de datos en grafo para modelar canciones, artistas y géneros, con búsqueda por similitud mediante embeddings
- **Embeddings semánticos**
    Generados con `distiluse-base-multilingual-cased-v2` para representar canciones y consultas en un espacio vectorial común.
- **LLM (Ollama + LlamaIndex)**
    Se utiliza un modelo local (`qwen2.5:0.5b`) para interpretar la intención del usuario y generar explicaciones naturales de las recomendaciones.
- **Streamlit**
  Interfaz web interactiva con:
  - Chat conversacional  
  - Búsqueda de canciones  
  - Configuración del perfil musical del usuario

---

## 🔄 Funcionamiento

1. El usuario introduce una consulta en lenguaje natural.  
2. Se genera un embedding de la consulta.  
3. Neo4j devuelve las canciones más similares.  
4. Se filtran y ordenan los resultados.  
5. El LLM genera una explicación de las recomendaciones.  
6. Se muestran las canciones en la interfaz.

---

## 📊 Análisis DAFO

### Fortalezas
- Arquitectura modular y explicable.  
- Independencia de APIs propietarias.  
- Uso de tecnologías modernas (LLM, grafos, embeddings).

### Debilidades
- Dataset limitado frente a plataformas comerciales.  
- Calidad del lenguaje dependiente de modelos locales pequeños.

### Oportunidades
- Ampliación del dataset.  
- Integración con APIs externas.  
- Personalización avanzada del perfil de usuario.

### Amenazas
- Limitaciones de hardware en ejecución local.  
- Escalabilidad frente a grandes volúmenes de datos.

---

## 🚀 Líneas de futuro

- Ampliar la base de datos musical.  
- Mejorar la personalización de recomendaciones.  
- Integrar modelos de lenguaje más potentes mediante servicios en la nube.  
- Incorporar información temporal y contextual.  
- Explorar sistemas de recomendación híbridos.

---

## 🧑‍💻 Tecnologías utilizadas

Python · Neo4j · Streamlit · Ollama · LlamaIndex · Sentence Transformers
