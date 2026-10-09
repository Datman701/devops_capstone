"""Full CRUD lifecycle for appointments."""

from app.models import AppointmentStatus
from tests.conftest import appointment_payload


class TestCreateAppointment:
    def test_create_returns_201_with_nested_objects(
        self, client, doctor, patient, future_slot
    ):
        response = client.post(
            "/api/appointments",
            json=appointment_payload(doctor, patient, future_slot),
        )
        assert response.status_code == 201
        body = response.json()
        assert body["doctor_id"] == doctor.id
        assert body["patient_id"] == patient.id
        assert body["status"] == "scheduled"
        assert body["doctor"]["full_name"] == doctor.full_name
        assert body["patient"]["full_name"] == patient.full_name

    def test_create_accepts_an_initial_status(
        self, client, doctor, patient, future_slot
    ):
        response = client.post(
            "/api/appointments",
            json=appointment_payload(doctor, patient, future_slot, status="confirmed"),
        )
        assert response.status_code == 201
        assert response.json()["status"] == "confirmed"

    def test_create_rejects_unknown_doctor(self, client, patient, future_slot):
        response = client.post(
            "/api/appointments",
            json={
                "doctor_id": 987654,
                "patient_id": patient.id,
                "scheduled_at": future_slot.isoformat(),
            },
        )
        assert response.status_code == 404
        assert "Doctor" in response.json()["detail"]

    def test_create_rejects_unknown_patient(self, client, doctor, future_slot):
        response = client.post(
            "/api/appointments",
            json={
                "doctor_id": doctor.id,
                "patient_id": 987654,
                "scheduled_at": future_slot.isoformat(),
            },
        )
        assert response.status_code == 404
        assert "Patient" in response.json()["detail"]


class TestReadAppointment:
    def test_list_returns_seeded_appointment(
        self, client, doctor, patient, future_slot, make_appointment
    ):
        row = make_appointment(doctor, patient, future_slot)
        response = client.get("/api/appointments")
        assert response.status_code == 200
        ids = [item["id"] for item in response.json()]
        assert row.id in ids

    def test_get_single_appointment(
        self, client, make_appointment, doctor, patient, future_slot
    ):
        row = make_appointment(doctor, patient, future_slot)
        response = client.get(f"/api/appointments/{row.id}")
        assert response.status_code == 200
        assert response.json()["id"] == row.id

    def test_get_unknown_appointment_returns_404(self, client):
        response = client.get("/api/appointments/999999")
        assert response.status_code == 404


class TestUpdateAppointment:
    def test_update_changes_reason_and_duration(
        self, client, make_appointment, doctor, patient, future_slot
    ):
        row = make_appointment(doctor, patient, future_slot)
        response = client.put(
            f"/api/appointments/{row.id}",
            json={"reason": "Updated reason", "duration_minutes": 45},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["reason"] == "Updated reason"
        assert body["duration_minutes"] == 45

    def test_update_can_reassign_doctor(
        self, client, make_appointment, doctor, other_doctor, patient, future_slot
    ):
        row = make_appointment(doctor, patient, future_slot)
        response = client.put(
            f"/api/appointments/{row.id}", json={"doctor_id": other_doctor.id}
        )
        assert response.status_code == 200
        assert response.json()["doctor_id"] == other_doctor.id

    def test_update_with_empty_body_returns_422(
        self, client, make_appointment, doctor, patient, future_slot
    ):
        row = make_appointment(doctor, patient, future_slot)
        assert client.put(f"/api/appointments/{row.id}", json={}).status_code == 422


class TestDeleteAppointment:
    def test_delete_returns_204_and_row_becomes_cancelled(
        self, client, make_appointment, doctor, patient, future_slot
    ):
        row = make_appointment(doctor, patient, future_slot)
        response = client.delete(f"/api/appointments/{row.id}")
        assert response.status_code == 204
        assert client.get(f"/api/appointments/{row.id}").json()["status"] == "cancelled"

    def test_delete_is_idempotent(
        self, client, make_appointment, doctor, patient, future_slot
    ):
        row = make_appointment(doctor, patient, future_slot)
        assert client.delete(f"/api/appointments/{row.id}").status_code == 204
        assert client.delete(f"/api/appointments/{row.id}").status_code == 204

    def test_delete_unknown_returns_404(self, client):
        assert client.delete("/api/appointments/999999").status_code == 404

    def test_cannot_cancel_a_completed_appointment(
        self, client, make_appointment, doctor, patient, future_slot
    ):
        row = make_appointment(
            doctor, patient, future_slot, status=AppointmentStatus.COMPLETED
        )
        response = client.delete(f"/api/appointments/{row.id}")
        assert response.status_code == 409
        assert "terminal state" in response.json()["detail"]

    def test_cannot_cancel_a_no_show_appointment(
        self, client, make_appointment, doctor, patient, future_slot
    ):
        row = make_appointment(
            doctor, patient, future_slot, status=AppointmentStatus.NO_SHOW
        )
        assert client.delete(f"/api/appointments/{row.id}").status_code == 409

    def test_can_cancel_a_confirmed_appointment(
        self, client, make_appointment, doctor, patient, future_slot
    ):
        row = make_appointment(
            doctor, patient, future_slot, status=AppointmentStatus.CONFIRMED
        )
        assert client.delete(f"/api/appointments/{row.id}").status_code == 204
        assert client.get(f"/api/appointments/{row.id}").json()["status"] == "cancelled"


class TestStatusTransitions:
    def test_scheduled_to_confirmed(
        self, client, make_appointment, doctor, patient, future_slot
    ):
        row = make_appointment(doctor, patient, future_slot)
        response = client.patch(
            f"/api/appointments/{row.id}/status", json={"status": "confirmed"}
        )
        assert response.status_code == 200
        assert response.json()["status"] == "confirmed"

    def test_confirmed_to_completed(
        self, client, make_appointment, doctor, patient, future_slot
    ):
        row = make_appointment(
            doctor, patient, future_slot, status=AppointmentStatus.CONFIRMED
        )
        response = client.patch(
            f"/api/appointments/{row.id}/status", json={"status": "completed"}
        )
        assert response.status_code == 200
        assert response.json()["status"] == "completed"

    def test_terminal_state_cannot_transition(
        self, client, make_appointment, doctor, patient, future_slot
    ):
        row = make_appointment(
            doctor, patient, future_slot, status=AppointmentStatus.COMPLETED
        )
        response = client.patch(
            f"/api/appointments/{row.id}/status", json={"status": "cancelled"}
        )
        assert response.status_code == 409
        assert "terminal state" in response.json()["detail"]

    def test_history_reports_allowed_next_states(
        self, client, make_appointment, doctor, patient, future_slot
    ):
        row = make_appointment(doctor, patient, future_slot)
        body = client.get(f"/api/appointments/{row.id}/history").json()
        assert body["status"] == "scheduled"
        assert set(body["allowed_next"]) == {"confirmed", "cancelled", "no_show"}
