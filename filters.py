
from parallel_processing import parallel_filter


def apply_filter(frame, filter_name, num_processes=4):
    """
    Apply the selected filter using multiple processes.

    Returns:
        processed_frame
        actual_processes
    """

    # rest of app calls this function and separates the thread coordination from multiprocessing implementation

    return parallel_filter(
        frame,
        filter_name,
        num_processes
    )
