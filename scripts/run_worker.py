#!/usr/bin/env python
"""
Entry point for running a simulation worker.

Usage:
    python scripts/run_worker.py
    python scripts/run_worker.py --concurrency 4
"""
import argparse
import asyncio
import logging
import sys
import os

# Ensure project root is on path when run as script
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.db import create_all_tables

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("run_worker")


async def main(concurrency: int) -> None:
    logger.info("Initialising database tables...")
    await create_all_tables()

    from workers.worker import worker_loop

    tasks = [asyncio.create_task(worker_loop()) for _ in range(concurrency)]
    logger.info("Started %d worker(s). Press Ctrl+C to stop.", concurrency)
    try:
        await asyncio.gather(*tasks)
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("Shutting down workers...")
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        logger.info("Workers stopped.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run simulation worker(s)")
    parser.add_argument(
        "--concurrency",
        type=int,
        default=2,
        help="Number of concurrent worker coroutines (default: 2)",
    )
    args = parser.parse_args()

    try:
        asyncio.run(main(args.concurrency))
    except KeyboardInterrupt:
        pass
