
import threading
import cv2
import numpy as np


FRAME_WIDTH = 640
FRAME_HEIGHT = 480


class DisplayBuffer:
    def __init__(self):
        self.lock = threading.Lock()
        self.image = None


def create_panel(frame, title, status):
    """Prepare one side of the display window."""

    if frame is None:
        panel = np.zeros(
            (FRAME_HEIGHT, FRAME_WIDTH, 3),
            dtype=np.uint8
        )
    else:
        panel = cv2.resize(
            frame, (FRAME_WIDTH, FRAME_HEIGHT)
        )

    panel = panel.copy()

    # Dark header at the top of the panel
    cv2.rectangle(
        panel, (0, 0), (FRAME_WIDTH, 50),
        (35, 35, 35), -1
    )

    cv2.putText(
        panel, title, (15, 32),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7, (255, 255, 255), 2
    )

    cv2.putText(
        panel, status, (15, FRAME_HEIGHT - 20),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7, (0, 255, 0), 2
    )

    return panel


def display_worker(state, display_buffer):
    """Prepare the two-panel display continuously."""

    print("[Display] Thread started.")

    try:
        while not state.stop_event.is_set():

            # Read shared images safely

            #copy shared image data while holding frame lock 
            #when is_frozen is true, left panel shows frozen_frame, otherwise it shows latest_frame
            #right panel shows most recent processed_frame
            
            with state.frame_lock:
                is_frozen = state.is_frozen

                if is_frozen:
                    source = state.frozen_frame
                else:
                    source = state.latest_frame

                live_frame = (
                    source.copy()
                    if source is not None else None
                )

                result_frame = (
                    state.processed_frame.copy()
                    if state.processed_frame is not None
                    else None
                )

            status = "FROZEN" if is_frozen else "LIVE"

            # Left panel: latest camera frame
            left_panel = create_panel(
                live_frame, "Camera Feed", status
            )

            # Right panel: processed result
            right_panel = create_panel(
                result_frame,
                "Processed Result",
                "WAITING" if result_frame is None else "READY"
            )

            # Combine both panels horizontally
            combined = np.hstack(
                (left_panel, right_panel)
            )

            # Publish composed image safely
            with display_buffer.lock:
                display_buffer.image = combined

            # Limit refresh rate to approximately 25 FPS
            state.stop_event.wait(0.04)

    except Exception as error:
        print(f"[Display] Error: {error}")
        state.stop_event.set()

    finally:
        print("[Display] Thread stopped.")
