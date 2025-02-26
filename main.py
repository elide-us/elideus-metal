import asyncpg, config, database
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from atproto import DidInMemoryCache, IdResolver
from routes.web import SetupWebRoutes
from routes.api import router
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
  app.state.algos = {config.FEED_URI: handler}

  await database.maybe_create_tables(app)

  try:
    yield
  finally:
    app.state.pool.close()

app = FastAPI(lifespan=lifespan)
app.include_router(router, prefix="/api")
app.mount("/static", StaticFiles(directory="static"), name="static")

SetupWebRoutes(app)
