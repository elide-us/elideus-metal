from pydantic import BaseModel
from datetime import datetime
from fastapi import FastAPI, HTTPException

class PostModel(BaseModel):
  uri: str
  cdi: str
  reply_parent: str | None = None
  reply_root: str | None = None
  indexed_at: datetime

class SubscriptionStateModel(BaseModel):
  service: str
  cursor: int

async def maybe_create_tables(app: FastAPI):
  async with app.state.pool.acquire() as conn:
    post_query = """
      CREATE TABLE IF NOT EXISTS post (
        uri TEXT PRIMARY KEY,
        cid TEXT NOT NULL,
        reply_parent TEXT,
        reply_root TEXT,
        indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      );
    """
    state_query = """
      CREATE TABLE IF NOT EXISTS subscription_state (
        service TEXT UNIQUE NOT NULL,
        cursor BIGINT NOT NULL
      );
    """
    try:
      await conn.execute(post_query)
    except Exception as e:
      raise

    try:
      await conn.execute(state_query)
    except Exception as e:
      raise

# @app.post("/posts", response_model=PostModel)
async def create_post(app: FastAPI, post: PostModel):
  async with app.state.pool.acquire() as conn:
    query = """
      INSERT INTO post (uri, cid, reply_parent, reply_root, indexed_at)
      VALUES ($1, $2, $3, $4, $5)
      ON CONFLICT (uri) DO NOTHING;
    """
    try:
      await conn.execute(query, post.uri, post.cid, post.reply_parent, post.reply_root, post.indexed_at)
    except Exception as e:
      raise HTTPException(status_code=500, detail=str(e))
  return post

# @app.get("/posts/{uri}", response_model=PostModel)
async def get_post(app: FastAPI, uri: str):
  async with app.state.pool.acquire() as conn:
    query = """
      SELECT * FROM post WHERE uri = $1;
    """
    row = await conn.fetchrow(query, uri)
    if row is None:
      raise HTTPException(status_code=404, detail="Post not found")
    return PostModel(**dict(row))