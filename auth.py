from fastapi import FastAPI, Request, HTTPException
from atproto import IdResolver, verify_jwt
from atproto.exceptions import TokenInvalidSignatureError

def validate_auth(app: FastAPI, request: Request) -> str:
  _PREFIX = "Bearer "
  _ID_RESOLVER: IdResolver = app.state.id_resolver
  """Validate authorization header.

  Args:
    request (Request): The FastAPI request to validate.

  Returns:
    str: Requester DID.

  Raises:
    HTTPException: If the authorization header is missing or invalid.
  """
  auth_header = request.headers.get("Authorization")
  if not auth_header:
    raise HTTPException(status_code=401, detail="Authorization header is missing")

  if not auth_header.startswith(_PREFIX):
    raise HTTPException(status_code=401, detail="Invalid authorization header")

  jwt = auth_header[len(_PREFIX):].strip()

  try:
    return verify_jwt(jwt, _ID_RESOLVER.did.resolve_atproto_key).iss
  except TokenInvalidSignatureError as e:
    raise HTTPException(status_code=401, detail='Invalid signature') from e
