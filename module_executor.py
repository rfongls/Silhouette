import threading
from queue import PriorityQueue
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Any


class ModuleExecutor:
    """Execute module functions in priority order using a thread pool."""

    def __init__(self, max_workers: int = 1):
        self.queue: PriorityQueue = PriorityQueue()
        self._counter = 0
        self.pool = ThreadPoolExecutor(max_workers=max_workers)
        self._dispatcher = threading.Thread(target=self._dispatch, daemon=True)
        self._dispatcher.start()

    def submit(self, priority: int, func: Callable[..., Any], *args, **kwargs) -> None:
        self._counter += 1
        self.queue.put((priority, self._counter, func, args, kwargs))

    def _dispatch(self) -> None:
        while True:
            priority, _, func, args, kwargs = self.queue.get()
            if func is None:
                self.queue.task_done()
                break
            self.pool.submit(func, *args, **kwargs)
            self.queue.task_done()

    def shutdown(self, wait: bool = True) -> None:
        self._counter += 1
        self.queue.put((0, self._counter, None, (), {}))
        if wait:
            self._dispatcher.join()
            self.pool.shutdown(wait=True)
