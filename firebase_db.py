import json
import os
import base64


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

    def _parse_service_account_env(self):
        """Parse Firebase service account JSON from env in multiple safe formats."""
        raw_json = (
            os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON", "").strip()
            or os.environ.get("SERVICE_ACCOUNT_JSON", "").strip()
        )
        base64_json = (
            os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON_BASE64", "").strip()
            or os.environ.get("SERVICE_ACCOUNT_JSON_BASE64", "").strip()
        )

        # Common dashboard mistake: pasting KEY=VALUE into value field.
        for key_prefix in (
            "FIREBASE_SERVICE_ACCOUNT_JSON=",
            "SERVICE_ACCOUNT_JSON=",
            "FIREBASE_SERVICE_ACCOUNT_JSON_BASE64=",
            "SERVICE_ACCOUNT_JSON_BASE64=",
        ):
            if raw_json.startswith(key_prefix):
                raw_json = raw_json[len(key_prefix):].strip()
            if base64_json.startswith(key_prefix):
                base64_json = base64_json[len(key_prefix):].strip()

        # Strip accidental wrapping quotes around payloads.
        if len(raw_json) >= 2 and raw_json[0] == raw_json[-1] and raw_json[0] in {'"', "'"}:
            raw_json = raw_json[1:-1]
        if len(base64_json) >= 2 and base64_json[0] == base64_json[-1] and base64_json[0] in {'"', "'"}:
            base64_json = base64_json[1:-1]

        # Prefer base64 payloads in hosted environments to avoid escaping issues.
        if base64_json:
            try:
                decoded = base64.b64decode(base64_json).decode("utf-8")
                return json.loads(decoded), "SERVICE_ACCOUNT_JSON_BASE64 env var"
            except Exception as exc:
                raise ValueError(f"Invalid base64 service account JSON: {exc}") from exc

        if not raw_json:
            return None, None

        # 1) Direct JSON object
        try:
            return json.loads(raw_json), "SERVICE_ACCOUNT_JSON env var"
        except json.JSONDecodeError:
            pass

        # 2) Double-escaped JSON string (common in CI/env dashboards)
        try:
            normalized = raw_json.encode("utf-8").decode("unicode_escape")
            return json.loads(normalized), "SERVICE_ACCOUNT_JSON env var (decoded escapes)"
        except Exception as exc:
            raise ValueError(
                "SERVICE_ACCOUNT_JSON could not be parsed. Use strict JSON with double quotes "
                "or provide SERVICE_ACCOUNT_JSON_BASE64."
            ) from exc

    def initialize(self):
        if not self._is_enabled():
            return False

        try:
            import firebase_admin
            from firebase_admin import credentials, firestore

            credential_path = os.environ.get("FIREBASE_CREDENTIALS_PATH", "").strip()
            if not credential_path:
                credential_path = os.path.join(self.base_path, "firebase-service-account.json")

            project_id = os.environ.get("FIREBASE_PROJECT_ID", "").strip()
            credential_data, credential_source = self._parse_service_account_env()

            if credential_data:
                print(f"[Firebase] Initializing via {credential_source}")
                cred = credentials.Certificate(credential_data)
            elif os.path.exists(credential_path):
                print(f"[Firebase] Initializing via credential file: {credential_path}")
                cred = credentials.Certificate(credential_path)
            else:
                print(f"[Firebase] Initializing via Application Default Credentials")
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
            print("[Firebase] Initialization successful. Client ready.")
            return True
        except Exception as exc:
            self.is_ready = False
            self.last_error = str(exc)
            print(f"[Firebase] CRITICAL INITIALIZATION ERROR: {exc}")
            import traceback
            traceback.print_exc()
            return False

    def upsert_user(self, user_id, username, role=None, email=None, full_name=None, guid=None, enrollment_id=None, is_approved=False):
        db = self.db
        fs = self.firestore
        if db is None or fs is None or not self.is_ready:
            return

        if not email:
            print("[Firebase] Cannot upsert user without email")
            return

        try:
            payload = {
                "user_id": user_id,
                "username": username,
                "role": role,
                "email": email,
                "full_name": full_name,
                "guid": guid,
                "enrollment_id": enrollment_id,
                "is_approved": bool(is_approved),
                "updated_at": fs.SERVER_TIMESTAMP,
            }
            # Use email as document ID for stable identity across database resets
            db.collection("users").document(email).set(payload, merge=True)
            print(f"[Firebase] Successfully updated profile for {email}")
        except Exception as e:
            print(f"[Firebase] Upsert failed: {e}")

    def get_user_by_email(self, email):
        db = self.db
        if db is None or not self.is_ready: 
            return None
        try:
            doc = db.collection("users").document(email).get()
            return doc.to_dict() if doc.exists else None
        except Exception as e:
            print(f"[Firebase] Lookup failed for {email}: {e}")
            return None

    def get_all_users(self):
        """Fetch all research subjects for the Command Center"""
        db = self.db
        if db is None or not self.is_ready: 
            return []
        try:
            docs = db.collection("users").stream()
            return [doc.to_dict() for doc in docs]
        except Exception as e:
            print(f"[Firebase] Failed to fetch all users: {e}")
            return []

    def get_user_by_username(self, username):
        """Lookup a user by their username"""
        db = self.db
        if db is None or not self.is_ready:
            return None
        try:
            docs = db.collection("users").where("username", "==", username).limit(1).stream()
            for doc in docs:
                return doc.to_dict()
            return None
        except Exception as e:
            print(f"[Firebase] Username lookup failed for {username}: {e}")
            return None

    def get_user_by_enrollment_id(self, enrollment_id):
        """Lookup a user by their enrollment ID"""
        db = self.db
        if db is None or not self.is_ready:
            return None
        try:
            docs = db.collection("users").where("enrollment_id", "==", enrollment_id).limit(1).stream()
            for doc in docs:
                return doc.to_dict()
            return None
        except Exception as e:
            print(f"[Firebase] Enrollment ID lookup failed for {enrollment_id}: {e}")
            return None


    def update_user_approval(self, email, is_approved):
        """Manually authorize or deny a subject's account"""
        db = self.db
        fs = self.firestore
        if db is None or fs is None or not self.is_ready: 
            return False
        try:
            db.collection("users").document(email).update({
                "is_approved": bool(is_approved),
                "updated_at": fs.SERVER_TIMESTAMP
            })
            return True
        except Exception as e:
            print(f"[Firebase] Approval update failed for {email}: {e}")
            return False

    def update_user_access(self, email, is_approved, role=None):
        """Update account approval and optionally role in one write."""
        db = self.db
        fs = self.firestore
        if db is None or fs is None or not self.is_ready:
            return False

        try:
            payload = {
                "is_approved": bool(is_approved),
                "updated_at": fs.SERVER_TIMESTAMP
            }
            if role:
                payload["role"] = role

            db.collection("users").document(email).update(payload)
            return True
        except Exception as e:
            print(f"[Firebase] Access update failed for {email}: {e}")
            return False

    def _lab_enrollment_doc_id(self, email, lab_id):
        return f"{email}__{lab_id}"

    def get_lab_enrollment(self, email, lab_id):
        """Fetch one lab enrollment record for a subject."""
        db = self.db
        if db is None or not self.is_ready:
            return None
        try:
            doc_id = self._lab_enrollment_doc_id(email, lab_id)
            doc = db.collection("lab_enrollments").document(doc_id).get()
            return doc.to_dict() if doc.exists else None
        except Exception as e:
            print(f"[Firebase] Lab enrollment lookup failed for {email} / {lab_id}: {e}")
            return None

    def get_user_lab_enrollments(self, email):
        """Fetch all lab enrollment records for a subject."""
        db = self.db
        if db is None or not self.is_ready:
            return []
        try:
            docs = db.collection("lab_enrollments").where("email", "==", email).stream()
            records = []
            for doc in docs:
                payload = doc.to_dict() or {}
                payload["doc_id"] = doc.id
                records.append(payload)
            records.sort(key=lambda item: str(item.get("lab_id") or ""))
            return records
        except Exception as e:
            print(f"[Firebase] Lab enrollment list failed for {email}: {e}")
            return []

    def create_lab_enrollment(self, email, lab_id, approval_status="pending"):
        """Create or overwrite one lab enrollment record."""
        db = self.db
        fs = self.firestore
        if db is None or fs is None or not self.is_ready:
            return False

        try:
            payload = {
                "email": email,
                "lab_id": lab_id,
                "approval_status": approval_status,
                "updated_at": fs.SERVER_TIMESTAMP,
            }
            db.collection("lab_enrollments").document(self._lab_enrollment_doc_id(email, lab_id)).set(payload, merge=True)
            return True
        except Exception as e:
            print(f"[Firebase] Lab enrollment create failed for {email} / {lab_id}: {e}")
            return False

    def update_lab_enrollment_status(self, email, lab_id, approval_status):
        """Update the approval state for one lab enrollment."""
        db = self.db
        fs = self.firestore
        if db is None or fs is None or not self.is_ready:
            return False

        try:
            payload = {
                "email": email,
                "lab_id": lab_id,
                "approval_status": approval_status,
                "updated_at": fs.SERVER_TIMESTAMP,
            }
            db.collection("lab_enrollments").document(self._lab_enrollment_doc_id(email, lab_id)).set(payload, merge=True)
            return True
        except Exception as e:
            print(f"[Firebase] Lab enrollment update failed for {email} / {lab_id}: {e}")
            return False

    def delete_lab_enrollment(self, email, lab_id):
        """Delete one lab enrollment record."""
        db = self.db
        if db is None or not self.is_ready:
            return False

        try:
            db.collection("lab_enrollments").document(self._lab_enrollment_doc_id(email, lab_id)).delete()
            return True
        except Exception as e:
            print(f"[Firebase] Lab enrollment delete failed for {email} / {lab_id}: {e}")
            return False

    def replace_user_lab_access(self, email, allowed_lab_ids):
        """Replace a subject's active lab allowlist with the selected lab IDs."""
        db = self.db
        if db is None or not self.is_ready:
            return False

        try:
            allowed = {str(lab_id).strip() for lab_id in allowed_lab_ids if str(lab_id).strip()}
            current_enrollments = self.get_user_lab_enrollments(email)

            for lab_id in allowed:
                self.update_lab_enrollment_status(email, lab_id, "approved")

            for enrollment in current_enrollments:
                lab_id = str(enrollment.get("lab_id") or "").strip()
                if lab_id and lab_id not in allowed:
                    self.delete_lab_enrollment(email, lab_id)

            return True
        except Exception as e:
            print(f"[Firebase] Lab access replacement failed for {email}: {e}")
            return False

    def submit_lab_progress(self, email, lab_id, variation, flag, is_correct, message="", canonical_lab_id=None, exact_lab_id=None, lab_path=None):
        """Record a research deliverable submission"""
        db = self.db
        fs = self.firestore
        if db is None or fs is None or not self.is_ready: 
            return
        try:
            # Progress record
            progress_doc_id = exact_lab_id or lab_id
            progress_ref = db.collection("lab_progress").document(email).collection("labs").document(progress_doc_id)
            
            payload = {
                "lab_id": progress_doc_id,
                "canonical_lab_id": canonical_lab_id or lab_id,
                "exact_lab_id": progress_doc_id,
                "lab_path": lab_path,
                "variation": variation,
                "last_flag_submitted": flag,
                "is_solved": bool(is_correct),
                "last_attempt_at": fs.SERVER_TIMESTAMP,
                "message": message
            }
            
            if is_correct:
                payload["solved_at"] = fs.SERVER_TIMESTAMP
                # Aggregate solved record for monitoring
                db.collection("solved_labs").add({
                    "email": email,
                    "lab_id": progress_doc_id,
                    "canonical_lab_id": canonical_lab_id or lab_id,
                    "exact_lab_id": progress_doc_id,
                    "lab_path": lab_path,
                    "variation": variation,
                    "solved_at": fs.SERVER_TIMESTAMP
                })

            progress_ref.set(payload, merge=True)
        except Exception as e:
            print(f"[Firebase] Progress submission failed: {e}")

    def get_user_progress(self, email):
        """Fetch all lab progress for a specific subject"""
        if not self.is_ready: return {}
        try:
            labs = self.db.collection("lab_progress").document(email).collection("labs").stream()
            return {doc.id: doc.to_dict() for doc in labs}
        except Exception as e:
            print(f"[Firebase] Progress fetch failed: {e}")
            return {}

    def get_solved_labs_feed(self, limit=50):
        """Fetch the global solved labs feed for Command Center monitoring"""
        if not self.is_ready: return []
        try:
            docs = self.db.collection("solved_labs").order_by("solved_at", direction=self.firestore.Query.DESCENDING).limit(limit).stream()
            return [doc.to_dict() for doc in docs]
        except Exception as e:
            print(f"[Firebase] solved_labs feed failed: {e}")
            return []
