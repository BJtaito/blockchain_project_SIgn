import hashlib
import uuid
from datetime import datetime

def generate_pdf_hash(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()

def generate_trade_id() -> str:
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    random_part = uuid.uuid4().hex[:8]
    return f"TRD-{timestamp}-{random_part}"