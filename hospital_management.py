"""Small, in-memory hospital model for a software testing assignment.

Uses fictional records only. No external packages or database are required.
Run ``python hospital_management.py`` for a short demonstration.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Prescription:
    medicine: str
    quantity: int
    doctor_id: str
    dispensed: bool = False


@dataclass
class Patient:
    patient_id: str
    name: str
    age: int
    appointments: list[tuple[str, str]] = field(default_factory=list)
    vital_signs: list[dict[str, int | float]] = field(default_factory=list)
    prescriptions: list[Prescription] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.patient_id.strip() or not self.name.strip():
            raise ValueError("Patient ID and name are required")
        if not 0 <= self.age <= 130:
            raise ValueError("Age must be between 0 and 130")

    def add_appointment(self, doctor_id: str, date: str) -> None:
        if not doctor_id.strip() or not date.strip():
            raise ValueError("Doctor ID and appointment date are required")
        appointment = (doctor_id, date)
        if appointment in self.appointments:
            raise ValueError("This appointment already exists")
        self.appointments.append(appointment)

    def get_pending_prescriptions(self) -> list[Prescription]:
        return [p for p in self.prescriptions if not p.dispensed]


@dataclass
class Doctor:
    doctor_id: str
    name: str
    specialty: str

    def schedule_appointment(self, patient: Patient, date: str) -> None:
        if not isinstance(patient, Patient):
            raise TypeError("A Patient object is required")
        patient.add_appointment(self.doctor_id, date)

    def prescribe(self, patient: Patient, medicine: str, quantity: int) -> Prescription:
        if not isinstance(patient, Patient):
            raise TypeError("A Patient object is required")
        if not medicine.strip():
            raise ValueError("Medicine name is required")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
            raise ValueError("Quantity must be a positive integer")
        prescription = Prescription(medicine.strip(), quantity, self.doctor_id)
        patient.prescriptions.append(prescription)
        return prescription


@dataclass
class Nurse:
    nurse_id: str
    name: str

    def record_vitals(
        self, patient: Patient, temperature_c: float, heart_rate: int
    ) -> dict[str, int | float]:
        if not isinstance(patient, Patient):
            raise TypeError("A Patient object is required")
        if not 30 <= temperature_c <= 45:
            raise ValueError("Temperature must be between 30 and 45 °C")
        if isinstance(heart_rate, bool) or not isinstance(heart_rate, int) or not 20 <= heart_rate <= 250:
            raise ValueError("Heart rate must be an integer between 20 and 250")
        reading = {"temperature_c": temperature_c, "heart_rate": heart_rate}
        patient.vital_signs.append(reading)
        return reading


@dataclass
class Pharmacist:
    pharmacist_id: str
    name: str
    inventory: dict[str, int] = field(default_factory=dict)

    def add_stock(self, medicine: str, quantity: int) -> None:
        if not medicine.strip():
            raise ValueError("Medicine name is required")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
            raise ValueError("Stock quantity must be a positive integer")
        key = medicine.strip().lower()
        self.inventory[key] = self.inventory.get(key, 0) + quantity

    def dispense(self, patient: Patient, prescription: Prescription) -> None:
        if not isinstance(patient, Patient) or not isinstance(prescription, Prescription):
            raise TypeError("A Patient and a Prescription are required")
        if not any(item is prescription for item in patient.prescriptions):
            raise ValueError("Prescription does not belong to this patient")
        if prescription.dispensed:
            raise ValueError("Prescription has already been dispensed")
        key = prescription.medicine.lower()
        if self.inventory.get(key, 0) < prescription.quantity:
            raise ValueError("Insufficient medicine in stock")
        self.inventory[key] -= prescription.quantity
        prescription.dispensed = True


if __name__ == "__main__":
    patient = Patient("P101", "Alex Rivera", 30)
    doctor = Doctor("D201", "Dr. Morgan", "General Medicine")
    nurse = Nurse("N301", "Taylor Lee")
    pharmacist = Pharmacist("PH401", "Jordan Kim")

    doctor.schedule_appointment(patient, "2026-11-05 09:00")
    nurse.record_vitals(patient, temperature_c=37.0, heart_rate=72)
    prescription = doctor.prescribe(patient, "ExampleMed", 5)
    pharmacist.add_stock("ExampleMed", 12)
    pharmacist.dispense(patient, prescription)

    print("Patient:", patient.name)
    print("Appointments:", patient.appointments)
    print("Latest vitals:", patient.vital_signs[-1])
    print("Prescription dispensed:", prescription.dispensed)
    print("Remaining stock:", pharmacist.inventory["examplemed"])
