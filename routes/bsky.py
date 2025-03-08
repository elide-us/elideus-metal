from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
import asyncio
import server.algos as algos

router = APIRouter()

@router.get("/.well-known/did.json")
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

@router.get("/xrpc/app.bsky.feed.describeFeedGenerator")
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

@router.get("/xrpc/app.bsky.feed.getFeedSkeleton")
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
