
import threading
import select
import sys


FILTERS = {
    "1": "Blur",
    "2": "Grayscale",
    "3": "Invert colors"
}


def menu_worker(state):
    print("[Menu] Thread started.")

    try:
        while not state.stop_event.is_set():
            print("\n--- Filters ---")
            print("1) Blur")
            print("2) Grayscale")
            print("3) Invert colors")
            print("0) Exit")
            print("Choose a filter: ", end="", flush=True)

            # Wait for terminal input without blocking shutdown
            while not state.stop_event.is_set():
                ready, _, _ = select.select(
                    [sys.stdin], [], [], 0.1
                )

                if ready:
                    break

            if state.stop_event.is_set():
                break

            choice = sys.stdin.readline().strip()

            # Handle terminal input closing
            if choice == "" and not sys.stdin.isatty():
                print("\n[Menu] Input closed.")
                state.stop_event.set()
                break

            if choice == "0":
                print("[Menu] Exit requested.")
                state.stop_event.set()
                break

            if choice not in FILTERS:
                print("[Menu] Invalid option. Try again.")
                continue

            filter_name = FILTERS[choice]

            # Completion signal for this request
            done_event = threading.Event()

            #menu thread produces filter requests 
            #processor thread consumes those requests 

            #done_event lets menu wait until processing finishes to prevent overlapping filter requests 

            # Send filter request to processor
            state.filter_queue.put(
                (filter_name, done_event)
            )

            print(f"[Menu] Requested: {filter_name}")
            print("[Menu] Waiting for processing...")

            # Wait until processor finishes
            while not state.stop_event.is_set():
                if done_event.wait(timeout=0.1):
                    break

    except Exception as error:
        print(f"\n[Menu] Error: {error}")
        state.stop_event.set()

    finally:
        print("[Menu] Thread stopped.")
