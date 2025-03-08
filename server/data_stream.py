import asyncio
from fastapi import FastAPI
from collections import defaultdict
from atproto import AtUri, CAR, firehose_models,models, parse_subscribe_repos_message, AsyncFirehoseSubscribeReposClient
from atproto.exceptions import FirehoseError

_INTERESTED_RECORDS = {
  models.AppBskyFeedLike: models.ids.AppBskyFeedLike,
  models.AppBskyFeedPost: models.ids.AppBskyFeedPost,
  models.AppBskyGraphFollow: models.ids.AppBskyGraphFollow,
}

def _get_ops_by_type(commit: models.ComAtprotoSyncSubscribeRepos.Commit) -> defaultdict:
  operations_by_type = defaultdict(lambda: {'created': [], 'deleted': []})
  car = CAR.from_bytes(commit.blocks)
  for op in commit.ops:
    if op.action == 'update':
      continue
    uri = AtUri.from_str(f'at://{commit.repo}/{op.path}')
    if op.action == 'create':
      if not op.cid:
        continue
      create_info = {'uri': str(uri), 'cid': str(op.cid), 'author': commit.repo}
      record_raw_data = car.blocks.get(op.cid)
      if not record_raw_data:
        continue
      record = models.get_or_create(record_raw_data, strict=False)
      if record is None:
        continue
      for record_type, record_nsid in _INTERESTED_RECORDS.items():
        if uri.collection == record_nsid and models.is_record_type(record, record_type):
          print("Adding record of interest")
          operations_by_type[record_nsid]['created'].append(
            {'record': record, **create_info}
          )
          break
    elif op.action == 'delete':
      operations_by_type[uri.collection]['deleted'].append({'uri': str(uri)})
  return operations_by_type

async def sip(name: str, operations_callback, app: FastAPI, stream_stop_event: asyncio.Event) -> None:
  print("Sip called")
  while not stream_stop_event.is_set():
    try:
      await _run(name, operations_callback, app, stream_stop_event)
    except FirehoseError as e:
      await asyncio.sleep(5)

async def _run(name: str, operations_callback, app: FastAPI, stream_stop_event: asyncio.Event) -> None:
  try:
    print("Getting cursor from database")
    async with app.state.pool.acquire() as conn:
      state = await conn.fetchrow("SELECT cursor FROM subscription_state WHERE service = $1;", name)
      print(f"Cursor: {state}")
  except Exception as e:
    print(f"Exception: {e}")
  
  params = models.ComAtprotoSyncSubscribeRepos.Params(cursor=state["cursor"]) if state else None
  client = AsyncFirehoseSubscribeReposClient(params)
  
  if not state:
    print(f"Adding state record")
    async with app.state.pool.acquire() as conn:
      await conn.execute("INSERT INTO subscription_state (service, cursor) VALUES ($1, $2);", name, 0)

  async def on_message_handler(message: firehose_models.MessageFrame) -> None:
    print("On message handler")
    if stream_stop_event.is_set():
      await client.stop()
      return
    commit = parse_subscribe_repos_message(message)
    print(f"Parsing commit {commit}")
    if not isinstance(commit, models.ComAtprotoSyncSubscribeRepos.Commit):
      return
    if commit.seq % 1 == 0:
      client.update_params(models.ComAtprotoSyncSubscribeRepos.Params(cursor=commit.seq))
      print("Updating cursor in database")
      async with app.state.pool.acquire() as conn:
        await conn.execute("UPDATE subscription_state SET cursor = $1 WHERE service = $2;", commit.seq, name)
      stream_stop_event.set()
      await client.stop()
      return
    if not commit.blocks:
      return
    ops = _get_ops_by_type(commit)
    await operations_callback(ops, app)

  await client.start(on_message_handler)
