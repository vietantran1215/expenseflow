from uuid import uuid4

from common import ApiClient, Case, assert_equal, assert_true, create_claim, main_for_suite

SUITE_NAME = "Cross-request persistence"


def test_claim_survives_new_http_client(api: ApiClient) -> None:
    employee_id = uuid4()
    created = create_claim(api, employee_id=employee_id)
    claim_id = str(created["id"])

    second_client = ApiClient(api.base_url)
    try:
        second_client.wait_until_ready()

        fetched = second_client.request(
            "GET",
            f"/claims/{claim_id}",
            expected_status=200,
        ).json()
        assert_equal(fetched["id"], claim_id, "New HTTP client could not retrieve created claim")

        listed = second_client.request(
            "GET",
            "/claims",
            expected_status=200,
            params={"employee_id": str(employee_id), "limit": 100, "offset": 0},
        ).json()
        assert_true(
            claim_id in {str(row["id"]) for row in listed},
            "Created claim was not persisted across requests",
        )
    finally:
        second_client.close()


CASES = [
    Case("Created claim is readable from a new HTTP client", test_claim_survives_new_http_client),
]


if __name__ == "__main__":
    main_for_suite(SUITE_NAME, CASES)
