from __future__ import annotations

import argparse
import os
import sys
import time
from dataclasses import dataclass
from decimal import Decimal
from typing import Callable
from uuid import UUID, uuid4

import httpx

DEFAULT_BASE_URL = os.getenv("EXPENSEFLOW_API_URL", "http://127.0.0.1:8000").rstrip("/")
DEFAULT_TIMEOUT = 10.0


class ApiTestFailure(AssertionError):
    """Raised when an API scenario does not satisfy its expected contract."""


class ApiClient:
    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        *,
        timeout: float = DEFAULT_TIMEOUT,
        verbose: bool = False,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.verbose = verbose
        self._client = httpx.Client(base_url=self.base_url, timeout=timeout)

    def close(self) -> None:
        self._client.close()

    def wait_until_ready(self, attempts: int = 40, delay_seconds: float = 0.25) -> None:
        last_error: Exception | None = None

        for _ in range(attempts):
            try:
                response = self._client.get("/openapi.json")
                if response.status_code == 200:
                    return
            except httpx.RequestError as exc:
                last_error = exc

            time.sleep(delay_seconds)

        detail = f": {last_error}" if last_error else ""
        raise ApiTestFailure(
            "Core API is not ready at "
            f"{self.base_url}{detail}\n"
            "Start it first with:\n"
            "  uv run uvicorn app.main:app --reload"
        )

    def request(
        self,
        method: str,
        path: str,
        *,
        expected_status: int,
        json: dict[str, object] | None = None,
        params: dict[str, object] | None = None,
    ) -> httpx.Response:
        if self.verbose:
            print(f"      {method.upper():6} {path}")

        try:
            response = self._client.request(method, path, json=json, params=params)
        except httpx.RequestError as exc:
            raise ApiTestFailure(
                f"{method.upper()} {path} could not reach {self.base_url}: {exc}"
            ) from exc

        if response.status_code != expected_status:
            raise ApiTestFailure(
                f"{method.upper()} {path} expected HTTP {expected_status}, "
                f"got {response.status_code}. Body: {response.text}"
            )

        return response


@dataclass(frozen=True)
class Case:
    name: str
    run: Callable[[ApiClient], None]


@dataclass
class SuiteResult:
    name: str
    passed: int
    failed: int
    failures: list[str]

    @property
    def ok(self) -> bool:
        return self.failed == 0


def assert_equal(actual: object, expected: object, message: str) -> None:
    if actual != expected:
        raise ApiTestFailure(f"{message}. Expected {expected!r}, got {actual!r}")


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise ApiTestFailure(message)


def assert_decimal(actual: object, expected: str, message: str) -> None:
    try:
        actual_decimal = Decimal(str(actual))
    except Exception as exc:
        raise ApiTestFailure(f"{message}. Value is not decimal-like: {actual!r}") from exc

    expected_decimal = Decimal(expected)
    if actual_decimal != expected_decimal:
        raise ApiTestFailure(
            f"{message}. Expected {expected_decimal}, got {actual_decimal}"
        )


def expect_error(response: httpx.Response, code: str) -> dict[str, object]:
    body = response.json()
    assert_equal(body.get("code"), code, "Unexpected API error code")
    assert_true(bool(body.get("message")), "Error response must contain a message")
    return body


def make_item(
    *,
    category: str = "MEAL",
    description: str = "Client lunch",
    amount: str = "25.00",
    currency: str = "USD",
    expense_date: str = "2026-10-01",
) -> dict[str, object]:
    return {
        "category": category,
        "description": description,
        "amount": amount,
        "currency": currency,
        "expense_date": expense_date,
    }


def make_claim_payload(
    *,
    employee_id: UUID | None = None,
    manager_id: UUID | None = None,
    purpose: str | None = None,
    items: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    return {
        "employee_id": str(employee_id or uuid4()),
        "manager_id": str(manager_id or uuid4()),
        "business_purpose": purpose or f"API scenario {uuid4()}",
        "items": [make_item()] if items is None else items,
    }


def create_claim(
    api: ApiClient,
    *,
    employee_id: UUID | None = None,
    manager_id: UUID | None = None,
    purpose: str | None = None,
    items: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    response = api.request(
        "POST",
        "/claims",
        expected_status=201,
        json=make_claim_payload(
            employee_id=employee_id,
            manager_id=manager_id,
            purpose=purpose,
            items=items,
        ),
    )
    return response.json()


def get_claim(api: ApiClient, claim_id: str) -> dict[str, object]:
    return api.request(
        "GET",
        f"/claims/{claim_id}",
        expected_status=200,
    ).json()


def transition_claim(
    api: ApiClient,
    claim_id: str,
    action: str,
    *,
    expected_status: int = 200,
) -> httpx.Response:
    return api.request(
        "POST",
        f"/claims/{claim_id}/{action}",
        expected_status=expected_status,
    )


def prepare_claim_in_state(api: ApiClient, state: str) -> dict[str, object]:
    claim = create_claim(api)
    claim_id = str(claim["id"])

    if state == "DRAFT":
        return claim

    claim = transition_claim(api, claim_id, "submit").json()
    if state == "SUBMITTED":
        return claim

    if state == "REJECTED":
        return transition_claim(api, claim_id, "reject").json()

    claim = transition_claim(api, claim_id, "approve").json()
    if state == "APPROVED":
        return claim

    if state == "REIMBURSED":
        return transition_claim(api, claim_id, "reimburse").json()

    raise ValueError(f"Unsupported state: {state}")


def run_suite(
    name: str,
    cases: list[Case],
    *,
    base_url: str = DEFAULT_BASE_URL,
    timeout: float = DEFAULT_TIMEOUT,
    verbose: bool = False,
) -> SuiteResult:
    print(f"\n=== {name} ===")
    api = ApiClient(base_url, timeout=timeout, verbose=verbose)

    try:
        api.wait_until_ready()
    except ApiTestFailure as exc:
        api.close()
        print(f"[FAIL] preflight: {exc}")
        return SuiteResult(name=name, passed=0, failed=1, failures=[str(exc)])

    passed = 0
    failures: list[str] = []

    try:
        for case in cases:
            started = time.perf_counter()
            try:
                case.run(api)
            except Exception as exc:
                elapsed_ms = (time.perf_counter() - started) * 1000
                failures.append(f"{case.name}: {exc}")
                print(f"[FAIL] {case.name} ({elapsed_ms:.0f} ms)")
                print(f"       {exc}")
            else:
                elapsed_ms = (time.perf_counter() - started) * 1000
                passed += 1
                print(f"[PASS] {case.name} ({elapsed_ms:.0f} ms)")
    finally:
        api.close()

    result = SuiteResult(
        name=name,
        passed=passed,
        failed=len(failures),
        failures=failures,
    )
    print(f"--- {name}: {result.passed} passed, {result.failed} failed")
    return result


def parse_cli(description: str) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"Core API base URL (default: {DEFAULT_BASE_URL})",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT,
        help=f"HTTP timeout in seconds (default: {DEFAULT_TIMEOUT})",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print every HTTP request.",
    )
    return parser.parse_args()


def main_for_suite(name: str, cases: list[Case]) -> None:
    args = parse_cli(f"Run ExpenseFlow API scenario suite: {name}")
    result = run_suite(
        name,
        cases,
        base_url=args.base_url,
        timeout=args.timeout,
        verbose=args.verbose,
    )
    sys.exit(0 if result.ok else 1)
