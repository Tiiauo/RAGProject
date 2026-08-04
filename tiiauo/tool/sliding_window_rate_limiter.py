import time
from collections import deque
from typing import Deque


class SlidingWindowRateLimiter:
    def __init__(self,rpm:int,window:float=60.0):
        if rpm <= 0:
            raise ValueError("rpm 必须大于 0")
        if window <= 0:
            raise ValueError("window 必须大于 0")

        self.rpm = rpm
        self.dq: Deque[float]= deque()
        self.window = window

    def acquire(self) -> None:

        while True:
            now = time.monotonic()

            while self.dq and now - self.dq[0] >= self.window:
                self.dq.popleft()

            if len(self.dq) < self.rpm:
                self.dq.append(now)
                return

            wait_time = self.window - (now - self.dq[0])
            if wait_time > 0:
                time.sleep(max(wait_time,0.01))