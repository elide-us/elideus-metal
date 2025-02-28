import aiohttp, asyncio
from fastapi import FastAPI, APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import algos

# Yes, these routes are silly, they're here to demonstrate the pattern...
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

# Back end routes under /api/...
def SetupAPIRouter(app: FastAPI, router: APIRouter):
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

  app.include_router(router, prefix="/api")

# Front end routes from /...
def SetupFastAPI(app: FastAPI):
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

  @app.get("/xrpc/app.bsky.feed.describeFeedGenerator")
  async def get_xrpc_app_bsky_feed_describeFeedGenerator(request: Request):
    feeds = [{"uri": uri} for uri in request.app.state.algos.keys()] # Dispatcher pattern for feed handlers
    response = {
      "encoding": "application/json",
      "body": {
        "did": request.app.state.service_did,
        "feeds": feeds
      }
    }
    return response
  
  @app.get("/xrpc/app.bsky.feed.getFeedSkeleton")
  async def get_xrpc_app_bsky_feed_getFeedSkeleton(request: Request):
    # Retrieve the 'feed' query parameter
    feed = request.args.get('feed', None)
    algo = algos.get(feed)
    if not algo:
      raise HTTPException(status_code=400, detail="Unsupported algorithm")

    # Example of checking authentication (if required)
    # from server.auth import AuthorizationError, validate_auth
    # try:
    #     # If validate_auth is async, await it
    #     requester_did = await validate_auth(request)
    # except AuthorizationError:
    #     raise HTTPException(status_code=401, detail="Unauthorized")

    try:
      cursor = request.args.get('cursor', None)
      limit = int(request.args.get('limit', 20))
      # If the algorithm function is asynchronous, await its result.
      if asyncio.iscoroutinefunction(algo):
        body = await algo(cursor, limit)
      else:
        body = algo(cursor, limit)
    except ValueError:
      raise HTTPException(status_code=400, detail="Malformed cursor")

    return JSONResponse(content=body)

  # Mount static folder
  app.mount("/static", StaticFiles(directory="static"), name="static")
  
  