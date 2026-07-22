from __future__ import annotations

from copy import deepcopy

from fastapi.testclient import TestClient


def test_health(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "environment": "test"}


def test_import_is_idempotent(client: TestClient, sample_events: dict) -> None:
    first = client.post("/api/v1/events/import", json=sample_events)
    second = client.post("/api/v1/events/import", json=sample_events)

    assert first.status_code == 201
    assert first.json()["total"] == 10
    assert first.json()["imported"] == 10
    assert first.json()["duplicates"] == 0

    assert second.status_code == 201
    assert second.json()["total"] == 10
    assert second.json()["imported"] == 0
    assert second.json()["duplicates"] == 10

    listing = client.get("/api/v1/events")
    assert listing.status_code == 200
    assert len(listing.json()) == 10


def test_import_counts_duplicate_ids_inside_one_payload(
    client: TestClient, sample_events: dict
) -> None:
    payload = deepcopy(sample_events)
    payload["Records"].append(deepcopy(payload["Records"][0]))

    response = client.post("/api/v1/events/import", json=payload)

    assert response.status_code == 201
    assert response.json()["total"] == 11
    assert response.json()["imported"] == 10
    assert response.json()["duplicates"] == 1


def test_get_event_and_not_found(client: TestClient, sample_events: dict) -> None:
    event_id = sample_events["Records"][0]["eventID"]
    client.post("/api/v1/events/import", json=sample_events)

    response = client.get(f"/api/v1/events/{event_id}")
    missing = client.get("/api/v1/events/does-not-exist")

    assert response.status_code == 200
    assert response.json()["event_id"] == event_id
    assert response.json()["raw_event"]["eventID"] == event_id
    assert missing.status_code == 404


def test_import_rejects_event_without_event_id(
    client: TestClient, sample_events: dict
) -> None:
    invalid_payload = deepcopy(sample_events)
    del invalid_payload["Records"][0]["eventID"]

    response = client.post("/api/v1/events/import", json=invalid_payload)

    assert response.status_code == 422


def test_detection_matches_every_ground_truth_label(
    client: TestClient, sample_events: dict, event_labels: dict
) -> None:
    imported = client.post("/api/v1/events/import", json=sample_events)
    assert imported.status_code == 201

    results: dict[str, dict] = {}
    for label in event_labels["labels"]:
        response = client.post(f"/api/v1/events/{label['eventID']}/analyze")
        assert response.status_code == 200
        results[label["eventID"]] = response.json()
        assert response.json()["matched"] is label["expectedMatch"]

    positives = [result for result in results.values() if result["matched"]]
    assert len(positives) == 2
    assert all(result["severity"] == "critical" for result in positives)
    assert all(len(result["evidence"]) == 5 for result in positives)

    incidents = client.get("/api/v1/incidents")
    assert incidents.status_code == 200
    assert len(incidents.json()) == 2
    assert all(item["requires_human_approval"] for item in incidents.json())

    first_positive_id = positives[0]["event_id"]
    repeated = client.post(f"/api/v1/events/{first_positive_id}/analyze")
    incidents_after_repeat = client.get("/api/v1/incidents")

    assert repeated.status_code == 200
    assert repeated.json()["incident_id"] == results[first_positive_id]["incident_id"]
    assert len(incidents_after_repeat.json()) == 2


def test_analyze_unknown_event_returns_not_found(client: TestClient) -> None:
    response = client.post("/api/v1/events/does-not-exist/analyze")

    assert response.status_code == 404


def test_all_rules_and_incident_report(
    client: TestClient, additional_events: dict, additional_event_labels: dict
) -> None:
    imported = client.post("/api/v1/events/import", json=additional_events)
    assert imported.status_code == 201

    incident_ids: list[str] = []
    for label in additional_event_labels["labels"]:
        response = client.post(
            f"/api/v1/events/{label['eventID']}/analyze-all"
        )
        assert response.status_code == 200
        assert [
            finding["rule_id"] for finding in response.json()["findings"]
        ] == label["expectedRuleIds"]
        incident_ids.extend(
            finding["incident_id"] for finding in response.json()["findings"]
        )

    assert len(incident_ids) == 4
    report = client.get(f"/api/v1/incidents/{incident_ids[0]}/report")
    assert report.status_code == 200
    assert report.json()["evidence"]
    assert report.json()["attack_techniques"]
    assert report.json()["recommended_actions"]
    assert report.json()["remediation_state"] == "awaiting_human_approval"


def test_report_for_unknown_incident_returns_not_found(client: TestClient) -> None:
    response = client.get("/api/v1/incidents/does-not-exist/report")

    assert response.status_code == 404


def test_human_approval_is_recorded_without_remediation(
    client: TestClient, sample_events: dict
) -> None:
    client.post("/api/v1/events/import", json=sample_events)
    positive_event_id = "00000000-0000-4000-8000-000000000003"
    analysis = client.post(
        f"/api/v1/events/{positive_event_id}/analyze-all"
    ).json()
    incident_id = analysis["findings"][0]["incident_id"]

    approval = client.post(
        f"/api/v1/incidents/{incident_id}/approval",
        json={
            "decision": "approve",
            "decided_by": "portfolio-reviewer",
            "rationale": "Authorized recovery action after evidence review.",
        },
    )
    duplicate = client.post(
        f"/api/v1/incidents/{incident_id}/approval",
        json={
            "decision": "reject",
            "decided_by": "portfolio-reviewer",
            "rationale": "This second decision must not replace the first.",
        },
    )
    report = client.get(f"/api/v1/incidents/{incident_id}/report")
    audit = client.get(f"/api/v1/incidents/{incident_id}/audit")

    assert approval.status_code == 201
    assert approval.json()["decision"] == "approve"
    assert duplicate.status_code == 409
    assert report.json()["remediation_state"] == "approved_not_executed"
    assert audit.status_code == 200
    assert audit.json()[-1]["action_type"] == "human_approval"
