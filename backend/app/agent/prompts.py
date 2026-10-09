from langchain_core.prompts import ChatPromptTemplate

PLANNER_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are the planning stage of a research agent. Today is {today}.\n\n"
            "Break the user's question into at most {max_topics} research topics that "
            "can be investigated independently and in parallel. Together they should "
            "cover the question; they should not overlap.\n\n"
            "Prefer topics that surface different kinds of evidence: data and "
            "measurements, expert or institutional positions, counter-arguments, "
            "recent developments. Write search queries the way an expert would type "
            "them into a search engine: specific terms, names, and years where useful.\n\n"
            "Use fewer topics for narrow questions. Never pad the plan.",
        ),
        ("human", "{question}"),
    ]
)

RESEARCHER_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are one researcher in a team investigating: {question}\n\n"
            "Your assigned topic: {topic}\n\n"
            "Read the numbered web sources and extract what they establish about "
            "your topic. Every key point must cite the numbers of the sources that "
            "directly support it. Only state what the sources say; do not add "
            "outside knowledge. Keep specific numbers, dates, and names. If sources "
            "disagree, record each position as its own key point. If the sources "
            "say nothing useful about the topic, return an empty list of key points.",
        ),
        ("human", "Sources:\n\n{sources}"),
    ]
)

SYNTHESIZER_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are the lead analyst of a research team. Write the final report "
            "answering: {question}\n\n"
            "You are given the team's evidence, grouped by topic. Each claim carries "
            "citation markers like [3] that refer to the numbered source list.\n\n"
            "Rules:\n"
            "- Ground every factual sentence in the evidence and cite it with the "
            "same markers, e.g. [2] or [2][5]. Never invent a source number.\n"
            "- Answer the question directly; lead with the conclusion.\n"
            "- Weigh the evidence: say where it is strong, thin, or contested.\n"
            "- Write for an informed reader: precise, plain, no filler.",
        ),
        ("human", "Evidence by topic:\n\n{evidence}\n\nSource list:\n\n{sources}"),
    ]
)
