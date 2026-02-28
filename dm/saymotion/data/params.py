"""Process parameters for Saymotion API."""

import json
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple, Any


@dataclass
class Text2MotionParams:
    """Parameters for text2motion (regular animation generation) job.

    Example:
        params = Text2MotionParams(
            prompt="A person walking",
            model_id="model_id",
            requested_animation_duration=5.0,
        )
    """

    prompt: str = ""
    model_id: str = ""
    dis: Optional[str] = None  # "s" to turn off simulation
    foot_locking_mode: Optional[str] = None  # "auto", "always", "never", "grounding"
    pose_filtering_strength: Optional[float] = None  # 0.0-1.0
    skip_fbx: Optional[int] = None  # 1 to skip FBX
    num_variant: Optional[int] = None  # 1-8
    requested_animation_duration: Optional[float] = None  # seconds

    def to_params_list(self) -> List[str]:
        """Convert to list of parameter strings for API."""
        params = []
        if self.prompt:
            params.append(f'prompt="{self.prompt}"')
        if self.model_id:
            params.append(f"model={self.model_id}")
        if self.dis is not None:
            params.append(f"dis={self.dis}")
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
        return params


@dataclass
class RenderParams:
    """Parameters for render processor (animation to video)."""

    t2m_rid: str = ""
    variant_id: Optional[int] = None
    bg_color: Optional[Tuple[int, int, int, int]] = None  # RGBA 0-255
    backdrop: Optional[str] = None  # "studio" or 2D backdrop name
    shadow: Optional[int] = None  # 0=off, 1=on
    cam_mode: Optional[int] = None  # 0=Cinematic, 1=Fixed, 2=Face
    cam_horizontal_angle: Optional[float] = None  # -90 to +90 degrees

    def to_params_list(self) -> List[str]:
        """Convert to list of parameter strings for API."""
        params = []
        if self.t2m_rid:
            params.append(f"t2m_rid={self.t2m_rid}")
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
class RerunParams:
    """Parameters for rerun job."""

    t2m_rid: str = ""
    variant_id: Optional[int] = None
    rerun: int = 1  # 0 or 1

    def to_params_list(self) -> List[str]:
        """Convert to list of parameter strings for API."""
        params = []
        if self.t2m_rid:
            params.append(f"t2m_rid={self.t2m_rid}")
        if self.variant_id is not None:
            params.append(f"variant_id={self.variant_id}")
        params.append(f'rerunRequest={{"rerun": {self.rerun}}}')
        return params


@dataclass
class InpaintingParams:
    """Parameters for inpainting job."""

    t2m_rid: str = ""
    variant_id: Optional[int] = None
    prompt: str = ""
    intervals: List[Dict[str, float]] = field(default_factory=list)  # [{"start": x, "end": y}]

    def to_params_list(self) -> List[str]:
        """Convert to list of parameter strings for API."""
        params = []
        if self.t2m_rid:
            params.append(f"t2m_rid={self.t2m_rid}")
        if self.variant_id is not None:
            params.append(f"variant_id={self.variant_id}")
        req = {"prompt": self.prompt, "intervals": self.intervals}
        params.append(f"inPaintingRequest={json.dumps(req)}")
        return params


@dataclass
class MergingParams:
    """Parameters for merging job."""

    t2m_rid: str = ""
    variant_id: Optional[int] = None
    edit_request: Optional[Dict[str, int]] = None  # {"numTrimLeft": x, "numTrimRight": y}
    prompt: str = ""
    blend_duration: Optional[float] = None

    def to_params_list(self) -> List[str]:
        """Convert to list of parameter strings for API."""
        params = []
        if self.t2m_rid:
            params.append(f"t2m_rid={self.t2m_rid}")
        if self.variant_id is not None:
            params.append(f"variant_id={self.variant_id}")
        req = {
            "t2m_rid": self.t2m_rid,
            "variant_id": self.variant_id,
            "editRequest": self.edit_request or {},
            "prompt": self.prompt,
            "blendDuration": self.blend_duration,
        }
        req = {k: v for k, v in req.items() if v is not None and v != "" and v != {}}
        params.append(f"mergingRequest={json.dumps(req)}")
        return params


@dataclass
class LoopParams:
    """Parameters for loop job."""

    t2m_rid: str = ""
    variant_id: Optional[int] = None
    prompt: Optional[str] = None
    num_reps: int = 1
    blend_duration: Optional[float] = None
    fix_root_mode: Optional[str] = None  # "INTERPOLATION" or "LOCKED"
    fix_root_position_altitude: Optional[int] = None  # 0 or 1
    fix_root_position_horizontal: Optional[int] = None  # 0 or 1
    fix_root_orientation: Optional[int] = None  # 0 or 1
    fix_across_entire_motion: Optional[int] = None  # 0 or 1

    def to_params_list(self) -> List[str]:
        """Convert to list of parameter strings for API."""
        params = []
        if self.t2m_rid:
            params.append(f"t2m_rid={self.t2m_rid}")
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
    """Parameters for refine job."""

    t2m_rid: str = ""
    variant_id: Optional[int] = None
    prompt: Optional[str] = None
    creativity: Optional[float] = None  # 0.0-1.0

    def to_params_list(self) -> List[str]:
        """Convert to list of parameter strings for API."""
        params = []
        if self.t2m_rid:
            params.append(f"t2m_rid={self.t2m_rid}")
        if self.variant_id is not None:
            params.append(f"variant_id={self.variant_id}")
        req = {}
        if self.prompt is not None:
            req["prompt"] = self.prompt
        if self.creativity is not None:
            req["creativity"] = self.creativity
        params.append(f"refineRequest={json.dumps(req)}")
        return params


# Alias for backward compatibility
ProcessParams = Text2MotionParams
