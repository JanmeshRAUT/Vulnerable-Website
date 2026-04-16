# MongoDB integration for Flask app
# Stores users, progress, and lab enrollments.
from pymongo import MongoClient, ASCENDING
import os
import uuid
import time

# Load .env so DATABASE_URL / MONGO_URI are available even when this module
# is imported before the Flask app has a chance to call load_dotenv().
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# Accept either MONGO_URI (explicit) or DATABASE_URL (used in .env).
MONGO_URI = (
    os.environ.get('MONGO_URI')
    or os.environ.get('DATABASE_URL')
    or 'mongodb://localhost:27017/'
)
MONGO_DB = os.environ.get('MONGO_DB', 'vuln_ecommerce')

try:
    import certifi
    ca = certifi.where()
except ImportError:
    ca = None

client = MongoClient(
    MONGO_URI,
    tls=True,                            # explicitly enable TLS
    tlsCAFile=ca,                        # use certifi bundle for secure SSL/TLS
    serverSelectionTimeoutMS=10000,
    connectTimeoutMS=10000,
    socketTimeoutMS=20000,
)
db = client[MONGO_DB]

# ── Ensure indexes ────────────────────────────────────────────────────────────
try:
    db.users.create_index([('email', ASCENDING)], unique=True, background=True)
    db.users.create_index([('username', ASCENDING)], unique=True, background=True)
    db.users.create_index([('enrollment_id', ASCENDING)], background=True)
    db.progress.create_index([('email', ASCENDING), ('lab_id', ASCENDING)], background=True)
    db.enrollments.create_index([('email', ASCENDING), ('lab_id', ASCENDING)], background=True)
except Exception:
    pass  # indexes may already exist

# ── User helpers ──────────────────────────────────────────────────────────────

def insert_user(user_data):
    """Insert a new user document into users collection."""
    return db.users.insert_one(user_data)


def find_user_by_email(email):
    """Return user dict by email, or None."""
    if not email:
        return None
    return db.users.find_one({'email': email.strip().lower()})


def find_user_by_username(username):
    """Return user dict by username (case-insensitive), or None."""
    if not username:
        return None
    return db.users.find_one({'username': {'$regex': f'^{username.strip()}$', '$options': 'i'}})


def find_user_by_enrollment_id(enrollment_id):
    """Return user dict by enrollment_id, or None."""
    if not enrollment_id:
        return None
    return db.users.find_one({'enrollment_id': enrollment_id.strip().upper()})


def upsert_user(email, username, role='user', full_name=None, guid=None,
                enrollment_id=None, is_approved=True, profile_picture=None,
                user_id=None):
    """Create or update a user document. Returns the updated user dict."""
    email = (email or '').strip().lower()
    if not email:
        return None

    update_fields = {
        'email': email,
        'username': username,
        'role': role,
        'is_approved': is_approved,
    }
    if full_name is not None:
        update_fields['full_name'] = full_name
    if guid is not None:
        update_fields['guid'] = guid
    if enrollment_id is not None:
        update_fields['enrollment_id'] = enrollment_id
    if profile_picture is not None:
        update_fields['profile_picture'] = profile_picture
    if user_id is not None:
        update_fields['user_id'] = user_id

    db.users.update_one(
        {'email': email},
        {'$set': update_fields},
        upsert=True
    )
    return db.users.find_one({'email': email})


def get_all_users():
    """Return list of all user documents."""
    return list(db.users.find({}))


def update_user_access(email, is_approved, role=None):
    """Approve or revoke a user and optionally change their role."""
    update = {'is_approved': is_approved}
    if role:
        update['role'] = role
    result = db.users.update_one({'email': email}, {'$set': update})
    return result.modified_count > 0


# ── Progress helpers ──────────────────────────────────────────────────────────

def get_user_progress(email):
    """Return {lab_id: progress_doc} for a user."""
    docs = db.progress.find({'email': email})
    return {d['lab_id']: d for d in docs}


def get_all_users_progress():
    """Return {email: {lab_id: progress_doc}} for all users."""
    result = {}
    for doc in db.progress.find({}):
        email = doc.get('email')
        lab_id = doc.get('lab_id')
        if email and lab_id:
            result.setdefault(email, {})[lab_id] = doc
    return result


def submit_lab_progress(email, lab_id, section_id, flag, is_solved, note=''):
    """Upsert a progress record for a user+lab."""
    db.progress.update_one(
        {'email': email, 'lab_id': lab_id},
        {'$set': {
            'email': email,
            'lab_id': lab_id,
            'section_id': section_id,
            'flag': flag,
            'is_solved': is_solved,
            'note': note,
            'updated_at': time.time(),
        }},
        upsert=True
    )


def get_solved_labs_feed():
    """Return all solved progress records."""
    return list(db.progress.find({'is_solved': True}))


# ── Enrollment helpers ────────────────────────────────────────────────────────

def get_user_lab_enrollments(email):
    """Return list of lab enrollment docs for a user (all approved)."""
    return list(db.enrollments.find({'email': email}))


def get_all_lab_enrollments():
    """Return {email: [enrollment_docs]} for all users."""
    result = {}
    for doc in db.enrollments.find({}):
        email = doc.get('email')
        if email:
            result.setdefault(email, []).append(doc)
    return result


def get_lab_enrollment(email, lab_id):
    """Return a single enrollment doc, or None."""
    return db.enrollments.find_one({'email': email, 'lab_id': lab_id})


def replace_user_lab_access(email, lab_id_list):
    """Replace all enrollments for a user with the provided lab IDs."""
    db.enrollments.delete_many({'email': email})
    for lab_id in lab_id_list:
        db.enrollments.update_one(
            {'email': email, 'lab_id': lab_id},
            {'$set': {
                'email': email,
                'lab_id': lab_id,
                'approval_status': 'approved',
                'updated_at': time.time(),
            }},
            upsert=True
        )
    return True


def update_lab_enrollment_status(email, lab_id, status):
    """Set approval_status on an enrollment."""
    db.enrollments.update_one(
        {'email': email, 'lab_id': lab_id},
        {'$set': {'approval_status': status, 'updated_at': time.time()}},
        upsert=True
    )
