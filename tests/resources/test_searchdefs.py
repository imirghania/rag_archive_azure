from docai.resources import searchdefs as sd
from docai.contracts.artifacts import ChunkRecord, NoteRecord


def test_vector_dimension_is_filled_in_and_profile_exists():
    d = sd.index_definition("docs", 1024)
    vec = next(f for f in d["fields"] if f["name"] == "text_vector")
    assert vec["dimensions"] == 1024
    assert vec["vectorSearchProfile"] in {p["name"] for p in d["vectorSearch"]["profiles"]}


def test_every_chunk_field_has_a_place_in_the_index():
    names = sd.field_names(sd.index_definition("docs", 1024))
    # `text` is split by language into text_en / text_ar; trust tiers travel as one JSON string
    mapped = {"text": "text_en", "trust_tiers": "trust_tiers_json"}
    missing = [f for f in ChunkRecord.model_fields if f != "schema_" and mapped.get(f, f) not in names]
    assert not missing, missing


def test_every_note_field_has_a_place_in_the_index():
    names = sd.field_names(sd.index_definition("notes", 1024))
    mapped = {"text": "text_en", "hint_type": "hint_type"}
    missing = [f for f in NoteRecord.model_fields if f != "schema_" and mapped.get(f, f) not in names]
    assert not missing, missing


def test_security_fields_are_filterable_and_keys_are_unique():
    d = sd.index_definition("docs", 1024)
    by = {f["name"]: f for f in d["fields"]}
    assert by["acl_groups"]["filterable"] and by["injection_suspect"]["filterable"]
    assert len(by) == len(d["fields"])
    assert sum(1 for f in d["fields"] if f.get("key")) == 1


def test_synonym_maps_referenced_by_fields_exist():
    maps = {m["name"] for m in sd.synonym_maps()}
    for which in ("docs", "notes"):
        for f in sd.index_definition(which, 1024)["fields"]:
            assert set(f.get("synonymMaps", [])) <= maps


def test_logical_names_resolve_to_the_versioned_indexes():
    assert sd.index_name("docs") == "docs-v1"
    assert sd.index_name("notes") == "notes-v1"


def test_only_searchable_fields_name_an_analyzer():
    """Azure refuses an analyzer on a field that is not searchable (found on the first real run, D47)."""
    for which in ("docs", "notes"):
        for f in sd.index_definition(which, 1024)["fields"]:
            if any(f.get(k) for k in ("analyzer", "searchAnalyzer", "indexAnalyzer")):
                assert f.get("searchable"), f"{which}.{f['name']}"


def test_compression_uses_the_settings_of_the_pinned_api_version():
    """`rescoringOptions` is unknown to 2024-07-01; this version spells it rerankWithOriginalVectors and defaultOversampling."""
    assert sd.API_VERSION == "2024-07-01"
    for which in ("docs", "notes"):
        for c in sd.index_definition(which, 1024)["vectorSearch"]["compressions"]:
            assert "rescoringOptions" not in c and c["rerankWithOriginalVectors"] is True
