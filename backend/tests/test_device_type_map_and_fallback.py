"""Device-type translation (BSS ids <-> OSS names) and the stored-data fallback.

Both exist because OSS and BSS disagree about what a device type *is*:

  * BSS `device_type.id` is a primary key in insertion order;
  * OSS has no type table and derives a positional ordinal from the sorted
    distinct names, so BSS 2 = AirQ while OSS 2 = IntelliHub.

Name is therefore the only stable key, and it is spelled differently on each
side ("Intellihub" vs "IntelliHub"), so matching must be case-insensitive.

These tests read BSS reference rows; nothing is written.
"""

from __future__ import annotations

import pytest

from app.db.session import SessionLocal
from app.services import device_type_map as dtm
from app.services import oss_fallback


@pytest.fixture(scope="module")
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


# ---------------------------------------------------------------------------
# device type translation
# ---------------------------------------------------------------------------

def test_bss_types_are_keyed_by_casefolded_name(db):
    names = dtm.by_name(db)
    assert names, "BSS device_type must be seeded for this suite"
    for key in names:
        assert key == key.casefold()


def test_oss_spelling_matches_bss_case_insensitively(db):
    """The exact mismatch that returned zero devices before this change."""
    names = dtm.by_name(db)
    if "intellihub" not in names:
        pytest.skip("BSS has no Intellihub type in this dataset")
    # OSS spells it "IntelliHub"; BSS "Intellihub". Both must resolve.
    assert names["IntelliHub".casefold()].id == names["Intellihub".casefold()].id


def test_name_for_bss_id_round_trips(db):
    for type_id, bss in dtm.by_id(db).items():
        assert dtm.name_for_bss_id(db, type_id) == bss.name
        assert dtm.name_for_bss_id(db, str(type_id)) == bss.name


def test_name_for_unknown_or_malformed_id_is_none(db):
    assert dtm.name_for_bss_id(db, 999999) is None
    assert dtm.name_for_bss_id(db, "not-a-number") is None


def test_item_is_rewritten_to_bss_id_and_canonical_name(db):
    names = dtm.by_name(db)
    bss = names["airq"] if "airq" in names else next(iter(names.values()))
    # An OSS item: positional id, OSS spelling, no short code.
    item = {
        "device_type": 999,
        "device_type_name": bss.name.upper(),
        "device_short_code": None,
    }
    out = dtm.apply_to_item(item, names)
    assert out["device_type"] == bss.id
    assert out["device_type_name"] == bss.name          # canonical BSS spelling
    assert out["device_short_code"] == bss.short_code   # BSS supplies what OSS lacks


def test_unknown_type_keeps_its_name_but_drops_the_ordinal(db):
    """A type OSS knows and BSS does not must not borrow a BSS id."""
    out = dtm.apply_to_item(
        {"device_type": 3, "device_type_name": "SomeFutureSensor"}, dtm.by_name(db)
    )
    assert out["device_type"] is None
    assert out["device_type_name"] == "SomeFutureSensor"


def test_apply_to_body_walks_nested_items(db):
    names = dtm.by_name(db)
    bss = next(iter(names.values()))
    body = {"items": [{"device_type": 99, "device_type_name": bss.name.swapcase()}]}
    out = dtm.apply_to_body(db, body)
    assert out["items"][0]["device_type"] == bss.id


def test_device_types_page_is_renumbered_to_bss_ids(db):
    """`/device-types` must hand the frontend the ids it already stores."""
    by_id = dtm.by_id(db)
    oss_page = {
        "items": [
            {"id": i + 1, "name": t.name.upper(), "device_short_code": None}
            for i, t in enumerate(by_id.values())
        ],
        "page": 1, "page_size": 20, "total": len(by_id),
    }
    out = dtm.device_types_as_bss(db, oss_page)
    returned = {i["id"]: i["name"] for i in out["items"]}
    assert returned == {t.id: t.name for t in by_id.values()}
    assert [i["id"] for i in out["items"]] == sorted(returned)


# ---------------------------------------------------------------------------
# stored-data fallback
# ---------------------------------------------------------------------------

def test_every_oss_list_prefix_has_a_stored_form():
    from app.core.oss_routes import OSS_READ_PREFIXES

    missing = [p for p in OSS_READ_PREFIXES if not oss_fallback.supports(p)]
    assert not missing, f"no stored fallback registered for {missing}"


def test_detail_paths_have_no_stored_form():
    # An OSS id does not address a BSS row; see oss_fallback module docstring.
    assert not oss_fallback.supports("/devices/abc")
    assert not oss_fallback.supports("/alerts/1/incidents")


def test_stored_page_shape_matches_the_live_contract(db):
    body = oss_fallback.serve(db, "/devices", [("page", "1"), ("page_size", "2")])
    assert set(body) >= {"items", "page", "page_size", "total"}
    assert body["page"] == 1 and body["page_size"] == 2
    assert len(body["items"]) <= 2


def test_filters_are_coerced_from_the_service_annotations(db):
    """Services use `from __future__ import annotations`; hints must resolve."""
    all_rows = oss_fallback.serve(db, "/devices", [("page_size", "100")])
    typed = oss_fallback.serve(db, "/devices", [("device_type", "2"), ("page_size", "100")])
    assert typed["total"] <= all_rows["total"]
    for item in typed["items"]:
        assert item["device_type"] == 2


def test_uuid_filter_is_really_applied(db):
    """A string that never became a UUID would silently match nothing."""
    page = oss_fallback.serve(db, "/devices", [("page_size", "100")])
    with_room = [i for i in page["items"] if i.get("amenity_id")]
    if not with_room:
        pytest.skip("no device carries an amenity_id in this dataset")
    amenity_id = with_room[0]["amenity_id"]
    filtered = oss_fallback.serve(db, "/devices", [("amenity_id", amenity_id)])
    assert filtered["total"] >= 1
    assert all(i["amenity_id"] == amenity_id for i in filtered["items"])


def test_unparseable_filter_is_rejected_not_ignored(db):
    # Ignoring it would return the unfiltered list and call it a match.
    with pytest.raises(oss_fallback.FallbackFilterError):
        oss_fallback.serve(db, "/devices", [("amenity_id", "not-a-uuid")])


def test_oss_only_filters_are_dropped(db):
    """`device_ids` / `q` exist only on the OSS side and must not leak through."""
    plain = oss_fallback.serve(db, "/devices", [("page_size", "100")])
    with_oss_only = oss_fallback.serve(
        db, "/devices", [("device_ids", "a,b"), ("q", "zzz"), ("page_size", "100")]
    )
    assert with_oss_only["total"] == plain["total"]
