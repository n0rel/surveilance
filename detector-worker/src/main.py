import base64
import datetime
import sys
import time
from pika import BlockingConnection, ConnectionParameters, PlainCredentials
import torch
import ultralytics
import cv2
import redis
import uuid
import cv2
from loguru import logger

from src.exceptions import EncodingError
from src.utils.detection_utils import prepare_detection
from src.utils.image_utils import draw_rectangle, draw_text
from src.models import Config, DetectedObject, DetectionResult, RedisConfig

from src.utils.redis_utils import create_index, query_knn, add_vector
from src.utils.mq_utils import (
    Publisher,
    RabbitMQBlockingPublisher,
    TCPPublisher,
)


KAFKA_MESSAGE_MAX_BYTES = "1000000000"
NEAR_CACHE_TAG = 'near'
FAR_CACHE_TAG = 'far'


def prepare_detection_result(detected_object: DetectedObject, frame_encoding_extention: str) -> DetectionResult | None:
    if (
        not detected_object.bbox
        or not detected_object.result_class
        or not detected_object.confidence
    ):
        return

    draw_rectangle(
        image=detected_object.image,
        x1=detected_object.bbox[0],
        y1=detected_object.bbox[1],
        x2=detected_object.bbox[2],
        y2=detected_object.bbox[3],
        color=(225, 0, 0),
    )

    draw_text(
        image=detected_object.image,
        text=f"[{detected_object.result_class}] {detected_object.confidence:.2f}",
        x=detected_object.bbox[0],
        y=detected_object.bbox[1],
        color=(255, 0, 0),
    )

    ret, encoded_frame = cv2.imencode(
        ext=frame_encoding_extention, img=detected_object.image
    )
    if not ret:
        raise EncodingError(
            f"Could not encode a detection result to {frame_encoding_extention}"
        )

    detection_id = str(uuid.uuid4())
    return DetectionResult(
        timestamp=datetime.datetime.now(datetime.timezone.utc),
        source=detected_object.source,
        preprocess_speed=(
            detected_object.preprocess_speed
            if detected_object.preprocess_speed
            else 0.00
        ),
        inference_speed=(
            detected_object.inference_speed
            if detected_object.inference_speed
            else 0.00
        ),
        postprocess_speed=(
            detected_object.postprocess_speed
            if detected_object.postprocess_speed
            else 0.00
        ),
        detection_id=detection_id,
        result_class=detected_object.result_class,
        confidence=detected_object.confidence,
        image=base64.b64encode(encoded_frame.tobytes()),
        image_encoding=frame_encoding_extention
    )


def detected_object_in_caches(
    detected_object: DetectedObject,
    redis_client: redis.Redis,
    redis_config: RedisConfig,
    far_cache_dict: dict[tuple[str, str], str]
) -> bool:
    """Checks both FAR (long term) and NEAR (short term) caches for this detection.

    This is to ensure there aren't a spam of the same objects every different
    frame.

    The logic is currently as follows:
        1. Check if the BBOX, CLASS & SOURCE are cached in the near cache
        2. If not, check if CLASS, SOURCE & PIXEL HASH are cached in the far cache
        3. If not, return True (object detected)

    The FAR (long term) caching logic basically says that if an object
    from the same source has the same class and exact pixels as a previously
    detected object, it is not only the same object, but informational wise is irrelevent.

    """
    if not detected_object.bbox or not detected_object.result_class or not detected_object.source:
        raise Exception

    knn_res = query_knn(
        redis_client=redis_client,
        index_name=redis_config.redis_index_name,
        vector=detected_object.bbox,
        result_class=detected_object.result_class,
        source=detected_object.source,
        radius=redis_config.caching_vector_radius,
        tag=NEAR_CACHE_TAG
    )
    if knn_res:
        logger.info(knn_res)
        return True
        
        if (detected_object.source, detected_object.result_class) not in far_cache_dict:
            return True
        else:
            try:
                template_img = cv2.imread(
                    filename=far_cache_dict[(detected_object.source, detected_object.result_class)]
                )
            except Exception as error:
                logger.error(f"Error reading file w/ opencv: {error}")
                return True
            
            match_result = cv2.matchTemplate(
                image=detected_object.bboxed_image, 
                templ=template_img, 
                method=cv2.TM_CCOEFF_NORMED
            )
            logger.info(f"Template matched result: {match_result}")
            return True


    return False


@logger.catch(Exception)
def main():
    config = Config()
    
    far_cache_dict: dict[tuple[str, str], str] = {}

    logger.info("Loading Model")
    model = ultralytics.YOLO("yolo11n.engine")

    logger.info("Loading External Connections")
    image_publisher: Publisher | None = None
    json_publisher: Publisher | None = None
    if config.publisher_type == "rabbitmq":
        rabbit_parameters=ConnectionParameters(
            host=config.rabbitmq.rabbitmq_host,
            port=config.rabbitmq.rabbitmq_port,
            credentials=PlainCredentials(
                username=config.rabbitmq.rabbitmq_user,
                password=config.rabbitmq.rabbitmq_pass,
            ),
        )
        json_publisher = RabbitMQBlockingPublisher(
            parameters=rabbit_parameters,
            exchange="",
            queue=config.rabbitmq.detection_json_queue,
        )
        image_publisher = RabbitMQBlockingPublisher(
            parameters=rabbit_parameters,
            exchange="",
            queue=config.rabbitmq.detection_image_queue,
        )
    elif config.publisher_type == "kafka":
        pass
    elif config.publisher_type == "tcp":
        json_publisher = TCPPublisher(
            host=config.tcp.detection_json_host, port=config.tcp.detection_json_port
        )
        image_publisher = TCPPublisher(
            host=config.tcp.detection_image_host, port=config.tcp.detection_image_port
        )

    redis_client = redis.Redis(
        host=config.redis.redis_host, port=config.redis.redis_port
    )
    if not json_publisher or not image_publisher:
        raise Exception("Couldn't connect to external connections...")

    
    logger.info("Checking streams")
    open_streams = []
    for stream in config.streams:
        capture = cv2.VideoCapture(stream.stream_uri)
        if capture.isOpened():
            ret, _ = capture.read()
            if ret:
                open_streams.append(stream)
                logger.info(f"Added stream: {stream.name} from URI: {stream.stream_uri}")
                capture.release()
                continue
        
        logger.error(f"Stream {stream.name} - {stream.stream_uri} was not open. Not adding to surveilance")
        capture.release()

    logger.info("Creating list.streams file")
    with open('list.streams', 'w', encoding='utf-8') as file:
        for index, stream in enumerate(open_streams):
            if index < 8:
                file.write(stream.stream_uri + "\n")

    logger.info("Connecting to Redis Index")
    create_index(
        redis_client=redis_client,
        index_name=config.redis.redis_index_name,
        vector_dimensions=4,
    )

    source_runtime_seconds_debug: dict[str, float] = {}

    logger.info("Beginning inference")
    for results in model.predict(
        source="list.streams",
        stream=True,
        conf=config.minimum_confidence,
        verbose=True,
        imgsz=config.detection_image_size,
        half=True,
        device=torch.device(f"cuda:{config.gpu_device}"),
        vid_stride=config.skip_frame_count,
        stream_buffer=False,
        batch=8,
    ):

        detection = prepare_detection(
            results=results, ignore_objects_detected=config.ignore_objects_detected
        )
        if len(detection.detected_objects) == 0:
            continue

        for detected_object in detection.detected_objects:
            with logger.contextualize(source=detected_object.source):
                if (
                    not detected_object.bbox
                    or not detected_object.result_class
                    or not detected_object.confidence
                ):
                    continue

                if detected_object_in_caches(
                    detected_object=detected_object, 
                    redis_client=redis_client, 
                    redis_config=config.redis,
                    far_cache_dict=far_cache_dict
                ):
                    continue
                    generated_filename = f"/tmp/{str(uuid.uuid4())}.jpg"
                    far_cache_dict[(detected_object.source, detected_object.result_class)] = generated_filename
                    cv2.imwrite(filename=generated_filename, img=detected_object.bboxed_image)

                    last_ran_time = time.time() - source_runtime_seconds_debug[detected_object.source] if detected_object.source in source_runtime_seconds_debug else 0
                    logger.info(
                            f"Detected an object! {detected_object.result_class} | {detected_object.confidence} | {detected_object.bbox}. There are {len(detection.detected_objects)} objects in this frame. Last detection from this source was {last_ran_time:.3f}s ago"
                    )

                    if (
                        detection_result := prepare_detection_result(
                            detected_object=detected_object, 
                            frame_encoding_extention=config.frame_encoding_extention
                        )
                    ):
                        json_publisher.publish(
                            body=detection_result.model_dump_json(
                                exclude=set(["image", "image_encoding"])
                            ).encode(),
                        )
                        image_publisher.publish(
                            body=detection_result.model_dump_json(
                                include=set(["image", "source", "detection_id", "image_encoding"])
                            ).encode(),
                        )
                else:
                    logger.debug(f"Cache hit: {detected_object.bbox}")

                add_vector(
                    redis_client=redis_client,
                    vector=detected_object.bbox,
                    result_class=detected_object.result_class,
                    source=detected_object.source,
                    ttl=datetime.timedelta(
                        milliseconds=config.redis.caching_ttl_milliseconds
                    ),
                    tag=NEAR_CACHE_TAG
                )
                source_runtime_seconds_debug[detected_object.source] = time.time()


if __name__ == "__main__":
    logger.remove()
    logger.add(
        sys.stdout,
        diagnose=False,
        backtrace=False,
        format="{time} | {level} | {extra} | {message}",
        level="INFO",
    )
    
    while True:
        main()
