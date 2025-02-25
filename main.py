from fastapi import FastAPI, APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager
import aiohttp, asyncio





@asynccontextmanager
async def lifespan(app: FastAPI):
  app.state.message = r"\m/"
  app.state.HOSTNAME = "elideus.net"
  app.state.SERVICE_DID = "did:web:elideus.net"
  yield





router = APIRouter()

@router.get("/message")
async def get_message(request: Request):
  return {"message": request.app.state.message}

@router.get("/ffmpeg")
async def get_ffmpeg():
  try:
    process = await asyncio.create_subprocess_exec(
      "ffmpeg", "-version",
      stdout=asyncio.subprocess.PIPE,
      stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    if stdout:
      version_line = stdout.decode().splitlines()[0]
    else:
      version_line = stderr.decode().splitlines()[0]
    return {"ffmpeg_version": version_line}
  except Exception as e:
    raise HTTPException(status_code=500, detail="Error checking ffmpeg: {e}")







app = FastAPI(lifespan=lifespan)
app.include_router(router, prefix="/api")

@app.get("/.well-known/did.json")
async def get_well_known_did_json(request: Request):
  return {
    "@context": ["http://www.w3.org/ns/did/v1"],
    "id": request.app.state.SERVICE_DID,
    "service": [
      {
        "id": "#bsky_fg",
        "type": "BskyFeedGenerator",
        "serviceEndpoint": f"https://{request.app.state.HOSTNAME}"
      }
    ]
  }





async def fetch_message():
  async with aiohttp.ClientSession() as session:
    async with session.get("http://127.0.0.1:8000/api/message") as response:
      data = await response.json()
      return data.get("message")

async def fetch_version():
  async with aiohttp.ClientSession() as session:
    async with session.get("http://127.0.0.1:8000/api/ffmpeg") as response:
      data = await response.json()
      return data.get("ffmpeg_version")








@app.get("/")
async def get_root():
  message = await fetch_message()
  version = await fetch_version()
  html = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <title>Elideus-Metal</title>
      <style>
        html, body {{
          height: 100%;
          margin: 0;
        }}
        body {{
          background-color: #333;
          color: black;
          display: flex;
          flex-direction: column;
          justify-content: center;
          align-items: center;
        }}
        .message {{
          font-size: 20vh;
        }}
        .version {{
          font-size: 14;
          color: #c1c1c1;
        }}
      </style>
    </head>
    <body>
      <div class="message">{message}</div>
      <div class="version">{version}</div>
    </body>
    </html>
  """

  return HTMLResponse(content=html, media_type="text/html")
