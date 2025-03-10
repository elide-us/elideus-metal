import asyncio
from fastapi import FastAPI
from collections import defaultdict
from atproto import AtUri, CAR, firehose_models, models, parse_subscribe_repos_message, AsyncFirehoseSubscribeReposClient
from atproto.exceptions import FirehoseError

# This constant lists the kinds of create records that we are interested in
INTERESTED_RECORDS = {
  models.AppBskyFeedLike: models.ids.AppBskyFeedLike,
  models.AppBskyFeedPost: models.ids.AppBskyFeedPost,
  models.AppBskyGraphFollow: models.ids.AppBskyGraphFollow,
}

# Sip a record from the firehose
async def sip(name: str, operations_callback, app: FastAPI, stream_stop_event: asyncio.Event) -> None:
  """
    Wrapper function for run that has an event flag for stopping the firehose reader.

    Meant to read one event off the firehose and then update the cursor in the database.
  """
  # As long as the stop stream event is not set, run
  while not stream_stop_event.is_set():
    try:
      # Drink the firehose
      await drink(name, operations_callback, app, stream_stop_event)
    except FirehoseError as e:
      # If something goes wrong, sleep for a few seconds and then try run again
      await asyncio.sleep(5)

# Drink the firehose
async def drink(name: str, operations_callback, app: FastAPI, stream_stop_event: asyncio.Event) -> None:
  """
    Manages the firehose cursor and the AsyncFirehoseSubscribeReposClient
  """
  # Commit sorting logic
  def _sort_commit_ops(commit: models.ComAtprotoSyncSubscribeRepos.Commit) -> defaultdict:
    """
      Creates a dictionary with two lists, one for create records and another for delete records.
      
      New records are parsed and set up in the "created" key
      Deleted records are parsed and set up in the "deleted" key

      These records should be parsed and the posts table in the database should be updated.
    """
    ops_of_interest = defaultdict(lambda: {'created': [], 'deleted': []})

    for op in commit.ops:
      # Ignore "update" operations
      if op.action == 'update':
        continue
      
      # Extract the URI and set up the record header for the post
      commit_uri = AtUri.from_str(f'at://{commit.repo}/{op.path}')
      create_record_header = {'uri': str(commit_uri), 'cid': str(op.cid), 'author': commit.repo}

      # Parse "create" operation
      if op.action == 'create':
        if not op.cid:
          continue

        # Extract the data portion of the CAR object
        car_blocks = CAR.from_bytes(commit.blocks)
        record_raw_data = car_blocks.blocks.get(op.cid)
        if not record_raw_data:
          continue

        # Extract record data from the data
        record = models.get_or_create(record_raw_data, strict=False)
        if record is None:
          continue
        
        # If the record is of a type we are interested in for our feed, add it to the collection
        for record_type, record_nsid in INTERESTED_RECORDS.items():
          if commit_uri.collection == record_nsid and models.is_record_type(record, record_type):
            ops_of_interest[record_nsid]['created'].append({'record': record, **create_record_header})
            break

      # Parse "delete" operation    
      elif op.action == 'delete':
        ops_of_interest[commit_uri.collection]['deleted'].append({'uri': str(commit_uri)})

    return ops_of_interest

  # Event handler for the firehose commit stream
  async def _on_message_handler(message: firehose_models.MessageFrame) -> None:
    """
      Coroutine to parse commits from the firehose.
    """
    # If the stop stream event is set, stop the client and return
    if stream_stop_event.is_set():
      await client.stop()
      return
    
    # Capture a message off the firehose
    commit = parse_subscribe_repos_message(message)

    # If this is not a commit, return
    if not isinstance(commit, models.ComAtprotoSyncSubscribeRepos.Commit):
      return
    
    # Parse some number of events (this parses 1)
    if commit.seq % 1 == 0:
      # Update the firehose client with the new cursor
      client.update_params(models.ComAtprotoSyncSubscribeRepos.Params(cursor=commit.seq))

      # Update the database with the new cursor number
      async with app.state.pool.acquire() as conn:
        await conn.execute("UPDATE subscription_state SET cursor = $1 WHERE service = $2;", commit.seq, name)

      # Set the stop stream event, the next loop should exit      
      stream_stop_event.set()
      return
    
    # If there are no blocks in the commit, return
    if not commit.blocks:
      return
    
    # Parse out the create and delete operations from this commit
    ops = _sort_commit_ops(commit)

    # Call the operations parser coroutine
    await operations_callback(ops, app)

  # Get the latest cursor record from the database
  try:
    async with app.state.pool.acquire() as conn:
      state = await conn.fetchrow("SELECT cursor FROM subscription_state WHERE service = $1;", name)
  except Exception as e:
    print(f"Exception: {e}")

  # If there is no cursor record, create one
  if not state:
    async with app.state.pool.acquire() as conn:
      await conn.execute("INSERT INTO subscription_state (service, cursor) VALUES ($1, $2);", name, 0)
  
  # Set up the firehose client
  params = models.ComAtprotoSyncSubscribeRepos.Params(cursor=state["cursor"]) if state else None
  client = AsyncFirehoseSubscribeReposClient(params)

  # Start the client
  await client.start(_on_message_handler)
