"""Listing and filtering behaviour for GET /appointments."""

from datetime import datetime, timedelta, timezone

from app.models import AppointmentStatus


class TestFilters:
    def test_filter_by_status(
        self, client, doctor, patient, future_slot, make_appointment
    ):
        make_appointment(doctor, patient, future_slot)
        make_appointment(
            doctor,
            patient,
            future_slot + timedelta(days=1),
            status=AppointmentStatus.CONFIRMED,
        )
        response = client.get("/api/appointments", params={"status": "confirmed"})
        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["status"] == "confirmed"

    def test_filter_by_doctor(
        self, client, doctor, other_doctor, patient, future_slot, make_appointment
    ):
        mine = make_appointment(doctor, patient, future_slot)
        make_appointment(other_doctor, patient, future_slot + timedelta(hours=1))
        body = client.get("/api/appointments", params={"doctor_id": doctor.id}).json()
        assert [item["id"] for item in body] == [mine.id]

    def test_filter_by_patient(
        self, client, doctor, patient, other_patient, future_slot, make_appointment
    ):
        mine = make_appointment(doctor, patient, future_slot)
        make_appointment(doctor, other_patient, future_slot + timedelta(hours=1))
        body = client.get("/api/appointments", params={"patient_id": patient.id}).json()
        assert [item["id"] for item in body] == [mine.id]

    def test_filter_by_date_range(
        self, client, doctor, patient, future_slot, make_appointment
    ):
        early = make_appointment(doctor, patient, future_slot)
        late = make_appointment(doctor, patient, future_slot + timedelta(days=5))
        body = client.get(
            "/api/appointments",
            params={
                "date_from": (future_slot + timedelta(days=4)).isoformat(),
                "date_to": (future_slot + timedelta(days=6)).isoformat(),
            },
        ).json()
        ids = [item["id"] for item in body]
        assert late.id in ids
        assert early.id not in ids

    def test_upcoming_only_hides_past_appointments(
        self, client, doctor, patient, make_appointment
    ):
        past = make_appointment(
            doctor, patient, datetime.now(timezone.utc) - timedelta(days=3)
        )
        future = make_appointment(
            doctor, patient, datetime.now(timezone.utc) + timedelta(days=3)
        )
        body = client.get("/api/appointments", params={"upcoming_only": True}).json()
        ids = [item["id"] for item in body]
        assert future.id in ids
        assert past.id not in ids

    def test_results_are_ordered_by_schedule_time(
        self, client, doctor, patient, future_slot, make_appointment
    ):
        third = make_appointment(doctor, patient, future_slot + timedelta(hours=4))
        first = make_appointment(doctor, patient, future_slot)
        body = client.get("/api/appointments").json()
        ids = [item["id"] for item in body]
        assert ids.index(first.id) < ids.index(third.id)


class TestPagination:
    def test_limit_caps_result_count(
        self, client, doctor, patient, future_slot, make_appointment
    ):
        for index in range(5):
            make_appointment(doctor, patient, future_slot + timedelta(hours=index))
        body = client.get("/api/appointments", params={"limit": 3}).json()
        assert len(body) == 3

    def test_skip_offsets_results(
        self, client, doctor, patient, future_slot, make_appointment
    ):
        for index in range(5):
            make_appointment(doctor, patient, future_slot + timedelta(hours=index))
        first_page = client.get("/api/appointments", params={"limit": 2}).json()
        second_page = client.get(
            "/api/appointments", params={"limit": 2, "skip": 2}
        ).json()
        assert first_page[0]["id"] != second_page[0]["id"]

    def test_limit_above_maximum_returns_422(self, client):
        assert (
            client.get("/api/appointments", params={"limit": 5000}).status_code == 422
        )

    def test_negative_skip_returns_422(self, client):
        assert client.get("/api/appointments", params={"skip": -1}).status_code == 422


class TestAvailability:
    def test_booked_slot_is_excluded_from_free_slots(
        self, client, doctor, patient, future_slot, make_appointment
    ):
        make_appointment(doctor, patient, future_slot)
        body = client.get(
            f"/api/appointments/{doctor.id}/availability",
            params={"day": future_slot.isoformat()},
        ).json()
        assert future_slot.isoformat() not in body["free_slots"]
        assert body["booked"] == 1

    def test_cancelled_appointment_frees_availability_slot(
        self, client, doctor, patient, future_slot, make_appointment
    ):
        make_appointment(
            doctor, patient, future_slot, status=AppointmentStatus.CANCELLED
        )
        body = client.get(
            f"/api/appointments/{doctor.id}/availability",
            params={"day": future_slot.isoformat()},
        ).json()
        assert future_slot.isoformat() in body["free_slots"]
        assert body["booked"] == 0

    def test_availability_for_unknown_doctor_returns_404(self, client):
        response = client.get("/api/appointments/987654/availability")
        assert response.status_code == 404
