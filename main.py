from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from server.lifespan import lifespan
from routes import api, web, bsky

app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(api.router, prefix="/api")
app.include_router(bsky.router)
app.include_router(web.router)

@app.get("/")
async def get_root():
  return { "message": "You should not be here." }
