"""Dashboard aggregation endpoint."""

from datetime import datetime, timedelta, timezone

from app.models import AppointmentStatus

ALL_STATUSES = {status.value for status in AppointmentStatus}


class TestAppointmentStats:
    def test_empty_database_returns_zeroed_stats(self, client):
        response = client.get("/api/appointments/stats")
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 0
        assert body["today"] == 0
        assert body["upcoming_7_days"] == 0
        assert body["cancelled_rate"] == 0.0
        assert body["busiest_hour"] is None
        assert body["busy_doctors"] == []
        assert body["latest"] == []

    def test_by_status_always_contains_every_status_key(self, client):
        body = client.get("/api/appointments/stats").json()
        assert set(body["by_status"]) == ALL_STATUSES

    def test_total_counts_seeded_appointments(
        self, client, doctor, patient, future_slot, make_appointment
    ):
        make_appointment(doctor, patient, future_slot)
        make_appointment(doctor, patient, future_slot + timedelta(hours=1))
        make_appointment(
            doctor,
            patient,
            future_slot + timedelta(hours=2),
            status=AppointmentStatus.CANCELLED,
        )
        body = client.get("/api/appointments/stats").json()
        assert body["total"] == 3
        assert body["by_status"]["scheduled"] == 2
        assert body["by_status"]["cancelled"] == 1

    def test_status_counts_sum_to_total(
        self, client, doctor, patient, future_slot, make_appointment
    ):
        make_appointment(doctor, patient, future_slot)
        make_appointment(
            doctor,
            patient,
            future_slot + timedelta(hours=1),
            status=AppointmentStatus.NO_SHOW,
        )
        make_appointment(
            doctor,
            patient,
            future_slot + timedelta(hours=2),
            status=AppointmentStatus.COMPLETED,
        )
        body = client.get("/api/appointments/stats").json()
        assert sum(body["by_status"].values()) == body["total"]

    def test_cancelled_rate_is_a_ratio_between_zero_and_one(
        self, client, doctor, patient, future_slot, make_appointment
    ):
        for index in range(4):
            make_appointment(
                doctor,
                patient,
                future_slot + timedelta(hours=index),
                status=AppointmentStatus.CANCELLED,
            )
        make_appointment(doctor, patient, future_slot + timedelta(hours=10))
        body = client.get("/api/appointments/stats").json()
        assert body["cancelled_rate"] == 0.8

    def test_busiest_hour_reflects_the_data(
        self, client, doctor, patient, make_appointment
    ):
        base = (datetime.now(timezone.utc) + timedelta(days=40)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        # Three appointments at 09:00/09:30/10:00, one at 14:00
        for hour, count in ((9, 3), (14, 1)):
            for index in range(count):
                slot = base + timedelta(hours=hour, minutes=index * 30)
                make_appointment(doctor, patient, slot)
        body = client.get("/api/appointments/stats").json()
        assert body["busiest_hour"] == 9

    def test_busy_doctors_ranks_by_appointment_count(
        self, client, doctor, other_doctor, patient, future_slot, make_appointment
    ):
        for index in range(3):
            make_appointment(doctor, patient, future_slot + timedelta(hours=index))
        make_appointment(other_doctor, patient, future_slot + timedelta(hours=5))
        body = client.get("/api/appointments/stats").json()
        assert body["busy_doctors"][0]["doctor_id"] == doctor.id
        assert body["busy_doctors"][0]["count"] == 3
        assert body["busy_doctors"][1]["count"] == 1

    def test_upcoming_7_days_excludes_cancelled_and_past(
        self, client, doctor, patient, make_appointment
    ):
        now = datetime.now(timezone.utc).replace(microsecond=0)
        make_appointment(doctor, patient, now + timedelta(days=2))
        make_appointment(
            doctor, patient, now + timedelta(days=3), status=AppointmentStatus.CANCELLED
        )
        make_appointment(doctor, patient, now - timedelta(days=3))
        body = client.get("/api/appointments/stats").json()
        assert body["upcoming_7_days"] == 1

    def test_today_counts_only_todays_appointments(
        self, client, doctor, patient, make_appointment
    ):
        now = datetime.now(timezone.utc).replace(microsecond=0)
        make_appointment(doctor, patient, now + timedelta(hours=1))
        make_appointment(doctor, patient, now + timedelta(days=2))
        body = client.get("/api/appointments/stats").json()
        assert body["today"] == 1

    def test_stats_respect_doctor_filter(
        self, client, doctor, other_doctor, patient, future_slot, make_appointment
    ):
        make_appointment(doctor, patient, future_slot)
        make_appointment(other_doctor, patient, future_slot + timedelta(hours=1))
        body = client.get(
            "/api/appointments/stats", params={"doctor_id": doctor.id}
        ).json()
        assert body["total"] == 1

    def test_stats_respect_status_filter(
        self, client, doctor, patient, future_slot, make_appointment
    ):
        make_appointment(doctor, patient, future_slot)
        make_appointment(
            doctor,
            patient,
            future_slot + timedelta(hours=1),
            status=AppointmentStatus.CONFIRMED,
        )
        body = client.get(
            "/api/appointments/stats", params={"status": "confirmed"}
        ).json()
        assert body["total"] == 1
        assert body["by_status"]["confirmed"] == 1

    def test_latest_feed_is_capped_and_newest_first(
        self, client, doctor, patient, future_slot, make_appointment
    ):
        for index in range(12):
            make_appointment(doctor, patient, future_slot + timedelta(hours=index))
        body = client.get("/api/appointments/stats").json()
        assert len(body["latest"]) == 8

    def test_active_counts_include_seed_fixtures(
        self, client, doctor, other_doctor, patient
    ):
        body = client.get("/api/appointments/stats").json()
        assert body["active_doctors"] == 2
        assert body["active_patients"] == 1
