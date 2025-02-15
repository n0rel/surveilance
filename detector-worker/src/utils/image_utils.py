"""Utility functions for writing on or encoding images"""
import cv2
from cv2.typing import MatLike



def draw_rectangle(
    image: MatLike,
    x1: int,
    x2: int,
    y1: int,
    y2: int,
    color: tuple[int, int, int]
):
    """Draws a rectangle on `image`."""
    cv2.rectangle(
        img=image,
        pt1=(x1, y1),
        pt2=(x2, y2),
        color=color,
        thickness=2,
    )


def draw_text(
    image: MatLike,
    text: str,
    x: int,
    y: int,
    color:
    tuple[int, int, int]
):
    """Writes `text` on `image`"""
    cv2.putText(
        img=image,
        text=text,
        org=(x, y),
        fontFace=cv2.FONT_HERSHEY_SIMPLEX,
        fontScale=1,
        color=color,
        thickness=2,
    )
