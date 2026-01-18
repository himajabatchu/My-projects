from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path

from flask import Flask, flash, jsonify, redirect, render_template, request, url_for

app = Flask(__name__)
app.secret_key = "change-me"

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
PATIENTS_FILE = DATA_DIR / "patients.json"
APPOINTMENTS_FILE = DATA_DIR / "appointments.json"
BILLS_FILE = DATA_DIR / "bills.json"

APPOINTMENT_SLOTS = [
    "09:00",
    "09:30",
    "10:00",
    "10:30",
    "11:00",
    "11:30",
    "12:00",
    "12:30",
    "13:00",
    "13:30",
    "14:00",
    "14:30",
    "15:00",
    "15:30",
    "16:00",
    "16:30",
]


def ensure_data_files() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    for path in (PATIENTS_FILE, APPOINTMENTS_FILE, BILLS_FILE):
        if not path.exists():
            path.write_text("[]", encoding="utf-8")


def load_data(path: Path) -> list[dict]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, FileNotFoundError):
        return []


def save_data(path: Path, data: list[dict]) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def find_patient(patients: list[dict], patient_id: str) -> dict | None:
    return next((p for p in patients if p["id"] == patient_id), None)


def parse_date(value: str) -> datetime.date | None:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def find_next_available_slot(
    appointments: list[dict], preferred_date: str
) -> tuple[str, str] | None:
    date = parse_date(preferred_date)
    if not date:
        return None
    while True:
        booked = {a["time"] for a in appointments if a["date"] == date.isoformat()}
        for slot in APPOINTMENT_SLOTS:
            if slot not in booked:
                return date.isoformat(), slot
        date += timedelta(days=1)


@app.route("/")
def index():
    patients = load_data(PATIENTS_FILE)
    appointments = load_data(APPOINTMENTS_FILE)
    bills = load_data(BILLS_FILE)
    totals = {
        "patients": len(patients),
        "appointments": len(appointments),
        "bills": len(bills),
        "unpaid": len([b for b in bills if b["status"] == "unpaid"]),
    }
    return render_template("index.html", totals=totals)


def build_patient(payload: dict) -> tuple[dict | None, str | None]:
    name = str(payload.get("name", "")).strip()
    age_raw = str(payload.get("age", "")).strip()
    gender = str(payload.get("gender", "")).strip()
    contact = str(payload.get("contact", "")).strip()
    if not name or not age_raw:
        return None, "Name and age are required."
    try:
        age = int(age_raw)
    except ValueError:
        return None, "Age must be a number."
    new_patient = {
        "id": f"P-{uuid.uuid4().hex[:8]}",
        "name": name,
        "age": age,
        "gender": gender or "unspecified",
        "contact": contact,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    return new_patient, None


def build_appointment(
    patient_records: list[dict], appointment_records: list[dict], payload: dict
) -> tuple[dict | None, str | None]:
    patient_id = str(payload.get("patient_id", "")).strip()
    preferred_date = str(payload.get("preferred_date", "")).strip()
    reason = str(payload.get("reason", "")).strip()
    if not patient_id or not preferred_date:
        return None, "Patient ID and preferred date are required."
    patient = find_patient(patient_records, patient_id)
    if not patient:
        return None, "Patient not found."
    slot = find_next_available_slot(appointment_records, preferred_date)
    if not slot:
        return None, "Preferred date must be in YYYY-MM-DD format."
    scheduled_date, scheduled_time = slot
    new_appointment = {
        "id": f"A-{uuid.uuid4().hex[:8]}",
        "patient_id": patient_id,
        "patient_name": patient["name"],
        "date": scheduled_date,
        "time": scheduled_time,
        "reason": reason or "general",
        "status": "scheduled",
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    return new_appointment, None


def build_bill(
    patient_records: list[dict], payload: dict
) -> tuple[dict | None, str | None]:
    patient_id = str(payload.get("patient_id", "")).strip()
    description = str(payload.get("description", "")).strip()
    amount_raw = str(payload.get("amount", "")).strip()
    if not patient_id or not amount_raw:
        return None, "Patient ID and amount are required."
    patient = find_patient(patient_records, patient_id)
    if not patient:
        return None, "Patient not found."
    try:
        amount = Decimal(amount_raw)
    except InvalidOperation:
        return None, "Amount must be a valid number."
    new_bill = {
        "id": f"B-{uuid.uuid4().hex[:8]}",
        "patient_id": patient_id,
        "patient_name": patient["name"],
        "description": description or "services",
        "amount": f"{amount:.2f}",
        "status": "unpaid",
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    return new_bill, None


@app.route("/patients", methods=["GET", "POST"])
def patients():
    ensure_data_files()
    patient_records = load_data(PATIENTS_FILE)
    if request.method == "POST":
        new_patient, error = build_patient(request.form)
        if error:
            flash(error, "error")
            return redirect(url_for("patients"))
        patient_records.append(new_patient)
        save_data(PATIENTS_FILE, patient_records)
        flash(f"Patient created: {new_patient['id']}", "success")
        return redirect(url_for("patients"))
    return render_template("patients.html", patients=patient_records)


@app.route("/appointments", methods=["GET", "POST"])
def appointments():
    ensure_data_files()
    patient_records = load_data(PATIENTS_FILE)
    appointment_records = load_data(APPOINTMENTS_FILE)
    if request.method == "POST":
        new_appointment, error = build_appointment(
            patient_records, appointment_records, request.form
        )
        if error:
            flash(error, "error")
            return redirect(url_for("appointments"))
        appointment_records.append(new_appointment)
        save_data(APPOINTMENTS_FILE, appointment_records)
        flash(
            f"Appointment booked for {new_appointment['date']} at {new_appointment['time']}.",
            "success",
        )
        return redirect(url_for("appointments"))
    return render_template(
        "appointments.html",
        appointments=appointment_records,
        patients=patient_records,
        slots=APPOINTMENT_SLOTS,
    )


@app.route("/billing", methods=["GET", "POST"])
def billing():
    ensure_data_files()
    patient_records = load_data(PATIENTS_FILE)
    bill_records = load_data(BILLS_FILE)
    if request.method == "POST":
        new_bill, error = build_bill(patient_records, request.form)
        if error:
            flash(error, "error")
            return redirect(url_for("billing"))
        bill_records.append(new_bill)
        save_data(BILLS_FILE, bill_records)
        flash(f"Bill generated: {new_bill['id']}", "success")
        return redirect(url_for("billing"))
    return render_template("billing.html", bills=bill_records, patients=patient_records)


@app.get("/api/overview")
def api_overview():
    ensure_data_files()
    patients = load_data(PATIENTS_FILE)
    appointments = load_data(APPOINTMENTS_FILE)
    bills = load_data(BILLS_FILE)
    return jsonify(
        {
            "patients": len(patients),
            "appointments": len(appointments),
            "bills": len(bills),
            "unpaid": len([b for b in bills if b["status"] == "unpaid"]),
        }
    )


@app.route("/api/patients", methods=["GET", "POST"])
def api_patients():
    ensure_data_files()
    patient_records = load_data(PATIENTS_FILE)
    if request.method == "POST":
        payload = request.get_json(silent=True) or {}
        new_patient, error = build_patient(payload)
        if error:
            return jsonify({"error": error}), 400
        patient_records.append(new_patient)
        save_data(PATIENTS_FILE, patient_records)
        return jsonify(new_patient), 201
    return jsonify(patient_records)


@app.route("/api/appointments", methods=["GET", "POST"])
def api_appointments():
    ensure_data_files()
    patient_records = load_data(PATIENTS_FILE)
    appointment_records = load_data(APPOINTMENTS_FILE)
    if request.method == "POST":
        payload = request.get_json(silent=True) or {}
        new_appointment, error = build_appointment(
            patient_records, appointment_records, payload
        )
        if error:
            return jsonify({"error": error}), 400
        appointment_records.append(new_appointment)
        save_data(APPOINTMENTS_FILE, appointment_records)
        return jsonify(new_appointment), 201
    return jsonify(appointment_records)


@app.route("/api/bills", methods=["GET", "POST"])
def api_bills():
    ensure_data_files()
    patient_records = load_data(PATIENTS_FILE)
    bill_records = load_data(BILLS_FILE)
    if request.method == "POST":
        payload = request.get_json(silent=True) or {}
        new_bill, error = build_bill(patient_records, payload)
        if error:
            return jsonify({"error": error}), 400
        bill_records.append(new_bill)
        save_data(BILLS_FILE, bill_records)
        return jsonify(new_bill), 201
    return jsonify(bill_records)


if __name__ == "__main__":
    ensure_data_files()
    app.run(debug=True)
