import time
import pytest
from module_executor import ModuleExecutor
from distributed_executor import DistributedExecutor


def test_priority_order():
    results = []
    ex = ModuleExecutor(max_workers=1)
    ex.submit(5, lambda: results.append(1))
    ex.submit(1, lambda: results.append(2))
    ex.submit(3, lambda: results.append(3))
    time.sleep(0.05)
    ex.shutdown()
    assert results == [2, 3, 1]


def test_concurrent_execution():
    results = []
    ex = ModuleExecutor(max_workers=2)
    start = time.time()
    for i in range(4):
        ex.submit(0, lambda i=i: (time.sleep(0.1), results.append(i)))
    time.sleep(0.2)
    ex.shutdown()
    duration = time.time() - start
    assert len(results) == 4
    assert duration < 0.4


def test_distributed_stub():
    dist = DistributedExecutor()
    with pytest.raises(NotImplementedError):
        dist.register_node('localhost')
