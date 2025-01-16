import asyncio
from utils import run_all
import json


try:
    # Load data from the JSON file
    with open('config.json', "r") as file:
        data = json.load(file)
except FileNotFoundError:
    raise FileNotFoundError(f"config.json file does not exist. Create one")
except json.JSONDecodeError:
    raise ValueError(f"The config file is not a valid JSON file.")

private_keys = data.get("private_keys", [])

asyncio.run(run_all(private_keys))
