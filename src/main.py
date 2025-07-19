import os
import asyncio
import time, logging, threading, coloredlogs
from lib.db import Database
from dotenv import load_dotenv
from util.constants import TEST_TRASHBIN_IDS, TRASHBIN_IDS
from util.test import test_simulate_trashbin

field_styles = {
    "asctime": {"color": "cyan"},
    "levelname": {"bold": True, "color": "magenta"},
    "message": {"color": "white"},
}

level_styles = {
    "debug": {"color": "blue"},
    "info": {"color": "green"},
    "warning": {"color": "yellow"},
    "error": {"color": "red"},
    "critical": {"bold": True, "color": "red", "background": "white"},
}

coloredlogs.install(
    level="DEBUG",  # Log everything from DEBUG and up
    fmt="%(asctime)s [%(levelname)s] %(message)s",
    field_styles=field_styles,
    level_styles=level_styles,
)


async def main():
    load_dotenv()
    connection_string = os.getenv("DATABASE_URL")

    if not connection_string:
        raise ValueError("DATABASE_URL is not set.")

    db = Database(connection_string)
    await db.connect()

    try:
        current_time = await db.get_current_time()
        version = await db.get_version()
        print(f"Connected to database at {current_time} with version: {version}")
    except Exception as e:
        logging.error(f"DB error: {e}")
        return

    tasks = [asyncio.create_task(test_simulate_trashbin(id, db)) for id in TRASHBIN_IDS]

    try:
        await asyncio.Event().wait()
    except (asyncio.CancelledError, KeyboardInterrupt):
        logging.info("KeyboardInterrupt received. Cancelling tasks...")
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
    finally:
        await db.disconnect()
        logging.info("Shutdown complete.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Application manually stopped.")
