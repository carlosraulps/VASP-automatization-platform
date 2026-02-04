import sys
import time
import threading
import itertools

class Thinking:
    """
    Context manager to display a spinner while a long-running process executes.
    Usage:
        with Thinking("Analyzing"):
            do_something()
    """
    def __init__(self, message: str = "Thinking", delay: float = 0.1):
        self.message = message
        self.delay = delay
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._spin)

    def _spin(self):
        spinner = itertools.cycle(['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'])
        while not self.stop_event.is_set():
            sys.stdout.write(f"\r{next(spinner)} {self.message}...")
            sys.stdout.flush()
            time.sleep(self.delay)
    
    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.stop_event.set()
        self.thread.join()
        # Clean up line
        sys.stdout.write(f"\r{' ' * (len(self.message) + 10)}\r")
        sys.stdout.flush()
