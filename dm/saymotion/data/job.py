"""Job summary model."""

from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime

from dm.saymotion.data.enums import Status


@dataclass
class Job:
    """Job summary information returned by /list API.

    Attributes:
        rid: Request ID
        status: Current status
        processor: Processor id (text2motion, render)
        parameters: Job input parameters
        variants: Variant info for text2motion jobs
        charged_amount: Credits used
        processing_info: Processing timing details
        ctime: Creation time (milliseconds since epoch)
        mtime: Last modification time (milliseconds since epoch)
    """

    rid: str
    status: Optional[Status] = None
    processor: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    variants: Optional[Dict[str, Any]] = None
    charged_amount: Optional[float] = None
    processing_info: Optional[Dict[str, Any]] = None
    ctime: Optional[int] = None
    mtime: Optional[int] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Job":
        """Create Job from API response."""
        status = None
        if "status" in data:
            try:
                status = Status(data["status"])
            except ValueError:
                pass

        return cls(
            rid=data.get("rid", ""),
            status=status,
            processor=data.get("processor"),
            parameters=data.get("parameters"),
            variants=data.get("variants"),
            charged_amount=data.get("chargedAmount"),
            processing_info=data.get("processingInfo"),
            ctime=data.get("ctime"),
            mtime=data.get("mtime"),
        )

    @property
    def created_at(self) -> Optional[datetime]:
        """Get creation time as datetime."""
        if self.ctime:
            return datetime.fromtimestamp(self.ctime / 1000.0)
        return None

    @property
    def modified_at(self) -> Optional[datetime]:
        """Get modification time as datetime."""
        if self.mtime:
            return datetime.fromtimestamp(self.mtime / 1000.0)
        return None

    def is_completed(self) -> bool:
        """Check if job is in a terminal state."""
        return self.status in (Status.SUCCESS, Status.FAILURE)

    def is_successful(self) -> bool:
        """Check if job completed successfully."""
        return self.status == Status.SUCCESS

    def is_failed(self) -> bool:
        """Check if job failed."""
        return self.status == Status.FAILURE

    def is_in_progress(self) -> bool:
        """Check if job is still processing."""
        return self.status == Status.PROGRESS
