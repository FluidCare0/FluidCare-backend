# utils.py
import random
import hashlib
import logging
from django.core.cache import cache
from django.conf import settings
from twilio.rest import Client

logger = logging.getLogger(__name__)

OTP_TTL = 300


def _is_bypass_enabled() -> bool:
    """Return True only in non-production environments."""
    return bool(getattr(settings, 'DEBUG', False))


def _get_master_phone() -> str:
    return getattr(settings, 'MASTER_PHONE', '')


def _get_master_otp() -> str:
    return getattr(settings, 'MASTER_OTP', '')

def _hash_otp(mobile, otp):
    return hashlib.sha256(f"{mobile}:{otp}".encode()).hexdigest()

def send_otp(mobile):
    # --- bypass check (dev/staging only) ---
    if _is_bypass_enabled():
        master_phone = _get_master_phone()
        if master_phone and mobile == master_phone:
            logger.debug(
                "[OTP bypass] Master phone detected – skipping Twilio call."
            )
            return True  
    # --- normal Twilio flow ---
    otp = str(random.randint(100000, 999999))
    hashed = _hash_otp(mobile, otp)
    cache.set(f"otp:{mobile}", hashed, OTP_TTL)
    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    client.messages.create(
        body=f"Your OTP is {otp}",
        from_=settings.TWILIO_FROM_NUMBER,
        to=mobile
    )
    return True

def verify_otp(mobile, otp):
    # --- bypass check (dev/staging only) ---
    if _is_bypass_enabled():
        master_phone = _get_master_phone()
        master_otp = _get_master_otp()
        if master_phone and master_otp and mobile == master_phone:
            is_valid = otp == master_otp
            logger.debug(
                "[OTP bypass] Master-phone verification attempt – valid=%s",
                is_valid,
            )
            return is_valid
    # --- normal cache-based flow ---
    hashed = cache.get(f"otp:{mobile}")
    if not hashed:
        return False
    return hashed == _hash_otp(mobile, otp)
