"""
Fuzzy term catalog used by report generation and scoring hints.
Source tags are embedded in category names for easy provenance.
Feel free to extend/trim this list.
"""

FUZZY_TERMS = {
    "Superlatives (ISO 29148)": ["best", "most"],
    "Subjective Language (ISO 29148)": [
        "user friendly", "easy", "easy to use", "cost effective",
        "efficient", "effective", "reliable", "robust", "secure", "intuitive"
    ],
    "Vague Pronouns (ISO 29148)": ["it", "this", "that", "these", "those"],
    "Ambiguous / General Terms (ISO 29148)": [
        "almost always", "significant", "minimal", "generally", "usually",
        "normal", "appropriate", "adequate"
    ],
    "Open-ended / Non-verifiable (ISO 29148)": [
        "provide support", "as a minimum", "but not limited to",
        "as applicable", "as appropriate"
    ],
    "Comparative Phrases (ISO 29148)": ["better", "improved", "higher quality", "faster"],
    "Loophole Phrases (ISO 29148)": ["if possible", "as appropriate", "as applicable", "when necessary"],
    "Totality Terms (ISO 29148)": ["all", "always", "never", "every"],

    "Weak Phrases (NASA ARM)": [
        "adequate", "as appropriate", "be able to", "be capable of",
        "capability of", "capability to", "effective", "as required",
        "normal", "provide for", "timely", "easy to"
    ],
    "Option Words (NASA ARM)": ["can", "may", "optionally"],
    "Comparative / Subjective (NASA ARM)": ["better", "best", "improved", "more", "less", "greater"],
}
