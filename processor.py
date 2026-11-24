
import os
import queue
import time
from pathlib import Path

import cv2

from filters import apply_filter


OUTPUT_DIR = Path("output")


def save_images(original_frame, result_frame):
    """Save the original and processed frames."""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    original_bgr = cv2.cvtColor(
        original_frame, cv2.COLOR_RGB2BGR
    )

    result_bgr = cv2.cvtColor(
        result_frame, cv2.COLOR_RGB2BGR
    )

    original_path = OUTPUT_DIR / "original.png"
    result_path = OUTPUT_DIR / "result.png"

    original_saved = cv2.imwrite(
        str(original_path), original_bgr
    )

    result_saved = cv2.imwrite(
        str(result_path), result_bgr
    )

    if not original_saved or not result_saved:
        raise RuntimeError("Unable to save output images.")


def processor_worker(state, num_processes=4):
    print("[Processor] Thread started.")

    # Optional delay for testing freeze/resume.
    # Normally this is zero.
    test_delay = max(
        0.0, float(os.environ.get("CAMERA_TEST_DELAY", "0"))
    )

    try:
        while not state.stop_event.is_set():

            try:
                filter_name, done_event = (
                    state.filter_queue.get(timeout=0.1)
                )
            except queue.Empty:
                continue

            start_time = time.perf_counter()

            try:
                print(
                    f"[Processor] Received request: {filter_name}"
                )

                # 1. Request capture to pause
                state.pause_event.set()

                # 2. Wait until capture confirms it is paused
                deadline = time.monotonic() + 5.0

                while not state.paused_ack_event.is_set():
                    if state.stop_event.is_set():
                        break

                    if time.monotonic() >= deadline:
                        raise TimeoutError(
                            "Capture did not acknowledge pause."
                        )

                    state.paused_ack_event.wait(timeout=0.1)

                if state.stop_event.is_set():
                    continue

                # 3. Freeze the most recent captured frame
                with state.frame_lock:
                    if state.latest_frame is None:
                        raise RuntimeError(
                            "No camera frame available."
                        )

                    original_frame = state.latest_frame.copy()

                    state.frozen_frame = original_frame.copy()
                    state.is_frozen = True
                    state.last_filter = filter_name

                print("[Processor] Camera frozen.")

                # 4. Optional test delay.
                # This wakes early if shutdown is requested.
                if test_delay > 0:
                    print(
                        f"[Processor] Test delay: "
                        f"{test_delay:.1f} seconds"
                    )

                    if state.stop_event.wait(test_delay):
                        continue

                # 5. Apply filter
                result_frame, actual_processes = apply_filter(
                    original_frame,
                    filter_name,
                    num_processes=num_processes
                )

                if state.stop_event.is_set():
                    continue

                # 6. Save original and result
                save_images(original_frame, result_frame)

                # 7. Publish processed image
                with state.frame_lock:
                    state.processed_frame = result_frame.copy()

                elapsed_ms = (
                    time.perf_counter() - start_time
                ) * 1000.0

                print("\n---Execution Report---")
                print(f"Filter: {filter_name}")

                print(f"Processes: {actual_processes}")

                print(f"Total Time: {elapsed_ms:.2f} ms\n")

            except Exception as error:
                print(f"[Processor] Error: {error}")

            finally:
                # Release frozen state on success or failure
                with state.frame_lock:
                    state.is_frozen = False
                    state.frozen_frame = None

                # Allow capture to resume
                state.pause_event.clear()

                # Let capture clear its own acknowledgement
                # before a new request can be submitted.
                deadline = time.monotonic() + 2.0

                while (
                    state.paused_ack_event.is_set()
                    and not state.stop_event.is_set()
                    and time.monotonic() < deadline
                ):
                    state.stop_event.wait(0.01)

                # Notify the menu even if processing failed
                done_event.set()
                state.filter_queue.task_done()

                print("[Processor] Processing cycle finished.")

    except Exception as error:
        print(f"[Processor] Fatal error: {error}")
        state.stop_event.set()

    finally:
        state.pause_event.clear()
        print("[Processor] Thread stopped.")
