"""
Extra tests for query_optimization branches.
"""

from app import models
from app import query_optimization


def test_paginate_invalid_sort(test_db):
    file_a = models.File(filename="a.txt", storage_key="/tmp/a", file_hash="a" * 64)
    file_b = models.File(filename="b.txt", storage_key="/tmp/b", file_hash="b" * 64)
    test_db.add_all([file_a, file_b])
    test_db.commit()

    query = test_db.query(models.File)
    data, total = query_optimization.paginate(query, page=1, page_size=10, sort_by="unknown", order="desc")
    assert total == 2
    assert len(data) == 2


def test_optimize_file_query_without_relations(test_db):
    query = query_optimization.optimize_file_query(test_db, with_relations=False)
    assert query is not None


def test_get_files_with_pagination_filename_sort(test_db):
    file_a = models.File(filename="a.txt", storage_key="/tmp/a2", file_hash="c" * 64)
    file_b = models.File(filename="b.txt", storage_key="/tmp/b2", file_hash="d" * 64)
    test_db.add_all([file_b, file_a])
    test_db.commit()

    result = query_optimization.get_files_with_pagination(
        test_db,
        page=1,
        page_size=10,
        sort_by="filename",
        order="asc",
    )
    assert result.data[0].filename == "a.txt"

    result_desc = query_optimization.get_files_with_pagination(
        test_db,
        page=1,
        page_size=10,
        sort_by="filename",
        order="desc",
    )
    assert result_desc.data[0].filename == "b.txt"
