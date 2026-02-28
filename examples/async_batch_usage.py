"""Async batch job submission example.

This example demonstrates how to:
1. Submit multiple text2motion jobs without waiting
2. Wait for all jobs to complete
"""

import asyncio

from dm.saymotion import (
    AsyncSaymotionClient,
    Text2MotionParams,
    ResultCallbackData,
    ProgressCallbackData,
)

# Configuration
API_SERVER_URL = "https://service.deepmotion.com"
CLIENT_ID = "your_client_id"
CLIENT_SECRET = "your_client_secret"

done_job_count = 0


def on_progress(data: ProgressCallbackData):
    """Progress callback."""
    if data.position_in_queue:
        print(f"Position of Job[{data.rid}] in queue: {data.position_in_queue}")
    else:
        print(f"Progress of Job[{data.rid}]: {data.progress_percent}%")


def on_result(data: ResultCallbackData):
    """Result callback."""
    if data.result:
        print(f"Job[{data.rid}] completed successfully!")
    elif data.error:
        print(f"Job[{data.rid}] failed: {data.error.message} (Code: {data.error.code})")

    global done_job_count
    done_job_count += 1


async def main():
    async with AsyncSaymotionClient(
        api_server_url=API_SERVER_URL,
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
    ) as client:
        # Get a character model ID
        all_models = await client.list_character_models(stock_model="deepmotion")
        if not all_models:
            print("No models found")
            return
        model_id = all_models[0].id

        # Prompts to process
        prompts = [
            "A person walking forward slowly",
            "A person waving hello",
            "A person sitting down",
        ]

        print("=== Submitting jobs ===")
        rids = []
        for prompt in prompts:
            params = Text2MotionParams(
                prompt=prompt,
                model_id=model_id,
            )
            rid = await client.start_new_job(
                prompt=prompt,
                model_id=model_id,
                params=params,
                progress_callback=on_progress,
                result_callback=on_result,
                poll_interval=10,
                blocking=False,
            )
            rids.append((prompt, rid))
            print(f"Submitted: {prompt[:30]}... -> Job ID: {rid}")

        while done_job_count < len(rids):
            await asyncio.sleep(3)

        print("\n=== All jobs processed ===")


if __name__ == "__main__":
    asyncio.run(main())
