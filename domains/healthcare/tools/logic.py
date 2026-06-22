"""Healthcare domain tools (mock implementations for demo)."""

from __future__ import annotations

import json
import random
from datetime import datetime
from typing import List


# Mock patient database
MOCK_PATIENT_DB = {
    "12345": {
        "patient_id": "12345",
        "name": "John Doe",
        "age": 45,
        "gender": "Male",
        "blood_type": "O+",
        "allergies": ["Penicillin", "Shellfish"],
        "current_medications": ["Metformin 500mg", "Lisinopril 10mg"],
        "conditions": ["Type 2 Diabetes", "Hypertension"],
        "last_visit": "2024-10-15",
        "primary_physician": "Dr. Emily Smith",
    },
    "67890": {
        "patient_id": "67890",
        "name": "Jane Smith",
        "age": 32,
        "gender": "Female",
        "blood_type": "A+",
        "allergies": ["None"],
        "current_medications": ["Levothyroxine 50mcg"],
        "conditions": ["Hypothyroidism"],
        "last_visit": "2024-11-01",
        "primary_physician": "Dr. Michael Johnson",
    },
    "P-00123": {
        "patient_id": "P-00123",
        "name": "Robert Williams",
        "age": 58,
        "gender": "Male",
        "blood_type": "B+",
        "allergies": ["Sulfa drugs"],
        "current_medications": ["Atorvastatin 20mg", "Aspirin 81mg", "Lisinopril 20mg"],
        "conditions": ["High Cholesterol", "Hypertension", "Coronary Artery Disease"],
        "last_visit": "2024-09-20",
        "primary_physician": "Dr. Sarah Chen",
    },
}


# Mock medication database
MOCK_MEDICATION_DB = {
    "lisinopril": {
        "name": "Lisinopril",
        "drug_class": "ACE Inhibitor",
        "uses": "Treatment of high blood pressure (hypertension) and heart failure",
        "common_dosages": ["5mg", "10mg", "20mg", "40mg"],
        "side_effects": ["Dry cough", "Dizziness", "Headache", "Fatigue", "Nausea"],
        "warnings": "Do not use if pregnant. May cause dizziness.",
    },
    "metformin": {
        "name": "Metformin",
        "drug_class": "Biguanide",
        "uses": "Treatment of type 2 diabetes mellitus",
        "common_dosages": ["500mg", "850mg", "1000mg"],
        "side_effects": ["Nausea", "Diarrhea", "Stomach upset", "Metallic taste"],
        "warnings": "Take with food. Avoid if you have severe kidney disease.",
    },
    "aspirin": {
        "name": "Aspirin",
        "drug_class": "NSAID / Antiplatelet",
        "uses": "Pain relief, fever reduction, heart attack/stroke prevention",
        "common_dosages": ["81mg", "325mg", "500mg"],
        "side_effects": ["Stomach upset", "Heartburn", "Nausea", "Easy bruising"],
        "warnings": "Take with food or milk. Do not give to children with viral infections.",
    },
    "atorvastatin": {
        "name": "Atorvastatin",
        "drug_class": "Statin",
        "uses": "Treatment of high cholesterol and triglycerides",
        "common_dosages": ["10mg", "20mg", "40mg", "80mg"],
        "side_effects": ["Muscle pain", "Headache", "Nausea"],
        "warnings": "Avoid grapefruit juice. Report unexplained muscle pain.",
    },
    "levothyroxine": {
        "name": "Levothyroxine",
        "drug_class": "Thyroid Hormone",
        "uses": "Treatment of hypothyroidism",
        "common_dosages": ["25mcg", "50mcg", "75mcg", "100mcg"],
        "side_effects": ["Insomnia", "Nervousness", "Weight changes"],
        "warnings": "Take on empty stomach 30–60 minutes before breakfast.",
    },
}


def get_patient_info(patient_id: str) -> str:
    """Retrieve patient information."""
    patient = MOCK_PATIENT_DB.get(patient_id)
    if not patient:
        return json.dumps({"error": f"Patient '{patient_id}' not found"})
    return json.dumps(patient)


def schedule_appointment(
    patient_id: str,
    provider_name: str,
    appointment_date: str,
    appointment_time: str,
    reason: str,
) -> str:
    """Schedule a medical appointment for a patient."""
    if patient_id not in MOCK_PATIENT_DB:
        return json.dumps({"error": f"Patient '{patient_id}' not found"})

    confirmation = {
        "confirmation_id": f"APT-{random.randint(100000, 999999)}",
        "patient_id": patient_id,
        "provider_name": provider_name,
        "appointment_date": appointment_date,
        "appointment_time": appointment_time,
        "reason": reason,
        "status": "scheduled",
        "created_at": datetime.utcnow().isoformat() + "Z",
    }
    return json.dumps(confirmation)


def get_medication_info(medication_name: str) -> str:
    """Return medication details."""
    key = (medication_name or "").strip().lower()
    med = MOCK_MEDICATION_DB.get(key)
    if not med:
        return json.dumps({"error": f"Medication '{medication_name}' not found"})
    return json.dumps(med)


def check_drug_interactions(medications: List[str]) -> str:
    """Check for potential interactions between multiple medications (mock)."""
    meds = [str(m).strip() for m in (medications or []) if str(m).strip()]
    normalized = [m.lower() for m in meds]

    interactions = []
    # Very small mock rules for demo purposes
    if "lisinopril" in normalized and "aspirin" in normalized:
        interactions.append(
            {
                "pair": ["Lisinopril", "Aspirin"],
                "severity": "moderate",
                "note": "NSAIDs like aspirin can reduce the antihypertensive effect of ACE inhibitors in some patients.",
            }
        )

    return json.dumps({"medications": meds, "interactions": interactions, "count": len(interactions)})


def get_lab_results(patient_id: str, test_type: str = "") -> str:
    """Retrieve lab results for a patient (mock)."""
    if patient_id not in MOCK_PATIENT_DB:
        return json.dumps({"error": f"Patient '{patient_id}' not found"})

    results = [
        {
            "date": "2024-10-10",
            "test": "HbA1c",
            "value": "7.2%",
            "reference": "< 7.0%",
        },
        {
            "date": "2024-10-10",
            "test": "LDL",
            "value": "110 mg/dL",
            "reference": "< 100 mg/dL",
        },
    ]

    if test_type:
        t = test_type.strip().lower()
        results = [r for r in results if t in r["test"].lower()]

    return json.dumps({"patient_id": patient_id, "results": results, "count": len(results)})


TOOLS = [
    get_patient_info,
    schedule_appointment,
    get_medication_info,
    check_drug_interactions,
    get_lab_results,
]
