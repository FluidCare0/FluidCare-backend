---

## 🧭 **1. Dashboard (Common for All Users)**

Show a quick summary with cards/charts:

* 🛏 **Total Beds** (and occupied vs free count)
* 🧍 **Total Patients** (admitted vs discharged)
* 📡 **Total Devices** (active vs inactive)
* 🩸 **Total Fluid Bags Monitored**
* ⚡ **Latest Alerts / Critical Readings** (e.g., low IV level)
* 📅 **Recent Activities** (device assigned, patient admitted, etc.)

👉 Example:

```
Beds: 50 (45 occupied, 5 free)
Patients: 80 (70 admitted, 10 discharged)
Devices: 30 (25 active, 5 inactive)
Fluid Bags: 45 monitored
Alerts: 3 urgent (View)
```

---

## 👤 **2. User Profile Section**

(For all user types)

* Name, Mobile, Email, Role
* Change password / Update profile
* Last login time
* Email verification status

---

## 🏢 **3. Floor, Ward, and Bed Management**

(For `root_admin` and `manager` roles)

* 📌 List of floors → wards → beds in hierarchy
* 📝 Ability to add / edit / delete floors, wards, beds
* 🛏 Show bed occupancy status visually (🟩 free, 🟥 occupied)
* 🔍 Click a bed → see **assigned patient**, **assigned device**, and fluid bag

👉 Example UI:

```
Floor 1
 ├─ Ward 1
 │   ├─ Bed 1 (Occupied - Patient A)
 │   └─ Bed 2 (Free)
 └─ Ward 2
     └─ Bed 1 (Occupied - Patient B)
```

---

## 👨‍⚕️ **4. Patient Management**

(For all roles, with different permissions)

* List of patients with search & filter
* Add new patient / discharge patient
* Show current bed assignment, admission date, discharge date
* View assignment history
* Link to sensor readings for the patient’s device

👉 Example:

| Name     | Age | Gender | Bed      | Admitted    | Status |
| -------- | --- | ------ | -------- | ----------- | ------ |
| John Doe | 45  | Male   | F1-W2-B3 | 04 Oct 2025 | Active |

---

## 🛰 **5. Device Management**

(For `root_admin` & `manager`)

* List of devices with type (node / repeater / master), status, MAC address
* Last seen timestamp
* Current assignment → Bed / Ward / Floor
* Battery % (from latest sensor reading)
* Option to reassign or deactivate device

👉 Example:

| Type | MAC Address | Status | Last Seen    | Bed      | Battery |
| ---- | ----------- | ------ | ------------ | -------- | ------- |
| Node | 3A:BC:2D:90 | Active | 04 Oct 10:21 | F1-W1-B2 | 82%     |

---

## 🩺 **6. Fluid Bag Monitoring**

(For `manager` and `user` especially nurses)

* List of all fluid bags by type (IV, Blood, Urine)
* Current fluid level (from last `SensorReading`)
* Threshold status (Normal / Low / High)
* Linked bed and patient
* Alert indicators for critical bags

👉 Example:

| Type   | Device | Bed      | Patient   | Reading | Status |
| ------ | ------ | -------- | --------- | ------- | ------ |
| IV Bag | Node 1 | F2-W3-B1 | Patient A | 120ml   | ⚠ Low  |

---

## 📝 **7. Assignment History**

(For `root_admin` and `manager`)

* 📅 **Device–Bed History**

  * Device, Bed, Start Time, End Time, Assigned By

* 🧍‍♂️ **Patient–Bed History**

  * Patient, Bed, Start Time, End Time, Assigned By

👉 Useful for audits and troubleshooting.

---

## ⚡ **8. Alerts & Notifications Panel**

(For all users, role-based filtering)

* Low IV bag alerts
* Device offline alerts
* Battery low alerts
* Patient reassignment updates
* Option to mark as “Acknowledged” or “Resolved”

---

## 📊 **9. Analytics Section**

(For `root_admin` & `manager`)

* Daily patient admissions/discharges chart
* Device uptime percentage
* Alert frequency trends
* Bed occupancy over time
* Fluid usage stats

👉 Example Charts:

* Line chart: “Patient Admissions per Day”
* Bar chart: “Alerts per Device”
* Pie chart: “Bag Types in Use”

---

## 🔐 **10. Role-Based Controls**

| Feature             | Root Admin | Manager | User    |
| ------------------- | ---------- | ------- | ------- |
| Dashboard           | ✅          | ✅       | ✅       |
| Floor/Ward/Bed CRUD | ✅          | ✅       | ❌       |
| Patient CRUD        | ✅          | ✅       | Limited |
| Device Assignments  | ✅          | ✅       | ❌       |
| Fluid Bag View      | ✅          | ✅       | ✅       |
| Analytics           | ✅          | ✅       | ❌       |
| Alerts              | ✅          | ✅       | ✅       |
| User Management     | ✅          | ❌       | ❌       |

---


