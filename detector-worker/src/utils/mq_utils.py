"""Utility Functions for actions on an MQ"""
import socket
from abc import abstractmethod
import time
from typing import Protocol
from pika.connection import Parameters
from pika.exceptions import AMQPConnectionError, ConnectionWrongStateError
from pika.adapters.blocking_connection import BlockingConnection, BlockingChannel
from confluent_kafka import Producer
from loguru import logger


class Publisher(Protocol):

    @abstractmethod
    def publish(self, body: bytes): ...



class TCPPublisher(Publisher):
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port

    def publish(self, body: bytes):
        sending_counter = 5
        while True:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((self.host, self.port))
                sock.send(body)
                sock.close()
            except Exception:
                logger.error("Could not connect to TCP socket!")
                if sending_counter == 0:
                    logger.error("Discarding message...")
                    break
                logger.error("Trying again in 5 seconds...")
                time.sleep(5)
                sending_counter -= 1

class RabbitMQBlockingPublisher(Publisher):
    def __init__(self, parameters: Parameters, exchange: str, queue: str):
        self.parameters = parameters
        self.exchange = exchange
        self.queue = queue
        self.connection = BlockingConnection(parameters=parameters)
        self.channel: BlockingChannel = self.connection.channel()

    def publish(self, body: bytes):
        try:
            if not self.channel:
                raise Exception("Tried publishing without a successful connection")
            pika_blocking_declare_queue(channel=self.channel, queue_name=self.queue)
            pika_blocking_publish(
                channel=self.channel,
                queue_name=self.queue,
                body=body,
                exchange=self.exchange,
            )
        except (AMQPConnectionError, ConnectionWrongStateError) as error:
            logger.error(error)
            logger.info("Connection error, reconnecting to channel...")
            self.connection = BlockingConnection(parameters=self.parameters)
            self.channel = self.connection.channel()

            self.publish(body=body)


class KafkaPublisher(Publisher):
    def __init__(self, producer: Producer, topic: str):
        self.producer = producer
        self.topic = topic

    def publish(self, body: bytes):
        kafka_publish(connection=self.producer, topic=self.topic, body=body)


def kafka_publish(connection: Producer, topic: str, body: bytes):
    connection.produce(topic, body)


def pika_blocking_declare_queue(
    channel: BlockingChannel, queue_name: str
) -> BlockingChannel:
    """Uses Pika to connect to a RabbitMQ channel.

    Will create the channel if it does not exist.

    Params:
        connection: The Pika connection object used as a connection
        channel_name: The name of the channel to connect to

    Returns:
        BlockingChannel: The RabbitMQ channel used if needed to perform future actions
    """
    logger.debug(f"Declaring queue")

    channel.queue_declare(queue=queue_name)

    logger.debug("Successfully connected to channel")
    return channel


def pika_blocking_publish(
    channel: BlockingChannel, queue_name: str, body: bytes, exchange: str = ""
):
    """Publishes `body` to the RabbitMQ queue `queue_name`

    Params:
        channel: The channel (pika connection derivative) to use to publish
        queue_name: The queue to publish to
        body: The bytes to send
        exchange: The exchange to publish to. Is "" by default.

    Raises:
        AMQPConnectionError: If the connection is closed
    """
    channel.basic_publish(exchange=exchange, routing_key=queue_name, body=body)
