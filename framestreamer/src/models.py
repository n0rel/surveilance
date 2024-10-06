"""Module containing models"""

from pydantic import BaseModel
from cv2.typing import MatLike

class Frame(BaseModel):
    """Represents a single frame coming from a camera"""
    class Config:
        # This is due to cv2's `MatLike` not being serializable in pydantic
        arbitrary_types_allowed=True

    raw_frame: MatLike
    camera_id: str

class CameraConfig(BaseModel):
    """Represents configuration per camera"""
    id: str
    url: str

class Config(BaseModel):
    """Represents the program configuration"""
    binding_url: str
    encoding_extention: str
    cameras: list[CameraConfig]
