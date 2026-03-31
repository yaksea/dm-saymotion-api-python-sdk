"""Async batch job submission example.

This example demonstrates how to:
1. Submit multiple text2motion jobs without waiting
2. Wait for all jobs to complete using asyncio primitives
"""

import asyncio
import os

from dm.saymotion import (
    AsyncSaymotionClient,
    ResultCallbackData,
    ProgressCallbackData,
)

# Configuration - replace with your credentials or set environment variables
API_SERVER_URL = os.environ.get("DM_API_SERVER_URL", "https://service.deepmotion.com")
CLIENT_ID = os.environ.get("DM_CLIENT_ID", "your_client_id")
CLIENT_SECRET = os.environ.get("DM_CLIENT_SECRET", "your_client_secret")


def on_progress(data: ProgressCallbackData):
    """Progress callback."""
    if data.position_in_queue:
        print(f"Position of Job[{data.rid}] in queue: {data.position_in_queue}")
    else:
        print(f"Progress of Job[{data.rid}]: {data.progress_percent}%")


async def main():
    pending_count = 0
    all_done = asyncio.Event()

    def on_result(data: ResultCallbackData):
        """Result callback."""
        nonlocal pending_count
        if data.result:
            print(f"Job[{data.rid}] completed successfully!")
        elif data.error:
            print(f"Job[{data.rid}] failed: {data.error.message} (Code: {data.error.code})")

        pending_count -= 1
        if pending_count <= 0:
            all_done.set()

    async with AsyncSaymotionClient(
        api_server_url=API_SERVER_URL,
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
    ) as client:
        all_models = await client.list_character_models()
        if not all_models:
            print("No models found")
            return
        model_id = all_models[0].id

        prompts = [
            "A person walking forward slowly",
            "A person waving hello",
            "A person sitting down",
        ]

        print("=== Submitting jobs ===")
        pending_count = len(prompts)
        for prompt in prompts:
            rid = await client.start_new_job(
                prompt=prompt,
                model_id=model_id,
                progress_callback=on_progress,
                result_callback=on_result,
                poll_interval=10,
                blocking=False,
            )
            print(f"Submitted: {prompt[:30]}... -> Job ID: {rid}")

        await all_done.wait()
        print("\n=== All jobs processed ===")


if __name__ == "__main__":
    asyncio.run(main())
