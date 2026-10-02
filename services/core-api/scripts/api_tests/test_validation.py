from collections.abc import Callable

from common import (
    ApiClient,
    ApiTestFailure,
    Case,
    expect_error,
    main_for_suite,
    make_claim_payload,
)

SUITE_NAME = "Request validation"


def expect_post_validation_error(api: ApiClient, payload: dict[str, object]) -> None:
    response = api.request("POST", "/claims", expected_status=422, json=payload)
    expect_error(response, "VALIDATION_ERROR")


def payload_case(
    name: str,
    mutate: Callable[[dict[str, object]], None],
) -> Case:
    def run(api: ApiClient) -> None:
        payload = make_claim_payload()
        mutate(payload)
        expect_post_validation_error(api, payload)

    return Case(name, run)


def mutate_item(payload: dict[str, object], field: str, value: object) -> None:
    items = payload["items"]
    if not isinstance(items, list) or not items:
        raise ApiTestFailure("Test fixture contains no expense item")
    item = items[0]
    if not isinstance(item, dict):
        raise ApiTestFailure("Test fixture item is not a JSON object")
    item[field] = value


def invalid_path_uuid(api: ApiClient) -> None:
    response = api.request("GET", "/claims/not-a-uuid", expected_status=422)
    expect_error(response, "VALIDATION_ERROR")


def invalid_status_filter(api: ApiClient) -> None:
    response = api.request(
        "GET",
        "/claims",
        expected_status=422,
        params={"status": "NOT_A_STATUS"},
    )
    expect_error(response, "VALIDATION_ERROR")


def invalid_limit_zero(api: ApiClient) -> None:
    response = api.request(
        "GET",
        "/claims",
        expected_status=422,
        params={"limit": 0},
    )
    expect_error(response, "VALIDATION_ERROR")


def invalid_limit_too_large(api: ApiClient) -> None:
    response = api.request(
        "GET",
        "/claims",
        expected_status=422,
        params={"limit": 101},
    )
    expect_error(response, "VALIDATION_ERROR")


def invalid_negative_offset(api: ApiClient) -> None:
    response = api.request(
        "GET",
        "/claims",
        expected_status=422,
        params={"offset": -1},
    )
    expect_error(response, "VALIDATION_ERROR")


CASES = [
    payload_case("Zero amount is rejected", lambda p: mutate_item(p, "amount", 0)),
    payload_case("Negative amount is rejected", lambda p: mutate_item(p, "amount", -1)),
    payload_case(
        "Unknown expense category is rejected",
        lambda p: mutate_item(p, "category", "COFFEE_MAGIC"),
    ),
    payload_case("Two-letter currency is rejected", lambda p: mutate_item(p, "currency", "US")),
    payload_case(
        "Four-letter currency is rejected",
        lambda p: mutate_item(p, "currency", "USDD"),
    ),
    payload_case("Blank business purpose is rejected", lambda p: p.update(business_purpose="   ")),
    payload_case(
        "Blank item description is rejected",
        lambda p: mutate_item(p, "description", "   "),
    ),
    payload_case("Malformed employee UUID is rejected", lambda p: p.update(employee_id="abc")),
    payload_case(
        "Client-supplied total_amount is rejected",
        lambda p: p.update(total_amount="999999.99"),
    ),
    payload_case(
        "Client-supplied status is rejected",
        lambda p: p.update(status="APPROVED"),
    ),
    Case("Malformed claim UUID is rejected", invalid_path_uuid),
    Case("Unknown status filter is rejected", invalid_status_filter),
    Case("limit=0 is rejected", invalid_limit_zero),
    Case("limit>100 is rejected", invalid_limit_too_large),
    Case("negative offset is rejected", invalid_negative_offset),
]


if __name__ == "__main__":
    main_for_suite(SUITE_NAME, CASES)
