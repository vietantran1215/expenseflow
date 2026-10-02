from decimal import Decimal
from uuid import uuid4

from common import (
    ApiClient,
    Case,
    assert_decimal,
    assert_equal,
    assert_true,
    create_claim,
    expect_error,
    get_claim,
    main_for_suite,
    make_item,
    transition_claim,
)

SUITE_NAME = "Happy path"


def test_full_claim_lifecycle(api: ApiClient) -> None:
    employee_id = uuid4()
    manager_id = uuid4()

    claim = create_claim(
        api,
        employee_id=employee_id,
        manager_id=manager_id,
        purpose="Singapore customer workshop",
        items=[
            make_item(
                category="HOTEL",
                description="Hotel",
                amount="300.00",
                currency="usd",
            ),
            make_item(
                category="MEAL",
                description="Client dinner",
                amount="50.00",
            ),
        ],
    )
    claim_id = str(claim["id"])

    assert_equal(claim["status"], "DRAFT", "New claim must start as DRAFT")
    assert_decimal(claim["total_amount"], "350.00", "Server calculated wrong total")
    assert_equal(claim["items"][0]["currency"], "USD", "Currency was not normalized")

    persisted = get_claim(api, claim_id)
    assert_equal(persisted["id"], claim_id, "GET returned a different claim")

    updated = api.request(
        "PATCH",
        f"/claims/{claim_id}",
        expected_status=200,
        json={
            "business_purpose": "Updated Singapore customer workshop",
            "items": [
                make_item(
                    category="HOTEL",
                    description="Hotel",
                    amount="320.00",
                )
            ],
        },
    ).json()
    assert_equal(updated["status"], "DRAFT", "Updating a draft changed its status")
    assert_decimal(updated["total_amount"], "320.00", "Patch did not recalculate total")

    submitted = transition_claim(api, claim_id, "submit").json()
    assert_equal(submitted["status"], "SUBMITTED", "Submit transition failed")

    approved = transition_claim(api, claim_id, "approve").json()
    assert_equal(approved["status"], "APPROVED", "Approve transition failed")

    reimbursed = transition_claim(api, claim_id, "reimburse").json()
    assert_equal(reimbursed["status"], "REIMBURSED", "Reimburse transition failed")

    final_claim = get_claim(api, claim_id)
    assert_equal(final_claim["status"], "REIMBURSED", "Final state was not persisted")
    assert_decimal(final_claim["total_amount"], "320.00", "Final total changed unexpectedly")

    list_response = api.request(
        "GET",
        "/claims",
        expected_status=200,
        params={"employee_id": str(employee_id), "limit": 100, "offset": 0},
    ).json()
    ids = {str(row["id"]) for row in list_response}
    assert_true(claim_id in ids, "Created claim was not returned by employee filter")

    blocked_edit = api.request(
        "PATCH",
        f"/claims/{claim_id}",
        expected_status=409,
        json={"business_purpose": "Illegal edit after reimbursement"},
    )
    expect_error(blocked_edit, "INVALID_CLAIM_TRANSITION")


def test_rejection_path(api: ApiClient) -> None:
    claim = create_claim(api)
    claim_id = str(claim["id"])

    transition_claim(api, claim_id, "submit")
    rejected = transition_claim(api, claim_id, "reject").json()

    assert_equal(rejected["status"], "REJECTED", "Reject transition failed")
    assert_equal(get_claim(api, claim_id)["status"], "REJECTED", "Rejected state was not persisted")


CASES = [
    Case("Create -> edit -> submit -> approve -> reimburse", test_full_claim_lifecycle),
    Case("Create -> submit -> reject", test_rejection_path),
]


if __name__ == "__main__":
    main_for_suite(SUITE_NAME, CASES)
