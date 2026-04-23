"""Synchronous client for Saymotion API."""
import math
import os
import threading
import time
from typing import List, Optional, Dict, Any, Callable

import requests
from requests.auth import HTTPBasicAuth

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
    TimeInterval,
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


class SaymotionClient:
    """Synchronous client for Saymotion REST API.

    This client provides a simple, blocking interface to the Saymotion API.
    For async operations, use AsyncSaymotionClient instead.

    Example:
        client = SaymotionClient(
            api_server_url="https://service.deepmotion.com",
            client_id="your_client_id",
            client_secret="your_client_secret",
        )

        # Start a new text2motion job
        rid = client.start_new_job(
            prompt="A person walking",
            model_id="model_id",
            params=Text2MotionParams(requested_animation_duration=5.0),
        )

        # Download results
        client.download_job(rid, output_dir="./output")
    """

    def __init__(
            self,
            api_server_url: str,
            client_id: str,
            client_secret: str,
            timeout: Optional[int] = None,
    ):
        """Initialize the client.

        Args:
            api_server_url: Base URL of the API server (e.g., "https://service.deepmotion.com")
            client_id: Client ID for authentication
            client_secret: Client secret for authentication
            timeout: Request timeout in seconds (default: None, no timeout)
        """
        self.api_server_url = api_server_url.rstrip("/")
        self.client_id = client_id
        self.client_secret = client_secret
        self.timeout = timeout
        self._session: Optional[requests.Session] = None
        self._authenticated = False

    def close(self) -> None:
        """Close the underlying HTTP session."""
        if self._session is not None:
            self._session.close()
            self._session = None
            self._authenticated = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def _get_session(self) -> requests.Session:
        """Get or create authenticated session."""
        if self._session is None:
            self._session = requests.Session()
            self._session.auth = HTTPBasicAuth(self.client_id, self.client_secret)
            self._authenticated = False

        if not self._authenticated:
            self._authenticate()

        return self._session

    def _authenticate(self) -> None:
        """Authenticate and get session cookie."""
        auth_url = f"{self.api_server_url}/account/v1/auth"

        if self._session is None:
            self._session = requests.Session()
            self._session.auth = HTTPBasicAuth(self.client_id, self.client_secret)

        try:
            response = self._session.get(auth_url, timeout=self.timeout)
            response.raise_for_status()

            if "dmsess" in response.cookies:
                self._authenticated = True
            else:
                raise AuthenticationError("Failed to get session cookie")
        except requests.exceptions.RequestException as e:
            raise AuthenticationError(f"Authentication failed: {str(e)}") from e

    def _request(
            self,
            method: str,
            path: str,
            params: Optional[Dict[str, Any]] = None,
            json_data: Optional[Dict[str, Any]] = None,
            data: Optional[bytes] = None,
            headers: Optional[Dict[str, str]] = None,
    ) -> requests.Response:
        """Make HTTP request to API."""
        url = f"{self.api_server_url}{path}"
        session = self._get_session()

        try:
            response = session.request(
                method=method,
                url=url,
                params=params,
                json=json_data,
                data=data,
                headers=headers,
                timeout=self.timeout,
            )

            if response.status_code >= 400:
                error_msg = f"API request failed with status {response.status_code}"
                content_type = response.headers.get("Content-Type", "")
                if "json" in content_type:
                    try:
                        error_data = response.json()
                        if "message" in error_data:
                            error_msg = error_data["message"]
                    except (ValueError, KeyError):
                        pass
                else:
                    body = response.text.strip()
                    if body:
                        error_msg += ": " + body

                raise APIError(error_msg, status_code=response.status_code)

            return response
        except requests.exceptions.RequestException as e:
            raise APIError(f"Request failed: {str(e)}") from e

    def _process_job(
            self,
            processor: str,
            params_list: List[str],
    ) -> str:
        """Start job processing.

        Args:
            processor: "text2motion" or "render"
            params_list: List of "key=value" parameter strings

        Returns:
            Request ID (rid)
        """
        process_data = {"params": params_list}
        response = self._request(
            "POST", f"/job/v1/process/{processor}", json_data=process_data
        )
        result = response.json()
        return result["rid"]

    # ==================== Character Model API ====================

    def list_character_models(
            self,
            model_id: Optional[str] = None,
            search_token: Optional[str] = None,
            only_custom: Optional[bool] = None,
    ) -> List[CharacterModel]:
        """List character models.

        Args:
            model_id: Specific model ID to retrieve
            search_token: Search by model name
            only_custom: If True, list custom models only. If False or None, request stockModel=all.

        Returns:
            List of CharacterModel objects
        """
        params = {}
        if model_id:
            params["modelId"] = model_id
        if search_token:
            params["searchToken"] = search_token
        if not only_custom:
            params["stockModel"] = "all"

        response = self._request("GET", "/character/v1/listModels", params=params)
        data = response.json()

        characters = []
        if isinstance(data, list):
            for char_data in data:
                characters.append(CharacterModel.from_dict(char_data))
        elif "list" in data:
            for char_data in data["list"]:
                characters.append(CharacterModel.from_dict(char_data))

        return characters

    def upload_character_model(
            self,
            source: str,
            name: Optional[str] = None,
            create_thumb: bool = False,
    ) -> str:
        """Upload or store a character model.

        Args:
            source: Local file path or HTTP URL of the model
            name: Model name (defaults to filename for local files)
            create_thumb: Whether to auto-generate thumbnail

        Returns:
            Model ID
        """
        if is_http_url(source):
            return self._store_model(
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
            upload_urls = self._get_model_upload_url(name, model_ext)
            self._upload_file_to_gcs(upload_urls["modelUrl"], source)

            return self._store_model(
                model_url=upload_urls["modelUrl"],
                model_name=name,
                create_thumb=create_thumb,
            )

    def _get_model_upload_url(
            self,
            name: str,
            model_ext: str,
    ) -> Dict[str, str]:
        """Get signed URLs for model upload."""
        params = {
            "name": name,
            "modelExt": model_ext,
            "resumable": "0",
        }
        response = self._request(
            "GET", "/character/v1/getModelUploadUrl", params=params
        )
        return response.json()

    def _upload_file_to_gcs(self, gcs_url: str, file_path: str) -> None:
        """Upload file to GCS URL."""
        with open(file_path, "rb") as f:
            file_data = f.read()

        headers = {
            "Content-Length": str(len(file_data)),
            "Content-Type": "application/octet-stream",
        }

        put_response = requests.put(
            gcs_url, headers=headers, data=file_data, timeout=self.timeout
        )
        put_response.raise_for_status()

    def _store_model(
            self,
            model_url: str,
            model_name: str,
            thumb_url: Optional[str] = None,
            model_id: Optional[str] = None,
            create_thumb: bool = False,
    ) -> str:
        """Store model in database."""
        store_data = {
            "modelUrl": model_url,
            "modelName": model_name,
        }
        if thumb_url:
            store_data["thumbUrl"] = thumb_url
        if model_id:
            store_data["modelId"] = model_id
        if create_thumb:
            store_data["createThumb"] = 1

        response = self._request(
            "POST", "/character/v1/storeModel", json_data=store_data
        )
        result = response.json()
        return result["modelId"]

    def delete_character_model(self, model_id: str) -> int:
        """Delete a character model."""
        response = self._request(
            "DELETE", f"/character/v1/deleteModel/{model_id}"
        )
        data = response.json()
        return data.get("count", 0)

    # ==================== Job API ====================

    def _start_and_poll(
            self,
            processor: str,
            params_list: List[str],
            result_callback: Optional[Callable[[ResultCallbackData], None]] = None,
            progress_callback: Optional[Callable[[ProgressCallbackData], None]] = None,
            poll_interval: int = 5,
            blocking: bool = True,
            timeout: Optional[int] = None,
    ) -> str:
        """Submit a job and optionally poll for completion.

        Args:
            processor: Processor name ("text2motion" or "render")
            params_list: List of "key=value" parameter strings
            result_callback: Callback for job completion
            progress_callback: Callback for progress updates
            poll_interval: Seconds between status polls
            blocking: Whether to block until job completes
            timeout: Maximum wait time in seconds

        Returns:
            Request ID (rid)
        """
        rid = self._process_job(processor, params_list)

        if blocking or progress_callback or result_callback:
            if blocking:
                self._poll_job(
                    rid,
                    result_callback=result_callback,
                    progress_callback=progress_callback,
                    poll_interval=poll_interval,
                    timeout=timeout,
                )
            else:
                thread = threading.Thread(
                    target=self._poll_job,
                    args=(rid,),
                    kwargs={
                        "result_callback": result_callback,
                        "progress_callback": progress_callback,
                        "poll_interval": poll_interval,
                        "timeout": timeout,
                    },
                    daemon=True,
                )
                thread.start()

        return rid

    def start_new_job(
            self,
            prompt: str,
            model_id: str,
            params: Optional[Text2MotionParams] = None,
            result_callback: Optional[Callable[[ResultCallbackData], None]] = None,
            progress_callback: Optional[Callable[[ProgressCallbackData], None]] = None,
            poll_interval: int = 5,
            blocking: bool = True,
            timeout: Optional[int] = None,
    ) -> str:
        """Start a new text2motion job (text prompt to animation).

        Args:
            prompt: Text prompt for motion generation
            model_id: Character model ID
            params: Optional Text2MotionParams for additional settings
            result_callback: Callback for job completion
            progress_callback: Callback for progress updates
            poll_interval: Seconds between status polls
            blocking: Whether to block until job completes
            timeout: Maximum wait time in seconds

        Returns:
            Request ID (rid)
        """
        if params is None:
            params = Text2MotionParams()

        return self._start_and_poll(
            "text2motion", params.to_params_list(prompt, model_id),
            result_callback=result_callback,
            progress_callback=progress_callback,
            poll_interval=poll_interval,
            blocking=blocking,
            timeout=timeout,
        )

    def start_render_job(
            self,
            t2m_rid: str,
            params: Optional[RenderParams] = None,
            result_callback: Optional[Callable[[ResultCallbackData], None]] = None,
            progress_callback: Optional[Callable[[ProgressCallbackData], None]] = None,
            poll_interval: int = 5,
            blocking: bool = True,
            timeout: Optional[int] = None,
    ) -> str:
        """Start render job (animation to video).

        Args:
            t2m_rid: Request ID of the text2motion job
            params: Optional RenderParams for additional settings
        """
        if params is None:
            params = RenderParams()

        return self._start_and_poll(
            "render", params.to_params_list(t2m_rid),
            result_callback=result_callback,
            progress_callback=progress_callback,
            poll_interval=poll_interval,
            blocking=blocking,
            timeout=timeout,
        )

    def rerun_job(
            self,
            t2m_rid: str,
            model_id: str,
            params: Optional[RerunParams] = None,
            result_callback: Optional[Callable[[ResultCallbackData], None]] = None,
            progress_callback: Optional[Callable[[ProgressCallbackData], None]] = None,
            poll_interval: int = 5,
            blocking: bool = True,
            timeout: Optional[int] = None,
    ) -> str:
        """Rerun a text2motion job.

        Args:
            t2m_rid: Request ID of the text2motion job to rerun
            params: Optional RerunParams for additional settings
        """
        if params is None:
            params = RerunParams()

        return self._start_and_poll(
            "text2motion", params.to_params_list(t2m_rid, model_id),
            result_callback=result_callback,
            progress_callback=progress_callback,
            poll_interval=poll_interval,
            blocking=blocking,
            timeout=timeout,
        )

    def start_inpainting_job(
            self,
            t2m_rid: str,
            prompt: str,
            intervals: List[TimeInterval],
            params: Optional[InpaintingParams] = None,
            result_callback: Optional[Callable[[ResultCallbackData], None]] = None,
            progress_callback: Optional[Callable[[ProgressCallbackData], None]] = None,
            poll_interval: int = 5,
            blocking: bool = True,
            timeout: Optional[int] = None,
    ) -> str:
        """Start inpainting job.

        Args:
            t2m_rid: Request ID of the text2motion job
            prompt: Inpainting prompt
            intervals: Time intervals, e.g. [TimeInterval(start=0.5, end=2.0)]
            params: Optional InpaintingParams for additional settings
        """
        if params is None:
            params = InpaintingParams()

        return self._start_and_poll(
            "text2motion", params.to_params_list(t2m_rid, prompt, intervals),
            result_callback=result_callback,
            progress_callback=progress_callback,
            poll_interval=poll_interval,
            blocking=blocking,
            timeout=timeout,
        )

    def start_merging_job(
            self,
            t2m_rid: str,
            prompt: str,
            params: Optional[MergingParams] = None,
            result_callback: Optional[Callable[[ResultCallbackData], None]] = None,
            progress_callback: Optional[Callable[[ProgressCallbackData], None]] = None,
            poll_interval: int = 5,
            blocking: bool = True,
            timeout: Optional[int] = None,
    ) -> str:
        """Start merging job.

        Args:
            t2m_rid: Request ID of the text2motion job
            prompt: Merging prompt
            params: Optional MergingParams for additional settings
        """
        if params is None:
            params = MergingParams()

        return self._start_and_poll(
            "text2motion", params.to_params_list(t2m_rid, prompt),
            result_callback=result_callback,
            progress_callback=progress_callback,
            poll_interval=poll_interval,
            blocking=blocking,
            timeout=timeout,
        )

    def start_loop_job(
            self,
            t2m_rid: str,
            params: Optional[LoopParams] = None,
            result_callback: Optional[Callable[[ResultCallbackData], None]] = None,
            progress_callback: Optional[Callable[[ProgressCallbackData], None]] = None,
            poll_interval: int = 5,
            blocking: bool = True,
            timeout: Optional[int] = None,
    ) -> str:
        """Start loop job.

        Args:
            t2m_rid: Request ID of the text2motion job
            params: Optional LoopParams for additional settings
        """
        if params is None:
            params = LoopParams()

        return self._start_and_poll(
            "text2motion", params.to_params_list(t2m_rid),
            result_callback=result_callback,
            progress_callback=progress_callback,
            poll_interval=poll_interval,
            blocking=blocking,
            timeout=timeout,
        )

    def start_refine_job(
            self,
            t2m_rid: str,
            params: Optional[RefineParams] = None,
            result_callback: Optional[Callable[[ResultCallbackData], None]] = None,
            progress_callback: Optional[Callable[[ProgressCallbackData], None]] = None,
            poll_interval: int = 5,
            blocking: bool = True,
            timeout: Optional[int] = None,
    ) -> str:
        """Start refine job.

        Args:
            t2m_rid: Request ID of the text2motion job
            params: Optional RefineParams for additional settings
        """
        if params is None:
            params = RefineParams()

        return self._start_and_poll(
            "text2motion", params.to_params_list(t2m_rid),
            result_callback=result_callback,
            progress_callback=progress_callback,
            poll_interval=poll_interval,
            blocking=blocking,
            timeout=timeout,
        )

    def import_animate3d_job(
            self,
            rid: str,
            model: str,
            params: List[str],
    ) -> str:
        """Import an Animate3D job to Saymotion."""
        body = {"model": model, "params": params}
        response = self._request(
            "POST", f"/job/v1/import/animate3d/{rid}", json_data=body
        )
        result = response.json()
        return result["rid"]

    def cancel_job(self, rid: str) -> bool:
        """Cancel a job in progress."""
        response = self._request("GET", f"/job/v1/cancel/{rid}")
        data = response.json()
        return data.get("result", False)

    def _poll_job(
            self,
            rid: str,
            result_callback: Optional[Callable[[ResultCallbackData], None]] = None,
            progress_callback: Optional[Callable[[ProgressCallbackData], None]] = None,
            poll_interval: int = 5,
            timeout: Optional[int] = None,
    ) -> None:
        """Poll job status until completion."""
        start_time = time.time()

        while True:
            job_status = self.get_job_status(rid)

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
                    progress_callback(data)
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
                    result_callback(data)
                return

            if timeout and (time.time() - start_time) > timeout:
                raise TimeoutError(
                    f"Job timed out after {timeout} seconds", rid=rid
                )

            time.sleep(poll_interval)

    def get_job_status(self, rid: str) -> JobStatus:
        """Get current status of a job."""
        response = self._request("GET", f"/job/v1/status/{rid}")
        data = response.json()

        if data.get("count", 0) > 0 and "status" in data:
            status_data = data["status"][0]
            return JobStatus.from_dict(status_data)

        return JobStatus(rid=rid, status=Status.PROGRESS)

    def list_jobs(
            self,
            status: Optional[List[Status]] = None,
            processor: Optional[str] = None,
    ) -> List[Job]:
        """List jobs, optionally filtered by status and processor."""
        if status and processor:
            status_str = ",".join([s.value for s in status])
            path = f"/job/v1/list/{status_str}/{processor}"
        elif status:
            status_str = ",".join([s.value for s in status])
            path = f"/job/v1/list/{status_str}"
        elif processor:
            path = f"/job/v1/list/SUCCESS,PROGRESS,FAILURE/{processor}"
        else:
            path = "/job/v1/list"

        response = self._request("GET", path)
        data = response.json()

        jobs = []
        if "list" in data:
            for job_data in data["list"]:
                jobs.append(Job.from_dict(job_data))

        return jobs

    def download_job(
            self,
            rid: str,
            output_dir: Optional[str] = None,
            variant_id: Optional[int] = None,
    ) -> DownloadLink:
        """Download completed job results.

        Args:
            rid: Request ID
            output_dir: Directory to save files (if None, only returns URLs)
            variant_id: Variant ID for text2motion jobs (optional)
        """
        path = f"/job/v1/download/{rid}"
        params = {}
        if variant_id is not None:
            params["variant_id"] = variant_id

        response = self._request("GET", path, params=params or None)
        data = response.json()

        if data.get("count", 0) == 0:
            raise APIError(f"No download links found for rid {rid}")

        link_data = data["links"][0]
        download_link = DownloadLink.from_dict(link_data)

        if output_dir:
            self._download_files(download_link, output_dir)

        return download_link

    def _download_files(self, download_link: DownloadLink, output_dir: str) -> int:
        """Download files from download link."""
        output_dir_with_rid = os.path.join(output_dir, download_link.rid)
        os.makedirs(output_dir_with_rid, exist_ok=True)

        session = self._get_session()
        count = 0

        for url_group in download_link.urls:
            name = url_group.name
            if name.startswith("inter"):
                continue

            for file_info in url_group.files:
                file_type = file_info.file_type
                file_url = file_info.url

                ext = "zip" if file_type == "fbx" else file_type
                output_file = os.path.join(
                    output_dir_with_rid, f"{name}.{ext}"
                )

                file_response = session.get(file_url, timeout=self.timeout)
                file_response.raise_for_status()

                with open(output_file, "wb") as f:
                    f.write(file_response.content)
                count += 1

        print(f"Downloaded {count} files to {output_dir_with_rid}")
        return count

    # ==================== Prompt API ====================

    def optimize_prompt(
            self,
            prompt: str,
            break_into_actionable_prompts: Optional[int] = None,
    ) -> str:
        """Start prompt optimization. Returns rid for status polling."""
        params_list = [f'prompt="{prompt}"']
        if break_into_actionable_prompts is not None:
            params_list.append(
                f"breakIntoActionablePrompts={break_into_actionable_prompts}"
            )

        body = {"params": params_list}
        response = self._request("POST", "/prompt/v1/optimize", json_data=body)
        result = response.json()
        return result["rid"]

    def get_prompt_status(self, rid: str) -> Dict[str, Any]:
        """Get prompt optimization status."""
        response = self._request("GET", f"/prompt/v1/status/{rid}")
        return response.json()

    # ==================== Account API ====================

    def get_credit_balance(self) -> float:
        """Get account credit balance."""
        response = self._request("GET", "/account/v1/creditBalance")
        data = response.json()
        return math.floor(data.get("credits", 0))
