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


def test_first_appearance_and_renumber():
    from app.agent.citations import first_appearance, renumber

    texts = ["Lead [7].", "Then [3][7] and [12]."]
    order = first_appearance(*texts)
    assert order == [7, 3, 12]
    mapping = {old: new for new, old in enumerate(order, start=1)}
    assert [renumber(t, mapping) for t in texts] == ["Lead [1].", "Then [2][1] and [3]."]


def test_build_report_numbers_sources_in_reading_order():
    from app.agent.nodes.synthesizer import build_report
    from app.agent.schemas import Conflict, Position, ReportDraft
    from tests.fakes import source

    registry = SourceRegistry()
    for n in (1, 2, 3, 4):
        registry.register(source(n))
    draft = ReportDraft(
        title="t", executive_summary="Lead [3].", key_findings=["F [1][3]", "Bogus [9]"],
        detailed_analysis="d", conflicting_evidence="c", limitations="l", conclusion="c",
    )
    conflict = Conflict(
        question="q", explanation="e", verdict="v",
        positions=[
            Position(stance="a", source_urls=["https://example.com/3"]),
            Position(stance="b", source_urls=["https://example.com/4"]),
        ],
    )
    report = build_report(draft, registry, [conflict])

    assert report.executive_summary == "Lead [1]."
    assert report.key_findings == ["F [2][1]", "Bogus "]
    assert [(s.id, s.title) for s in report.sources] == [
        (1, "Source 3"), (2, "Source 1"), (3, "Source 4"),  # source 2 was never cited
    ]
    assert [p.source_ids for p in report.conflicts[0].positions] == [[1], [3]]
