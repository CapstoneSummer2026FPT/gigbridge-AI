from app.services.rag.hotword_resolver import HotwordResolver


def test_layers_prioritize_existing_structured_job_data():
    resolver = HotwordResolver()

    result = resolver.resolve(
        "Backend Engineer",
        ["PostgreSQL", "Custom Integration"],
        job_major="Development & IT",
        job_category="Backend Development",
        job_questions=["How did you use FastAPI with node.js?"],
        phonetic_aliases={"QuickBooks": ["quick books"]},
    )

    assert result == [
        "PostgreSQL",
        "Custom Integration",
        "QuickBooks",
        "Backend Development",
        "Development & IT",
        "Backend Engineer",
        "FastAPI",
        "node.js",
    ]


def test_new_taxonomy_values_work_without_a_category_map():
    resolver = HotwordResolver()

    result = resolver.resolve(
        "Bilingual Bookkeeper",
        ["QuickBooks", "Accounts Payable"],
        job_major="Accounting & Consulting",
        job_category="Bookkeeping",
    )

    assert result == [
        "QuickBooks",
        "Accounts Payable",
        "Bookkeeping",
        "Accounting & Consulting",
        "Bilingual Bookkeeper",
    ]


def test_terms_are_deduplicated_and_bounded_across_layers():
    resolver = HotwordResolver(max_terms=4)

    result = resolver.resolve(
        "React Engineer",
        ["React", "TypeScript"],
        job_major="Development",
        job_category="React",
        phonetic_aliases={"TypeScript": ["type script"]},
    )

    assert result == ["React", "TypeScript", "Development", "React Engineer"]
