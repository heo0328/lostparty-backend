"""Durable authority lives in opening rows, never in process wake-up time."""
import os,asyncio,logging
from app.raid_rooms.continuation import process_due


async def run():
    if os.getenv('RECRUITMENT_WORKER_ENABLED','1')=='0':return
    while True:
        await asyncio.sleep(5)
        try:await asyncio.to_thread(process_due)
        except Exception:logging.getLogger(__name__).warning('Recruitment opening attempt failed')
