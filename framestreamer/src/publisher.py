from typing import Protocol
import zmq



class PublisherProtocol(Protocol):
    """Base class for publishing clients.

    Assumes the client implements a basic Topic PUB/SUB architechture.
    """

    @classmethod
    def start():
        """Starts the Publisher, allowing clients to subscribe"""
    
    @classmethod
    def stop():
        """Stops the Publisher, releasing subscriber resources & disallowing clients to subscribe"""

    @classmethod
    def publish(topic: str, message: object):
        """Publishes a message to all clients subscribing to the topic `topic`"""


class ZeroMQPublisher(PublisherProtocol):
    """Publisher Implementation using ZeroMQ"""

    def __init__(self, binding_url: str) -> None:
        super().__init__()
        self.binding_url = binding_url

        self._context: zmq.Context | None = None
        self._socket: zmq.Socket | None = None

    def start(self):
        """Creates a ZeroMQ context & publishing socket and binds to `self.binding_url`

        ZeroMQ behind the scenes creates an I/O thread that will listen for subscribers
        and deliver them published messages.
        """

        self._context = zmq.Context()
        self._socket = self._context.socket(zmq.PUB)
        self._socket.bind(self.binding_url)

    def stop(self):
        """Stops the current ZeroMQ context.
        
        Subscribers will be unable to connect & stop receving publishes.
        """

        self._context.destroy()


    def publish(self, topic: str, message: object):
        """Publishes a ZeroMQ message using multipart messaging.
        
        `topic` will always be the first part while `message` will always be the second.
        """
        self._socket.send_multipart([topic.encode(), message])
