import asyncio
from utils import run_all
from utils import data

private_keys = data.get("private_keys", [])

asyncio.run(run_all(private_keys))
