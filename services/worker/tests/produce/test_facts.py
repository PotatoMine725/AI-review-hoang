from __future__ import annotations

import pytest

from worker.produce.facts import FactBook, FactError

PKB = {
    "pricing": {
        "free_plan": {
            "origin": "crawled",
            "source_id": "src_01",
            "evidence": "Hoàn toàn Miễn phí",
            "value": True,
        },
        "limit": {"source_id": "src_02", "label": "Tối đa 100 tệp", "value": 100},
    },
    "sizes": [5, 10],
}


def test_bool_leaf_quotes_parent_evidence_and_source() -> None:
    book = FactBook(PKB)
    fid = book.add("pricing.free_plan.value")
    assert fid == "src_01:pricing.free_plan.value"
    assert book.facts[fid] == "Hoàn toàn Miễn phí"  # không tự viết "True"/"Có"


def test_number_leaf_falls_back_to_parent_label() -> None:
    book = FactBook(PKB)
    fid = book.add("pricing.limit.value")
    assert book.facts[fid] == "Tối đa 100 tệp"
    assert fid.startswith("src_02:")


def test_scalar_list_item_without_text_is_rejected() -> None:
    with pytest.raises(FactError, match="không có chữ"):
        FactBook(PKB).add("sizes[0]")


def test_missing_scalar_path_is_rejected() -> None:
    with pytest.raises(FactError, match="không tồn tại"):
        FactBook(PKB).add("pricing.free_plan.khong_co")
