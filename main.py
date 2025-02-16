from fastapi import FastAPI, APIRouter, Request
from fastapi.responses import HTMLResponse
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
      return data.get("message")

@app.get("/")
async def get_root():
  message = await fetch_message()
  html = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <title>Metal Emoji</title>
      <style>
        html, body {{
          height: 100%;
          margin: 0;
        }}
        body {{
          background-color: #333;
          color: black;
          display: flex;
          justify-content: center;
          align-items: center;
        }}
        .message {{
          font-size: 20vh;
        }}
      </style>
    </head>
    <body>
      <div class="message">{message}</div>
    </body>
    </html>
  """

  return HTMLResponse(content=html, media_type="text/html")
