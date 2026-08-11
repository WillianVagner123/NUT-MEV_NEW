from nutev.global_watch.watch_scoring import score_watch_item


def test_generic_implementation_trial_is_downranked_without_nutev_anchor() -> None:
    score = score_watch_item(
        {"title": "Implementation trial of service delivery in hospital operations"}
    )

    assert score < 0


def test_nutev_anchored_implementation_trial_keeps_operational_priority() -> None:
    generic = score_watch_item(
        {"title": "Implementation trial of service delivery in hospital operations"}
    )
    anchored = score_watch_item(
        {"title": "Implementation trial of nutrition counseling in obesity care"}
    )

    assert anchored > generic
    assert anchored > 0


def test_generic_penalty_does_not_remove_raw_item_or_create_inclusion_decision() -> None:
    item = {
        "title": "Implementation science framework for hospital operations",
        "doi": "10.1234/example",
    }

    _ = score_watch_item(item)

    assert item["doi"] == "10.1234/example"
    assert "include" not in item
    assert "exclude" not in item
