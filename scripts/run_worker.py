"""Script to run the Kafka ReviewWorker as a background consumer daemon."""

import asyncio
import signal
import sys
from pathlib import Path

# Add project root and backend to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "backend"))

from app.core.config import settings
from app.core.logging import setup_logging, get_logger
from app.workers.review_worker import ReviewWorker
from app.services.analysis_service import handle_review_created_event

setup_logging(level=settings.LOG_LEVEL, environment=settings.ENVIRONMENT)
logger = get_logger("cva.scripts.run_worker")


async def main():
    logger.info("Starting Customer Voice AI ReviewWorker...")
    worker = ReviewWorker()
    worker.register_handler(handle_review_created_event)

    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def _signal_handler():
        logger.info("Received termination signal, stopping worker...")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _signal_handler)
        except NotImplementedError:
            # Signal handling on some platforms
            pass

    worker_task = asyncio.create_task(worker.run())
    stop_waiter = asyncio.create_task(stop_event.wait())

    done, pending = await asyncio.wait([worker_task, stop_waiter], return_when=asyncio.FIRST_COMPLETED)

    if stop_waiter in done:
        await worker.stop()
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass

    logger.info("Worker process terminated cleanly.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
