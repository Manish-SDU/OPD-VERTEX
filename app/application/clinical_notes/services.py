"""Application services for transcript normalization and report generation."""

from __future__ import annotations

from datetime import datetime

from app.core.config import get_settings
from app.domain.auth.models import StaffRepository
from app.domain.clinical_notes.models import (
    ClinicalNoteGenerator,
    ClinicalReportRequest,
    ConsultationDocument,
    ConsultationDocumentRepository,
    GeneratedDocument,
    GeneratedDocumentRepository,
    GeneratedDocumentStatus,
    LlmExecutionMetadata,
    LlmHealthStatus,
    LocalLlmHealthService,
    PromptRepository,
    TranscriptNormalizationRequest,
    TranscriptNormalizer,
)
from app.domain.common.types import utcnow
from app.domain.consultations.models import ConsultationRepository, ConsultationStatus
from app.domain.patients.models import PatientRepository
from app.infrastructure.logging import apply_logging_aspect


NORMALIZATION_PROMPT_ID = "transcript_normalization_v1"
CLINICAL_REPORT_PROMPT_ID = "clinical_report_generation_v3"


@apply_logging_aspect("service", "transcript_normalization")
class TranscriptNormalizationApplicationService:
    def __init__(
        self,
        consultation_doc_repository: ConsultationDocumentRepository,
        prompt_repository: PromptRepository,
        transcript_normalizer: TranscriptNormalizer,
    ) -> None:
        self.consultation_doc_repository = consultation_doc_repository
        self.prompt_repository = prompt_repository
        self.transcript_normalizer = transcript_normalizer

    def normalize_for_consultation(
        self, consultation_id: int, *, force: bool = False
    ) -> ConsultationDocument:
        consultation_doc = self.consultation_doc_repository.get_by_consultation_id(
            consultation_id
        )
        if consultation_doc is None:
            raise ValueError(f"Consultation document {consultation_id} was not found.")

        raw_text = consultation_doc.transcript.full_text.strip()
        if not raw_text:
            raise ValueError(
                f"Consultation {consultation_id} does not have a stored transcript."
            )

        if consultation_doc.normalized_transcript and not force:
            return consultation_doc

        prompt = self.prompt_repository.get_by_id(NORMALIZATION_PROMPT_ID)
        if prompt is None:
            raise ValueError(
                f"Prompt '{NORMALIZATION_PROMPT_ID}' is missing from llm_prompts."
            )

        normalized = self.transcript_normalizer.normalize(
            TranscriptNormalizationRequest(
                consultation_id=consultation_id,
                transcript_text=raw_text,
                prompt=prompt,
            )
        )

        now = utcnow()
        consultation_doc.normalized_transcript = normalized
        consultation_doc.normalization_metadata = LlmExecutionMetadata(
            model_name=prompt.model_target or "qwen3:8b",
            prompt_id=prompt.id,
            prompt_version=prompt.version,
            temperature=prompt.temperature,
            max_tokens=prompt.max_tokens,
            generated_at=now,
        )
        if consultation_doc.created_at is None:
            consultation_doc.created_at = now
        consultation_doc.updated_at = now
        return self.consultation_doc_repository.save(consultation_doc)


@apply_logging_aspect("service", "clinical_notes")
class ClinicalNotesApplicationService:
    def __init__(
        self,
        consultation_repository: ConsultationRepository,
        consultation_doc_repository: ConsultationDocumentRepository,
        generated_repository: GeneratedDocumentRepository,
        prompt_repository: PromptRepository,
        patient_repository: PatientRepository,
        staff_repository: StaffRepository,
        normalization_service: TranscriptNormalizationApplicationService,
        note_generator: ClinicalNoteGenerator,
    ) -> None:
        self.consultation_repository = consultation_repository
        self.consultation_doc_repository = consultation_doc_repository
        self.generated_repository = generated_repository
        self.prompt_repository = prompt_repository
        self.patient_repository = patient_repository
        self.staff_repository = staff_repository
        self.normalization_service = normalization_service
        self.note_generator = note_generator

    def generate_report(
        self, consultation_id: int, *, regenerate: bool = False
    ) -> GeneratedDocument:
        consultation = self.consultation_repository.get_by_id(consultation_id)
        if consultation is None:
            raise ValueError(f"Consultation {consultation_id} was not found.")

        existing_document = self.generated_repository.get_by_consultation_id(
            consultation_id
        )
        if existing_document and not regenerate:
            return existing_document

        self.consultation_repository.update_status(
            consultation_id, ConsultationStatus.PROCESSING
        )

        consultation_doc = self.normalization_service.normalize_for_consultation(
            consultation_id, force=regenerate
        )
        if consultation_doc.normalized_transcript is None:
            raise ValueError(
                f"Consultation {consultation_id} does not have a normalized transcript."
            )

        prompt = self.prompt_repository.get_by_id(CLINICAL_REPORT_PROMPT_ID)
        if prompt is None:
            raise ValueError(
                f"Prompt '{CLINICAL_REPORT_PROMPT_ID}' is missing from llm_prompts."
            )

        now = utcnow()
        started_at = consultation.started_at or now
        settings = get_settings()

        patient = self.patient_repository.get_by_id(consultation.patient_id)
        if patient:
            patient_name = f"{patient.first_name} {patient.last_name}".strip()
            dob = patient.date_of_birth
            on = started_at.date()
            age_years = on.year - dob.year - ((on.month, on.day) < (dob.month, dob.day))
            patient_age = str(age_years)
            patient_gender = patient.gender or ""
            patient_date_of_birth = dob.isoformat()
            patient_phone = patient.phone or ""
            patient_address = patient.address or ""
            patient_allergies = patient.allergies or ""
            patient_medical_history = patient.medical_history or ""
        else:
            patient_name = ""
            patient_age = ""
            patient_gender = ""
            patient_date_of_birth = ""
            patient_phone = ""
            patient_address = ""
            patient_allergies = ""
            patient_medical_history = ""

        clinician = self.staff_repository.get_by_id(consultation.doctor_id)
        clinician_name = (
            f"{clinician.first_name} {clinician.last_name}".strip() if clinician else ""
        )

        generated_notes = self.note_generator.generate(
            ClinicalReportRequest(
                consultation_id=consultation_id,
                doctor_id=consultation.doctor_id,
                patient_id=consultation.patient_id,
                patient_name=patient_name,
                patient_age=patient_age,
                patient_gender=patient_gender,
                patient_date_of_birth=patient_date_of_birth,
                patient_phone=patient_phone,
                patient_address=patient_address,
                patient_allergies=patient_allergies,
                patient_medical_history=patient_medical_history,
                clinician_name=clinician_name,
                facility_name=settings.app_name,
                department="Outpatient Department (OPD)",
                visit_type="Not mentioned",
                consultation_mode="Not mentioned",
                encounter_date=started_at.strftime("%d-%b-%Y"),
                encounter_time=started_at.strftime("%H:%M"),
                transcript_text=consultation_doc.transcript.full_text,
                normalized_transcript=consultation_doc.normalized_transcript,
                prompt=prompt,
            )
        )

        self._enrich_notes_with_metadata(
            generated_notes,
            consultation_id=consultation_id,
            patient_id=consultation.patient_id,
            facility_name=settings.app_name,
            department="Outpatient Department (OPD)",
            clinician_name=clinician_name,
            patient_name=patient_name,
            patient_age=patient_age,
            patient_gender=patient_gender,
            patient_date_of_birth=patient_date_of_birth,
            patient_phone=patient_phone,
            patient_address=patient_address,
            patient_allergies=patient_allergies,
            patient_medical_history=patient_medical_history,
            date_of_visit=started_at.strftime("%d-%b-%Y"),
            time_of_visit=started_at.strftime("%H:%M"),
        )
        self._sync_derived_fields(generated_notes)
        generated_notes.report_markdown = self._render_template_markdown(
            generated_notes,
            consultation_id=consultation_id,
            generated_at=now,
            model_name=prompt.model_target or "qwen3:8b",
            facility_name=settings.app_name,
            department="Outpatient Department (OPD)",
        )

        generated_document = GeneratedDocument(
            id=existing_document.id if existing_document else None,
            consultation_id=consultation_id,
            doctor_id=consultation.doctor_id,
            patient_id=consultation.patient_id,
            generated_output=generated_notes,
            normalized_transcript=consultation_doc.normalized_transcript,
            suggestive_output=None,
            report_metadata=LlmExecutionMetadata(
                model_name=prompt.model_target or "qwen3:8b",
                prompt_id=prompt.id,
                prompt_version=prompt.version,
                temperature=prompt.temperature,
                max_tokens=prompt.max_tokens,
                generated_at=now,
            ),
            suggestive_metadata=None,
            doctor_edits=[],
            status=GeneratedDocumentStatus.PENDING_REVIEW,
            approved_at=None,
            created_at=existing_document.created_at if existing_document else now,
            updated_at=now,
        )
        saved_document = self.generated_repository.save(generated_document)

        consultation_doc.ai_clinical_notes = saved_document.generated_output
        consultation_doc.ai_suggestions = None
        consultation_doc.updated_at = now
        if consultation_doc.created_at is None:
            consultation_doc.created_at = now
        self.consultation_doc_repository.save(consultation_doc)

        self.consultation_repository.update_status(
            consultation_id, ConsultationStatus.REVIEW
        )
        return saved_document

    def _enrich_notes_with_metadata(
        self,
        notes,
        *,
        consultation_id: int,
        patient_id: int,
        facility_name: str,
        department: str,
        clinician_name: str,
        patient_name: str,
        patient_age: str,
        patient_gender: str,
        patient_date_of_birth: str,
        patient_phone: str,
        patient_address: str,
        patient_allergies: str,
        patient_medical_history: str,
        date_of_visit: str,
        time_of_visit: str,
    ) -> None:
        notes.patient_info.update(
            {
                "name": patient_name,
                "age": patient_age,
                "gender": patient_gender,
                "date_of_birth": patient_date_of_birth,
                "patient_id": str(patient_id),
                "phone": patient_phone,
                "address": patient_address,
                "known_allergies": patient_allergies,
                "medical_history": patient_medical_history,
                "facility_name": facility_name,
                "department": department,
            }
        )
        notes.encounter_info.encounter_id = str(consultation_id)
        notes.encounter_info.date = date_of_visit
        notes.encounter_info.time = time_of_visit
        if not notes.encounter_info.clinician_name:
            notes.encounter_info.clinician_name = clinician_name

    def _sync_derived_fields(self, notes) -> None:
        if not notes.assessment.primary_diagnosis and notes.diagnosis:
            notes.assessment.primary_diagnosis = notes.diagnosis
        if not notes.diagnosis and notes.assessment.primary_diagnosis:
            notes.diagnosis = notes.assessment.primary_diagnosis

        if not notes.plan.medications and notes.medications:
            notes.plan.medications = notes.medications
        if not notes.medications and notes.plan.medications:
            notes.medications = notes.plan.medications

        if not notes.plan.lab_tests_ordered and notes.lab_tests_ordered:
            notes.plan.lab_tests_ordered = notes.lab_tests_ordered
        if not notes.lab_tests_ordered and notes.plan.lab_tests_ordered:
            notes.lab_tests_ordered = notes.plan.lab_tests_ordered

        if not notes.plan.follow_up and notes.follow_up:
            notes.plan.follow_up = notes.follow_up
        if not notes.follow_up and notes.plan.follow_up:
            notes.follow_up = notes.plan.follow_up

        if not notes.plan.patient_instructions and notes.patient_instructions:
            notes.plan.patient_instructions = notes.patient_instructions
        if not notes.patient_instructions and notes.plan.patient_instructions:
            notes.patient_instructions = notes.plan.patient_instructions

    @staticmethod
    def _nm(value: str, *, default: str = "Not mentioned") -> str:
        cleaned = (value or "").strip()
        return cleaned if cleaned else default

    @staticmethod
    def _format_report_timestamp(value: datetime) -> str:
        return value.strftime("%d-%b-%Y %H:%M UTC")

    @staticmethod
    def _render_bullets(
        items: list[str], *, empty_line: str = "- Not mentioned"
    ) -> list[str]:
        cleaned = [item.strip() for item in items if item and item.strip()]
        if not cleaned:
            return [empty_line]
        return [f"- {item}" for item in cleaned]

    @staticmethod
    def _is_value_empty(value: str, default: str = "Not mentioned") -> bool:
        """Check if a string value is effectively empty (None, empty, or matching default)."""
        if not value:
            return True
        cleaned = value.strip()
        return not cleaned or cleaned.lower() == default.lower()

    @staticmethod
    def _is_section_empty(
        section_data: dict | list | str | object, *, check_nested: bool = True
    ) -> bool:
        """
        Determine if a section has significant data.
        Returns True if empty/missing, False if has data.
        """
        if isinstance(section_data, list):
            return len(section_data) == 0

        if isinstance(section_data, str):
            return ClinicalNotesApplicationService._is_value_empty(section_data)

        if isinstance(section_data, dict):
            if not check_nested:
                return len(section_data) == 0
            # For nested models, check if all fields are empty-ish
            for value in section_data.values():
                if isinstance(value, str):
                    if not ClinicalNotesApplicationService._is_value_empty(value):
                        return False
                elif isinstance(value, list) and len(value) > 0:
                    return False
                elif isinstance(value, dict) and len(value) > 0:
                    return False
            return True

        # For Pydantic models, check __dict__
        if hasattr(section_data, "__dict__"):
            return ClinicalNotesApplicationService._is_section_empty(
                section_data.__dict__, check_nested=check_nested
            )

        return False

    def _render_template_markdown(
        self,
        notes,
        *,
        consultation_id: int,
        generated_at: datetime,
        model_name: str,
        facility_name: str,
        department: str,
    ) -> str:
        patient_name = self._nm(notes.patient_info.get("name", ""))
        patient_age = self._nm(notes.patient_info.get("age", ""))
        patient_gender = self._nm(notes.patient_info.get("gender", ""))
        patient_dob = self._nm(notes.patient_info.get("date_of_birth", ""))
        patient_id = self._nm(notes.patient_info.get("patient_id", ""))
        patient_phone = self._nm(notes.patient_info.get("phone", ""))
        patient_address = self._nm(notes.patient_info.get("address", ""))

        date_of_visit = self._nm(notes.encounter_info.date)
        time_of_visit = self._nm(notes.encounter_info.time)
        clinician_name = self._nm(notes.encounter_info.clinician_name)

        lines: list[str] = []
        lines.append("MEDICAL OUTPATIENT CLINICAL REPORT")
        lines.append("")
        lines.append(f"Facility Name: {self._nm(facility_name)}")
        lines.append(
            f"Department: {self._nm(department, default='Outpatient Department (OPD)')}"
        )
        lines.append(f"Encounter ID: {consultation_id}")
        lines.append(f"Date of Visit: {date_of_visit}")
        lines.append(f"Time of Visit: {time_of_visit}")
        lines.append(f"Clinician: {clinician_name}")
        lines.append("Report Status: Draft")
        lines.append(
            "Source: AI-assisted documentation generated from local transcription and clinician review"
        )
        lines.append("")

        def rule():
            return "----------------------------------------------------------------"

        # Define all optional sections (those that can be skipped if empty)
        sections = [
            {
                "title": "PATIENT INFORMATION",
                "content": lambda: [
                    f"Full Name: {patient_name}",
                    f"Age: {patient_age}",
                    f"Gender: {patient_gender}",
                    f"Date of Birth: {patient_dob}",
                    f"Patient ID / MRN: {patient_id}",
                    f"Phone / Contact: {patient_phone}",
                    f"Address: {patient_address}",
                ],
                "always_show": True,
            },
            {
                "title": "ENCOUNTER DETAILS",
                "content": lambda: [
                    f"Visit Type: {self._nm(notes.encounter_info.visit_type)}",
                    f"Mode of Consultation: {self._nm(notes.encounter_info.consultation_mode)}",
                    f"Accompanied By: {self._nm(notes.encounter_info.accompanied_by)}",
                    f"Primary Language: {self._nm(notes.encounter_info.primary_language)}",
                    f"Information Reliability: {self._nm(notes.encounter_info.information_reliability)}",
                ],
                "always_show": True,
            },
            {
                "title": "CHIEF COMPLAINT",
                "content": lambda: [self._nm(notes.chief_complaint)],
                "always_show": True,
            },
            {
                "title": "HISTORY OF PRESENT ILLNESS",
                "content": lambda: [self._nm(notes.history_of_present_illness)],
                "always_show": True,
            },
            {
                "title": "RELEVANT REVIEW OF SYSTEMS",
                "content": lambda: [
                    f"General: {self._nm(notes.review_of_systems.general)}",
                    f"Respiratory: {self._nm(notes.review_of_systems.respiratory)}",
                    f"Cardiovascular: {self._nm(notes.review_of_systems.cardiovascular)}",
                    f"Gastrointestinal: {self._nm(notes.review_of_systems.gastrointestinal)}",
                    f"Neurological: {self._nm(notes.review_of_systems.neurological)}",
                    f"Genitourinary: {self._nm(notes.review_of_systems.genitourinary)}",
                    f"Musculoskeletal: {self._nm(notes.review_of_systems.musculoskeletal)}",
                    f"Other Systems: {self._nm(notes.review_of_systems.other)}",
                ],
                "is_empty": lambda: self._is_section_empty(notes.review_of_systems),
            },
            {
                "title": "PAST MEDICAL HISTORY",
                "content": lambda: [self._nm(notes.past_medical_history)],
                "is_empty": lambda: self._is_value_empty(notes.past_medical_history),
            },
            {
                "title": "MEDICATION HISTORY",
                "content": lambda: (
                    ["Current Medications Mentioned:"]
                    + self._render_bullets(notes.current_medications_mentioned)
                    + [
                        "",
                        "Recent Over-the-Counter / Home Remedies:",
                        "- Not mentioned",
                        "",
                        "Medication Adherence Notes:",
                        "Not mentioned",
                    ]
                ),
                "is_empty": lambda: len(notes.current_medications_mentioned) == 0,
            },
            {
                "title": "ALLERGIES",
                "content": lambda: [
                    f"Drug Allergies: {self._nm(notes.allergies)}",
                    "Food Allergies: Not mentioned",
                    "Other Allergies: Not mentioned",
                    "Reaction Details: Not mentioned",
                ],
                "is_empty": lambda: self._is_value_empty(notes.allergies),
            },
            {
                "title": "FAMILY AND SOCIAL HISTORY",
                "content": lambda: [
                    f"Family History: {self._nm(notes.family_history)}",
                    f"Smoking Status: {self._nm(notes.social_history.smoking)}",
                    f"Alcohol Use: {self._nm(notes.social_history.alcohol)}",
                    f"Substance Use: {self._nm(notes.social_history.substance_use)}",
                    f"Occupation / Exposure Risks: {self._nm(notes.social_history.occupation)}",
                    "Pregnancy / Lactation Status: Not mentioned",
                    "Other Social Factors: Not mentioned",
                ],
                "is_empty": lambda: (
                    self._is_section_empty(notes.social_history)
                    and self._is_value_empty(notes.family_history)
                ),
            },
            {
                "title": "VITAL SIGNS",
                "content": lambda: [
                    f"Blood Pressure: {self._nm(notes.vitals.blood_pressure, default='Not recorded')}",
                    f"Heart Rate: {self._nm(notes.vitals.heart_rate, default='Not recorded')}",
                    f"Temperature: {self._nm(notes.vitals.temperature, default='Not recorded')}",
                    f"Respiratory Rate: {self._nm(notes.vitals.respiratory_rate, default='Not recorded')}",
                    f"SpO2: {self._nm(notes.vitals.spo2, default='Not recorded')}",
                    f"Weight: {self._nm(notes.vitals.weight, default='Not recorded')}",
                    f"Height: {self._nm(notes.vitals.height, default='Not recorded')}",
                    f"BMI: {self._nm(notes.vitals.bmi, default='Not recorded')}",
                ],
                "is_empty": lambda: self._is_section_empty(notes.vitals),
            },
            {
                "title": "PHYSICAL EXAMINATION / EXAMINATION FINDINGS",
                "content": lambda: (
                    [
                        "General Appearance:",
                        "Not mentioned",
                        "",
                        "Systemic Examination:",
                    ]
                    + (
                        [self._nm(notes.examination_findings)]
                        if notes.examination_findings
                        else ["Not mentioned"]
                    )
                ),
                "is_empty": lambda: self._is_value_empty(notes.examination_findings),
            },
            {
                "title": "CLINICAL ASSESSMENT",
                "content": lambda: (
                    [
                        "Primary Diagnosis / Working Diagnosis:",
                        self._nm(notes.assessment.primary_diagnosis or notes.diagnosis),
                        "",
                        "Differential Diagnoses:",
                    ]
                    + self._render_bullets(
                        notes.assessment.differential_diagnoses,
                        empty_line="- Not mentioned",
                    )
                    + [
                        "",
                        "Clinical Impression:",
                        self._nm(notes.assessment.clinical_impression),
                    ]
                ),
                "always_show": True,
            },
            {
                "title": "MANAGEMENT PLAN",
                "content": lambda: (
                    ["A. Medications Prescribed"]
                    + (
                        [
                            item
                            for med in notes.medications
                            for item in [
                                f"- Medication Name: {self._nm(med.name)}",
                                f"  Dose: {self._nm(med.dosage)}",
                                f"  Route: {self._nm(med.route)}",
                                f"  Frequency: {self._nm(med.frequency)}",
                                f"  Duration: {self._nm(med.duration)}",
                                f"  Special Instructions: {self._nm(med.special_instructions or '')}",
                                "",
                            ]
                        ]
                        if notes.medications
                        else ["- Not mentioned", ""]
                    )
                    + ["B. Investigations Ordered", "Laboratory Tests:"]
                    + self._render_bullets(notes.lab_tests_ordered)
                    + ["", "Imaging:"]
                    + self._render_bullets(notes.plan.imaging_ordered)
                    + ["", "Procedures:", "- Not mentioned", "", "C. Referrals"]
                    + self._render_bullets(notes.plan.referrals)
                    + ["", "D. Follow-up Plan", self._nm(notes.follow_up)]
                ),
                "is_empty": lambda: (
                    len(notes.medications) == 0
                    and len(notes.lab_tests_ordered) == 0
                    and len(notes.plan.imaging_ordered) == 0
                    and len(notes.plan.referrals) == 0
                    and self._is_value_empty(notes.follow_up)
                ),
            },
            {
                "title": "PATIENT INSTRUCTIONS",
                "content": lambda: [self._nm(notes.patient_instructions)],
                "is_empty": lambda: self._is_value_empty(notes.patient_instructions),
            },
            {
                "title": "SAFETY-NET / RETURN PRECAUTIONS",
                "content": lambda: (
                    [
                        "The patient was advised to seek urgent medical attention if any of the following occur:"
                    ]
                    + self._render_bullets(
                        notes.return_precautions, empty_line="- Not mentioned"
                    )
                ),
                "is_empty": lambda: len(notes.return_precautions) == 0,
            },
            {
                "title": "CLINICAL NOTES SUMMARY",
                "content": lambda: [self._nm(notes.clinical_notes_summary)],
                "is_empty": lambda: self._is_value_empty(notes.clinical_notes_summary),
            },
            {
                "title": "DOCUMENTATION GAPS / MISSING BUT RELEVANT INFORMATION",
                "content": lambda: self._render_bullets(
                    notes.missing_but_relevant_information, empty_line="- Not mentioned"
                ),
                "is_empty": lambda: len(notes.missing_but_relevant_information) == 0,
            },
            {
                "title": "INTERNAL CLINICIAN REVIEW FLAGS",
                "content": lambda: [
                    "(Internal use only - do not include in patient-facing printout unless approved)",
                    "",
                    "Risk Level: Not run",
                    "",
                    "Review Suggestions:",
                    "- Not run",
                ],
                "always_show": True,
            },
            {
                "title": "CLINICIAN APPROVAL",
                "content": lambda: [
                    f"Reviewed By: {self._nm(notes.clinician_approval.reviewed_by)}",
                    f"Reviewed On: {self._nm(notes.clinician_approval.reviewed_at)}",
                    f"Final Status: {self._nm(notes.clinician_approval.status)}",
                    "Digital Signature / Initials: Not mentioned",
                ],
                "is_empty": lambda: self._is_section_empty(notes.clinician_approval),
            },
            {
                "title": "AUDIT / SYSTEM METADATA",
                "content": lambda: [
                    "Transcript Source: Faster-Whisper local transcription",
                    "Normalization Status: Completed",
                    f"Report Generation Model: {model_name}",
                    "Safety Review Status: Not run",
                    f"Last Updated: {self._format_report_timestamp(generated_at)}",
                ],
                "always_show": True,
            },
        ]

        # Filter sections: keep always_show or non-empty sections
        visible_sections = []
        for section in sections:
            if section.get("always_show", False):
                visible_sections.append(section)
            elif not section.get("is_empty", lambda: False)():
                visible_sections.append(section)

        # Render with dynamic numbering
        section_num = 1
        for section in visible_sections:
            lines.append(rule())
            lines.append(f"{section_num}. {section['title']}")
            lines.append(rule())
            lines.extend(section["content"]())
            lines.append("")
            section_num += 1

        return "\n".join(lines)


@apply_logging_aspect("service", "llm_health")
class LlmHealthApplicationService:
    def __init__(self, health_service: LocalLlmHealthService) -> None:
        self.health_service = health_service

    def check(self) -> LlmHealthStatus:
        return self.health_service.check_health()
