Great question, Kartik 👌
You already have a solid Django model structure, so we can now write **Django ORM queries** for all the 9 sections (Dashboard, Profile, Floors, Patients, Devices, Fluid Bags, Assignment History, Alerts, Analytics).

I’ll give you clean **function-based Django view snippets** for each section.
Assuming:

* Models are imported
* You’re using `render(request, 'template.html', context)` to send data to templates.
* Logged-in user is available as `request.user`.

---

## 🧭 **1. Dashboard Data**

```python
from django.utils import timezone
from django.db.models import Count, Q

def dashboard_view(request):
    total_beds = Bed.objects.count()
    occupied_beds = Bed.objects.filter(is_occupied=True).count()
    free_beds = total_beds - occupied_beds

    total_patients = Patient.objects.count()
    admitted_patients = Patient.objects.filter(discharged_at__isnull=True).count()
    discharged_patients = total_patients - admitted_patients

    total_devices = Device.objects.count()
    active_devices = Device.objects.filter(status=True).count()
    inactive_devices = total_devices - active_devices

    total_fluid_bags = FluidBag.objects.count()

    latest_alerts = SensorReading.objects.filter(
        Q(fluidBag__type='iv_bag', reading__lte=models.F('fluidBag__threshold_low')) |
        Q(fluidBag__type__in=['blood_bag','urine_bag'], reading__gte=models.F('fluidBag__threshold_high'))
    ).select_related('fluidBag').order_by('-timestamp')[:5]

    recent_activities = DeviceBedAssignmentHistory.objects.select_related('device', 'bed', 'user').order_by('-start_time')[:5]

    context = {
        'total_beds': total_beds,
        'occupied_beds': occupied_beds,
        'free_beds': free_beds,
        'total_patients': total_patients,
        'admitted_patients': admitted_patients,
        'discharged_patients': discharged_patients,
        'total_devices': total_devices,
        'active_devices': active_devices,
        'inactive_devices': inactive_devices,
        'total_fluid_bags': total_fluid_bags,
        'latest_alerts': latest_alerts,
        'recent_activities': recent_activities,
    }
    return render(request, 'dashboard.html', context)
```

---

## 👤 **2. User Profile Section**

```python
def profile_view(request):
    user = request.user
    context = {
        'user': user,
    }
    return render(request, 'profile.html', context)
```

---

## 🏢 **3. Floor, Ward, Bed Hierarchy**

```python
def floor_ward_bed_view(request):
    floors = Floor.objects.prefetch_related('wards__beds').all()
    context = {
        'floors': floors,
    }
    return render(request, 'floor_ward_bed.html', context)
```

👉 This gives you:

* `floor.wards.all` → all wards in a floor
* `ward.beds.all` → all beds in a ward

---

## 👨‍⚕️ **4. Patient Management**

```python
def patient_list_view(request):
    patients = Patient.objects.all().order_by('-admitted_at')
    # Optional: Annotate current bed
    active_assignments = PatientBedAssignmentHistory.objects.filter(end_time__isnull=True)
    bed_map = {a.patient_id: a.bed for a in active_assignments}

    context = {
        'patients': patients,
        'bed_map': bed_map,
    }
    return render(request, 'patients.html', context)
```

---

## 🛰 **5. Device Management**

```python
def device_list_view(request):
    devices = Device.objects.prefetch_related('assignments__bed__ward__floor').all()

    # Latest battery percent (from SensorReading)
    battery_map = {}
    latest_readings = (
        SensorReading.objects
        .order_by('fluidBag_id', '-timestamp')
        .distinct('fluidBag_id')
        .values('fluidBag__device_id', 'battery_percent')
    )
    for r in latest_readings:
        battery_map[r['fluidBag__device_id']] = r['battery_percent']

    context = {
        'devices': devices,
        'battery_map': battery_map,
    }
    return render(request, 'devices.html', context)
```

---

## 🩺 **6. Fluid Bag Monitoring**

```python
def fluid_bag_list_view(request):
    fluid_bags = FluidBag.objects.select_related('device').all()

    latest_readings = (
        SensorReading.objects
        .order_by('fluidBag_id', '-timestamp')
        .distinct('fluidBag_id')
    )

    reading_map = {r.fluidBag_id: r for r in latest_readings}

    context = {
        'fluid_bags': fluid_bags,
        'reading_map': reading_map,
    }
    return render(request, 'fluid_bags.html', context)
```

---

## 📝 **7. Assignment History**

```python
def assignment_history_view(request):
    device_history = DeviceBedAssignmentHistory.objects.select_related('device','bed','user').order_by('-start_time')
    patient_history = PatientBedAssignmentHistory.objects.select_related('patient','bed','user').order_by('-start_time')

    context = {
        'device_history': device_history,
        'patient_history': patient_history,
    }
    return render(request, 'assignment_history.html', context)
```

---

## ⚡ **8. Alerts & Notifications**

```python
def alerts_view(request):
    alerts = SensorReading.objects.filter(
        Q(fluidBag__type='iv_bag', reading__lte=models.F('fluidBag__threshold_low')) |
        Q(fluidBag__type__in=['blood_bag','urine_bag'], reading__gte=models.F('fluidBag__threshold_high'))
    ).select_related('fluidBag', 'fluidBag__device').order_by('-timestamp')

    context = {
        'alerts': alerts,
    }
    return render(request, 'alerts.html', context)
```

---

## 📊 **9. Analytics Section**

Here’s a **basic example** — you can extend this later with Chart.js.

```python
from django.db.models.functions import TruncDate

def analytics_view(request):
    # Daily patient admissions
    admissions_per_day = (
        Patient.objects
        .annotate(date=TruncDate('admitted_at'))
        .values('date')
        .annotate(total=Count('id'))
        .order_by('date')
    )

    # Device uptime (Active count / total)
    total_devices = Device.objects.count()
    active_devices = Device.objects.filter(status=True).count()
    device_uptime_percent = (active_devices / total_devices * 100) if total_devices else 0

    # Alert count per device
    alerts_per_device = (
        SensorReading.objects
        .filter(
            Q(fluidBag__type='iv_bag', reading__lte=models.F('fluidBag__threshold_low')) |
            Q(fluidBag__type__in=['blood_bag','urine_bag'], reading__gte=models.F('fluidBag__threshold_high'))
        )
        .values('fluidBag__device__mac_address')
        .annotate(total=Count('id'))
        .order_by('-total')
    )

    context = {
        'admissions_per_day': list(admissions_per_day),
        'device_uptime_percent': device_uptime_percent,
        'alerts_per_device': list(alerts_per_device),
    }
    return render(request, 'analytics.html', context)
```

---

## ✅ Summary of Views

| Section            | View Function             |
| ------------------ | ------------------------- |
| Dashboard          | `dashboard_view`          |
| Profile            | `profile_view`            |
| Floors/Wards/Beds  | `floor_ward_bed_view`     |
| Patients           | `patient_list_view`       |
| Devices            | `device_list_view`        |
| Fluid Bags         | `fluid_bag_list_view`     |
| Assignment History | `assignment_history_view` |
| Alerts             | `alerts_view`             |
| Analytics          | `analytics_view`          |

---

