from app.agent.evidence import quote_in_sources, resolve_evidence
from app.agent.schemas import KeyPoint, Source, TopicAnalysis

SOURCE = Source(
    url="https://example.com/a",
    title="A",
    content="In 2023, the trial enrolled 1,204 adults.  Weight loss averaged 4.2 kg over “12 months”.",
)


def test_exact_quote_is_verified():
    assert quote_in_sources("the trial enrolled 1,204 adults", [SOURCE])


def test_case_whitespace_and_quote_marks_are_ignored():
    assert quote_in_sources('"Weight loss averaged 4.2 kg over 12 months"', [SOURCE])
    assert quote_in_sources("THE TRIAL   enrolled 1,204 adults", [SOURCE])


def test_ellipsis_fragments_must_all_appear():
    assert quote_in_sources("the trial enrolled … averaged 4.2 kg", [SOURCE])
    assert not quote_in_sources("the trial enrolled ... averaged 9 kg", [SOURCE])


def test_paraphrase_is_not_verified():
    assert not quote_in_sources("about 1,200 adults took part", [SOURCE])
    assert not quote_in_sources("   ", [SOURCE])


def test_resolve_evidence_maps_ids_and_flags_unverified_quotes():
    analysis = TopicAnalysis(
        summary="s",
        key_points=[
            KeyPoint(statement="real", quote="enrolled 1,204 adults", source_ids=[1, 1]),
            KeyPoint(statement="invented", quote="enrolled 5,000 adults", source_ids=[1]),
            KeyPoint(statement="uncited", quote="x", source_ids=[3]),
        ],
    )
    evidence = resolve_evidence(analysis, [SOURCE])
    assert [(e.statement, e.quote_verified) for e in evidence] == [
        ("real", True),
        ("invented", False),
    ]
    assert evidence[0].source_urls == [SOURCE.url]
