import datetime, server.config as config
from collections import defaultdict
from atproto import models
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI

from database import PostModel, insert_post

# After the ops are extracted, parse them here
async def imbibe(ops: defaultdict, app: FastAPI) -> None:
  """
    The coroutine that parses the operations that have been extracted from a commit.
  """
  def _post_is_tepid(record: "models.AppBskyFeedPost.Record", threshold: int = 1) -> bool:
    # Sometimes users will import old posts from Twitter/X which can flood a feed with
    # old posts. Unfortunately, the only way to test for this is to look an old
    # created_at date. However, there are other reasons why a post might have an old
    # date, such as firehose or firehose consumer outages. It is up to you, the feed
    # creator to weigh the pros and cons, amd and optionally include this function in
    # your filter conditions, and adjust the threshold to your liking.
    tepid_threshold = timedelta(days=threshold)
    created_at = datetime.fromisoformat(record.created_at)
    now = datetime.now(timezone.utc)
    return now - created_at > tepid_threshold

  def _filter_for_fresh_videos(record: "models.AppBskyFeedPost.Record") -> bool:
    if config.IGNORE_ARCHIVED_POSTS and _post_is_tepid(record):
      return True
    if config.IGNORE_REPLY_POSTS and record.reply:
      return True
    # ADS: If not video.
    if not isinstance(record.embed, models.AppBskyEmbedVideo.Main):
      return True
    # ^(?=(?:\S+\s+){4,}\S+$)(?=(?:\b\S{4,}\b.*){3}) ## Regex for at least three words four letters long
    return False

  def _make_post(created_post: defaultdict, record: "models.AppBskyFeedPost.Record") -> PostModel:
    post = PostModel()
    post.reply_root = record.reply.root.uri if record.reply else None
    post.reply_parent = record.reply.parent.uri if record.reply else None
    post.uri = created_post['uri']
    post.cid = created_post['cid']
    return post

  posts_to_create = []
  posts_to_delete = []

  # From the operation data provided, select the feed "created" posts
  for created_post in ops[models.ids.AppBskyFeedPost]['created']:
    # Extract the record
    record = created_post['record']

    # If any of these conditions, skip it
    if _filter_for_fresh_videos(record):
      continue
    
    # If feet then keep
    if "feet" in record.text.lower():
      posts_to_create.append(_make_post(created_post, record))
  
  # Create posts in the feed
  for post in posts_to_create:
    await insert_post(app, post)

  # From the operaton data provided, select the feed "deleted" posts
  deleted_posts = ops[models.ids.AppBskyFeedPost]['deleted']
  posts_to_delete = [post["uri"] for post in deleted_posts] if deleted_posts else []  

  # Delete posts from the feed
  async with app.state.pool.acquire() as conn:
    query_delete = """
      DELETE FROM posts WHERE uri = ANY($1::text[]);
    """
    if posts_to_delete:
      await conn.execute(query_delete, posts_to_delete)