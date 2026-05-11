from django.contrib.auth import get_user_model
from django.utils.text import slugify

from tennants.services.sms import TwilioNotificationService


def _unique_username(full_name, email="", phone=""):
    User = get_user_model()

    email_name = (email or "").split("@", 1)[0]
    phone_digits = "".join(char for char in str(phone) if char.isdigit())
    base = slugify(email_name or full_name) or f"tenant{phone_digits[-4:] or ''}"
    base = base.replace("-", "_")[:24] or "tenant"

    username = base
    counter = 1
    while User.objects.filter(username=username).exists():
        counter += 1
        username = f"{base[:20]}{counter}"

    return username


def generate_tenant_password(id_number="", phone=""):
    identifier = "".join(char for char in str(id_number or "") if char.isalnum())
    if not identifier:
        identifier = "".join(char for char in str(phone or "") if char.isdigit())[-6:]
    return f"tenant{identifier or '123'}"


def create_tenant_login_user(full_name, email="", phone="", id_number=""):
    User = get_user_model()
    password = generate_tenant_password(id_number=id_number, phone=phone)
    username = _unique_username(full_name, email=email, phone=phone)

    user = User.objects.create_user(
        username=username,
        email=email or "",
        password=password,
        first_name=(full_name or "").split(" ", 1)[0],
        last_name=(full_name or "").split(" ", 1)[1] if " " in (full_name or "") else "",
    )

    return user, password


def send_tenant_credentials_sms(tenant, password, login_url=None):
    if not tenant.sms_notifications:
        return False, "Notifications disabled"

    login_line = f"\nLogin: {login_url}" if login_url else ""
    message = (
        f"Hi {tenant.full_name}, your PropertyEmpire tenant account is ready.\n\n"
        f"Username: {tenant.user.username}\n"
        f"Password: {password}"
        f"{login_line}\n\n"
        "Please sign in and change your password after your first login."
    )

    return TwilioNotificationService().send_sms(tenant.phone, message)
