from app.agent.citations import SourceRegistry, cited_ids, sanitize
from tests.fakes import source


def test_registry_assigns_stable_ids_by_url():
    registry = SourceRegistry()
    assert registry.register(source(1)) == 1
    assert registry.register(source(2)) == 2
    assert registry.register(source(1)) == 1
    assert [s.id for s in registry.all()] == [1, 2]


def test_sanitize_removes_unknown_ids_and_normalises_lists():
    text = "A [1]. B [1, 2]. C [9]. D [2,9]."
    assert sanitize(text, {1, 2}) == "A [1]. B [1][2]. C . D [2]."


def test_sanitize_leaves_non_citation_brackets_alone():
    assert sanitize("see [note] and [1]", {1}) == "see [note] and [1]"


def test_cited_ids_across_texts():
    assert cited_ids("x [1][3]", "y [2, 3]") == {1, 2, 3}
