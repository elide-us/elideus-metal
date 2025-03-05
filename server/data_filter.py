import datetime, config
from collections import defaultdict
from atproto import models
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI

def post_is_archive(record: "models.AppBskyFeedPost.Record", threshold: int = 1) -> bool:
  # Sometimes users will import old posts from Twitter/X which can flood a feed with
  # old posts. Unfortunately, the only way to test for this is to look an old
  # created_at date. However, there are other reasons why a post might have an old
  # date, such as firehose or firehose consumer outages. It is up to you, the feed
  # creator to weigh the pros and cons, amd and optionally include this function in
  # your filter conditions, and adjust the threshold to your liking.
  archived_threadshold = timedelta(days=threshold)
  created_at = datetime.fromisoformat(record.created_at)
  now = datetime.now(timezone.utc)
  return now - created_at > archived_threadshold

def maybe_ignore_post(record: "models.AppBskyFeedPost.Record") -> bool:
  if config.IGNORE_ARCHIVED_POSTS and post_is_archive(record):
    return True
  if config.IGNORE_REPLY_POSTS and record.reply:
    return True
  # ADS: If not video.
  if not isinstance(record.embed, models.AppBskyEmbedVideo.Main):
    return True
  # ^(?=(?:\S+\s+){4,}\S+$)(?=(?:\b\S{4,}\b.*){3}) ## Regex for at least three words four letters long
  return False

def pack_post(created_post: defaultdict, record: "models.AppBskyFeedPost.Record"):
  reply_root = record.reply.root.uri if record.reply else None
  reply_parent = record.reply.parent.uri if record.reply else None
  return {
    'uri': created_post['uri'],
    'cid': created_post['cid'],
    'reply_parent': reply_parent,
    'reply_root': reply_root,
  }

async def operations_callback(ops: defaultdict, app: FastAPI) -> None:
  posts_to_create = []
  posts_to_delete = []
  for created_post in ops[models.ids.AppBskyFeedPost]['created']:
    record = created_post['record']
    if maybe_ignore_post(record):
      continue
    if "feet" in record.text.lower():
      posts_to_create.append(pack_post(created_post, record))
  deleted_posts = ops[models.ids.AppBskyFeedPost]['deleted']
  posts_to_delete = [post["uri"] for post in deleted_posts] if deleted_posts else []
  async with app.state.pool.acquire() as conn:
    query_insert = """
      INSERT INTO posts (uri, cid, reply_parent, reply_root)
      VALUES ($1, $2, $3, $4);
    """
    query_delete = """
      DELETE FROM posts WHERE uri = ANY($1::text[]);
    """
    if posts_to_delete:
      await conn.execute(query_delete, posts_to_delete)
    for post in posts_to_create:
      await conn.execute(query_insert, post["uri"], post["cid"], post["reply_paret"], post["reply_root"])
