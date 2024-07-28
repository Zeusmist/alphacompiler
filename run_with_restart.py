import sys
import time
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent
import subprocess
import os


class RestartHandler(FileSystemEventHandler):
    def __init__(self):
        self.process = None
        self.last_restart_time = 0
        self.start_process()

    def start_process(self):
        if self.process:
            self.process.terminate()
            self.process.wait()
        self.process = subprocess.Popen([sys.executable, "main.py"])
        self.last_restart_time = time.time()

    def on_modified(self, event):
        if not isinstance(event, FileModifiedEvent):
            return

        current_time = time.time()
        if (
            event.src_path.endswith(".py")
            and os.path.basename(event.src_path) != "run_with_restart.py"
            and (current_time - self.last_restart_time) > 5  # 5-second cooldown
        ):
            print(f"Change detected in {event.src_path}. Restarting...")
            self.start_process()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    path = "."
    event_handler = RestartHandler()
    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
