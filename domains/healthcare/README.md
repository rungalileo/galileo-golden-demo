# Healthcare Domain 🏥

A medical assistant for healthcare professionals with comprehensive clinical documentation and patient management tools.

## Available Tools

The healthcare domain includes 6 tools (5 domain-specific + 1 RAG retrieval tool):

### 1. `get_patient_info`
Retrieve patient information including demographics, medical history, and current conditions.

**Parameters:**
- `patient_id` (string, required): Unique patient identifier (e.g., 12345, P-00123)

**Example queries:**
- "Get patient information for patient ID 12345"
- "Show me the details for patient 67890"
- "What information do you have on patient P-00123?"

### 2. `schedule_appointment`
Schedule a medical appointment for a patient with a healthcare provider.

**Parameters:**
- `patient_id` (string, required): Patient identifier
- `provider_name` (string, required): Healthcare provider name
- `appointment_date` (string, required): Appointment date
- `appointment_time` (string, required): Appointment time
- `reason` (string, required): Reason for appointment

**Example queries:**
- "Schedule an appointment with Dr. Smith for patient 12345 on next Monday at 2pm for annual checkup"
- "Book patient 67890 with Dr. Johnson on December 1st at 10am for thyroid follow-up"
- "Schedule a consultation with Dr. Chen for patient P-00123 tomorrow at 3:30pm"

### 3. `get_medication_info`
Get detailed information about a medication including usage, dosage, and side effects.

**Parameters:**
- `medication_name` (string, required): Medication name

**Example queries:**
- "What are the side effects of Lisinopril?"
- "Tell me about Metformin"
- "What are the warnings for Levothyroxine?"

### 4. `check_drug_interactions`
Check for potential interactions between multiple medications.

**Parameters:**
- `medications` (array, required): List of medication names

**Example queries:**
- "Check for drug interactions between Lisinopril and Aspirin"
- "Are there any interactions between Atorvastatin, Metformin, and Aspirin?"
- "Check if Warfarin and Aspirin interact"

### 5. `get_lab_results`
Retrieve laboratory test results for a patient.

**Parameters:**
- `patient_id` (string, required): Patient identifier
- `test_type` (string, optional): Type of lab test

**Example queries:**
- "Get lab results for patient 12345"
- "Show me the thyroid panel results for patient 67890"
- "Get the metabolic panel for patient 12345"

### 6. `retrieve_healthcare_documents` (RAG Tool)
Automatically added when RAG is enabled. Retrieves information from the healthcare knowledge base.

**What it searches:**
- Common medical conditions and treatments (diabetes, hypertension, CKD, etc.)
- Medication reference guide (15+ medications with interactions, dosing, side effects)
- Clinical treatment protocols and emergency procedures (anaphylaxis, MI, stroke, DKA, sepsis)
- Preventive care and screening guidelines (cancer screening, immunizations, etc.)
- Patient education materials for medical procedures (colonoscopy, imaging, cardiac tests)

This tool is invoked automatically by the agent when you ask general medical knowledge questions.

**Example queries that trigger the RAG tool:**
- "What are the symptoms of Type 2 Diabetes?"
- "What is the MONA-B protocol for treating a heart attack?"
- "What are the breast cancer screening guidelines?"

## Mock Patient Data

The domain includes 3 realistic patient records:
- **Patient 12345**: John Doe (Type 2 Diabetes, Hypertension)
- **Patient 67890**: Jane Smith (Hypothyroidism)
- **Patient P-00123**: Robert Williams (High Cholesterol, Hypertension, CAD)

Each patient has complete records including allergies, current medications, conditions, and lab results.

## Mock Medication Database

Includes detailed information for:
- Lisinopril, Metformin, Atorvastatin, Amlodipine, Levothyroxine
- Drug interaction database for safety checks
- Comprehensive side effects and contraindications

## Galileo Project

Logs to: `galileo-demo-healthcare` unless custom project is configured

## Try It Out!

Start the app and navigate to: `http://localhost:8501/healthcare`

**Quick test queries:**

*Patient-specific (uses tools):*
1. "Get patient information for patient ID 12345"
2. "Schedule an appointment with Dr. Smith for patient 12345 next Monday at 2pm"
3. "Check drug interactions for Lisinopril and Aspirin"

*Medical knowledge (triggers RAG tool):*
1. "What are the symptoms of Type 2 Diabetes?"
2. "What is the MONA-B protocol for treating a heart attack?"
3. "What are the breast cancer screening guidelines?"

> **Note:** This is a demo application designed to showcase Galileo's observability capabilities for healthcare AI applications. It is NOT a real medical assistant and should NOT be used for actual patient care or medical decisions. All patient data is simulated for demonstration purposes only.

