import cv2
import numpy as np
import zmq
import threading
from ultralytics import YOLO
import queue

ZMQ_PUBLISH_SERVER = "tcp://localhost:5555"

yolo = YOLO("yolo11n.pt")
q = queue.Queue()


def display_frame():
    while True:
        frame = q.get()
        results = yolo.track(frame, stream=True)
        for result in results:
            if result.boxes:
                for box in result.boxes:
                    if box.conf[0] > 0.4:
                        [x1, y1, x2, y2] = box.xyxy[0]
                        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (225, 0, 0), 2)
                        cv2.putText(
                            frame,
                            f"{result.names[int(box.cls[0])]}{box.conf[0]:.2f}",
                            (x1, y1),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            1,
                            (255, 0, 0),
                            2,
                        )

        cv2.imshow("frame", frame)
        cv2.waitKey(1)


def handle_message(body: bytes):
    image = np.frombuffer(body, dtype="uint8")
    frame = cv2.imdecode(image, cv2.IMREAD_COLOR)
    q.put(frame)


thread = threading.Thread(target=display_frame)
thread.daemon = True
thread.start()


context = zmq.Context()
socket = context.socket(zmq.SUB)
socket.connect(ZMQ_PUBLISH_SERVER)
socket.setsockopt_string(zmq.SUBSCRIBE, "")

while True:
    data = socket.recv_multipart()
    handle_message(body=data[1])
