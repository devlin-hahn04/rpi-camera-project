
import threading
import queue

#Lock prevents multiple accesses to shared frame data while one thread is readding or modifying
#queue safely transfers filter requests from menu thread to processor thread 

class AppState:
    def __init__(self):
        # Protect shared frame variables
        self.frame_lock = threading.Lock()

        # Camera and processing data
        self.latest_frame = None
        self.frozen_frame = None
        self.processed_frame = None

        # Current application status
        self.is_frozen = False
        self.last_filter = None

        # Menu-to-processor communication
        self.filter_queue = queue.Queue()

        # Capture synchronization
        self.pause_event = threading.Event()
        self.paused_ack_event = threading.Event()

        # Application shutdown
        self.stop_event = threading.Event()
