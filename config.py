import os

VERSION = "0.0.5"

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
    raise RuntimeError("You must set 'HOSTNAME' environment variable first.")

SERVICE_DID = _get_str_env_var("SERVICE_DID")
if not SERVICE_DID:
    SERVICE_DID = f"did:web:{HOSTNAME}"

FEED_URI = _get_str_env_var("FEED_URI")
if not FEED_URI:
    raise RuntimeError("Publish your feed first (run publish_feed.py) to obtain Feed URI. Set 'FEED_URI' environment variable to the provided URI.")

IGNORE_ARCHIVED_POSTS = _get_bool_env_var("IGNORE_ARCHIVED_POSTS")
IGNORE_REPLY_POSTS = _get_bool_env_var("IGNORE_REPLY_POSTS")
