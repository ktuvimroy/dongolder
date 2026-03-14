"""Entry point for running gold_signal_bot as a module.

Usage:
    python -m gold_signal_bot
"""

import asyncio

from gold_signal_bot import main

if __name__ == "__main__":
    asyncio.run(main())
