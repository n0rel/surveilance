from copy import deepcopy
import logging

from ultralytics.engine.results import Results
from src.models import DetectedObject, Detection

logging.getLogger("ultralytics").setLevel(logging.ERROR)


def prepare_detection(results: Results, ignore_objects_detected: list[str]):
    detection = Detection(detected_objects=[])

    for result in results:
        if result.boxes:
            for box in result.boxes:
                detected_object = DetectedObject(
                    result_class=None,
                    bbox=None,
                    tracking_id=None,
                    confidence=float(box.conf[0]),
                    image=deepcopy(result.orig_img),
                    bboxed_image=deepcopy(result.orig_img),
                    preprocess_speed=result.speed["preprocess"],
                    inference_speed=result.speed["inference"],
                    postprocess_speed=result.speed["postprocess"],
                    source=result.path,
                )
                result_class = result.names[int(box.cls[0])]
                if result_class in ignore_objects_detected:
                    continue

                detected_object.result_class = result_class

                x1, y1, x2, y2 = box.xyxy[0]
                detected_object.bbox = (int(x1), int(y1), int(x2), int(y2))

                detected_object.bboxed_image = detected_object.bboxed_image[int(x1):int(x2), int(y1):int(y2)]

                detection.detected_objects.append(detected_object)

    return detection
