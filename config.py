import os

import dotenv
dotenv.load_dotenv()

VERSION = "0.1.0"

def _get_str_env_var(var_name: str) -> str:
  value = os.getenv(var_name)
  if not value:
    raise RuntimeError(f"ERROR: {var_name} missing.")
  return value
def _get_bool_env_var(var_name: str) -> bool:
  value = os.getenv(var_name)
  if value is None:
     return False
  normalized_vaue = value.strip().lower()
  if normalized_vaue in {"1", "true", "t", "yes", "y"}:
     return True
  return False

HOSTNAME = _get_str_env_var("HOSTNAME")
if not HOSTNAME:
    raise RuntimeError("You must set 'HOSTNAME' environment variable.")

SERVICE_DID = _get_str_env_var("SERVICE_DID")
if not SERVICE_DID:
    SERVICE_DID = f"did:web:{HOSTNAME}"

FEED_URI = _get_str_env_var("MY_FEED_URI")
if not FEED_URI:
    raise RuntimeError("Publish your feed first (run publish_feed.py) to obtain Feed URI. Set 'FEED_URI' environment variable to the provided URI.")

IGNORE_ARCHIVED_POSTS = _get_bool_env_var("IGNORE_ARCHIVED_POSTS")
IGNORE_REPLY_POSTS = _get_bool_env_var("IGNORE_REPLY_POSTS")

DATABASE_URL = _get_str_env_var("DATABASE_URL")
if not DATABASE_URL:
   raise RuntimeError("You must set 'DATABASE_URL' environment variable.")