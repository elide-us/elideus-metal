import asyncio
from fastapi import APIRouter, HTTPException

router = APIRouter()

@router.get("/ffmpeg")
async def get_ffmpeg():
  try:
    process = await asyncio.create_subprocess_exec(
      "ffmpeg", "-version",
      stdout=asyncio.subprocess.PIPE,
      stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    if stdout:
      version_line = stdout.decode().splitlines()[0]
    else:
      version_line = stderr.decode().splitlines()[0]
    return {"ffmpeg_version": version_line}
  except Exception as e:
    raise HTTPException(status_code=500, detail="Error checking ffmpeg: {e}")