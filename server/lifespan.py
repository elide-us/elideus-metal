from fastapi import FastAPI
from contextlib import asynccontextmanager
from asyncpg import create_pool
from asyncio import Event, create_task
from atproto import DidInMemoryCache, IdResolver
from server.config import VERSION, HOSTNAME, SERVICE_DID, DATABASE_URL, FEED_URI
from server.algos.feed import handler
from server.data_stream import sip
from server.data_filter import operations_callback
from server.database import maybe_create_tables

@asynccontextmanager
async def lifespan(app: FastAPI):
  app.state.version = VERSION
  app.state.hostname = HOSTNAME
  app.state.service_did = SERVICE_DID
  app.state.pool = await create_pool(DATABASE_URL)

  app.state.did_cache = DidInMemoryCache()
  app.state.id_resolver = IdResolver(cache=app.state.did_cache)
  app.state.algos = {
    FEED_URI: handler
  }

  app.state.feed_stop_event = Event()
  app.state.feed_task = create_task(
    sip("elideus_feed_generator", operations_callback, app, app.state.feed_stop_event)
  )

  await maybe_create_tables(app)

  try:
    yield
  finally:
    await app.state.pool.close()
