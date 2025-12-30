import os
import time
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from dotenv import load_dotenv

from .graph import init_schema, ping
from .reco import ingest_user, recommend_by_features
from .auth import get_authorize_url, handle_callback

load_dotenv()  # carga .env
app = FastAPI()

@app.on_event("startup")
async def _startup():
    # Espera breve a que Neo4j esté listo; si no, la app igual arranca.
    for _ in range(20):
        if ping():
            try:
                init_schema()
            except Exception as e:
                print("init_schema error:", e)
            break
        time.sleep(0.5)
    else:
        print("⚠️ Neo4j no disponible al arranque; prueba /db/ping")

# ---- Diagnóstico ----
@app.get("/db/ping")
def db_ping():
    return {"neo4j_ok": ping()}

# ---- Login Spotify ----
@app.get("/login/{uid}")
def login(uid: str):
    url = get_authorize_url(uid)
    return RedirectResponse(url)
    print("no borres main.py")

@app.get("/auth/callback")
def auth_callback(request: Request):
    code = request.query_params.get("code")
    state = request.query_params.get("state")  # uid
    if not code or not state:
        raise HTTPException(400, "Faltan parámetros en el callback")
    handle_callback(state, code)
    return HTMLResponse(f"<h2>Login correcto para: {state}</h2>"
                        f"<p>Ahora ejecuta /ingest/{state} y luego /recommend/{state}</p>")

# ---- Funcionalidad ----
@app.post("/ingest/{uid}")
def ingest(uid: str):
    res = ingest_user(uid)
    return {"ok": True, "ingested": res.get("tracks", 0)}

@app.get("/recommend/{uid}")
def recommend(uid: str, k: int = 20):
    return {"tracks": recommend_by_features(uid, k)}

@app.get("/debug/login-url/{uid}")
def debug_login_url(uid: str):
    return {"authorize_url": get_authorize_url(uid)}