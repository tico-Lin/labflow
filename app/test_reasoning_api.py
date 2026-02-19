"""
=============================================================================
Test Reasoning Chain API Endpoints (v0.3)
=============================================================================
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from uuid import UUID

import hashlib

from app.models import User, ReasoningChain, File, Conclusion

def test_create_reasoning_chain(test_client: TestClient, test_db: Session, admin_user: User, auth_headers: dict):
    """
    Test creating a new reasoning chain.
    """
    chain_data = {
        "name": "Test Chain",
        "description": "A test reasoning chain.",
        "nodes": [
            {
                "node_id": "node1",
                "node_type": "data_input",
                "config": {"file_type": "xrd"}
            }
        ]
    }
    
    response = test_client.post("/reasoning/chains", json=chain_data, headers=auth_headers)
    
    assert response.status_code == 201
    
    data = response.json()
    assert data["name"] == "Test Chain"
    assert "id" in data
    
    # Verify the chain is in the database
    chain = test_db.query(ReasoningChain).filter(ReasoningChain.id == UUID(data["id"])).first()
    assert chain is not None
    assert chain.name == "Test Chain"
    assert len(chain.nodes) == 1
    assert chain.created_by_id == admin_user.id


def test_execute_reasoning_chain_end_to_end(
    test_client: TestClient,
    test_db: Session,
    admin_user: User,
    auth_headers: dict,
):
    """End-to-end chain execution via API, including output storage."""
    file_content = b"labflow-performance-sample"
    file_hash = hashlib.sha256(file_content).hexdigest()
    db_file = File(
        filename="sample.txt",
        storage_key=f"/tmp/{file_hash}.bin",
        file_hash=file_hash,
    )
    test_db.add(db_file)
    test_db.commit()
    test_db.refresh(db_file)

    chain_data = {
        "name": "Store Conclusion Chain",
        "description": "Store output as a conclusion",
        "nodes": [
            {
                "node_id": "input_file_id",
                "node_type": "data_input",
                "name": "Input File ID",
                "config": {"source_type": "global", "key_path": "file_id"},
            },
            {
                "node_id": "store_output",
                "node_type": "output",
                "name": "Store Conclusion",
                "inputs": ["input_file_id"],
                "config": {
                    "output_type": "store",
                    "store_target": "conclusion",
                    "file_id_key": "file_id",
                    "content": "Auto conclusion from chain",
                },
            },
        ],
    }

    create_response = test_client.post(
        "/reasoning/chains",
        json=chain_data,
        headers=auth_headers,
    )
    assert create_response.status_code == 201
    chain_id = create_response.json()["id"]

    execute_response = test_client.post(
        f"/reasoning/chains/{chain_id}/execute",
        json={"input_data": {"file_id": db_file.id}},
        headers=auth_headers,
    )
    assert execute_response.status_code == 200
    execution_id = execute_response.json()["execution_id"]

    result_response = test_client.get(
        f"/reasoning/executions/{execution_id}",
        headers=auth_headers,
    )
    assert result_response.status_code == 200
    result_data = result_response.json()
    assert result_data["status"] == "completed"
    assert result_data["results"]["store_output"]["status"] == "completed"

    stored = (
        test_db.query(Conclusion)
        .filter(Conclusion.file_id == db_file.id)
        .first()
    )
    assert stored is not None
    assert "Auto conclusion" in stored.content


def test_reasoning_chain_history(
    test_client: TestClient,
    test_db: Session,
    admin_user: User,
    auth_headers: dict,
):
    chain_data = {
        "name": "History Chain",
        "description": "History test",
        "nodes": [
            {
                "node_id": "node1",
                "node_type": "data_input",
                "config": {"source_type": "constant", "value": 1, "data_type": "integer"},
            },
            {"node_id": "node2", "node_type": "output", "inputs": ["node1"], "config": {"format": "raw"}},
        ],
    }

    create_response = test_client.post(
        "/reasoning/chains",
        json=chain_data,
        headers=auth_headers,
    )
    assert create_response.status_code == 201
    chain_id = create_response.json()["id"]

    execute_response = test_client.post(
        f"/reasoning/chains/{chain_id}/execute",
        json={"input_data": {}},
        headers=auth_headers,
    )
    assert execute_response.status_code == 200

    history_response = test_client.get(
        f"/reasoning/chains/{chain_id}/history",
        headers=auth_headers,
    )
    assert history_response.status_code == 200
    history = history_response.json()
    assert history["chain_id"] == chain_id
    assert history["total_executions"] >= 1
