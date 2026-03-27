import json
import os
import re
from datetime import datetime, timezone


class FirebaseDataStore:
    def __init__(self, base_path):
        self.base_path = base_path
        self.db = None
        self.firestore = None
        self.is_ready = False
        self.last_error = ""

    def _is_enabled(self):
        value = os.environ.get("FIREBASE_ENABLED", "false")
        return str(value).strip().lower() in {"1", "true", "yes", "on"}

    def initialize(self):
        if not self._is_enabled():
            return False

        try:
            import firebase_admin
            from firebase_admin import credentials, firestore

            credential_path = os.environ.get("FIREBASE_CREDENTIALS_PATH", "").strip()
            if not credential_path:
                credential_path = os.path.join(self.base_path, "firebase-service-account.json")

            service_account_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON", "").strip()
            project_id = os.environ.get("FIREBASE_PROJECT_ID", "").strip()

            if service_account_json:
                credential_data = json.loads(service_account_json)
                cred = credentials.Certificate(credential_data)
            elif os.path.exists(credential_path):
                cred = credentials.Certificate(credential_path)
            else:
                cred = credentials.ApplicationDefault()

            options = {}
            if project_id:
                options["projectId"] = project_id

            if not firebase_admin._apps:
                if options:
                    firebase_admin.initialize_app(cred, options)
                else:
                    firebase_admin.initialize_app(cred)

            self.firestore = firestore
            self.db = firestore.client()
            self.is_ready = True
            return True
        except Exception as exc:
            self.is_ready = False
            self.last_error = str(exc)
            print(f"[Firebase] Disabled: {exc}")
            return False

    def _extract_lab_id(self, path):
        if not path:
            return None

        match = re.match(r"^/lab(\d+)(?:/(\d+))?", path)
        if not match:
            return None

        main_lab = match.group(1)
        sub_lab = match.group(2)
        if sub_lab:
            return f"lab{main_lab}_{sub_lab}"
        return f"lab{main_lab}"

    def upsert_user(self, user_id, username, role=None, email=None, full_name=None, guid=None):
        if not self.is_ready:
            return

        payload = {
            "user_id": int(user_id),
            "username": username,
            "role": role,
            "email": email,
            "full_name": full_name,
            "guid": guid,
            "updated_at": self.firestore.SERVER_TIMESTAMP,
        }
        self.db.collection("users").document(str(user_id)).set(payload, merge=True)

    def sync_lab_state(self, user_id, enrollments, progress_summary):
        if not self.is_ready:
            return

        payload = {
            "user_id": int(user_id),
            "enrollments": enrollments,
            "progress_summary": progress_summary,
            "updated_at": self.firestore.SERVER_TIMESTAMP,
        }
        self.db.collection("user_lab_state").document(str(user_id)).set(payload, merge=True)

    def track_auth_event(self, event_type, user_id=None, username=None, email=None):
        if not self.is_ready:
            return

        payload = {
            "event_type": event_type,
            "user_id": int(user_id) if user_id is not None else None,
            "username": username,
            "email": email,
            "created_at": self.firestore.SERVER_TIMESTAMP,
            "created_at_iso": datetime.now(timezone.utc).isoformat(),
        }
        self.db.collection("auth_events").add(payload)

    def track_user_activity(self, user_id, username, role, path, method, status_code, query_string, ip_address, user_agent):
        if not self.is_ready:
            return

        lab_id = self._extract_lab_id(path)
        payload = {
            "user_id": int(user_id),
            "username": username,
            "role": role,
            "path": path,
            "method": method,
            "status_code": int(status_code),
            "query_string": query_string,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "lab_id": lab_id,
            "created_at": self.firestore.SERVER_TIMESTAMP,
            "created_at_iso": datetime.now(timezone.utc).isoformat(),
        }

        self.db.collection("user_activity").add(payload)

        if lab_id:
            usage_ref = self.db.collection("user_lab_usage").document(f"{user_id}_{lab_id}")
            usage_ref.set(
                {
                    "user_id": int(user_id),
                    "username": username,
                    "lab_id": lab_id,
                    "visit_count": self.firestore.Increment(1),
                    "last_path": path,
                    "updated_at": self.firestore.SERVER_TIMESTAMP,
                },
                merge=True,
            )
