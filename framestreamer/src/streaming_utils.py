"""Module containing utilities which deal with images."""

import queue
import cv2
from cv2.typing import MatLike
from typing import Any
from loguru import logger
from numpy import dtype, ndarray, uint8

from src.exceptions import CameraStreamError, EncodingError
from src.models import CameraConfig, Frame


def encode_frame(frame: MatLike, extention: str) -> ndarray[Any, dtype[uint8]]:
    """Encodes a frame using extention `extention`.
    
    Params:
        frame (MatLike): The frame to encode.
        extention (str): The extention encoding to use.

    Returns:
        ndarray: The encoded array
    """
    ret, encoded_frame = cv2.imencode(".jpg", frame)

    if not ret:
        raise EncodingError(f"Can't encode frame to specified format {extention}")

    return encoded_frame



def stream_frames(cameras: list[CameraConfig], frames_queue: queue.Queue[Frame]):
    """Streams frames from several cameras.
    
    Params:
        cameras (list[CameraConfig]): The configurations for the cameras.
        frames_queue (Queue[Frame]): The queue where frames will be put.
    """
    captures = {
        camera_config.id: cv2.VideoCapture(camera_config.url)
        for camera_config in cameras
    }

    for camera, capture in captures.items():
        if not capture.isOpened():
            raise CameraStreamError(f"Could not open stream of camera {camera}. Check Camera or URL.")

    try:
        while True:
            for camera in cameras:
                ret, frame = captures[camera.id].read()
                if not ret:
                    logger.error(f"Couldn't receive frame from camera {camera.id}")
                    continue
                
                frame = Frame(raw_frame=frame, camera_id=camera.id)
                frames_queue.put(frame)
    except Exception:
        logger.exception("An unexpected exception occurred, releasing all captures...")
        for capture in captures.values():
            capture.release()
