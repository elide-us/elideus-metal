from fastapi import FastAPI, APIRouter, Request
from contextlib import asynccontextmanager
import aiohttp, json

@asynccontextmanager
async def lifespan(app: FastAPI):
  app.state.message = r"\m/"
  yield

router = APIRouter()

@router.get("/message")
async def get_message(request: Request):
  return {"message": request.app.state.message}

app = FastAPI(lifespan=lifespan)
app.include_router(router, prefix="/api")

async def fetch_message():
  async with aiohttp.ClientSession() as session:
    async with session.get("http://127.0.0.1:8000/api/message") as response:
      data = await response.json()
      data = json.loads(data)
      return data.get("message")

@app.get("/")
async def get_root():
  message = await fetch_message()
  return message
