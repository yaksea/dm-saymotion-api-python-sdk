"""Basic synchronous usage example for Saymotion SDK.

This example demonstrates how to use the synchronous client to:
1. Start a new text2motion job (text prompt to animation)
2. Wait for completion with progress and result callbacks
3. Download results
"""

import os

from dm.saymotion import (
    SaymotionClient,
    Text2MotionParams,
    ResultCallbackData,
    ProgressCallbackData,
)

# Configuration - replace with your credentials or set environment variables
API_SERVER_URL = os.environ.get("DM_API_SERVER_URL", "https://service.deepmotion.com")
CLIENT_ID = os.environ.get("DM_CLIENT_ID", "your_client_id")
CLIENT_SECRET = os.environ.get("DM_CLIENT_SECRET", "your_client_secret")

OUTPUT_DIR = "./output"

client = SaymotionClient(
    api_server_url=API_SERVER_URL,
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    timeout=30,
)


def on_progress(data: ProgressCallbackData):
    """Progress callback."""
    if data.position_in_queue:
        print(f"Position in queue: {data.position_in_queue}")
    else:
        print(f"Progress: {data.progress_percent}%")


def on_result(data: ResultCallbackData):
    """Result callback."""
    if data.result:
        print("Job completed successfully!")
        if data.result.output:
            print(f"Output: {data.result.output}")
        print("Downloading results...")
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        client.download_job(data.rid, output_dir=OUTPUT_DIR)
    elif data.error:
        print(f"Job failed: {data.error.message} (Code: {data.error.code})")


def main():
    # Check credit balance
    balance = client.get_credit_balance()
    print(f"Credit balance: {balance}")

    if balance <= 0:
        print("No credit, cannot process job")
        return

    # Get a character model ID (use stockModel for built-in models)
    all_models = client.list_character_models(stock_model="deepmotion")
    if not all_models:
        print("No models found")
        return
    model_id = all_models[0].id

    # Text prompt for motion generation
    prompt = "A person walking forward slowly"

    print(f"\n=== Starting text2motion job ===")
    print(f"Prompt: {prompt}")

    rid = client.start_new_job(
        prompt=prompt,
        model_id=model_id,
        params=Text2MotionParams(requested_animation_duration=5.0),
        result_callback=on_result,
        progress_callback=on_progress,
    )
    print(f"Job finished, RID: {rid}")

    print("\n=== Done! ===")


if __name__ == "__main__":
    main()
