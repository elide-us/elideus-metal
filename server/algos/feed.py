from datetime import datetime
from typing import Optional

CURSOR_EOF = 'eof'

async def handler(pool, cursor: Optional[str], limit: int) -> dict:
    async with pool.acquire() as conn:
        if cursor:
            if cursor == CURSOR_EOF:
                return {"cursor": CURSOR_EOF, "feed": []}
            cursor_parts = cursor.split("::")
            if len(cursor_parts) != 2:
                raise ValueError("Malformed cursor")
            indexed_at_str, cid = cursor_parts
            try:
                indexed_at_ts = int(indexed_at_str)
            except ValueError:
                raise ValueError("Malformed cursor")
            indexed_at = datetime.fromtimestamp(indexed_at_ts / 1000)
            # Query with cursor filtering: select posts where either
            # the indexed_at matches and cid is less than the cursor cid,
            # or indexed_at is less than the cursor's indexed_at.
            query = """
                SELECT * FROM posts
                WHERE (indexed_at = $1 AND cid < $2) OR (indexed_at < $1)
                ORDER BY indexed_at DESC, cid DESC
                LIMIT $3
            """
            rows = await conn.fetch(query, indexed_at, cid, limit)
        else:
            query = """
                SELECT * FROM posts
                ORDER BY indexed_at DESC, cid DESC
                LIMIT $1
            """
            rows = await conn.fetch(query, limit)
    
    # Build the feed from the returned rows.
    feed = [{"post": row["uri"]} for row in rows]
    
    # Determine the new cursor based on the last row, if available.
    new_cursor = CURSOR_EOF
    if rows:
        last_row = rows[-1]
        # Assumes 'indexed_at' is returned as a datetime.
        new_cursor = f'{int(last_row["indexed_at"].timestamp() * 1000)}::{last_row["cid"]}'
    
    return {"cursor": new_cursor, "feed": feed}
