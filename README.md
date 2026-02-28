# Saymotion Python SDK

Python SDK for the Saymotion REST API, providing both synchronous and asynchronous interfaces for text-to-motion and render operations.

## Installation

```bash
pip install dm-saymotion-api
```

## Quick Start

### Synchronous Usage

```python
from dm.saymotion import SaymotionClient, Text2MotionParams

client = SaymotionClient(
    api_server_url="https://service.deepmotion.com",
    client_id="your_client_id",
    client_secret="your_client_secret",
)

# Check credit balance
balance = client.get_credit_balance()
print(f"Credit balance: {balance}")

# Get a character model
all_models = client.list_character_models(stock_model="deepmotion")
model_id = all_models[0].id if all_models else None


# Callbacks
def on_progress(data):
    if data.position_in_queue:
        print(f"Position in queue: {data.position_in_queue}")
    else:
        print(f"Progress: {data.progress_percent}%")


def on_result(data):
    if data.result:
        print("Job completed successfully!")
        print(f"Output: {data.result.output}")
        client.download_job(data.rid, output_dir="./output")
    elif data.error:
        print(f"Job failed: {data.error.message}")


# Start text2motion job
if model_id:
    params = Text2MotionParams(
        prompt="A person walking forward slowly",
        model_id=model_id,
        requested_animation_duration=5.0,
    )

    print("Starting job...")
    rid = client.start_new_job(
        prompt="A person walking forward slowly",
        model_id=model_id,
        params=params,
        result_callback=on_result,
        progress_callback=on_progress,
    )
    print(f"Job finished, RID: {rid}")
```

### Asynchronous Usage

```python
import asyncio
from dm.saymotion import AsyncSaymotionClient, Text2MotionParams


async def main():
    async with AsyncSaymotionClient(
            api_server_url="https://service.deepmotion.com",
            client_id="your_client_id",
            client_secret="your_client_secret",
    ) as client:

        balance = await client.get_credit_balance()
        print(f"Credit balance: {balance}")

        all_models = await client.list_character_models(stock_model="deepmotion")
        model_id = all_models[0].id if all_models else None

        if not model_id:
            return

        params = Text2MotionParams(
            prompt="A person walking forward slowly",
            model_id=model_id,
            requested_animation_duration=5.0,
        )

        def on_progress(data):
            if data.position_in_queue:
                print(f"Position in queue: {data.position_in_queue}")
            else:
                print(f"Progress: {data.progress_percent}%")

        async def on_result(data):
            if data.result:
                print("Success!")
                await client.download_job(data.rid, output_dir="./output")
            elif data.error:
                print(f"Failed: {data.error.message}")

        rid = await client.start_new_job(
            prompt="A person walking forward slowly",
            model_id=model_id,
            params=params,
            result_callback=on_result,
            progress_callback=on_progress,
        )
        print(f"Job finished, RID: {rid}")


asyncio.run(main())
```

## API Reference

### Client Initialization

```python
# Synchronous client
client = SaymotionClient(
    api_server_url: str,
    client_id: str,
    client_secret: str,
    timeout: Optional[int],
)

# Asynchronous client
async with AsyncSaymotionClient(
    api_server_url: str,
    client_id: str,
    client_secret: str,
    timeout: Optional[int],
) as client:
    ...
```

### Character Model API

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `list_character_models` | model_id?, search_token?, stock_model? | List[CharacterModel] | List available models |
| `upload_character_model` | source, name?, create_thumb? | str (model_id) | Upload or store a model |
| `delete_character_model` | model_id | int (count) | Delete a model |

### Job API

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `start_new_job` | prompt, model_id, params?, result_callback?, progress_callback?, poll_interval?, blocking?, timeout? | str (rid) | Start text2motion job |
| `start_render_job` | t2m_rid, variant_id, params?, ... | str (rid) | Render animation to video |
| `start_inpainting_job` | params (InpaintingParams), ... | str (rid) | Inpainting job |
| `start_merging_job` | params (MergingParams), ... | str (rid) | Merging job |
| `start_loop_job` | params (LoopParams), ... | str (rid) | Loop job |
| `start_refine_job` | params (RefineParams), ... | str (rid) | Refine job |
| `import_animate3d_job` | rid, model, params | str (rid) | Import Animate3D job |
| `rerun_job` | t2m_rid, variant_id?, params?, ... | str (new_rid) | Rerun with rerunRequest |
| `cancel_job` | rid | bool | Cancel job |
| `get_job_status` | rid | JobStatus | Get job status |
| `list_jobs` | status?, processor? | List[Job] | List jobs |
| `download_job` | rid, output_dir?, variant_id? | DownloadLink | Download results |

### Prompt API

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `optimize_prompt` | prompt, break_into_actionable_prompts? | str (rid) | Optimize prompt |
| `get_prompt_status` | rid | dict | Get prompt optimization status |

### Account API

| Method | Returns | Description |
|--------|---------|-------------|
| `get_credit_balance` | float | Get account credit balance |

## Parameter Classes

### Text2MotionParams

```python
Text2MotionParams(
    prompt="A person walking",
    model_id="model_id",
    dis=None,                      # "s" to turn off simulation
    foot_locking_mode="auto",      # "auto", "always", "never", "grounding"
    pose_filtering_strength=0.0,   # 0.0-1.0
    skip_fbx=None,                 # 1 to skip FBX
    num_variant=1,                 # 1-8
    requested_animation_duration=None,  # seconds
)
```

### RenderParams

```python
RenderParams(
    t2m_rid="rid",
    variant_id=1,
    bg_color=(0, 177, 64, 0),      # RGBA for green screen
    backdrop="studio",             # or 2D backdrop name
    shadow=1,                      # 0=off, 1=on
    cam_mode=0,                    # 0=Cinematic, 1=Fixed, 2=Face
    cam_horizontal_angle=0.0,      # -90 to +90 degrees
)
```

## Usage Examples

See the `examples/` directory:

- `sync_basic_usage.py` - Basic synchronous text2motion
- `sync_batch_usage.py` - Batch text2motion (sync)
- `sync_render_job_usage.py` - Render animation to video (sync)
- `async_basic_usage.py` - Basic asynchronous text2motion
- `async_batch_usage.py` - Batch text2motion (async)
- `async_render_job_usage.py` - Render animation to video (async)
- `character_model_usage.py` - Character model management
- `rerun_job_usage.py` - Rerunning jobs with RerunParams

## Error Handling

```python
from dm.saymotion import (
    Animate3DError,
    AuthenticationError,
    APIError,
    ValidationError,
    TimeoutError,
)

def on_result(data):
    if data.error:
        print(f"Job failed: {data.error.message} (Code: {data.error.code})")
```

## Requirements

- Python 3.8+
- requests >= 2.28.0
- aiohttp >= 3.8.0

## License

MIT License

## Support

For issues and questions, please contact DeepMotion support.
