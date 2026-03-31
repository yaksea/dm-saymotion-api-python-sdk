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

balance = client.get_credit_balance()
print(f"Credit balance: {balance}")

all_models = client.list_character_models()
model_id = all_models[0].id if all_models else None


def on_progress(data):
    if data.position_in_queue:
        print(f"Position in queue: {data.position_in_queue}")
    else:
        print(f"Progress: {data.progress_percent}%")


def on_result(data):
    if data.result:
        print("Job completed successfully!")
        client.download_job(data.rid, output_dir="./output")
    elif data.error:
        print(f"Job failed: {data.error.message}")


if model_id:
    rid = client.start_new_job(
        prompt="A person walking forward slowly",
        model_id=model_id,
        params=Text2MotionParams(requested_animation_duration=5.0),
        result_callback=on_result,
        progress_callback=on_progress,
    )
    print(f"Job finished, RID: {rid}")

client.close()
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

        all_models = await client.list_character_models()
        model_id = all_models[0].id if all_models else None

        if not model_id:
            return

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
            params=Text2MotionParams(requested_animation_duration=5.0),
            result_callback=on_result,
            progress_callback=on_progress,
        )
        print(f"Job finished, RID: {rid}")


asyncio.run(main())
```

## Configuration

Credentials can be set via environment variables:

```bash
export DM_API_SERVER_URL="https://service.deepmotion.com"
export DM_CLIENT_ID="your_client_id"
export DM_CLIENT_SECRET="your_client_secret"
```

## API Reference

### Client Initialization

Both clients support the same constructor parameters:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `api_server_url` | str | Yes | Base URL of the API server |
| `client_id` | str | Yes | Client ID for authentication |
| `client_secret` | str | Yes | Client secret for authentication |
| `timeout` | int | No | Request timeout in seconds |

`SaymotionClient` supports context manager (`with` statement) and `close()`.
`AsyncSaymotionClient` supports async context manager (`async with`) and `close()`.

### Character Model API

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `list_character_models` | model_id?, search_token?, only_custom? | List[CharacterModel] | List available models. Default sends `stockModel=all`; pass `only_custom=True` for custom models only |
| `upload_character_model` | source, name?, create_thumb? | str (model_id) | Upload or store a model. `source` can be a local file path or HTTP URL |
| `delete_character_model` | model_id | int (count) | Delete a model |

### Job API

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `start_new_job` | **prompt**, **model_id**, params?(Text2MotionParams), result_callback?, progress_callback?, poll_interval?, blocking?, timeout? | str (rid) | Start text2motion job |
| `start_render_job` | **t2m_rid**, params?(RenderParams), result_callback?, progress_callback?, poll_interval?, blocking?, timeout? | str (rid) | Render animation to video |
| `start_inpainting_job` | **t2m_rid**, **prompt**, **intervals**(List[TimeInterval]), params?(InpaintingParams), result_callback?, progress_callback?, poll_interval?, blocking?, timeout? | str (rid) | Inpainting job |
| `start_merging_job` | **t2m_rid**, **prompt**, params?(MergingParams), result_callback?, progress_callback?, poll_interval?, blocking?, timeout? | str (rid) | Merging job |
| `start_loop_job` | **t2m_rid**, params?(LoopParams), result_callback?, progress_callback?, poll_interval?, blocking?, timeout? | str (rid) | Loop job |
| `start_refine_job` | **t2m_rid**, params?(RefineParams), result_callback?, progress_callback?, poll_interval?, blocking?, timeout? | str (rid) | Refine job |
| `import_animate3d_job` | rid, model, params | str (rid) | Import Animate3D job |
| `rerun_job` | **t2m_rid**, **model_id**, params?(RerunParams), result_callback?, progress_callback?, poll_interval?, blocking?, timeout? | str (new_rid) | Rerun with rerunRequest |
| `cancel_job` | rid | bool | Cancel job |
| `get_job_status` | rid | JobStatus | Get job status |
| `list_jobs` | status?, processor? | List[Job] | List jobs |
| `download_job` | rid, output_dir?, variant_id? | DownloadLink | Download results. If `output_dir` is set, files are saved to disk |

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

### Text2MotionParams (optional settings for `start_new_job`)

Required params `prompt` and `model_id` are on the method signature.

```python
Text2MotionParams(
    physics_filter=None,                 # False to turn off simulation (dis=s)
    foot_locking_mode="auto",            # "auto", "always", "never", "grounding"
    pose_filtering_strength=0.0,         # 0.0-1.0
    skip_fbx=None,                       # 1 to skip FBX generation
    num_variant=1,                       # 1-8 variants
    requested_animation_duration=None,   # seconds (0 means AI decides)
)
```

### RenderParams (optional settings for `start_render_job`)

Required param `t2m_rid` is on the method signature.

```python
RenderParams(
    variant_id=1,                        # variant to render
    bg_color=(0, 177, 64, 0),            # RGBA for green screen
    backdrop="studio",                   # "studio" or 2D backdrop name
    shadow=1,                            # 0=off, 1=on
    cam_mode=0,                          # 0=Cinematic, 1=Fixed, 2=Face
    cam_horizontal_angle=0.0,            # -90 to +90 degrees
)
```

### RerunParams (optional settings for `rerun_job`, extends Text2MotionParams)

Inherits all `Text2MotionParams` optional settings. Required params `t2m_rid` and `model_id` are on the method signature.

```python
RerunParams(
    variant_id=1,                        # variant to rerun
    rerun=1,                             # 0 or 1
    # inherited from Text2MotionParams:
    physics_filter=None,                 # False to turn off simulation
    foot_locking_mode="auto",            # "auto", "always", "never", "grounding"
    pose_filtering_strength=0.0,         # 0.0-1.0
    skip_fbx=None,                       # 1 to skip FBX generation
    num_variant=1,                       # 1-8 variants
    requested_animation_duration=None,   # seconds
)
```

### TimeInterval

```python
TimeInterval(start=0.5, end=2.0)
```

### InpaintingParams (optional settings for `start_inpainting_job`)

Required params `t2m_rid`, `prompt`, `intervals` are on the method signature.
`intervals` is a `List[TimeInterval]`.

```python
from dm.saymotion import TimeInterval, InpaintingParams

client.start_inpainting_job(
    t2m_rid="rid",
    prompt="modified motion",
    intervals=[TimeInterval(start=0.5, end=2.0)],
    params=InpaintingParams(variant_id=1),
)
```

### MergingParams (optional settings for `start_merging_job`)

Required params `t2m_rid`, `prompt` are on the method signature.

```python
MergingParams(
    variant_id=1,
    edit_request={"numTrimLeft": 5, "numTrimRight": 5},
    blend_duration=0.5,
)
```

### LoopParams (optional settings for `start_loop_job`)

Required param `t2m_rid` is on the method signature.

```python
LoopParams(
    variant_id=1,
    prompt="looping motion",
    num_reps=3,
    blend_duration=0.5,
    fix_root_mode="INTERPOLATION",       # "INTERPOLATION" or "LOCKED"
    fix_root_position_altitude=0,        # 0 or 1
    fix_root_position_horizontal=0,      # 0 or 1
    fix_root_orientation=0,              # 0 or 1
    fix_across_entire_motion=0,          # 0 or 1
)
```

### RefineParams (optional settings for `start_refine_job`)

Required param `t2m_rid` is on the method signature.

```python
RefineParams(
    variant_id=1,
    prompt="refined motion description",
    creativity=0.5,                      # 0.0-1.0
    num_variant=1,                       # 1-8 variants
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

try:
    rid = client.start_new_job(...)
except AuthenticationError:
    print("Invalid credentials")
except TimeoutError as e:
    print(f"Job timed out: {e}, RID: {e.rid}")
except APIError as e:
    print(f"API error: {e}, status: {e.status_code}")
except ValidationError as e:
    print(f"Invalid input: {e}")
```

In result callbacks:

```python
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
