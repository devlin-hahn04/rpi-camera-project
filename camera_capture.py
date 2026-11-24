
from picamera2 import Picamera2
import time


def capture_worker(state):
    camera = None

    try:
        # Initialize Raspberry Pi camera
        camera = Picamera2()

        config = camera.create_preview_configuration(
            main={
                "size": (640, 480),
                "format": "RGB888"
            }
        )

        camera.configure(config)
        camera.start()

        print("[Capture] Camera started.")

        # Keep capturing until shutdown
        while not state.stop_event.is_set():

            # Pause camera capture when requested
            if state.pause_event.is_set():
                state.paused_ack_event.set()

                while state.pause_event.is_set():
                    if state.stop_event.wait(0.05):
                        break

                state.paused_ack_event.clear()
                continue

            # Read camera frame
            frame = camera.capture_array()

            # Do not publish new frames if pause
            # was requested during capture
            if state.pause_event.is_set():
                continue

            # Protect the shared frame variable
            with state.frame_lock:
                state.latest_frame = frame.copy()

    except Exception as error:
        print(f"[Capture] Error: {error}")
        state.stop_event.set()

    finally:
        # Release camera resources
        if camera is not None:
            try:
                camera.stop()
            finally:
                camera.close()

        print("[Capture] Camera stopped.")
