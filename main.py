import asyncpg, config, database
from fastapi import FastAPI, APIRouter
from contextlib import asynccontextmanager
from atproto import DidInMemoryCache, IdResolver
from router import SetupFastAPI, SetupAPIRouter
from algos.feed import handler

@asynccontextmanager
async def lifespan(app: FastAPI):
  app.state.message = r"\m/"
  app.state.app_version = config.VERSION
  app.state.hostname = config.HOSTNAME
  app.state.service_did = config.SERVICE_DID
  app.state.pool = await asyncpg.create_pool(config.DATABASE_URL)
  app.state.did_cache = DidInMemoryCache()
  app.state.id_resolver = IdResolver(cache=app.state.did_cache)
  app.state.algos = {
    config.FEED_URI: handler
  }

  await database.maybe_create_tables(app)

  try:
    yield
  finally:
    app.state.pool.close()

# The following "app" object is the WSGI entry point for the service
app = FastAPI(lifespan=lifespan)
router = APIRouter()
SetupAPIRouter(app, router)
SetupFastAPI(app)
