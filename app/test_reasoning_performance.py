import time


import pytest

from app.reasoning_engine.engine import ReasoningEngine
from app.reasoning_engine.node_types import NodeResult, NodeStatus, NodeType


@pytest.mark.slow
def test_reasoning_engine_parallel_benchmark(monkeypatch):
    """Basic performance baseline for parallel vs sequential execution."""
    sleep_seconds = 0.05

    def slow_execute(node_config, inputs, global_input=None):
        time.sleep(sleep_seconds)
        return NodeResult(
            node_id=node_config.get("node_id"),
            status=NodeStatus.COMPLETED,
            output={"ok": True},
            error=None,
        )

    nodes = [
        {
            "node_id": f"node_{idx}",
            "node_type": NodeType.DATA_INPUT.value,
            "name": f"Node {idx}",
            "config": {"source_type": "constant", "value": idx},
        }
        for idx in range(8)
    ]

    engine_parallel = ReasoningEngine(db_session=None, storage=None, enable_parallel=True, max_workers=4)
    monkeypatch.setattr(engine_parallel.executor, "execute", slow_execute)

    start_parallel = time.perf_counter()
    parallel_result = engine_parallel.execute_chain(nodes=nodes, enable_parallel=True, max_workers=4)
    parallel_elapsed = time.perf_counter() - start_parallel

    engine_sequential = ReasoningEngine(db_session=None, storage=None, enable_parallel=False)
    monkeypatch.setattr(engine_sequential.executor, "execute", slow_execute)

    start_seq = time.perf_counter()
    sequential_result = engine_sequential.execute_chain(nodes=nodes, enable_parallel=False)
    sequential_elapsed = time.perf_counter() - start_seq

    assert parallel_result["status"] == "completed"
    assert sequential_result["status"] == "completed"
    assert parallel_elapsed <= sequential_elapsed


@pytest.mark.slow
def test_reasoning_chain_execution_under_five_seconds():
    """Acceptance check: 10+ nodes execute under 5 seconds."""
    nodes = [
        {
            "node_id": f"input_{idx}",
            "node_type": NodeType.DATA_INPUT.value,
            "name": f"Input {idx}",
            "config": {"source_type": "constant", "value": idx},
        }
        for idx in range(10)
    ]
    nodes.append(
        {
            "node_id": "output_node",
            "node_type": NodeType.OUTPUT.value,
            "name": "Output",
            "inputs": [node["node_id"] for node in nodes],
            "config": {"output_format": "raw"},
        }
    )

    engine = ReasoningEngine(db_session=None, storage=None)
    start_time = time.perf_counter()
    result = engine.execute_chain(nodes=nodes)
    elapsed = time.perf_counter() - start_time

    assert result["status"] == "completed"
    assert elapsed < 5.0


@pytest.mark.slow
def test_health_endpoint_latency_p95(test_client):
    """Acceptance check: /health p95 latency under 200ms."""
    durations = []
    for _ in range(30):
        start_time = time.perf_counter()
        response = test_client.get("/health")
        elapsed = time.perf_counter() - start_time
        assert response.status_code == 200
        durations.append(elapsed)

    durations.sort()
    index = max(0, int(len(durations) * 0.95) - 1)
    p95 = durations[index]

    assert p95 < 0.2
