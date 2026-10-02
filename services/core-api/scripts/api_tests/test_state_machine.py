from common import (
    ApiClient,
    Case,
    assert_equal,
    expect_error,
    main_for_suite,
    prepare_claim_in_state,
    transition_claim,
)

SUITE_NAME = "Claim state machine"


def test_valid_approval_flow(api: ApiClient) -> None:
    claim = prepare_claim_in_state(api, "DRAFT")
    claim_id = str(claim["id"])

    submitted = transition_claim(api, claim_id, "submit").json()
    assert_equal(submitted["status"], "SUBMITTED", "DRAFT -> SUBMITTED failed")

    approved = transition_claim(api, claim_id, "approve").json()
    assert_equal(approved["status"], "APPROVED", "SUBMITTED -> APPROVED failed")

    reimbursed = transition_claim(api, claim_id, "reimburse").json()
    assert_equal(reimbursed["status"], "REIMBURSED", "APPROVED -> REIMBURSED failed")


def test_valid_rejection_flow(api: ApiClient) -> None:
    claim = prepare_claim_in_state(api, "SUBMITTED")
    rejected = transition_claim(api, str(claim["id"]), "reject").json()
    assert_equal(rejected["status"], "REJECTED", "SUBMITTED -> REJECTED failed")


def invalid_transition_case(state: str, action: str) -> Case:
    def run(api: ApiClient) -> None:
        claim = prepare_claim_in_state(api, state)
        response = transition_claim(
            api,
            str(claim["id"]),
            action,
            expected_status=409,
        )
        expect_error(response, "INVALID_CLAIM_TRANSITION")

    return Case(f"{state} -> {action.upper()} is rejected", run)


def immutable_patch_case(state: str) -> Case:
    def run(api: ApiClient) -> None:
        claim = prepare_claim_in_state(api, state)
        response = api.request(
            "PATCH",
            f"/claims/{claim['id']}",
            expected_status=409,
            json={"business_purpose": f"Illegal patch while {state}"},
        )
        expect_error(response, "INVALID_CLAIM_TRANSITION")

    return Case(f"{state} claim cannot be patched", run)


INVALID_ACTIONS = {
    "DRAFT": ["approve", "reject", "reimburse"],
    "SUBMITTED": ["submit", "reimburse"],
    "APPROVED": ["submit", "approve", "reject"],
    "REJECTED": ["submit", "approve", "reject", "reimburse"],
    "REIMBURSED": ["submit", "approve", "reject", "reimburse"],
}

CASES = [
    Case("Valid approval/reimbursement path", test_valid_approval_flow),
    Case("Valid rejection path", test_valid_rejection_flow),
]

for source_state, actions in INVALID_ACTIONS.items():
    CASES.extend(invalid_transition_case(source_state, action) for action in actions)

for immutable_state in ["SUBMITTED", "APPROVED", "REJECTED", "REIMBURSED"]:
    CASES.append(immutable_patch_case(immutable_state))


if __name__ == "__main__":
    main_for_suite(SUITE_NAME, CASES)
