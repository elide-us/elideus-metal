from atproto import DidInMemoryCache, IdResolver, verify_jwt
from atproto.exceptions import TokenInvalidSignatureError
from fastapi import Request, HTTPException

_CACHE = DidInMemoryCache()
_ID_RESOLVER = IdResolver(cache=_CACHE)

_AUTHORIZATION_HEADER_NAME = 'Authorization'
_AUTHORIZATION_HEADER_VALUE_PREFIX = 'Bearer '

def validate_auth(request: Request) -> str:
  """Validate authorization header.

  Args:
    request (Request): The FastAPI request to validate.

  Returns:
    str: Requester DID.

  Raises:
    HTTPException: If the authorization header is missing or invalid.
  """
  auth_header = request.headers.get(_AUTHORIZATION_HEADER_NAME)
  if not auth_header:
    raise HTTPException(status_code=401, detail='Authorization header is missing')

  if not auth_header.startswith(_AUTHORIZATION_HEADER_VALUE_PREFIX):
    raise HTTPException(status_code=401, detail='Invalid authorization header')

  jwt = auth_header[len(_AUTHORIZATION_HEADER_VALUE_PREFIX):].strip()

  try:
    return verify_jwt(jwt, _ID_RESOLVER.did.resolve_atproto_key).iss
  except TokenInvalidSignatureError as e:
    raise HTTPException(status_code=401, detail='Invalid signature') from e
