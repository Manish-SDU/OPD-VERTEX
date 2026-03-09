from app.infrastructure.persistence.in_memory.repositories import InMemoryPatientRepository


def test_in_memory_patient_repository_lists_seeded_patients() -> None:
    repository = InMemoryPatientRepository()
    patients = repository.list_all()
    assert len(patients) >= 2
    assert patients[0].id.startswith("pat_")
