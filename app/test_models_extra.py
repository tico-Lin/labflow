"""
Extra model validation coverage.
"""

import pytest

from app import models


def test_reasoning_chain_validation_errors(test_db):
    with pytest.raises(ValueError):
        models.ReasoningChain(name=" ", description="", nodes=[{}])

    with pytest.raises(ValueError):
        models.ReasoningChain(name="chain", description="", nodes="bad")

    with pytest.raises(ValueError):
        models.ReasoningChain(name="chain", description="", nodes=[])


def test_reasoning_node_validation_errors():
    with pytest.raises(ValueError):
        models.ReasoningNode(
            chain_id=None,
            node_id=" ",
            node_type="type",
            name="node",
        )

    with pytest.raises(ValueError):
        models.ReasoningNode(
            chain_id=None,
            node_id="node",
            node_type=" ",
            name="node",
        )

    with pytest.raises(ValueError):
        models.ReasoningNode(
            chain_id=None,
            node_id="node",
            node_type="type",
            name=" ",
        )


def test_reasoning_execution_status_validation():
    with pytest.raises(ValueError):
        models.ReasoningExecution(status="bad")


def test_script_name_validation():
    with pytest.raises(ValueError):
        models.Script(name=" ", content="x")
