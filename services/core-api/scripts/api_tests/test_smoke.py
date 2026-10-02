from common import ApiClient, Case, assert_equal, assert_true, main_for_suite

SUITE_NAME = "Smoke and OpenAPI"

REQUIRED_OPERATIONS = {
    ("post", "/claims"),
    ("get", "/claims"),
    ("get", "/claims/{claim_id}"),
    ("patch", "/claims/{claim_id}"),
    ("post", "/claims/{claim_id}/submit"),
    ("post", "/claims/{claim_id}/approve"),
    ("post", "/claims/{claim_id}/reject"),
    ("post", "/claims/{claim_id}/reimburse"),
}


def test_docs_available(api: ApiClient) -> None:
    response = api.request("GET", "/docs", expected_status=200)
    assert_true("Swagger UI" in response.text, "Swagger UI page was not returned")


def test_openapi_contract(api: ApiClient) -> None:
    body = api.request("GET", "/openapi.json", expected_status=200).json()
    assert_equal(body["info"]["title"], "ExpenseFlow Core API", "Unexpected OpenAPI title")

    operations = {
        (method, path)
        for path, definitions in body["paths"].items()
        for method in definitions
        if method.lower() in {"get", "post", "patch", "put", "delete"}
    }

    missing = REQUIRED_OPERATIONS - operations
    assert_true(not missing, f"OpenAPI is missing required operations: {sorted(missing)}")


CASES = [
    Case("Swagger UI is available", test_docs_available),
    Case("OpenAPI exposes all 8 required operations", test_openapi_contract),
]


if __name__ == "__main__":
    main_for_suite(SUITE_NAME, CASES)
