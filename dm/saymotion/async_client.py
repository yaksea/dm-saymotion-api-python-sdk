"""Asynchronous client for Saymotion API."""

import asyncio
import math
import os
from typing import List, Optional, Dict, Any, Callable, Awaitable

import aiohttp
from aiohttp import BasicAuth

from dm.saymotion.data.callback import (
    ProgressCallbackData,
    ResultCallbackData,
    JobResult,
    JobError,
)
from dm.saymotion.data.character import CharacterModel
from dm.saymotion.data.enums import Status
from dm.saymotion.data.job import Job
from dm.saymotion.data.job_status import JobStatus
from dm.saymotion.data.params import (
    Text2MotionParams,
    RenderParams,
    RerunParams,
    InpaintingParams,
    MergingParams,
    LoopParams,
    RefineParams,
)
from dm.saymotion.data.response import DownloadLink
from dm.saymotion.exceptions import (
    AuthenticationError,
    APIError,
    ValidationError,
    TimeoutError,
)
from dm.saymotion.utils import (
    is_http_url,
    get_file_extension,
    get_file_name_without_ext,
)


class AsyncSaymotionClient:
    """Asynchronous client for Saymotion REST API."""

    def __init__(
            self,
            api_server_url: str,
            client_id: str,
            client_secret: str,
            timeout: Optional[int] = None,
    ):
        self.api_server_url = api_server_url.rstrip("/")
        self.client_id = client_id
        self.client_secret = client_secret
        self.timeout = aiohttp.ClientTimeout(total=timeout) if timeout else None
        self._session: Optional[aiohttp.ClientSession] = None
        self._authenticated = False
        self._auth = BasicAuth(client_id, client_secret)
        self._cookie_jar: Optional[aiohttp.CookieJar] = None

    async def _authenticate(self, session: aiohttp.ClientSession) -> None:
        auth_url = f"{self.api_server_url}/account/v1/auth"
        try:
            async with session.get(auth_url) as response:
                response.raise_for_status()
                if "dmsess" in response.cookies:
                    self._authenticated = True
                else:
                    raise AuthenticationError("Failed to get session cookie")
        except aiohttp.ClientError as e:
            raise AuthenticationError(f"Authentication failed: {str(e)}") from e

    async def _request(
            self,
            method: str,
            path: str,
            params: Optional[Dict[str, Any]] = None,
            json_data: Optional[Dict[str, Any]] = None,
            data: Optional[bytes] = None,
            headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        url = f"{self.api_server_url}{path}"
        session = self._session or await self._get_session()
        if not self._authenticated:
            await self._authenticate(session)

        try:
            async with session.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json_data,
                    data=data,
                    headers=headers,
            ) as response:
                return await self._handle_response(response)
        except aiohttp.ClientError as e:
            raise APIError(f"Request failed: {str(e)}") from e

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._cookie_jar is None:
            self._cookie_jar = aiohttp.CookieJar()
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                auth=self._auth,
                timeout=self.timeout,
                cookie_jar=self._cookie_jar,
                trust_env=True,
            )
        return self._session

    async def _handle_response(
            self, response: aiohttp.ClientResponse
    ) -> Dict[str, Any]:
        if response.status >= 400:
            error_msg = f"API request failed with status {response.status}"
            content_type = response.headers.get("Content-Type", "")
            if "json" in content_type:
                try:
                    error_data = await response.json()
                    if "message" in error_data:
                        error_msg = error_data["message"]
                except (ValueError, KeyError, aiohttp.ContentTypeError):
                    pass
            else:
                body = (await response.text()).strip()
                if body:
                    error_msg += ": " + body
            raise APIError(error_msg, status_code=response.status)
        return await response.json()

    async def _process_job(
            self,
            processor: str,
            params_list: List[str],
    ) -> str:
        process_data = {"params": params_list}
        result = await self._request(
            "POST", f"/job/v1/process/{processor}", json_data=process_data
        )
        return result["rid"]

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
            await asyncio.sleep(0.25)

    async def __aenter__(self):
        if self._cookie_jar is None:
            self._cookie_jar = aiohttp.CookieJar()
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                auth=self._auth,
                timeout=self.timeout,
                cookie_jar=self._cookie_jar,
                trust_env=True,
            )
            self._authenticated = False
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    # ==================== Character Model API ====================

    async def list_character_models(
            self,
            model_id: Optional[str] = None,
            search_token: Optional[str] = None,
            stock_model: Optional[str] = None,
    ) -> List[CharacterModel]:
        params = {}
        if model_id:
            params["modelId"] = model_id
        if search_token:
            params["searchToken"] = search_token
        if stock_model:
            params["stockModel"] = stock_model

        data = await self._request(
            "GET", "/character/v1/listModels", params=params
        )
        characters = []
        if isinstance(data, list):
            for char_data in data:
                characters.append(CharacterModel.from_dict(char_data))
        elif "list" in data:
            for char_data in data["list"]:
                characters.append(CharacterModel.from_dict(char_data))
        return characters

    async def upload_character_model(
            self,
            source: str,
            name: Optional[str] = None,
            create_thumb: bool = False,
    ) -> str:
        if is_http_url(source):
            return await self._store_model(
                model_url=source,
                model_name=name or "Unnamed Model",
                create_thumb=create_thumb,
            )
        else:
            if not os.path.exists(source):
                raise ValidationError(f"Model file does not exist: {source}")
            if name is None:
                name = get_file_name_without_ext(source)
            model_ext = get_file_extension(source)
            upload_urls = await self._get_model_upload_url(name, model_ext)
            await self._upload_file_to_gcs(upload_urls["modelUrl"], source)
            return await self._store_model(
                model_url=upload_urls["modelUrl"],
                model_name=name,
                create_thumb=create_thumb,
            )

    async def _get_model_upload_url(
            self, name: str, model_ext: str
    ) -> Dict[str, str]:
        params = {"name": name, "modelExt": model_ext, "resumable": "0"}
        return await self._request(
            "GET", "/character/v1/getModelUploadUrl", params=params
        )

    async def _upload_file_to_gcs(
            self, gcs_url: str, file_path: str
    ) -> None:
        with open(file_path, "rb") as f:
            file_data = f.read()
        headers = {
            "Content-Length": str(len(file_data)),
            "Content-Type": "application/octet-stream",
        }
        async with aiohttp.ClientSession(timeout=self.timeout) as temp:
            async with temp.put(
                    gcs_url, headers=headers, data=file_data
            ) as resp:
                resp.raise_for_status()

    async def _store_model(
            self,
            model_url: str,
            model_name: str,
            thumb_url: Optional[str] = None,
            model_id: Optional[str] = None,
            create_thumb: bool = False,
    ) -> str:
        store_data = {"modelUrl": model_url, "modelName": model_name}
        if thumb_url:
            store_data["thumbUrl"] = thumb_url
        if model_id:
            store_data["modelId"] = model_id
        if create_thumb:
            store_data["createThumb"] = 1
        result = await self._request(
            "POST", "/character/v1/storeModel", json_data=store_data
        )
        return result["modelId"]

    async def delete_character_model(self, model_id: str) -> int:
        data = await self._request(
            "DELETE", f"/character/v1/deleteModel/{model_id}"
        )
        return data.get("count", 0)

    # ==================== Job API ====================

    async def start_new_job(
            self,
            prompt: str,
            model_id: str,
            params: Optional[Text2MotionParams] = None,
            result_callback: Optional[
                Callable[[ResultCallbackData], Optional[Awaitable[None]]]
            ] = None,
            progress_callback: Optional[
                Callable[[ProgressCallbackData], Optional[Awaitable[None]]]
            ] = None,
            poll_interval: int = 5,
            blocking: bool = True,
            timeout: Optional[int] = None,
    ) -> str:
        if params is None:
            params = Text2MotionParams(prompt=prompt, model_id=model_id)
        else:
            params = Text2MotionParams(
                prompt=prompt,
                model_id=model_id,
                dis=params.dis,
                foot_locking_mode=params.foot_locking_mode,
                pose_filtering_strength=params.pose_filtering_strength,
                skip_fbx=params.skip_fbx,
                num_variant=params.num_variant,
                requested_animation_duration=params.requested_animation_duration,
            )

        rid = await self._process_job("text2motion", params.to_params_list())

        if blocking or progress_callback or result_callback:
            if blocking:
                await self._poll_job(
                    rid,
                    result_callback=result_callback,
                    progress_callback=progress_callback,
                    poll_interval=poll_interval,
                    timeout=timeout,
                )
            else:
                asyncio.create_task(
                    self._poll_job(
                        rid,
                        result_callback=result_callback,
                        progress_callback=progress_callback,
                        poll_interval=poll_interval,
                        timeout=timeout,
                    )
                )
        return rid

    async def start_render_job(
            self,
            t2m_rid: str,
            variant_id: int,
            params: Optional[RenderParams] = None,
            result_callback: Optional[
                Callable[[ResultCallbackData], Optional[Awaitable[None]]]
            ] = None,
            progress_callback: Optional[
                Callable[[ProgressCallbackData], Optional[Awaitable[None]]]
            ] = None,
            poll_interval: int = 5,
            blocking: bool = True,
            timeout: Optional[int] = None,
    ) -> str:
        if params is None:
            params = RenderParams(t2m_rid=t2m_rid, variant_id=variant_id)
        else:
            params = RenderParams(
                t2m_rid=t2m_rid,
                variant_id=variant_id,
                bg_color=params.bg_color,
                backdrop=params.backdrop,
                shadow=params.shadow,
                cam_mode=params.cam_mode,
                cam_horizontal_angle=params.cam_horizontal_angle,
            )
        rid = await self._process_job("render", params.to_params_list())
        if blocking or progress_callback or result_callback:
            if blocking:
                await self._poll_job(
                    rid,
                    result_callback=result_callback,
                    progress_callback=progress_callback,
                    poll_interval=poll_interval,
                    timeout=timeout,
                )
            else:
                asyncio.create_task(
                    self._poll_job(
                        rid,
                        result_callback=result_callback,
                        progress_callback=progress_callback,
                        poll_interval=poll_interval,
                        timeout=timeout,
                    )
                )
        return rid

    async def rerun_job(
            self,
            t2m_rid: str,
            variant_id: Optional[int] = None,
            params: Optional[RerunParams] = None,
            result_callback: Optional[
                Callable[[ResultCallbackData], Optional[Awaitable[None]]]
            ] = None,
            progress_callback: Optional[
                Callable[[ProgressCallbackData], Optional[Awaitable[None]]]
            ] = None,
            poll_interval: int = 5,
            blocking: bool = True,
            timeout: Optional[int] = None,
    ) -> str:
        if params is None:
            params = RerunParams(t2m_rid=t2m_rid, variant_id=variant_id or 1)
        else:
            params = RerunParams(
                t2m_rid=t2m_rid,
                variant_id=variant_id or params.variant_id,
                rerun=params.rerun,
            )
        rid = await self._process_job("text2motion", params.to_params_list())
        if blocking or progress_callback or result_callback:
            if blocking:
                await self._poll_job(
                    rid,
                    result_callback=result_callback,
                    progress_callback=progress_callback,
                    poll_interval=poll_interval,
                    timeout=timeout,
                )
            else:
                asyncio.create_task(
                    self._poll_job(
                        rid,
                        result_callback=result_callback,
                        progress_callback=progress_callback,
                        poll_interval=poll_interval,
                        timeout=timeout,
                    )
                )
        return rid

    async def start_inpainting_job(
            self,
            params: InpaintingParams,
            result_callback: Optional[
                Callable[[ResultCallbackData], Optional[Awaitable[None]]]
            ] = None,
            progress_callback: Optional[
                Callable[[ProgressCallbackData], Optional[Awaitable[None]]]
            ] = None,
            poll_interval: int = 5,
            blocking: bool = True,
            timeout: Optional[int] = None,
    ) -> str:
        rid = await self._process_job("text2motion", params.to_params_list())
        if blocking or progress_callback or result_callback:
            if blocking:
                await self._poll_job(
                    rid,
                    result_callback=result_callback,
                    progress_callback=progress_callback,
                    poll_interval=poll_interval,
                    timeout=timeout,
                )
            else:
                asyncio.create_task(
                    self._poll_job(
                        rid,
                        result_callback=result_callback,
                        progress_callback=progress_callback,
                        poll_interval=poll_interval,
                        timeout=timeout,
                    )
                )
        return rid

    async def start_merging_job(
            self,
            params: MergingParams,
            result_callback: Optional[
                Callable[[ResultCallbackData], Optional[Awaitable[None]]]
            ] = None,
            progress_callback: Optional[
                Callable[[ProgressCallbackData], Optional[Awaitable[None]]]
            ] = None,
            poll_interval: int = 5,
            blocking: bool = True,
            timeout: Optional[int] = None,
    ) -> str:
        rid = await self._process_job("text2motion", params.to_params_list())
        if blocking or progress_callback or result_callback:
            if blocking:
                await self._poll_job(
                    rid,
                    result_callback=result_callback,
                    progress_callback=progress_callback,
                    poll_interval=poll_interval,
                    timeout=timeout,
                )
            else:
                asyncio.create_task(
                    self._poll_job(
                        rid,
                        result_callback=result_callback,
                        progress_callback=progress_callback,
                        poll_interval=poll_interval,
                        timeout=timeout,
                    )
                )
        return rid

    async def start_loop_job(
            self,
            params: LoopParams,
            result_callback: Optional[
                Callable[[ResultCallbackData], Optional[Awaitable[None]]]
            ] = None,
            progress_callback: Optional[
                Callable[[ProgressCallbackData], Optional[Awaitable[None]]]
            ] = None,
            poll_interval: int = 5,
            blocking: bool = True,
            timeout: Optional[int] = None,
    ) -> str:
        rid = await self._process_job("text2motion", params.to_params_list())
        if blocking or progress_callback or result_callback:
            if blocking:
                await self._poll_job(
                    rid,
                    result_callback=result_callback,
                    progress_callback=progress_callback,
                    poll_interval=poll_interval,
                    timeout=timeout,
                )
            else:
                asyncio.create_task(
                    self._poll_job(
                        rid,
                        result_callback=result_callback,
                        progress_callback=progress_callback,
                        poll_interval=poll_interval,
                        timeout=timeout,
                    )
                )
        return rid

    async def start_refine_job(
            self,
            params: RefineParams,
            result_callback: Optional[
                Callable[[ResultCallbackData], Optional[Awaitable[None]]]
            ] = None,
            progress_callback: Optional[
                Callable[[ProgressCallbackData], Optional[Awaitable[None]]]
            ] = None,
            poll_interval: int = 5,
            blocking: bool = True,
            timeout: Optional[int] = None,
    ) -> str:
        rid = await self._process_job("text2motion", params.to_params_list())
        if blocking or progress_callback or result_callback:
            if blocking:
                await self._poll_job(
                    rid,
                    result_callback=result_callback,
                    progress_callback=progress_callback,
                    poll_interval=poll_interval,
                    timeout=timeout,
                )
            else:
                asyncio.create_task(
                    self._poll_job(
                        rid,
                        result_callback=result_callback,
                        progress_callback=progress_callback,
                        poll_interval=poll_interval,
                        timeout=timeout,
                    )
                )
        return rid

    async def import_animate3d_job(
            self, rid: str, model: str, params: List[str]
    ) -> str:
        body = {"model": model, "params": params}
        result = await self._request(
            "POST", f"/job/v1/import/animate3d/{rid}", json_data=body
        )
        return result["rid"]

    async def cancel_job(self, rid: str) -> bool:
        data = await self._request("GET", f"/job/v1/cancel/{rid}")
        return data.get("result", False)

    async def _poll_job(
            self,
            rid: str,
            result_callback: Optional[
                Callable[[ResultCallbackData], Optional[Awaitable[None]]]
            ] = None,
            progress_callback: Optional[
                Callable[[ProgressCallbackData], Optional[Awaitable[None]]]
            ] = None,
            poll_interval: int = 5,
            timeout: Optional[int] = None,
    ) -> None:
        import time
        start_time = time.time()

        while True:
            job_status = await self.get_job_status(rid)

            if job_status.status == Status.PROGRESS:
                step = (
                    job_status.details.step
                    if job_status.details and job_status.details.step is not None
                    else 0
                )
                total = (
                    job_status.details.total
                    if job_status.details and job_status.details.total
                    else 100
                )
                percent = math.ceil((step / total) * 100) if total > 0 else 0
                queue_pos = job_status.position_in_queue or 0

                if progress_callback:
                    data = ProgressCallbackData(
                        rid=rid,
                        progress_percent=percent,
                        position_in_queue=queue_pos,
                    )
                    res = progress_callback(data)
                    if asyncio.iscoroutine(res):
                        await res
                else:
                    if queue_pos:
                        print(f"Position in queue: {queue_pos}")
                    else:
                        print(f"Progress: {percent}%")

            if job_status.status in (Status.SUCCESS, Status.FAILURE):
                if not result_callback:
                    if job_status.status == Status.SUCCESS:
                        print("Job completed successfully!")
                    else:
                        msg = (
                            job_status.details.exc_message
                            if job_status.details
                            else "Unknown error"
                        )
                        print(f"Job failed: {msg}")
                else:
                    result_data = None
                    error_data = None
                    if job_status.status == Status.SUCCESS:
                        inp = (
                            job_status.details.input_file
                            if job_status.details and job_status.details.input_file
                            else []
                        )
                        if not isinstance(inp, list):
                            inp = [inp] if inp else []
                        out = (
                            job_status.details.output_file
                            if job_status.details
                            else None
                        )
                        result_data = JobResult(input=inp, output=out)
                    else:
                        code = (
                            job_status.details.exc_type
                            if job_status.details
                            else "Unknown"
                        )
                        msg = (
                            job_status.details.exc_message
                            if job_status.details
                            else "Unknown error"
                        )
                        error_data = JobError(code=code, message=msg)
                    data = ResultCallbackData(
                        rid=rid, result=result_data, error=error_data
                    )
                    res = result_callback(data)
                    if asyncio.iscoroutine(res):
                        await res
                return

            if timeout and (time.time() - start_time) > timeout:
                raise TimeoutError(
                    f"Job timed out after {timeout} seconds", rid=rid
                )
            await asyncio.sleep(poll_interval)

    async def get_job_status(self, rid: str) -> JobStatus:
        data = await self._request("GET", f"/job/v1/status/{rid}")
        if data.get("count", 0) > 0 and "status" in data:
            return JobStatus.from_dict(data["status"][0])
        return JobStatus(rid=rid, status=Status.PROGRESS)

    async def list_jobs(
            self,
            status: Optional[List[Status]] = None,
            processor: Optional[str] = None,
    ) -> List[Job]:
        if status and processor:
            status_str = ",".join([s.value for s in status])
            path = f"/job/v1/list/{status_str}/{processor}"
        elif status:
            status_str = ",".join([s.value for s in status])
            path = f"/job/v1/list/{status_str}"
        else:
            path = "/job/v1/list"
        data = await self._request("GET", path)
        jobs = []
        if "list" in data:
            for job_data in data["list"]:
                jobs.append(Job.from_dict(job_data))
        return jobs

    async def download_job(
            self,
            rid: str,
            output_dir: Optional[str] = None,
            variant_id: Optional[int] = None,
    ) -> DownloadLink:
        path = f"/job/v1/download/{rid}"
        params = {}
        if variant_id is not None:
            params["variant_id"] = variant_id
        data = await self._request("GET", path, params=params or None)
        if data.get("count", 0) == 0:
            raise APIError(f"No download links found for rid {rid}")
        link_data = data["links"][0]
        download_link = DownloadLink.from_dict(link_data)
        if output_dir:
            await self._download_files(download_link, output_dir)
        return download_link

    async def _download_files(
            self, download_link: DownloadLink, output_dir: str
    ) -> int:
        output_dir_with_rid = os.path.join(output_dir, download_link.rid)
        os.makedirs(output_dir_with_rid, exist_ok=True)
        files_to_download = []
        for url_group in download_link.urls:
            name = url_group.name
            if name.startswith("inter"):
                continue
            for file_info in url_group.files:
                file_type = file_info.file_type
                file_url = file_info.url
                output_file = os.path.join(
                    output_dir_with_rid, f"{name}.{file_type}"
                )
                files_to_download.append((file_url, output_file))
        if not files_to_download:
            return 0
        count = 0
        download_timeout = aiohttp.ClientTimeout(total=3600)
        proxy_url = os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY")
        connector = aiohttp.TCPConnector(
            limit=10, force_close=True, enable_cleanup_closed=True
        )
        try:
            async with aiohttp.ClientSession(
                    timeout=download_timeout, connector=connector, trust_env=True
            ) as download_session:
                for file_url, output_file in files_to_download:
                    async with download_session.get(
                            file_url, proxy=proxy_url
                    ) as file_response:
                        file_response.raise_for_status()
                        file_data = await file_response.read()
                    with open(output_file, "wb") as f:
                        f.write(file_data)
                    count += 1
        finally:
            await connector.close()
        print(f"Downloaded {count} files to {output_dir_with_rid}")
        return count

    # ==================== Prompt API ====================

    async def optimize_prompt(
            self,
            prompt: str,
            break_into_actionable_prompts: Optional[int] = None,
    ) -> str:
        params_list = [f'prompt="{prompt}"']
        if break_into_actionable_prompts is not None:
            params_list.append(
                f"breakIntoActionablePrompts={break_into_actionable_prompts}"
            )
        body = {"params": params_list}
        result = await self._request(
            "POST", "/prompt/v1/optimize", json_data=body
        )
        return result["rid"]

    async def get_prompt_status(self, rid: str) -> Dict[str, Any]:
        return await self._request("GET", f"/prompt/v1/status/{rid}")

    # ==================== Account API ====================

    async def get_credit_balance(self) -> float:
        data = await self._request("GET", "/account/v1/creditBalance")
        return math.floor(data.get("credits", 0))


# Backward compatibility alias
AsyncAnimate3DClient = AsyncSaymotionClient
