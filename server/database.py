from pydantic import BaseModel, Field
from typing import Any, ClassVar, Optional, Type, Dict
from datetime import datetime
from fastapi import FastAPI, HTTPException
import asyncpg

class DBError(Exception):
  pass

class DBBaseModel(BaseModel):
    # Class variables for database connection pool and table name.
    _pool: ClassVar[Optional[asyncpg.Pool]] = None
    _table: ClassVar[Optional[str]] = None
    _initialized: ClassVar[bool] = False

    def _assert_initialized(cls) -> None:
      if not cls._initialized or cls._pool is None or cls._table is None:
        raise DBError(f"{cls.__name__} is not initialized. Please call init_db first.")

    @classmethod
    async def init_db(cls: Type["DBBaseModel"], pool: asyncpg.Pool, table_name: Optional[str] = None) -> None:
      """
      Initializes the connection pool and optionally overrides the table name.
      """
      if cls._initialized:
        return
      cls._pool = pool
      # Auto-generate table name from the class name if not provided
      cls._table = table_name or cls.__name__.lower()
      cls._initialized = True

    @classmethod
    async def create_table(cls) -> None:
      """
      Creates the table in the database based on the Pydantic model's fields.
      Assumes the first field is the unique key.
      """
      cls._assert_initialized()

      columns: Dict[str, Any] = {}
      columns["id"] = "SEREAL PRIMARY KEY"
      for idx, (name, field) in enumerate(cls.model_fields.items()):
        # For simplicity, we map Python types to SQL types with some assumptions.
        py_type = field.type_
        if py_type == int:
          sql_type = "INTEGER"
        elif py_type == float:
          sql_type = "REAL"
        elif py_type == bool:
          sql_type = "BOOLEAN"
        elif py_type == datetime:
          sql_type = "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
        else:
          sql_type = "TEXT"
        columns[name] = sql_type

      columns_def = ", ".join(f"{col} {definition}" for col, definition in columns.items())
      query = f"CREATE TABLE IF NOT EXISTS {cls._table} ({columns_def});"

      async with cls._pool.acquire() as conn:
        await conn.execute(query)

    @classmethod
    async def insert(self) -> None:
      """
      Inserts this model instance into the table.
      """
      self.__class__._assert_initialized()
      # Convert instance to dict and build a parameterized query.
      data = self.model_dump()
      columns = ", ".join(data.keys())
      # asyncpg uses $1, $2, ... for placeholders.
      placeholders = ", ".join(f"${i+1}" for i in range(len(data)))
      query = f"INSERT INTO {self.__class__._table} ({columns}) VALUES ({placeholders});"

      async with self.__class__._pool.acquire() as conn:
        await conn.execute(query, *data.values())

    @classmethod
    async def delete(cls, column: str, value: Any) -> None:
      """
      Deletes a row (or rows) based on a column and value.
      For simplicity, assumes equality in the WHERE clause.
      """
      cls._assert_initialized()
      query = f"DELETE FROM {cls._table} WHERE {column} = $1;"
      async with cls._pool.acquire() as conn:
        await conn.execute(query, value)


class PostModel(DBBaseModel):
  uri: str
  cid: str
  reply_parent: str | None = None
  reply_root: str | None = None
  indexed_at: datetime

# 
class SubscriptionStateModel(DBBaseModel):
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
async def insert_post(app: FastAPI, post: PostModel):
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