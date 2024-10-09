# Frame Streamer
Python implementation of a frame collector.

Collects frames from streams (e.g: IP Cameras) and distributes them to a ZeroMQ socket.

The messages sent to the ZeroMQ socket are multipart messages where:
1. the first part is the camera ID (see: config.yaml)
2. the second part is the actual binary frame encoded in `encoding_extention` (see: config.yaml)

This allows consumers to subscribe to specific IDs.

example config.yaml:
```
binding_url: "tcp://*:5555"
encoding_extention: ".jpg"
cameras:
  - id: "18"
    url: "rtsp://localhost/stream"
  - id: "17"
    url: 
```


Example usage:
```
docker build -t framestreamer
docker run --name framestreamer -p 5555:5555 --rm -d framestreamer:latest
```
