import queue
import threading
import yaml
from loguru import logger
from pathlib import Path
from src.streaming_utils import encode_frame
from src.models import Config, Frame
from src.publisher import PublisherProtocol, ZeroMQPublisher
from src.streaming_utils import stream_frames


def load_config(config_path: Path) -> Config:
    """Loads the programs configuration file.
    
    Params:
        config_path (Path) The file path to the config file

    Returns:
        Config: A configuration object
    """
    with open(config_path, 'r') as config_file_handle:
        try:
            config = yaml.load(config_file_handle, Loader=yaml.Loader)
        except yaml.YAMLError as error:
            logger.error(f"There was an error in the configuration file: {error}")

    return Config.model_validate(config)


def main():
    logger.info("Loading config...")
    config = load_config('config.yaml')

    publisher: PublisherProtocol = ZeroMQPublisher(binding_url=config.binding_url)
    raw_frame_queue: queue.Queue[Frame] = queue.Queue()

    streaming_thread = threading.Thread(target=stream_frames, kwargs={'cameras': config.cameras, 'frames_queue': raw_frame_queue})
    streaming_thread.daemon = True

    logger.info("Starting Streaming Thread")
    streaming_thread.start()

    logger.info("Starting Publisher")
    publisher.start()

    while True:
        logger.info(f"Receiving frame, queue size: {raw_frame_queue.qsize()}")
        frame: Frame = raw_frame_queue.get()
        encoded_frame = encode_frame(frame=frame.raw_frame, extention=config.encoding_extention)
        publisher.publish(topic=frame.camera_id, message=encoded_frame)

if __name__ == "__main__":
    main()
