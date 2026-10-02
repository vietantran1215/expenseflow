from uuid import uuid4

from common import ApiClient, Case, expect_error, main_for_suite

SUITE_NAME = "Not-found and error contracts"


def get_missing(api: ApiClient) -> None:
    response = api.request("GET", f"/claims/{uuid4()}", expected_status=404)
    expect_error(response, "CLAIM_NOT_FOUND")


def patch_missing(api: ApiClient) -> None:
    response = api.request(
        "PATCH",
        f"/claims/{uuid4()}",
        expected_status=404,
        json={"business_purpose": "Missing"},
    )
    expect_error(response, "CLAIM_NOT_FOUND")


def missing_action_case(action: str) -> Case:
    def run(api: ApiClient) -> None:
        response = api.request(
            "POST",
            f"/claims/{uuid4()}/{action}",
            expected_status=404,
        )
        expect_error(response, "CLAIM_NOT_FOUND")

    return Case(f"{action} missing claim returns CLAIM_NOT_FOUND", run)


CASES = [
    Case("GET missing claim returns CLAIM_NOT_FOUND", get_missing),
    Case("PATCH missing claim returns CLAIM_NOT_FOUND", patch_missing),
    missing_action_case("submit"),
    missing_action_case("approve"),
    missing_action_case("reject"),
    missing_action_case("reimburse"),
]


if __name__ == "__main__":
    main_for_suite(SUITE_NAME, CASES)
