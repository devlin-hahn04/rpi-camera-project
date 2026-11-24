
import os
import multiprocessing as mp

import cv2
import numpy as np


def process_section(section, filter_name, trim_top, output_rows, connection):
    """Process one assigned image section."""

    try:
        cv2.setNumThreads(1)

        if filter_name == "Blur":
            result = cv2.GaussianBlur(section, (15, 15), 0)

        elif filter_name == "Grayscale":
            gray = cv2.cvtColor(
                section, cv2.COLOR_RGB2GRAY
            )
            result = cv2.cvtColor(
                gray, cv2.COLOR_GRAY2RGB
            )

        elif filter_name == "Invert colors":
            result = cv2.bitwise_not(section)

        else:
            raise ValueError(f"Unknown filter: {filter_name}")

        # Remove overlapping rows used for Blur
        result = result[
            trim_top:trim_top + output_rows
        ].copy()

        # Send the result and actual PID to the parent
        connection.send(("ok", result, os.getpid()))

    except Exception as error:
        connection.send(("error", str(error), os.getpid()))

    finally:
        connection.close()


def parallel_filter(frame, filter_name, num_processes=4):
    """Split image and process each section independently."""

    if not isinstance(frame, np.ndarray):
        raise TypeError("Frame must be a NumPy array.")

    if frame.ndim != 3 or frame.shape[2] != 3:
        raise ValueError("Expected a three-channel image.")

    if frame.dtype != np.uint8:
        raise ValueError("Expected uint8 image data.")

    if filter_name not in ("Blur", "Grayscale", "Invert colors"):
        raise ValueError("Invalid filter.")

    if not isinstance(num_processes, int) or num_processes < 2:
        raise ValueError("At least two processes are required.")

    height = frame.shape[0]

    if height < num_processes:
        raise ValueError("Too many processes for image height.")

    # Calculate horizontal sections
    boundaries = np.linspace(
        0, height, num_processes + 1, dtype=int
    )

    context = mp.get_context("spawn")

    processes = []
    connections = []
    results = []
    worker_pids = set()

    try:
        # Create one process per image section
        for i in range(num_processes):
            start = int(boundaries[i])
            end = int(boundaries[i + 1])

            # Include extra neighboring rows for Blur
            halo = 7 if filter_name == "Blur" else 0

            section_start = max(0, start - halo)
            section_end = min(height, end + halo)

            section = np.ascontiguousarray(
                frame[section_start:section_end]
            )

            trim_top = start - section_start
            output_rows = end - start

            # One-way pipe to receive the worker result
            parent_conn, child_conn = context.Pipe(
                duplex=False
            )

            process = context.Process(
                target=process_section,
                args=(
                    section,
                    filter_name,
                    trim_top,
                    output_rows,
                    child_conn
                )
            )

            process.start()
            child_conn.close()

            processes.append(process)
            connections.append(parent_conn)

        # Collect results in image-section order
        for connection in connections:
            if not connection.poll(30):
                raise TimeoutError(
                    "Image worker did not respond."
                )

            status, data, pid = connection.recv()

            if status == "error":
                raise RuntimeError(
                    f"Worker {pid} failed: {data}"
                )

            results.append(data)
            worker_pids.add(pid)

        # Join all processes
        for process in processes:
            process.join(timeout=5)

            if process.is_alive():
                raise TimeoutError(
                    "Image worker did not terminate."
                )

            if process.exitcode != 0:
                raise RuntimeError(
                    f"Worker exited with code {process.exitcode}"
                )

        # Reconstruct full image
        processed_frame = np.concatenate(
            results, axis=0
        )

        if processed_frame.shape != frame.shape:
            raise RuntimeError(
                "Incorrect output image dimensions."
            )

        return processed_frame, len(worker_pids)

    finally:
        # Release resources even if a worker fails
        for connection in connections:
            connection.close()

        for process in processes:
            if process.is_alive():
                process.terminate()

            process.join()
