import threading
import cv2

from shared_state import AppState
from camera_capture import capture_worker
from display import DisplayBuffer, display_worker
from menu import menu_worker
from processor import processor_worker

WINDOW_NAME = "Parallel Camera Filter Viewer"

#entry point to the application
#create a shared state object and launch independent threads for camera capture, display, menu, and processing
#each thread handles different tasks so camera capture, user interaction, displauy preparation and proccesing coordination are separated



def main():
    state = AppState()
    display_buffer = DisplayBuffer()

    # Create and start threads for each component of the application
    capture_thread = threading.Thread(
        target=capture_worker,
        args=(state,),
        name="CaptureThread"
    )

    display_thread = threading.Thread(
        target=display_worker,
        args=(state, display_buffer),
        name="DisplayThread"
    )

    menu_thread = threading.Thread(
        target=menu_worker,
        args=(state,),
        name="MenuThread"
    )

    processor_thread = threading.Thread(
        target=processor_worker,
        args=(state, 4),   # 4 processes for now
        name="ProcessorThread"
    )

    threads = [
        capture_thread,
        display_thread,
        menu_thread,
        processor_thread
    ]

    try:
        cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(WINDOW_NAME, 1100, 450)

        #starting threads
        for thread in threads:
            thread.start() #launches worker threads 

        print("[Main] All 4 threads started.")
        print("[Main] Use the terminal menu to choose a filter.")
        print("[Main] Press Q in the window or close the window to exit.")

        while not state.stop_event.is_set():
            with display_buffer.lock:
                image = (
                    display_buffer.image.copy()
                    if display_buffer.image is not None
                    else None
                )

            if image is not None:
                cv2.imshow(WINDOW_NAME, image)

            key = cv2.waitKey(30) & 0xFF

            if key in (ord("q"), ord("Q")):
                print("[Main] Exit requested from window.")
                break

            try:
                visible = cv2.getWindowProperty(
                    WINDOW_NAME, cv2.WND_PROP_VISIBLE
                )
                if visible < 1:
                    print("[Main] Window closed.")
                    break
            except cv2.error:
                print("[Main] Window no longer available.")
                break

    except KeyboardInterrupt:
        print("\n[Main] Interrupted by user.")

    finally:
        print("[Main] Stopping application...")

        state.stop_event.set()  #signals app shutdown
        state.pause_event.clear() #prvents Capture thread from staying paused

        #stopping threads
        for thread in threads:
            if thread.ident is not None:
                thread.join()  #waits for each one to terminate during shutdown 

        cv2.destroyAllWindows()

        print("[Main] Application stopped cleanly.")


if __name__ == "__main__":
    main()