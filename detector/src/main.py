import cv2
import numpy as np
import zmq
import threading
from ultralytics import YOLO
import easyocr
import queue

ZMQ_PUBLISH_SERVER = "tcp://localhost:5555"

cars_model = YOLO("yolo11n.pt")
license_plate_model = YOLO("models/license_plate_detector.pt")
frame_queue = queue.Queue()

reader = easyocr.Reader(['en'])

def display_frame():
    while True:
        try:
            print(frame_queue.qsize())
            frame = frame_queue.get(timeout=5)
        except queue.Empty:
            return
        

        cv2.imshow("frame", frame)
        cv2.waitKey(1)


def handle_message(body: bytes):
    image = np.frombuffer(body, dtype="uint8")
    frame = cv2.imdecode(image, cv2.IMREAD_COLOR)

    car_results = cars_model.track(
        frame, 
        conf=0.25, 
        imgsz=(1056, 1920), 
        vid_stride=10, 
        stream=True,
        verbose=False
    )
    for car_result in car_results:
        if not car_result.boxes:
            continue

        for car_box in car_result.boxes:
            if not car_box.id:
                continue

            result_class = car_result.names[int(car_box.id)]
            [x1, y1, x2, y2] = car_box.xyxy[0]
            x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)

            if result_class == "car" or result_class == "bicycle":
                car_frame = frame[y1:y2, x1:x2]
                license_plate_results = license_plate_model.track(
                    car_frame,
                    conf=0.25,
                    imgsz=640,
                    vid_stride=3,
                    stream=True,
                    verbose=False
                )
                for plate_result in license_plate_results:
                    if plate_result.boxes:
                        plate_box = plate_result.boxes[0]
                        [plate_x1, plate_y1, plate_x2, plate_y2] = plate_box.xyxy[0]
                        plate_x1, plate_y1, plate_x2, plate_y2 = int(plate_x1),\
                                                                 int(plate_y1),\
                                                                 int(plate_x2),\
                                                                 int(plate_y2)

                        # plate_frame = car_frame[plate_y1:plate_y2, plate_x1:plate_x2]

                        # read_object = reader.readtext(plate_frame)
                        # if not read_object:
                        #     continue

                        # license_plate_text = read_object[0][1]
                        # cv2.putText(
                        #     frame,
                        #     license_plate_text,
                        #     (x1 + plate_x1, y1 + plate_y1),
                        #     cv2.FONT_HERSHEY_SIMPLEX,
                        #     1,
                        #     (0, 255, 0),
                        #     2
                        # )
                        cv2.rectangle(
                            frame,
                            (x1 + plate_x1, y1 + plate_y1), 
                            (x1 + plate_x2, y1 + plate_y2), 
                            (0, 255, 0),
                            2
                        )

            cv2.rectangle(frame, (x1, y1), (x2, y2), (225, 0, 0), 2)
            cv2.putText(
                frame,
                f"[{car_box.id}] {car_result.names[int(car_box.id)]} - {car_box.conf[0]:.2f}",
                (x1, y1),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (255, 0, 0),
                2,
            )
    frame_queue.put(frame)


def receive_frame_from_stream(camera_id: str, frame_output_queue: queue.Queue):
    socket = context.socket(zmq.SUB)
    socket.connect(ZMQ_PUBLISH_SERVER)
    socket.setsockopt_string(zmq.SUBSCRIBE, camera_id)

    while True:
        try:
            data = socket.recv_multipart()
            frame_output_queue.put(data[1])
        except Exception:
            socket.close()
            break


thread = threading.Thread(target=display_frame)
thread.daemon = True
thread.start()


context = zmq.Context()
cameras = ["16", "18"]

while True:
    try:
        data = socket.recv_multipart()
        handle_message(body=data[1])
    except Exception:
        context.destroy()
        thread.join(timeout=1)
        break
