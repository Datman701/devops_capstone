"""Request validation: the API should reject bad input with 422, not 500."""

from datetime import datetime, timedelta, timezone


class TestAppointmentValidation:
    def test_missing_required_fields_returns_422(self, client):
        response = client.post("/api/appointments", json={})
        assert response.status_code == 422

    def test_past_scheduled_at_returns_422(
        self, client, doctor, patient, make_appointment
    ):
        past = datetime.now(timezone.utc) - timedelta(days=2)
        response = client.post(
            "/api/appointments",
            json={
                "doctor_id": doctor.id,
                "patient_id": patient.id,
                "scheduled_at": past.isoformat(),
            },
        )
        assert response.status_code == 422
        assert "past" in response.text

    def test_naive_datetime_without_timezone_returns_422(self, client, doctor, patient):
        naive = (datetime.now(timezone.utc) + timedelta(days=5)).replace(tzinfo=None)
        response = client.post(
            "/api/appointments",
            json={
                "doctor_id": doctor.id,
                "patient_id": patient.id,
                "scheduled_at": naive.isoformat(),
            },
        )
        assert response.status_code == 422
        assert "timezone" in response.text

    def test_zero_duration_returns_422(self, client, doctor, patient, future_slot):
        response = client.post(
            "/api/appointments",
            json={
                "doctor_id": doctor.id,
                "patient_id": patient.id,
                "scheduled_at": future_slot.isoformat(),
                "duration_minutes": 0,
            },
        )
        assert response.status_code == 422

    def test_invalid_status_value_returns_422(
        self, client, doctor, patient, future_slot
    ):
        response = client.post(
            "/api/appointments",
            json={
                "doctor_id": doctor.id,
                "patient_id": patient.id,
                "scheduled_at": future_slot.isoformat(),
                "status": "teleported",
            },
        )
        assert response.status_code == 422

    def test_non_integer_doctor_id_returns_422(self, client, patient, future_slot):
        response = client.post(
            "/api/appointments",
            json={
                "doctor_id": "not-a-number",
                "patient_id": patient.id,
                "scheduled_at": future_slot.isoformat(),
            },
        )
        assert response.status_code == 422


class TestDoctorValidation:
    def test_malformed_email_returns_422(self, client):
        response = client.post(
            "/api/doctors",
            json={
                "full_name": "Dr. Nobody",
                "specialty": "Cardiology",
                "email": "not-an-email",
            },
        )
        assert response.status_code == 422

    def test_reserved_test_domain_is_accepted(self, client):
        response = client.post(
            "/api/doctors",
            json={
                "full_name": "Dr. Fixture",
                "specialty": "Neurology",
                "email": "fixture@clinicdesk.test",
            },
        )
        assert response.status_code == 201

    def test_short_name_returns_422(self, client):
        response = client.post(
            "/api/doctors",
            json={"full_name": "D", "specialty": "Cardiology", "email": "a@b.test"},
        )
        assert response.status_code == 422

    def test_negative_consultation_fee_returns_422(self, client):
        response = client.post(
            "/api/doctors",
            json={
                "full_name": "Dr. Negative",
                "specialty": "Cardiology",
                "email": "negative@clinicdesk.test",
                "consultation_fee": -50,
            },
        )
        assert response.status_code == 422

    def test_duplicate_doctor_email_returns_409(self, client, doctor):
        response = client.post(
            "/api/doctors",
            json={
                "full_name": "Dr. Duplicate",
                "specialty": "Cardiology",
                "email": doctor.email,
            },
        )
        assert response.status_code == 409


class TestPatientValidation:
    def test_duplicate_phone_returns_409(self, client, patient):
        response = client.post(
            "/api/patients",
            json={"full_name": "Someone Else", "phone": patient.phone},
        )
        assert response.status_code == 409

    def test_missing_name_returns_422(self, client):
        response = client.post("/api/patients", json={"phone": "+919000000099"})
        assert response.status_code == 422
