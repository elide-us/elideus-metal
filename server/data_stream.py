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
async def sip(name: str, drops_callback, app: FastAPI, stream_stop_event: asyncio.Event) -> None:
  """
    Wrapper function for run that has an event flag for stopping the firehose reader.

    Meant to read one event off the firehose and then update the cursor in the database.
  """
  # As long as the stop stream event is not set, run
  while not stream_stop_event.is_set():
    try:
      # Drink the firehose
      await drink(name, drops_callback, app, stream_stop_event)
    except FirehoseError as e:
      # If something goes wrong, sleep for a few seconds and then try run again
      await asyncio.sleep(5)

# Drink the firehose
async def drink(name: str, drops_callback, app: FastAPI, stream_stop_event: asyncio.Event) -> None:
  """
    Manages the firehose cursor and the AsyncFirehoseSubscribeReposClient
  """
  # Commit sorting logic
  def _sort_aspersion_drops(aspersion: models.ComAtprotoSyncSubscribeRepos.Commit) -> defaultdict:
    """
      Creates a dictionary with two lists, one for create records and another for delete records.
      
      New records are parsed and set up in the "created" key
      Deleted records are parsed and set up in the "deleted" key

      These records should be parsed and the posts table in the database should be updated.
    """
    drops_of_interest = defaultdict(lambda: {'created': [], 'deleted': []})

    for drop in aspersion.ops:
      # Ignore "update" operations
      if drop.action == 'update':
        continue
      
      # Extract the URI and set up the record header for the post
      aspersion_uri = AtUri.from_str(f'at://{aspersion.repo}/{drop.path}')
      create_droplet_header = {'uri': str(aspersion_uri), 'cid': str(drop.cid), 'author': aspersion.repo}

      # Parse "create" operation
      if drop.action == 'create':
        if not drop.cid:
          continue

        # Extract the data portion of the CAR object
        car_bytes = CAR.from_bytes(aspersion.blocks)
        droplet_data = car_bytes.blocks.get(drop.cid)
        if not droplet_data:
          continue

        # Extract record data from the data
        droplet = models.get_or_create(droplet_data, strict=False)
        if droplet is None:
          continue
        
        # If the record is of a type we are interested in for our feed, add it to the collection
        for droplet_type, droplet_nsid in INTERESTED_RECORDS.items():
          if aspersion_uri.collection == droplet_nsid and models.is_record_type(droplet, droplet_type):
            drops_of_interest[droplet_nsid]['created'].append({'record': droplet, **create_droplet_header})
            break

      # Parse "delete" operation    
      elif drop.action == 'delete':
        drops_of_interest[aspersion_uri.collection]['deleted'].append({'uri': str(aspersion_uri)})

    return drops_of_interest

  # Event handler for the firehose commit stream
  async def _stream_handler(message: firehose_models.MessageFrame) -> None:
    """
      Coroutine to parse commits from the firehose.
    """
    # If the stop stream event is set, stop the client and return
    if stream_stop_event.is_set():
      await client.stop()
      return
    
    # Capture a message off the firehose
    aspersion = parse_subscribe_repos_message(message)

    # If this is not a commit, return
    if not isinstance(aspersion, models.ComAtprotoSyncSubscribeRepos.Commit):
      return
    
    # Parse some number of events (this parses 1)
    if aspersion.seq % 1 == 0:
      # Update the firehose client with the new cursor
      client.update_params(models.ComAtprotoSyncSubscribeRepos.Params(cursor=aspersion.seq))

      # Update the database with the new cursor number
      async with app.state.pool.acquire() as conn:
        await conn.execute("UPDATE subscription_state SET cursor = $1 WHERE service = $2;", aspersion.seq, name)

      # Set the stop stream event, the next loop should exit      
      stream_stop_event.set()
      return
    
    # If there are no blocks in the commit, return
    if not aspersion.blocks:
      return
    
    # Parse out the create and delete operations from this commit
    ops = _sort_aspersion_drops(aspersion)

    # Call the operations parser coroutine
    await drops_callback(ops, app)

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
  await client.start(_stream_handler)
