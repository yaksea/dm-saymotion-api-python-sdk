"""Basic asynchronous usage example for Saymotion SDK.

This example demonstrates how to use the async client with text2motion:
1. Start a new text2motion job
2. Receive progress updates via callback
3. Download results
"""

import asyncio
import os

from dm.saymotion import (
    AsyncSaymotionClient,
    Text2MotionParams,
    ResultCallbackData,
    ProgressCallbackData,
)

# Configuration - replace with your credentials
API_SERVER_URL = "https://service.deepmotion.com"
CLIENT_ID = "your_client_id"
CLIENT_SECRET = "your_client_secret"

OUTPUT_DIR = "./output"


def on_progress(data: ProgressCallbackData):
    """Progress callback."""
    if data.position_in_queue:
        print(f"Position in queue: {data.position_in_queue}")
    else:
        print(f"Progress: {data.progress_percent}%")


async def on_result(data: ResultCallbackData):
    """Result callback."""
    if data.result:
        print("Job completed successfully!")
        if data.result.output:
            print(f"Output: {data.result.output}")
        print("Downloading results...")
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        await client.download_job(data.rid, output_dir=OUTPUT_DIR)
    elif data.error:
        print(f"Job failed: {data.error.message} (Code: {data.error.code})")


async def main():
    async with AsyncSaymotionClient(
        api_server_url=API_SERVER_URL,
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
    ) as client:
        # Check credit balance
        balance = await client.get_credit_balance()
        print(f"Credit balance: {balance}")

        if balance <= 0:
            print("No credit, cannot process job")
            return

        # Get a character model ID
        all_models = await client.list_character_models(stock_model="deepmotion")
        if not all_models:
            print("No models found")
            return
        model_id = all_models[0].id

        # Text prompt for motion generation
        prompt = "A person walking forward slowly"
        params = Text2MotionParams(
            prompt=prompt,
            model_id=model_id,
            requested_animation_duration=5.0,
        )

        print(f"\n=== Starting text2motion job ===")
        print(f"Prompt: {prompt}")

        rid = await client.start_new_job(
            prompt=prompt,
            model_id=model_id,
            params=params,
            result_callback=on_result,
            progress_callback=on_progress,
        )
        print(f"Job finished, RID: {rid}")

    print("\n=== Done! ===")


if __name__ == "__main__":
    asyncio.run(main())
