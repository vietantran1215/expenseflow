from common import (
    ApiClient,
    Case,
    assert_decimal,
    assert_equal,
    create_claim,
    expect_error,
    main_for_suite,
    make_item,
    transition_claim,
)

SUITE_NAME = "Business rules"


def test_total_is_server_calculated(api: ApiClient) -> None:
    claim = create_claim(
        api,
        items=[
            make_item(amount="10.25"),
            make_item(category="TRANSPORT", amount="20.50"),
        ],
    )
    assert_decimal(claim["total_amount"], "30.75", "Server did not sum expense items")


def test_patch_recalculates_total(api: ApiClient) -> None:
    claim = create_claim(api, items=[make_item(amount="10.00")])
    claim_id = str(claim["id"])

    updated = api.request(
        "PATCH",
        f"/claims/{claim_id}",
        expected_status=200,
        json={
            "items": [
                make_item(amount="12.50"),
                make_item(category="HOTEL", amount="100.00"),
            ]
        },
    ).json()

    assert_decimal(updated["total_amount"], "112.50", "Patch did not recalculate total")


def test_empty_draft_cannot_be_submitted(api: ApiClient) -> None:
    claim = create_claim(api, items=[])
    claim_id = str(claim["id"])

    assert_equal(claim["status"], "DRAFT", "Empty claim should still be created as DRAFT")
    assert_decimal(claim["total_amount"], "0.00", "Empty draft must have zero total")

    response = transition_claim(api, claim_id, "submit", expected_status=422)
    expect_error(response, "CLAIM_ITEMS_REQUIRED")


def test_currency_is_normalized(api: ApiClient) -> None:
    claim = create_claim(api, items=[make_item(currency="vnd")])
    assert_equal(claim["items"][0]["currency"], "VND", "Currency was not normalized to uppercase")


CASES = [
    Case("Claim total is calculated by the server", test_total_is_server_calculated),
    Case("Draft patch recalculates total", test_patch_recalculates_total),
    Case("Empty draft cannot be submitted", test_empty_draft_cannot_be_submitted),
    Case("Currency is normalized", test_currency_is_normalized),
]


if __name__ == "__main__":
    main_for_suite(SUITE_NAME, CASES)
