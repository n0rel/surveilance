from cv2.typing import MatLike
from pydantic import BaseModel


class Frame(BaseModel):
    class Config:
        arbitrary_types_allowed = True

    raw_frame: MatLike
    camera_id: str
