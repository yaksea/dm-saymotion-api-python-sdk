"""Rerun job example.

This example demonstrates how to rerun a previous text2motion job.
"""

import os

from dm.saymotion import (
    SaymotionClient,
    Status,
    ProgressCallbackData,
    ResultCallbackData, RerunParams,
)

# Configuration - replace with your credentials or set environment variables
API_SERVER_URL = os.environ.get("DM_API_SERVER_URL", "https://service.deepmotion.com")
CLIENT_ID = os.environ.get("DM_CLIENT_ID", "your_client_id")
CLIENT_SECRET = os.environ.get("DM_CLIENT_SECRET", "your_client_secret")


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
    elif data.error:
        print(f"Job failed: {data.error.message} (Code: {data.error.code})")


def main():
    client = SaymotionClient(
        api_server_url=API_SERVER_URL,
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
    )

    # List completed text2motion jobs
    jobs = client.list_jobs(
        status=[Status.SUCCESS],
        processor="text2motion",
    )
    if not jobs:
        print("No completed jobs to rerun")
        return

    # Use the first completed job
    rid = jobs[0].rid
    variant_id = 1  # Default variant
    if jobs[0].variants and isinstance(jobs[0].variants, dict):
        first_key = next(iter(jobs[0].variants.keys()), "1")
        try:
            variant_id = int(first_key)
        except (ValueError, TypeError):
            variant_id = 1

    print(f"Rerunning job RID: {rid}, variant_id: {variant_id}")

    # Get a character model ID
    all_models = client.list_character_models()
    if not all_models:
        print("No models found")
        return
    model_id = all_models[0].id

    try:
        new_rid = client.rerun_job(
            t2m_rid=rid,
            model_id=model_id,
            params=RerunParams(variant_id=variant_id),
            result_callback=on_result,
            progress_callback=on_progress,
        )
        print(f"New RID of rerun job : {new_rid}")

    except Exception as e:
        print(f"Error rerunning job: {e}")
        print("Note: This example requires a valid RID from a previous text2motion job.")


if __name__ == "__main__":
    main()
