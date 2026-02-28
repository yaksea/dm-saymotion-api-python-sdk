"""Saymotion Python SDK.

This module provides synchronous and asynchronous clients for the Saymotion REST API.
"""

from dm.saymotion.client import SaymotionClient, Animate3DClient
from dm.saymotion.async_client import AsyncSaymotionClient, AsyncAnimate3DClient
from dm.saymotion.data.params import (
    ProcessParams,
    Text2MotionParams,
    RenderParams,
    RerunParams,
    InpaintingParams,
    MergingParams,
    LoopParams,
    RefineParams,
)
from dm.saymotion.data.enums import Status
from dm.saymotion.data.job import Job
from dm.saymotion.data.job_status import JobStatus, JobStatusDetails
from dm.saymotion.data.callback import (
    ProgressCallbackData,
    ResultCallbackData,
    JobResult,
    JobError,
)
from dm.saymotion.data.character import CharacterModel
from dm.saymotion.data.response import DownloadLink, DownloadUrl, DownloadFile
from dm.saymotion.exceptions import (
    Animate3DError,
    AuthenticationError,
    APIError,
    ValidationError,
)

__version__ = "2.0.0"

__all__ = [
    # Clients
    "SaymotionClient",
    "Animate3DClient",
    "AsyncSaymotionClient",
    "AsyncAnimate3DClient",
    # Parameters
    "ProcessParams",
    "Text2MotionParams",
    "RenderParams",
    "RerunParams",
    "InpaintingParams",
    "MergingParams",
    "LoopParams",
    "RefineParams",
    # Models
    "Status",
    "Job",
    "JobStatus",
    "JobStatusDetails",
    "ProgressCallbackData",
    "ResultCallbackData",
    "JobResult",
    "JobError",
    "CharacterModel",
    "DownloadLink",
    "DownloadUrl",
    "DownloadFile",
    # Exceptions
    "Animate3DError",
    "AuthenticationError",
    "APIError",
    "ValidationError",
]
