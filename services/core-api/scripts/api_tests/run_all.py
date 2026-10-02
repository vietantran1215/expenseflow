from common import DEFAULT_BASE_URL, DEFAULT_TIMEOUT, parse_cli, run_suite
from test_business_rules import CASES as BUSINESS_CASES
from test_business_rules import SUITE_NAME as BUSINESS_SUITE
from test_filter_pagination import CASES as FILTER_CASES
from test_filter_pagination import SUITE_NAME as FILTER_SUITE
from test_happy_path import CASES as HAPPY_CASES
from test_happy_path import SUITE_NAME as HAPPY_SUITE
from test_not_found import CASES as NOT_FOUND_CASES
from test_not_found import SUITE_NAME as NOT_FOUND_SUITE
from test_persistence import CASES as PERSISTENCE_CASES
from test_persistence import SUITE_NAME as PERSISTENCE_SUITE
from test_smoke import CASES as SMOKE_CASES
from test_smoke import SUITE_NAME as SMOKE_SUITE
from test_state_machine import CASES as STATE_CASES
from test_state_machine import SUITE_NAME as STATE_SUITE
from test_validation import CASES as VALIDATION_CASES
from test_validation import SUITE_NAME as VALIDATION_SUITE

SUITES = [
    (SMOKE_SUITE, SMOKE_CASES),
    (HAPPY_SUITE, HAPPY_CASES),
    (BUSINESS_SUITE, BUSINESS_CASES),
    (VALIDATION_SUITE, VALIDATION_CASES),
    (STATE_SUITE, STATE_CASES),
    (NOT_FOUND_SUITE, NOT_FOUND_CASES),
    (FILTER_SUITE, FILTER_CASES),
    (PERSISTENCE_SUITE, PERSISTENCE_CASES),
]


def main() -> None:
    args = parse_cli("Run every ExpenseFlow Phase 1 black-box API scenario")

    print("ExpenseFlow Phase 1 API Scenario Test Harness")
    print(f"Base URL: {args.base_url or DEFAULT_BASE_URL}")
    print(f"Timeout: {args.timeout or DEFAULT_TIMEOUT}s")

    results = [
        run_suite(
            name,
            cases,
            base_url=args.base_url,
            timeout=args.timeout,
            verbose=args.verbose,
        )
        for name, cases in SUITES
    ]

    passed = sum(result.passed for result in results)
    failed = sum(result.failed for result in results)

    print("\n========================================")
    print(f"TOTAL: {passed} passed, {failed} failed")
    print("========================================")

    if failed:
        print("\nFailures:")
        for result in results:
            for failure in result.failures:
                print(f"- [{result.name}] {failure}")
        raise SystemExit(1)

    raise SystemExit(0)


if __name__ == "__main__":
    main()
