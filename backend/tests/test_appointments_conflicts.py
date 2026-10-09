"""Slot-conflict behaviour, which is the core business rule of the app."""

from datetime import timedelta

from app.models import AppointmentStatus
from tests.conftest import appointment_payload


class TestCreateSlotConflict:
    def test_duplicate_slot_for_same_doctor_returns_409(
        self, client, doctor, patient, future_slot, make_appointment
    ):
        make_appointment(doctor, patient, future_slot)
        response = client.post(
            "/api/appointments", json=appointment_payload(doctor, patient, future_slot)
        )
        assert response.status_code == 409
        assert "already has an appointment" in response.json()["detail"]

    def test_same_slot_is_allowed_for_a_different_doctor(
        self, client, doctor, other_doctor, patient, future_slot, make_appointment
    ):
        make_appointment(doctor, patient, future_slot)
        response = client.post(
            "/api/appointments",
            json=appointment_payload(other_doctor, patient, future_slot),
        )
        assert response.status_code == 201

    def test_cancelled_appointment_frees_the_slot(
        self, client, doctor, patient, future_slot, make_appointment
    ):
        row = make_appointment(
            doctor, patient, future_slot, status=AppointmentStatus.CANCELLED
        )
        response = client.post(
            "/api/appointments", json=appointment_payload(doctor, patient, future_slot)
        )
        assert response.status_code == 201
        assert response.json()["id"] != row.id

    def test_terminal_appointment_keeps_blocking_the_slot(
        self, client, doctor, patient, future_slot, make_appointment
    ):
        make_appointment(
            doctor, patient, future_slot, status=AppointmentStatus.COMPLETED
        )
        response = client.post(
            "/api/appointments", json=appointment_payload(doctor, patient, future_slot)
        )
        assert response.status_code == 409


class TestUpdateSlotConflict:
    def test_moving_onto_an_occupied_slot_returns_409(
        self, client, doctor, other_patient, future_slot, make_appointment
    ):
        first = make_appointment(doctor, other_patient, future_slot)
        second = make_appointment(
            doctor, other_patient, future_slot + timedelta(hours=1)
        )
        response = client.put(
            f"/api/appointments/{second.id}",
            json={"scheduled_at": first.scheduled_at.isoformat()},
        )
        assert response.status_code == 409

    def test_appointment_can_be_moved_to_a_free_slot(
        self, client, doctor, patient, future_slot, make_appointment
    ):
        row = make_appointment(doctor, patient, future_slot)
        new_time = future_slot + timedelta(hours=3)
        response = client.put(
            f"/api/appointments/{row.id}", json={"scheduled_at": new_time.isoformat()}
        )
        assert response.status_code == 200
        assert response.json()["scheduled_at"].startswith(
            new_time.strftime("%Y-%m-%dT%H:%M:%S")
        )

    def test_appointment_can_keep_its_own_slot_while_editing_other_fields(
        self, client, doctor, patient, future_slot, make_appointment
    ):
        row = make_appointment(doctor, patient, future_slot)
        response = client.put(
            f"/api/appointments/{row.id}",
            json={"reason": "New reason", "scheduled_at": future_slot.isoformat()},
        )
        assert response.status_code == 200

    def test_cancelled_appointment_can_move_onto_an_occupied_slot(
        self, client, doctor, other_patient, future_slot, make_appointment
    ):
        occupied = make_appointment(doctor, other_patient, future_slot)
        free = make_appointment(
            doctor,
            other_patient,
            future_slot + timedelta(hours=2),
            status=AppointmentStatus.CANCELLED,
        )
        response = client.put(
            f"/api/appointments/{free.id}",
            json={"scheduled_at": occupied.scheduled_at.isoformat()},
        )
        assert response.status_code == 200

    def test_deleting_then_rebooking_the_same_slot_succeeds(
        self, client, doctor, patient, future_slot, make_appointment
    ):
        row = make_appointment(doctor, patient, future_slot)
        assert client.delete(f"/api/appointments/{row.id}").status_code == 204
        response = client.post(
            "/api/appointments", json=appointment_payload(doctor, patient, future_slot)
        )
        assert response.status_code == 201
