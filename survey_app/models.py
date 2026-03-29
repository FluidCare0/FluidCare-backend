import uuid
from django.db import models
from hospital_app.models import Bed, Patient
from sensor_app.models import Device
from django.contrib.auth import get_user_model
from django.db.models import Q, UniqueConstraint
from django.core.exceptions import ValidationError

User = get_user_model()
