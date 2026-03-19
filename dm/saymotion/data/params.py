"""Process parameters for Saymotion API."""

import json
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple, Any


@dataclass
class TimeInterval:
    """A time interval with start and end times in seconds.

    Example:
        interval = TimeInterval(start=0.5, end=2.0)
    """

    start: float = 0.0
    end: float = 0.0

    def to_dict(self) -> Dict[str, float]:
        return {"start": self.start, "end": self.end}


@dataclass
class Text2MotionParams:
    """Optional parameters for text2motion job.

    Required parameters (prompt, model_id) are on the method signature.

    Example:
        rid = client.start_new_job(
            prompt="A person walking",
            model_id="model_id",
            params=Text2MotionParams(requested_animation_duration=5.0),
        )
    """

    physics_filter: Optional[bool] = None  # "s" to turn off simulation
    foot_locking_mode: Optional[str] = None  # "auto", "always", "never", "grounding"
    pose_filtering_strength: Optional[float] = None  # 0.0-1.0
    skip_fbx: Optional[int] = None  # 1 to skip FBX
    num_variant: Optional[int] = None  # 1-8
    requested_animation_duration: Optional[float] = None  # seconds

    def _append_optional_params(self, params: List[str]) -> None:
        """Append optional text2motion parameters to the list."""
        if self.physics_filter is False:
            params.append("dis=s")
        if self.foot_locking_mode:
            params.append(f"footLockingMode={self.foot_locking_mode}")
        if self.pose_filtering_strength is not None:
            params.append(f"poseFilteringStrength={self.pose_filtering_strength}")
        if self.skip_fbx is not None:
            params.append(f"skipFBX={self.skip_fbx}")
        if self.num_variant is not None:
            params.append(f"numVariant={self.num_variant}")
        if self.requested_animation_duration is not None:
            params.append(f"requestedAnimationDuration={self.requested_animation_duration}")

    def to_params_list(self, prompt: str, model_id: str) -> List[str]:
        """Convert to list of parameter strings for API.

        Args:
            prompt: Text prompt for motion generation (required).
            model_id: Character model ID (required).
        """
        params = [f'prompt="{prompt}"', f"model={model_id}"]
        self._append_optional_params(params)
        return params


@dataclass
class RenderParams:
    """Optional parameters for render processor (animation to video).

    Required parameter (t2m_rid) is on the method signature.
    """

    variant_id: Optional[int] = None
    bg_color: Optional[Tuple[int, int, int, int]] = None  # RGBA 0-255
    backdrop: Optional[str] = None  # "studio" or 2D backdrop name
    shadow: Optional[int] = None  # 0=off, 1=on
    cam_mode: Optional[int] = None  # 0=Cinematic, 1=Fixed, 2=Face
    cam_horizontal_angle: Optional[float] = None  # -90 to +90 degrees

    def to_params_list(self, t2m_rid: str) -> List[str]:
        """Convert to list of parameter strings for API.

        Args:
            t2m_rid: Request ID of the text2motion job (required).
        """
        params = [f"t2m_rid={t2m_rid}"]
        if self.variant_id is not None:
            params.append(f"variant_id={self.variant_id}")
        if self.bg_color is not None:
            params.append(
                f"bgColor={self.bg_color[0]},{self.bg_color[1]},"
                f"{self.bg_color[2]},{self.bg_color[3]}"
            )
        if self.backdrop:
            params.append(f"backdrop={self.backdrop}")
        if self.shadow is not None:
            params.append(f"shadow={self.shadow}")
        if self.cam_mode is not None:
            params.append(f"camMode={self.cam_mode}")
        if self.cam_horizontal_angle is not None:
            params.append(f"camHorizontalAngle={self.cam_horizontal_angle}")
        return params


@dataclass
class RerunParams(Text2MotionParams):
    """Optional parameters for rerun job, extends Text2MotionParams.

    Inherits all optional text2motion settings (physics_filter, foot_locking_mode,
    pose_filtering_strength, skip_fbx, num_variant, requested_animation_duration).

    Required parameters (t2m_rid, model_id) are on the method signature.

    Example:
        new_rid = client.rerun_job(
            t2m_rid="rid",
            model_id="model_id",
            params=RerunParams(variant_id=1, physics_filter=False),
        )
    """

    variant_id: Optional[int] = None
    rerun: int = 1  # 0 or 1

    def to_params_list(self, t2m_rid: str, model_id: str) -> List[str]:  # type: ignore[override]
        """Convert to list of parameter strings for API.

        Args:
            t2m_rid: Request ID of the text2motion job (required).
            model_id: Character model ID (required).
        """
        params = [f"t2m_rid={t2m_rid}", f"model={model_id}"]
        self._append_optional_params(params)
        if self.variant_id is not None:
            params.append(f"variant_id={self.variant_id}")
        params.append(f'rerunRequest={{"rerun": {self.rerun}}}')
        return params


@dataclass
class InpaintingParams:
    """Optional parameters for inpainting job.

    Required parameters (t2m_rid, prompt, intervals) are on the method signature.
    """

    variant_id: Optional[int] = None

    def to_params_list(
        self, t2m_rid: str, prompt: str, intervals: List[TimeInterval],
    ) -> List[str]:
        """Convert to list of parameter strings for API.

        Args:
            t2m_rid: Request ID of the text2motion job (required).
            prompt: Inpainting prompt (required).
            intervals: Time intervals to inpaint (required).
        """
        params = [f"t2m_rid={t2m_rid}"]
        if self.variant_id is not None:
            params.append(f"variant_id={self.variant_id}")
        req = {"prompt": prompt, "intervals": [iv.to_dict() for iv in intervals]}
        params.append(f"inPaintingRequest={json.dumps(req)}")
        return params


@dataclass
class MergingParams:
    """Optional parameters for merging job.

    Required parameters (t2m_rid, prompt) are on the method signature.
    """

    variant_id: Optional[int] = None
    edit_request: Optional[Dict[str, int]] = None  # {"numTrimLeft": x, "numTrimRight": y}
    blend_duration: Optional[float] = None

    def to_params_list(self, t2m_rid: str, prompt: str) -> List[str]:
        """Convert to list of parameter strings for API.

        Args:
            t2m_rid: Request ID of the text2motion job (required).
            prompt: Merging prompt (required).
        """
        params = [f"t2m_rid={t2m_rid}"]
        if self.variant_id is not None:
            params.append(f"variant_id={self.variant_id}")
        req: Dict[str, Any] = {
            "t2m_rid": t2m_rid,
            "prompt": prompt,
        }
        if self.variant_id is not None:
            req["variant_id"] = self.variant_id
        if self.edit_request:
            req["editRequest"] = self.edit_request
        if self.blend_duration is not None:
            req["blendDuration"] = self.blend_duration
        params.append(f"mergingRequest={json.dumps(req)}")
        return params


@dataclass
class LoopParams:
    """Optional parameters for loop job.

    Required parameter (t2m_rid) is on the method signature.
    """

    variant_id: Optional[int] = None
    prompt: Optional[str] = None
    num_reps: int = 1
    blend_duration: Optional[float] = None
    fix_root_mode: Optional[str] = None  # "INTERPOLATION" or "LOCKED"
    fix_root_position_altitude: Optional[int] = None  # 0 or 1
    fix_root_position_horizontal: Optional[int] = None  # 0 or 1
    fix_root_orientation: Optional[int] = None  # 0 or 1
    fix_across_entire_motion: Optional[int] = None  # 0 or 1

    def to_params_list(self, t2m_rid: str) -> List[str]:
        """Convert to list of parameter strings for API.

        Args:
            t2m_rid: Request ID of the text2motion job (required).
        """
        params = [f"t2m_rid={t2m_rid}"]
        if self.variant_id is not None:
            params.append(f"variant_id={self.variant_id}")
        req = {}
        if self.prompt is not None:
            req["prompt"] = self.prompt
        req["numReps"] = self.num_reps
        if self.blend_duration is not None:
            req["blendDuration"] = self.blend_duration
        if self.fix_root_mode:
            req["fixRootMode"] = self.fix_root_mode
        if self.fix_root_position_altitude is not None:
            req["fixRootPositionAltitude"] = self.fix_root_position_altitude
        if self.fix_root_position_horizontal is not None:
            req["fixRootPositionHorizontal"] = self.fix_root_position_horizontal
        if self.fix_root_orientation is not None:
            req["fixRootOrientation"] = self.fix_root_orientation
        if self.fix_across_entire_motion is not None:
            req["fixAcrossEntireMotion"] = self.fix_across_entire_motion
        params.append(f"loopRequest={json.dumps(req)}")
        return params


@dataclass
class RefineParams:
    """Optional parameters for refine job.

    Required parameter (t2m_rid) is on the method signature.
    """

    variant_id: Optional[int] = None
    prompt: Optional[str] = None
    creativity: Optional[float] = None  # 0.0-1.0
    num_variant: Optional[int] = None  # 1-8

    def to_params_list(self, t2m_rid: str) -> List[str]:
        """Convert to list of parameter strings for API.

        Args:
            t2m_rid: Request ID of the text2motion job (required).
        """
        params = [f"t2m_rid={t2m_rid}"]
        if self.variant_id is not None:
            params.append(f"variant_id={self.variant_id}")
        req = {}
        if self.prompt is not None:
            req["prompt"] = self.prompt
        if self.creativity is not None:
            req["creativity"] = self.creativity
        if self.num_variant is not None:
            params.append(f"numVariant={self.num_variant}")
        params.append(f"refineRequest={json.dumps(req)}")
        return params


# Alias for backward compatibility
ProcessParams = Text2MotionParams
