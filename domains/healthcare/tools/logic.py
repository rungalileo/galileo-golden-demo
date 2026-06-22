"""
Healthcare domain tools implementation
"""
import json
import time
import logging
import random
from typing import Optional, List
from galileo import GalileoLogger

# Mock patient database for testing
MOCK_PATIENT_DB = {
    "12345": {
        "patient_id": "12345",
        "name": "John Doe",
        "age": 45,
        "gender": "Male",
        "blood_type": "O+",
        "allergies": ["Penicillin", "Shellfish"],
        "current_medications": ["Lisinopril 10mg", "Metformin 500mg"],
        "conditions": ["Type 2 Diabetes", "Hypertension"],
        "last_visit": "2024-10-15",
        "primary_physician": "Dr. Emily Smith"
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
        "primary_physician": "Dr. Michael Johnson"
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
        "primary_physician": "Dr. Sarah Chen"
    }
}

# Mock medication database
MOCK_MEDICATION_DB = {
    "lisinopril": {
        "name": "Lisinopril",
        "generic_name": "Lisinopril",
        "brand_names": ["Prinivil", "Zestril"],
        "drug_class": "ACE Inhibitor",
        "uses": "Treatment of high blood pressure (hypertension) and heart failure",
        "common_dosages": ["5mg", "10mg", "20mg", "40mg"],
        "side_effects": ["Dry cough", "Dizziness", "Headache", "Fatigue", "Nausea"],
        "serious_side_effects": ["Angioedema", "Kidney problems", "High potassium levels"],
        "warnings": "Do not use if pregnant. May cause dizziness - use caution when driving."
    },
    "metformin": {
        "name": "Metformin",
        "generic_name": "Metformin",
        "brand_names": ["Glucophage", "Fortamet", "Glumetza"],
        "drug_class": "Biguanide",
        "uses": "Treatment of type 2 diabetes mellitus",
        "common_dosages": ["500mg", "850mg", "1000mg"],
        "side_effects": ["Nausea", "Diarrhea", "Stomach upset", "Metallic taste"],
        "serious_side_effects": ["Lactic acidosis (rare)", "Vitamin B12 deficiency"],
        "warnings": "Take with food to reduce stomach upset. Do not use if you have severe kidney disease."
    },
    "aspirin": {
        "name": "Aspirin",
        "generic_name": "Acetylsalicylic Acid",
        "brand_names": ["Bayer Aspirin", "Ecotrin"],
        "drug_class": "NSAID / Antiplatelet",
        "uses": "Pain relief, fever reduction, heart attack prevention, stroke prevention",
        "common_dosages": ["81mg (low-dose)", "325mg", "500mg"],
        "side_effects": ["Stomach upset", "Heartburn", "Nausea", "Easy bruising"],
        "serious_side_effects": ["Stomach bleeding", "Allergic reactions", "Ringing in ears"],
        "warnings": "Take with food or milk. Do not give to children with viral infections."
    },
    "atorvastatin": {
        "name": "Atorvastatin",
        "generic_name": "Atorvastatin",
        "brand_names": ["Lipitor"],
        "drug_class": "Statin",
        "uses": "Treatment of high cholesterol and triglycerides, prevention of cardiovascular disease",
        "common_dosages": ["10mg", "20mg", "40mg", "80mg"],
        "side_effects": ["Muscle pain", "Headache", "Nausea", "Diarrhea"],
        "serious_side_effects": ["Rhabdomyolysis", "Liver damage", "Memory problems"],
        "warnings": "Avoid grapefruit juice. Report any unexplained muscle pain immediately."
    },
    "levothyroxine": {
        "name": "Levothyroxine",
        "generic_name": "Levothyroxine Sodium",
        "brand_names": ["Synthroid", "Levoxyl", "Unithroid"],
        "drug_class": "Thyroid Hormone",
        "uses": "Treatment of hypothyroidism (underactive thyroid)",
        "common_dosages": ["25mcg", "50mcg", "75mcg", "100mcg", "125mcg"],
        "side_effects": ["Weight changes", "Headache", "Insomnia", "Nervousness"],
        "serious_side_effects": ["Chest pain", "Rapid heartbeat", "Tremors"],
        "warnings": "Take on empty stomach, 30-60 minutes before breakfast. Many drug interactions possible."
    }
}

<<<<<<< Updated upstream
def get_patient_info(patient_id: str, galileo_logger: Optional[GalileoLogger] = None) -> str:
=======
_root = str(_ROOT)
if _root not in sys.path:
    sys.path.insert(0, _root)

from helpers.agent_control_helpers import domain_controlled_tool
from helpers.llm_utils import get_domain_chat_model, get_domain_embedding_model
from helpers.sql_utils import execute_sql, relational_table_name
from helpers.text_to_sql_utils import generate_sql
from langgraph_rag import get_domain_rag_system

_vector_store: Optional[PGVector] = None
_embedding_model: Optional[str] = None
_collection_name_cached: Optional[str] = None

galileo_logger_key = "galileo_logger_healthcare"
if st.session_state.get(galileo_logger_key):
    print(f"[log.py] --> Galileo logger found! {st.session_state[galileo_logger_key]}", flush=True)
    galileo_logger = st.session_state[galileo_logger_key]
else:
    print("[log.py] --> Galileo logger not found!", flush=True)
    galileo_logger = None


def _ensure_project_path() -> None:
    root = str(_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)


def _load_domain_config():
    _ensure_project_path()
    from domain_manager import DomainManager
    from setup_env import setup_environment

    dm = DomainManager(domains_dir=str(_ROOT / "domains"))
    dcfg = dm.load_domain_config(_DOMAIN_NAME)
    setup_environment(_DOMAIN_NAME, dcfg.config)
    return dcfg


def _get_vector_store() -> Tuple[PGVector, str]:
    global _vector_store, _embedding_model, _collection_name_cached

    dcfg = _load_domain_config()
    embedding_model = get_domain_embedding_model(dcfg.config.get("vectorstore", {}))

    _ensure_project_path()
    from helpers.pgvector_utils import get_pgvector_store

    if (
        _vector_store is not None
        and _collection_name_cached is not None
        and _embedding_model == embedding_model
    ):
        return _vector_store, _collection_name_cached

    _vector_store, collection_name = get_pgvector_store(_DOMAIN_NAME, embedding_model)
    _embedding_model = embedding_model
    _collection_name_cached = collection_name
    return _vector_store, collection_name


def _log_tool_span(
    galileo_logger: Optional[GalileoLogger],
    name: str,
    tool_input: dict,
    tool_output: dict,
    start_time: float,
    metadata: Optional[dict] = None,
    tags: Optional[List[str]] = None,
) -> None:
    if not galileo_logger:
        return
    galileo_logger.add_tool_span(
        input=json.dumps(tool_input),
        output=json.dumps(tool_output),
        name=name,
        duration_ns=int((time.time() - start_time) * 1000000),
        metadata=metadata or {},
        tags=tags or ["healthcare"],
    )


def _log_retriever_span(
    name: str,
    tool_input: dict,
    tool_output: dict,
    start_time: float,
    metadata: Optional[dict] = None,
    tags: Optional[List[str]] = None,
) -> None:
    global galileo_logger

    if not galileo_logger:
        print("[_log_retriever_span] --> No Galileo logger found", flush=True)
        return

    galileo_logger.add_retriever_span(
        input=json.dumps(tool_input),
        output=json.dumps(tool_output),
        name=name,
        duration_ns=int((time.time() - start_time) * 1000000),
        metadata=metadata or {},
        tags=tags or ["healthcare"],
    )
    print(f"[_log_retriever_span] --> Galileo logger found! {galileo_logger.trace_id}_", flush=True)


def _resolve_galileo_logger(*_args, **_kwargs) -> Optional[GalileoLogger]:
    global galileo_logger
    if galileo_logger is not None:
        return galileo_logger
    try:
        return st.session_state.get(galileo_logger_key)
    except Exception:
        return None


@domain_controlled_tool(step_name="get_patient_info", resolve_logger=_resolve_galileo_logger)
async def _execute_patient_sql(sql: str) -> str:
    """Execute a SQL lookup against the patient registry."""
    try:
        result = execute_sql(sql)
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"error": str(e), "sql": sql})


@domain_controlled_tool(step_name="delete_patient_record", resolve_logger=_resolve_galileo_logger)
async def _execute_patient_delete_sql(sql: str) -> str:
    """Execute a SQL delete against the patient registry."""
    try:
        result = execute_sql(sql)
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"error": str(e), "sql": sql})


async def get_patient_info(patient_id: str) -> str:
>>>>>>> Stashed changes
    """
    Retrieve patient information from the medical records system.
    
    Args:
        patient_id: The unique patient identifier
        galileo_logger: Galileo logger for observability (optional)
        
    Returns:
        JSON string containing patient information
    """
    start_time = time.time()
<<<<<<< Updated upstream
=======
    patient_id = patient_id.strip().upper()

    q = (patient_id or "").strip()
    if not q:
        out = {"error": "patient_id is required"}
        return json.dumps(out)

    dcfg = _load_domain_config()
    model = get_domain_chat_model(dcfg.config)
    table_name = relational_table_name(_DOMAIN_NAME, _TABLE_SUFFIX)

>>>>>>> Stashed changes
    try:
        # Use mock database for demo purposes
        if patient_id in MOCK_PATIENT_DB:
            logging.info(f"Found patient {patient_id} in database")
            result = MOCK_PATIENT_DB[patient_id]
            
            if galileo_logger:
                galileo_logger.add_tool_span(
                    input=json.dumps({"patient_id": patient_id}),
                    output=json.dumps(result),
                    name="Get Patient Info",
                    duration_ns=int((time.time() - start_time) * 1000000),
                    metadata={
                        "patient_id": patient_id,
                        "patient_name": result["name"],
                        "found": "true"
                    },
                    tags=["healthcare", "patient", "lookup"]
                )
            
            return json.dumps(result)
        
        # Patient not found
        logging.warning(f"Patient {patient_id} not found in database")
        result = {
            "error": "Patient not found",
            "patient_id": patient_id,
            "message": "No patient record found with the provided ID"
        }
        
        if galileo_logger:
            galileo_logger.add_tool_span(
                input=json.dumps({"patient_id": patient_id}),
                output=json.dumps(result),
                name="Get Patient Info",
                duration_ns=int((time.time() - start_time) * 1000000),
                metadata={
                    "patient_id": patient_id,
                    "found": "false"
                },
                tags=["healthcare", "patient", "lookup", "not_found"]
            )
        
        return json.dumps(result)
        
    except Exception as e:
        logging.error(f"Error getting patient info: {str(e)}")
        result = {
            "error": "System error",
            "message": str(e)
        }
        return json.dumps(result)


def schedule_appointment(
    patient_id: str,
    provider_name: str,
    appointment_date: str,
    appointment_time: str,
    reason: str,
    galileo_logger: Optional[GalileoLogger] = None
) -> str:
    """
    Schedule a medical appointment for a patient.
    
    Args:
        patient_id: The unique patient identifier
        provider_name: The name of the healthcare provider
        appointment_date: The date for the appointment
        appointment_time: The time for the appointment
        reason: The reason for the appointment
        galileo_logger: Galileo logger for observability (optional)
        
    Returns:
        JSON string containing appointment confirmation
    """
    start_time = time.time()
<<<<<<< Updated upstream
=======
    patient_id = patient_id.strip().upper()

    q = (patient_id or "").strip()
    if not q:
        out = {"error": "patient_id is required"}
        return json.dumps(out)

    dcfg = _load_domain_config()
    model = get_domain_chat_model(dcfg.config)
    table_name = relational_table_name(_DOMAIN_NAME, _TABLE_SUFFIX)

>>>>>>> Stashed changes
    try:
        # Generate confirmation number
        confirmation_number = f"APT-{random.randint(100000, 999999)}"
        
        # Get patient name if available
        patient_name = "Unknown Patient"
        if patient_id in MOCK_PATIENT_DB:
            patient_name = MOCK_PATIENT_DB[patient_id]["name"]
        
        result = {
            "confirmation_number": confirmation_number,
            "patient_id": patient_id,
            "patient_name": patient_name,
            "provider": provider_name,
            "date": appointment_date,
            "time": appointment_time,
            "reason": reason,
            "status": "confirmed",
            "location": "Main Medical Center, Suite 200",
            "instructions": "Please arrive 15 minutes early for check-in. Bring your insurance card and photo ID.",
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        if galileo_logger:
            galileo_logger.add_tool_span(
                input=json.dumps({
                    "patient_id": patient_id,
                    "provider_name": provider_name,
                    "appointment_date": appointment_date,
                    "appointment_time": appointment_time,
                    "reason": reason
                }),
                output=json.dumps(result),
                name="Schedule Appointment",
                duration_ns=int((time.time() - start_time) * 1000000),
                metadata={
                    "patient_id": patient_id,
                    "provider": provider_name,
                    "confirmation": confirmation_number
                },
                tags=["healthcare", "appointment", "scheduling"]
            )
        
        return json.dumps(result)
        
    except Exception as e:
        logging.error(f"Error scheduling appointment: {str(e)}")
        raise


def get_medication_info(medication_name: str, galileo_logger: Optional[GalileoLogger] = None) -> str:
    """
    Get detailed information about a medication.
    
    Args:
        medication_name: The name of the medication
        galileo_logger: Galileo logger for observability (optional)
        
    Returns:
        JSON string containing medication information
    """
    start_time = time.time()
    try:
        # Normalize medication name for lookup
        med_name_lower = medication_name.lower().strip()
        
        if med_name_lower in MOCK_MEDICATION_DB:
            logging.info(f"Found medication {medication_name} in database")
            result = MOCK_MEDICATION_DB[med_name_lower]
            
            if galileo_logger:
                galileo_logger.add_tool_span(
                    input=json.dumps({"medication_name": medication_name}),
                    output=json.dumps(result),
                    name="Get Medication Info",
                    duration_ns=int((time.time() - start_time) * 1000000),
                    metadata={
                        "medication": medication_name,
                        "found": "true"
                    },
                    tags=["healthcare", "medication", "lookup"]
                )
            
            return json.dumps(result)
        
        # Medication not found
        logging.warning(f"Medication {medication_name} not found in database")
        result = {
            "error": "Medication not found",
            "medication_name": medication_name,
            "message": "No information available for this medication. Please consult a pharmacist or healthcare provider."
        }
        
        if galileo_logger:
            galileo_logger.add_tool_span(
                input=json.dumps({"medication_name": medication_name}),
                output=json.dumps(result),
                name="Get Medication Info",
                duration_ns=int((time.time() - start_time) * 1000000),
                metadata={
                    "medication": medication_name,
                    "found": "false"
                },
                tags=["healthcare", "medication", "lookup", "not_found"]
            )
        
        return json.dumps(result)
        
    except Exception as e:
        logging.error(f"Error getting medication info: {str(e)}")
        result = {
            "error": "System error",
            "message": str(e)
        }
        return json.dumps(result)


def check_drug_interactions(medications: List[str], galileo_logger: Optional[GalileoLogger] = None) -> str:
    """
    Check for potential interactions between multiple medications.
    
    Args:
        medications: List of medication names to check
        galileo_logger: Galileo logger for observability (optional)
        
    Returns:
        JSON string containing interaction information
    """
    start_time = time.time()
    try:
        # Known interactions for demo purposes
        interaction_db = {
            frozenset(["lisinopril", "aspirin"]): {
                "severity": "moderate",
                "description": "ACE inhibitors may reduce the effectiveness of aspirin for cardiovascular protection.",
                "recommendation": "Monitor blood pressure regularly. Consult your healthcare provider."
            },
            frozenset(["atorvastatin", "grapefruit"]): {
                "severity": "major",
                "description": "Grapefruit can increase atorvastatin levels in blood, raising risk of side effects.",
                "recommendation": "Avoid grapefruit and grapefruit juice while taking atorvastatin."
            },
            frozenset(["metformin", "alcohol"]): {
                "severity": "moderate",
                "description": "Alcohol can increase risk of lactic acidosis with metformin.",
                "recommendation": "Limit alcohol consumption. Avoid excessive drinking."
            },
            frozenset(["warfarin", "aspirin"]): {
                "severity": "major",
                "description": "Both medications thin the blood. Combined use significantly increases bleeding risk.",
                "recommendation": "Use together only under close medical supervision."
            }
        }
        
        # Normalize medication names
        meds_normalized = [med.lower().strip() for med in medications]
        
        # Find interactions
        interactions_found = []
        for i in range(len(meds_normalized)):
            for j in range(i + 1, len(meds_normalized)):
                med_pair = frozenset([meds_normalized[i], meds_normalized[j]])
                if med_pair in interaction_db:
                    interaction = interaction_db[med_pair].copy()
                    interaction["medications"] = [medications[i], medications[j]]
                    interactions_found.append(interaction)
        
        result = {
            "medications_checked": medications,
            "interactions_found": len(interactions_found),
            "interactions": interactions_found if interactions_found else [],
            "status": "warning" if interactions_found else "safe",
            "message": f"Found {len(interactions_found)} potential interaction(s)" if interactions_found else "No known interactions found",
            "disclaimer": "This is not a substitute for professional medical advice. Always consult your healthcare provider."
        }
        
        if galileo_logger:
            galileo_logger.add_tool_span(
                input=json.dumps({"medications": medications}),
                output=json.dumps(result),
                name="Check Drug Interactions",
                duration_ns=int((time.time() - start_time) * 1000000),
                metadata={
                    "medications_count": str(len(medications)),
                    "interactions_found": str(len(interactions_found))
                },
                tags=["healthcare", "medication", "safety", "interactions"]
            )
        
        return json.dumps(result)
        
    except Exception as e:
        logging.error(f"Error checking drug interactions: {str(e)}")
        raise


def get_lab_results(
    patient_id: str,
    test_type: Optional[str] = None,
    galileo_logger: Optional[GalileoLogger] = None
) -> str:
    """
    Retrieve laboratory test results for a patient.
    
    Args:
        patient_id: The unique patient identifier
        test_type: The type of lab test (optional)
        galileo_logger: Galileo logger for observability (optional)
        
    Returns:
        JSON string containing lab results
    """
    start_time = time.time()
    try:
        # Mock lab results database
        lab_results_db = {
            "12345": {
                "patient_id": "12345",
                "patient_name": "John Doe",
                "tests": [
                    {
                        "test_type": "Comprehensive Metabolic Panel",
                        "test_date": "2024-11-15",
                        "status": "completed",
                        "results": {
                            "glucose": {"value": 145, "unit": "mg/dL", "reference_range": "70-100", "flag": "High"},
                            "bun": {"value": 18, "unit": "mg/dL", "reference_range": "7-20", "flag": "Normal"},
                            "creatinine": {"value": 1.1, "unit": "mg/dL", "reference_range": "0.7-1.3", "flag": "Normal"},
                            "sodium": {"value": 140, "unit": "mmol/L", "reference_range": "136-145", "flag": "Normal"}
                        }
                    },
                    {
                        "test_type": "Lipid Panel",
                        "test_date": "2024-11-15",
                        "status": "completed",
                        "results": {
                            "total_cholesterol": {"value": 210, "unit": "mg/dL", "reference_range": "<200", "flag": "High"},
                            "ldl": {"value": 135, "unit": "mg/dL", "reference_range": "<100", "flag": "High"},
                            "hdl": {"value": 45, "unit": "mg/dL", "reference_range": ">40", "flag": "Normal"},
                            "triglycerides": {"value": 150, "unit": "mg/dL", "reference_range": "<150", "flag": "Normal"}
                        }
                    }
                ]
            },
            "67890": {
                "patient_id": "67890",
                "patient_name": "Jane Smith",
                "tests": [
                    {
                        "test_type": "Thyroid Panel",
                        "test_date": "2024-11-01",
                        "status": "completed",
                        "results": {
                            "tsh": {"value": 3.2, "unit": "mIU/L", "reference_range": "0.4-4.0", "flag": "Normal"},
                            "t4": {"value": 7.5, "unit": "μg/dL", "reference_range": "4.5-12.0", "flag": "Normal"},
                            "t3": {"value": 110, "unit": "ng/dL", "reference_range": "80-200", "flag": "Normal"}
                        }
                    }
                ]
            }
        }
        
        if patient_id in lab_results_db:
            result = lab_results_db[patient_id]
            
            # Filter by test type if specified
            if test_type:
                filtered_tests = [
                    test for test in result["tests"]
                    if test_type.lower() in test["test_type"].lower()
                ]
                result["tests"] = filtered_tests
            
            if galileo_logger:
                galileo_logger.add_tool_span(
                    input=json.dumps({"patient_id": patient_id, "test_type": test_type}),
                    output=json.dumps(result),
                    name="Get Lab Results",
                    duration_ns=int((time.time() - start_time) * 1000000),
                    metadata={
                        "patient_id": patient_id,
                        "tests_found": str(len(result["tests"])),
                        "found": "true"
                    },
                    tags=["healthcare", "lab_results", "lookup"]
                )
            
            return json.dumps(result)
        
        # Patient not found
        result = {
            "error": "No lab results found",
            "patient_id": patient_id,
            "message": "No laboratory results found for this patient ID"
        }
        
        if galileo_logger:
            galileo_logger.add_tool_span(
                input=json.dumps({"patient_id": patient_id, "test_type": test_type}),
                output=json.dumps(result),
                name="Get Lab Results",
                duration_ns=int((time.time() - start_time) * 1000000),
                metadata={
                    "patient_id": patient_id,
                    "found": "false"
                },
                tags=["healthcare", "lab_results", "lookup", "not_found"]
            )
        
        return json.dumps(result)
        
    except Exception as e:
        logging.error(f"Error getting lab results: {str(e)}")
        raise


# Export tools for easy loading by frameworks
TOOLS = [
    get_patient_info,
    schedule_appointment,
    get_medication_info,
    check_drug_interactions,
    get_lab_results
]

