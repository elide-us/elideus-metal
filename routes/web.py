import aiohttp
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

async def _fetch_message():
  async with aiohttp.ClientSession() as session:
    async with session.get("http://127.0.0.1:8000/api/message") as response:
      data = await response.json()
      return data.get("message")

async def _fetch_version():
  async with aiohttp.ClientSession() as session:
    async with session.get("http://127.0.0.1:8000/api/ffmpeg") as response:
      data = await response.json()
      return data.get("ffmpeg_version")

async def SetupWebRoutes(app: FastAPI):
  @app.get("/")
  async def get_root():
    message = await _fetch_message()
    version = await _fetch_version()
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
          .link {{
            font-size: 14;
            color: #c1c1c1;
          }}
          a {{
            font-size: 14;
            color: #c1c1c1;
            text-decoration: none;
          }}
          a:hover {{
            text-decoration: underline;
          }}
        </style>
      </head>
      <body>
        <div class="message">{message}</div>
        <div class="version">{version}</div>
        <div class="version"><a href="/.well-known/did.json">at://{app.state.service_did}</a> v{app.state.app_version} running on {app.state.hostname}</div>
        <div class="link">GitHub: <a href="https://github.com/elide-us/elideus-metal" target="_blank" rel="noopener noreferrer">repo</a> - <a href="https://github.com/elide-us/elideus-metal/actions" target="_blank" rel="noopener noreferrer">build</a></div>
      </body>
      </html>
    """

    return HTMLResponse(content=html, media_type="text/html")

  @app.get("/.well-known/did.json")
  async def get_well_known_did_json(request: Request):
    return {
      "@context": ["http://www.w3.org/ns/did/v1"],
      "id": request.app.state.service_did,
      "service": [
        {
          "id": "#bsky_fg",
          "type": "BskyFeedGenerator",
          "serviceEndpoint": f"https://{request.app.state.hostname}"
        }
      ]
    }
