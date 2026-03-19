"""Render job example (synchronous).

This example demonstrates how to use the synchronous client to:
1. Find a completed text2motion job
2. Start a render job (animation to video)
3. Wait for completion with progress and result callbacks
4. Download results
"""

import os

from dm.saymotion import (
    SaymotionClient,
    RenderParams,
    Status,
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
        print("Render job completed successfully!")
        if data.result.output:
            print(f"Output: {data.result.output}")
        print("Downloading results...")
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        client.download_job(data.rid, output_dir=OUTPUT_DIR)
    elif data.error:
        print(f"Render job failed: {data.error.message} (Code: {data.error.code})")


def main():
    # Check credit balance
    balance = client.get_credit_balance()
    print(f"Credit balance: {balance}")

    if balance <= 0:
        print("No credit, cannot process job")
        return

    # List completed text2motion jobs (render needs a completed text2motion job)
    jobs = client.list_jobs(
        status=[Status.SUCCESS],
        processor="text2motion",
    )
    if not jobs:
        print("No completed text2motion jobs found.")
        print("Run sync_basic_usage.py first to create a text2motion job.")
        return

    # Use the first completed job
    t2m_rid = jobs[0].rid
    variant_id = 1
    if jobs[0].variants and isinstance(jobs[0].variants, dict):
        first_key = next(iter(jobs[0].variants.keys()), "1")
        try:
            variant_id = int(first_key)
        except (ValueError, TypeError):
            variant_id = 1

    # Optional: customize render params (backdrop, shadow, etc.)
    params = RenderParams(
        variant_id=variant_id,
        backdrop="studio",
        shadow=1,
        cam_mode=0,
    )

    print(f"\n=== Starting render job ===")
    print(f"t2m_rid: {t2m_rid}, variant_id: {variant_id}")

    rid = client.start_render_job(
        t2m_rid=t2m_rid,
        params=params,
        result_callback=on_result,
        progress_callback=on_progress,
    )
    print(f"Render job finished, RID: {rid}")

    print("\n=== Done! ===")


if __name__ == "__main__":
    main()
