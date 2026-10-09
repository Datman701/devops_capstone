"""Doctors and patients directory endpoints."""


class TestDoctors:
    def test_list_doctors(self, client, doctor, other_doctor):
        response = client.get("/api/doctors")
        assert response.status_code == 200
        body = response.json()
        assert {row["full_name"] for row in body} == {
            doctor.full_name,
            other_doctor.full_name,
        }

    def test_list_is_sorted_by_name(self, client, doctor, other_doctor):
        names = [row["full_name"] for row in client.get("/api/doctors").json()]
        assert names == sorted(names)

    def test_get_single_doctor(self, client, doctor):
        response = client.get(f"/api/doctors/{doctor.id}")
        assert response.status_code == 200
        assert response.json()["email"] == doctor.email

    def test_unknown_doctor_returns_404(self, client):
        response = client.get("/api/doctors/987654")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_inactive_doctors_hidden_by_default(self, client, doctor, other_doctor, db):
        other_doctor.is_active = False
        db.commit()
        body = client.get("/api/doctors").json()
        assert [row["id"] for row in body] == [doctor.id]

    def test_include_inactive_reveals_all(self, client, doctor, other_doctor, db):
        other_doctor.is_active = False
        db.commit()
        body = client.get("/api/doctors", params={"include_inactive": True}).json()
        assert len(body) == 2


class TestPatients:
    def test_list_patients(self, client, patient, other_patient):
        response = client.get("/api/patients")
        assert response.status_code == 200
        assert len(response.json()) == 2

    def test_get_single_patient(self, client, patient):
        response = client.get(f"/api/patients/{patient.id}")
        assert response.status_code == 200
        assert response.json()["phone"] == patient.phone

    def test_unknown_patient_returns_404(self, client):
        assert client.get("/api/patients/987654").status_code == 404

    def test_create_patient_accepts_optional_email(self, client):
        response = client.post(
            "/api/patients", json={"full_name": "No Email", "phone": "+919111111111"}
        )
        assert response.status_code == 201
        assert response.json()["email"] is None
