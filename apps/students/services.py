# students/services.py
import requests
from django.conf import settings
from django.utils import timezone
from .models import Student

SYNC_STALE_AFTER = timezone.timedelta(hours=6) 

class UniversityAPIClient:
    def __init__(self, base_url=None, api_key=None):
        self.base_url = base_url or settings.UNIVERSITY_API_BASE_URL
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key or settings.UNIVERSITY_API_KEY}"
        })

    def fetch_students(self, page=1):
        resp = self.session.get(f"{self.base_url}/students", params={"page": page})
        resp.raise_for_status()
        return resp.json()

    def fetch_student(self, student_id):
        resp = self.session.get(f"{self.base_url}/students/{student_id}")
        resp.raise_for_status()
        return resp.json()


def _upsert_student(record: dict) -> Student:
    student, _ = Student.objects.update_or_create(
        student_id=record["id"],
        defaults={
            "name": record["name"],
            "email": record.get("email"),
            "faculty": record.get("faculty"),
            "course": record.get("course"),
            "year": record.get("year"),
            "category": record.get("category"),
            "raw_data": record,
            "last_synced_at": timezone.now(),
        },
    )
    return student


def sync_all_students(client: UniversityAPIClient):
    page = 1
    while True:
        data = client.fetch_students(page)
        if not data["results"]:
            break
        for record in data["results"]:
            _upsert_student(record)
        page += 1


def get_or_sync_student(student_id: str, client: UniversityAPIClient) -> Student:
    student = Student.objects.filter(student_id=student_id).first()

    is_stale = (
        student is None
        or student.last_synced_at is None
        or timezone.now() - student.last_synced_at > SYNC_STALE_AFTER
    )

    if is_stale:
        record = client.fetch_student(student_id)
        student = _upsert_student(record)

    return student