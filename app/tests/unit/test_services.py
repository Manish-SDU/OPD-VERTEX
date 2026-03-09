from app.infrastructure.persistence.in_memory.repositories import InMemoryGeneratedDocumentRepository, MockClinicalNoteGenerator


def test_mock_clinical_note_generator_returns_generated_document() -> None:
    repository = InMemoryGeneratedDocumentRepository()
    service = MockClinicalNoteGenerator(repository)
    document = service.generate("con_test", "sample transcript")
    assert document.consultation_id == "con_test"
    assert document.notes.assessment == "Placeholder assessment."
