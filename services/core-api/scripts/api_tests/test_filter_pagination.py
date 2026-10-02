from uuid import uuid4

from common import (
    ApiClient,
    Case,
    assert_equal,
    assert_true,
    create_claim,
    main_for_suite,
    transition_claim,
)

SUITE_NAME = "Filtering and pagination"


def test_employee_filter(api: ApiClient) -> None:
    employee_id = uuid4()
    first = create_claim(api, employee_id=employee_id)
    second = create_claim(api, employee_id=employee_id)

    response = api.request(
        "GET",
        "/claims",
        expected_status=200,
        params={"employee_id": str(employee_id), "limit": 100, "offset": 0},
    ).json()

    ids = {str(row["id"]) for row in response}
    assert_equal(ids, {str(first["id"]), str(second["id"])}, "Employee filter returned wrong claims")


def test_status_filter(api: ApiClient) -> None:
    approved = create_claim(api)
    approved_id = str(approved["id"])
    transition_claim(api, approved_id, "submit")
    transition_claim(api, approved_id, "approve")

    create_claim(api)

    response = api.request(
        "GET",
        "/claims",
        expected_status=200,
        params={"status": "APPROVED", "limit": 100, "offset": 0},
    ).json()

    assert_true(response, "Status filter returned no rows")
    assert_true(
        all(row["status"] == "APPROVED" for row in response),
        "Status filter returned a non-APPROVED claim",
    )
    assert_true(
        approved_id in {str(row["id"]) for row in response},
        "Known APPROVED claim was missing from status filter",
    )


def test_combined_filter(api: ApiClient) -> None:
    employee_id = uuid4()
    draft = create_claim(api, employee_id=employee_id)
    approved = create_claim(api, employee_id=employee_id)
    approved_id = str(approved["id"])
    transition_claim(api, approved_id, "submit")
    transition_claim(api, approved_id, "approve")

    response = api.request(
        "GET",
        "/claims",
        expected_status=200,
        params={
            "status": "DRAFT",
            "employee_id": str(employee_id),
            "limit": 100,
            "offset": 0,
        },
    ).json()

    assert_equal(
        {str(row["id"]) for row in response},
        {str(draft["id"])},
        "Combined status + employee filter returned wrong claims",
    )


def test_pagination(api: ApiClient) -> None:
    employee_id = uuid4()
    created_ids = {
        str(create_claim(api, employee_id=employee_id)["id"])
        for _ in range(12)
    }

    page_1 = api.request(
        "GET",
        "/claims",
        expected_status=200,
        params={"employee_id": str(employee_id), "limit": 5, "offset": 0},
    ).json()
    page_2 = api.request(
        "GET",
        "/claims",
        expected_status=200,
        params={"employee_id": str(employee_id), "limit": 5, "offset": 5},
    ).json()
    page_3 = api.request(
        "GET",
        "/claims",
        expected_status=200,
        params={"employee_id": str(employee_id), "limit": 5, "offset": 10},
    ).json()

    assert_equal(len(page_1), 5, "First page size is wrong")
    assert_equal(len(page_2), 5, "Second page size is wrong")
    assert_equal(len(page_3), 2, "Third page size is wrong")

    returned_ids = {
        str(row["id"])
        for page in (page_1, page_2, page_3)
        for row in page
    }
    assert_equal(returned_ids, created_ids, "Pagination lost or duplicated claims")


CASES = [
    Case("Filter by employee_id", test_employee_filter),
    Case("Filter by status", test_status_filter),
    Case("Filter by status + employee_id", test_combined_filter),
    Case("Paginate a 12-claim result set", test_pagination),
]


if __name__ == "__main__":
    main_for_suite(SUITE_NAME, CASES)
