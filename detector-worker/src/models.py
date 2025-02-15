from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict, JsonConfigSettingsSource

class DetectionResult(BaseModel):
    timestamp: datetime
    source: str
    detection_id: str
    result_class: str
    confidence: float
    image: bytes
    image_encoding: str
    preprocess_speed: float
    inference_speed: float
    postprocess_speed: float

class DetectedObject(BaseModel):
    """Represents a detected object from an ai model"""
    result_class: str | None
    tracking_id: int | None
    bbox: tuple[int, int, int, int] | None
    confidence: float | None
    preprocess_speed: float | None
    inference_speed: float | None
    postprocess_speed: float | None
    source: str = "NO SOURCE"
    image: Any = None
    bboxed_image: Any = None

class Detection(BaseModel):
    """Detection object"""
    detected_objects: list[DetectedObject]

class RabbitMQConfig(BaseModel):
    rabbitmq_host: str
    rabbitmq_port: str
    rabbitmq_user: str
    rabbitmq_pass: str
    detection_json_queue: str
    detection_image_queue: str


class KafkaConfig(BaseModel):
    servers: str
    client_id: str
    detection_json_topic: str
    detection_image_topic: str

class RedisConfig(BaseModel):
    redis_host: str
    redis_port: int
    redis_index_name: str
    caching_vector_radius: float
    caching_ttl_milliseconds: int
    caching_far_ttl_milliseconds: int

class TCPConfig(BaseModel):
    detection_json_host: str
    detection_json_port: int
    detection_image_host: str
    detection_image_port: int

class StreamConfig(BaseModel):
    name: str
    stream_uri: str

class Config(BaseSettings):
    """Represents the program configuration"""

    model_config = SettingsConfigDict(json_file="settings.json", json_file_encoding="utf-8")
    
    publisher_type: Literal['rabbitmq', 'kafka', 'tcp']
    rabbitmq: RabbitMQConfig
    kafka: KafkaConfig
    tcp: TCPConfig
    redis: RedisConfig
    frame_encoding_extention: str
    ignore_objects_detected: list[str]
    skip_frame_count: int
    gpu_device: int
    minimum_confidence: float
    detection_image_size: tuple[int, int]
    streams: list[StreamConfig]

    @classmethod
    def settings_customise_sources(cls, settings_cls: type[BaseSettings], init_settings: PydanticBaseSettingsSource, env_settings: PydanticBaseSettingsSource, dotenv_settings: PydanticBaseSettingsSource, file_secret_settings: PydanticBaseSettingsSource) -> tuple[PydanticBaseSettingsSource, ...]:
        return (JsonConfigSettingsSource(settings_cls),)
