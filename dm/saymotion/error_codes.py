"""Error code mappings for Saymotion REST API.

Based on "Saymotion Restful API Error Codes" section in api_doc.md.
"""

from typing import Any, Optional

# Saymotion REST API error codes
ERROR_CODES = {
    # General
    101: "Not enough credit",
    # Pipeline
    494: "Invalid pipeline input",
    498: "Unknown pipeline error",
    # Motion generation
    501: "Error while generating motion",
    502: "Error parsing motion generation parameters",
    599: "Motion generation timeout",
    # Pose tracking
    603: "Error processing pose tracking parameters",
    604: "Error loading animation data for pose tracking",
    605: "Physics Filter is incompatible with used custom character",
    607: "Error while processing the body tracking",
    610: "Error saving pose tracking intermediate results",
    699: "Pose tracking timeout",
    # Pose correction
    703: "Error processing pose correction parameters",
    704: "Error loading the character animation assets for pose corrections",
    710: "Error saving pose correction intermediate results",
    799: "Pose correction timeout",
    # BVH exporting
    803: "Error processing bvh exporter parameters",
    804: "Error loading the character animation assets for bvh exporting",
    810: "Error saving bvh results",
    899: "Bvh exporting timeout",
    # Custom character / animation baking
    901: "Error loading the mesh of the custom character",
    902: "Error loading the BVH custom character",
    903: "Error copying animations onto the custom character",
    904: "Error exporting animations for the custom character",
    905: "Custom character doesn't include skinned mesh information",
    906: "More than half of the required blendshapes are missing",
    907: "Error loading facial definition for the custom character",
    908: "Error loading facial tracking data",
    909: "Error loading the metadata of the custom character",
    999: "Animation baking timeout",
    # Rendering
    1101: "Process stuck",
    1102: "Invalid input parameter",
    1105: "Failed to load input character",
    1106: "Failed to attach animation to character",
    1107: "Failed to configure backdrop",
}


def get_error_message(error_code: Any) -> str:
    """Get error message for an error code.

    Args:
        error_code: Error code, which can be an int, str, or list of codes

    Returns:
        Error message string
    """
    # Handle list format (e.g., ['101'])
    if isinstance(error_code, list):
        if not error_code:
            return "Unknown error"
        # Get messages for all codes in the list
        messages = []
        for code in error_code:
            code_int = _parse_error_code(code)
            if code_int and code_int in ERROR_CODES:
                messages.append(f"Error {code_int}: {ERROR_CODES[code_int]}")
            else:
                messages.append(f"Error {code}")
        return "; ".join(messages)

    # Handle single code
    code_int = _parse_error_code(error_code)
    if code_int and code_int in ERROR_CODES:
        return f"Error {code_int}: {ERROR_CODES[code_int]}"

    # Fallback to original value
    return str(error_code) if error_code is not None else "Unknown error"


def _parse_error_code(code: Any) -> Optional[int]:
    """Parse error code to integer.

    Args:
        code: Error code (can be int, str, etc.)

    Returns:
        Integer error code or None if cannot parse
    """
    if isinstance(code, int):
        return code
    if isinstance(code, str):
        try:
            return int(code)
        except ValueError:
            return None
    return None


def format_error_message(exc_message: Any, exc_type: Optional[str] = None) -> str:
    """Format error message from exc_message and exc_type.

    Args:
        exc_message: Exception message (can be str, list, etc.)
        exc_type: Exception type (optional)

    Returns:
        Formatted error message
    """
    # Handle exc_message which may be a string, list, or other format
    if isinstance(exc_message, list):
        # If it's a list, treat each element as an error code
        error_messages = []
        for item in exc_message:
            msg = get_error_message(item)
            error_messages.append(msg)
        message = "; ".join(error_messages)
    elif exc_message:
        # Try to parse as error code first
        parsed = _parse_error_code(exc_message)
        if parsed and parsed in ERROR_CODES:
            message = get_error_message(parsed)
        else:
            message = str(exc_message)
    else:
        message = "Unknown error"

    # Add exception type if provided
    if exc_type:
        message = f"{exc_type}: {message}"

    return message
