# INSILOS INDUSTRIAL GROUP — STANDARD OPERATING FORM
## FORM-06: AUTOMATED AI COMPUTER VISION PPE & DANGER ZONE VIOLATION NOTICE

**Document Identifier**: `INSILOS-FRM-HSE-006`  
**Revision**: `3.0`  
**Governing Standard**: `Decree 12/2022/ND-CP (Article 32), Vietnam Law on OSH No. 84/2015/QH13, ISO 45001:2018, SOP-04`  
**GRC Permitting Collection**: `hse_violations` & `hse_incidents`  
**ERP Integration**: Insilos ERP Contractor Qualification (`res.partner.hse_rating`) & Shop Floor Alert  

---

### SECTION 1: CITATION ADMINISTRATIVE METADATA

| Administrative Field | Automated AI System & Field Telemetry Record |
| :--- | :--- |
| **Violation Notice Number** | `VIO-2026-09-00194` |
| **Associated GRC Incident ID**| `INC-2026-09-0842` |
| **Detection Timestamp (UTC)** | `2026-09-29 08:42:15.302 UTC` |
| **Detection Timestamp (Local)**| `2026-09-29 15:42:15.302 GMT+7` |
| **Edge Inference Node ID** | `EDGE-JETSON-ORIN-W02-01` (NVIDIA Jetson AGX Orin 64GB) |
| **CCTV Camera Identifier** | `CAM-W02-BAY03-PTZ01` (4K Industrial Starlight IP Camera) |
| **Camera RTSP Stream URI** | `rtsp://192.168.40.103:554/live/stream_h265_ch01` |
| **Monitored Physical Zone** | Workshop 02: Bay 03 — CNC Laser Cutting & High-Pressure Gas Manifold |
| **Machine Cell Identification**| `AST-LASER-CNC-01` (Bystronic 20kW Fiber Laser Station) |

---

### SECTION 2: DETECTED SUBJECT & CONTRACTOR INFORMATION

| Subject Parameter | Profile Record (Verified via RFID & Safety Badge) |
| :--- | :--- |
| **Individual Full Name** | Nguyen Van Tam |
| **Employee / Contractor ID** | `CTR-VNG-88412` |
| **Employer / Contractor Name** | Vanguard Marine Engineering & Fabrication Services JSC |
| **Insilos ERP Partner Vendor ID** | `res.partner` ID: `3482` (Status: `WARNING_ACTIVE_VIOLATION`) |
| **Trade / Craft Function** | Senior Pipefitter & Mechanical Assembler |
| **Current Safety Passport ID** | `SAF-PASSPORT-2026-44910` (Expiry Date: `2027-02-15`) |
| **Contractor Safety Supervisor**| Le Manh Cuong (Site Safety Superintendent — Phone: `+84-908-112-998`) |

---

### SECTION 3: AI COMPUTER VISION TELEMETRY & DIGITAL VERIFICATION

*The violation was automatically classified by the Insilos-YOLO-HSE neural model and verified by temporal persistence filtering.*

```
+---------------------------------------------------------------------------------------------------+
| NEURAL INFERENCE TELEMETRY METRICS                                                                |
+------------------------------+------------------------------------+-------------------------------+
| Target Violation Class       | Model Confidence Score             | Bounding Box Coordinates      |
+------------------------------+------------------------------------+-------------------------------+
| Class 2: helmet_violation    | 94.2% (Score = 0.942)              | [ymin: 0.185, xmin: 0.412,    |
|                              |                                    |  ymax: 0.742, xmax: 0.589]    |
| Class 5: danger_zone_intrus. | 98.7% (Score = 0.987)              | Geofence Polygon Collision    |
|                              |                                    | Intersects Laser Perimeter    |
+------------------------------+------------------------------------+-------------------------------+
| Temporal Persistence Frames  | 6 consecutive frames (240 ms)      | Trigger Threshold Exceeded    |
| Local Acoustic Siren Fired   | Output: 95dB @ 880Hz <-> 1240Hz    | Latency to Trip: 74 ms        |
| Red LED Strobe Beacon Status | 2.5 Hz High-Intensity Pulse        | Activated: 08:42:15.376 UTC   |
| Evidentiary Frame SHA-256    | 8f4c9103e8712a4dfb6510ea9b208c14902bca81014e7a885091cbf745d0124a  |
+------------------------------+------------------------------------+-------------------------------+
```

---

### SECTION 4: DIGITAL EVIDENCE SNAPSHOT & HUD ANNOTATION

```
+---------------------------------------------------------------------------------------------------+
| CCTV CAMERA SNAPSHOT: CAM-W02-BAY03-PTZ01 [2026-09-29 08:42:15.302 UTC]                           |
|                                                                                                   |
|    ======================= HIGH-PRESSURE NITROGEN MANIFOLD BAY =======================            |
|    |                                                                                 |            |
|    |                             [ RESTRICTED ZONE ]                                 |            |
|    |                                                                                 |            |
|    |                     +-----------------------------------+                       |            |
|    |                     | ! RED ALERT: NO SAFETY HELMET !   |                       |            |
|    |                     | Class: helmet_violation (0.942)   |                       |            |
|    |                     | Subject: CTR-VNG-88412            |                       |            |
|    |                     | [X] HEAD EXPOSED / NO HARD HAT    |                       |            |
|    |                     |                                   |                       |            |
|    |                     |        ( o _ o )   <-- [NO HELMET]|                       |            |
|    |                     |         / | | \                   |                       |            |
|    |                     |        /  | |  \   [VEST: COMPL.] |                       |            |
|    |                     |           | |                     |                       |            |
|    |                     |          /   \                    |                       |            |
|    |                     |         |     |                   |                       |            |
|    |                     +-----------------------------------+                       |            |
|    |                                                                                 |            |
|    | [!] SIREN ACTIVE (95dB) | [!] SHOP FLOOR TABLET PAUSED | [!] ERP NOTIFIED       |            |
|    ===================================================================================            |
+---------------------------------------------------------------------------------------------------+
```

---

### SECTION 5: STATUTORY VIOLATION & LEGAL ASSESSMENT

The observed condition represents a direct violation of Vietnamese Labor Safety Law and Corporate Governance:

1. **Government Decree No. 12/2022/ND-CP Article 32, Clause 1**:
   *"A fine ranging from 1,000,000 VND to 3,000,000 VND shall be imposed on any employee who fails to wear or use the personal protective equipment allocated by the employer during the performance of work."*
2. **Insilos Corporate Golden Safety Rule #3**:
   *"Mandatory, continuous wearing of Type 1 industrial safety hard hats (TCVN 6407 / EN 397) and high-visibility garments (ISO 20471) within all designated heavy manufacturing, laser cutting, and gantry crane staging zones."*
3. **Breach of e-PTW Condition**:
   - Master permit `ePTW-2026-09-00842` explicitly stipulates 100% PPE compliance for all contractors inside Bay 03.

---

### SECTION 6: DISCIPLINARY SANCTION & PENALTY ENFORCEMENT

| Disciplinary Dimension | Enforcement Determination & Action Taken |
| :--- | :--- |
| **Offense Frequency** | **First Offense (Strike 1)** on record within the preceding 12-month period. |
| **Individual Worker Penalty** | Written safety citation; mandatory immediate stand-down and 2-hour safety retraining. |
| **Contractor Employer Demerit**| 5 demerit penalty points applied to Vanguard Marine in Insilos GRC (`hse_contractors`). |
| **Financial Withholding** | 1,000,000 VND safety non-conformance chargeback billed to Vanguard Marine Invoice. |
| **Insilos ERP Vendor Impact** | Vendor qualification status de-rated to `CONDITIONAL_PROBATION`. Any new Purchase Order ($PO > 50,000,000\text{ VND}$) requires mandatory VP Operations approval in Insilos ERP. |

---

### SECTION 7: FIELD OFFICER INTERVENTION & IMMEDIATE RECTIFICATION

The on-duty Zone Safety Officer arrived at Bay 03 within 45 seconds of siren activation and completed the following field actions:
- [x] **Worker Stand-Down**: Ordered Nguyen Van Tam to immediately step back into the marked Green Walkway.
- [x] **Hazard Abatement**: Issued certified Insilos spare safety helmet (Serial: `HLM-INS-8812`, conforming to TCVN 6407). Inspected chin strap adjustment.
- [x] **Field Briefing**: Conducted on-the-spot 10-minute briefing on laser beam reflection hazards and high-pressure nitrogen rupture risks.
- [x] **Siren Reset**: Manually reset the field acoustic siren and cleared the Insilos ERP Shop Floor lock after verifying full PPE compliance.

---

### SECTION 8: RIGHT OF APPEAL & FORMAL SIGN-OFF

*Notice to Cited Party: Under SOP-04 §8, you have the statutory right to appeal this citation within twenty-four (24) hours if you believe an AI false positive occurred. Appeals are filed through the Insilos GRC portal.*

```
ON-DUTY FIELD HSE OFFICER:
I certify that the automated AI violation was physically verified on site, the worker was stood down, 
and corrective PPE donning was completed prior to authorizing work resumption.
Name: Hoang Thi Mai                  Badge: INS-HSE-00088        Date: 2026-09-29 08:55:00 UTC
Signature: [DIGITALLY SIGNED & VERIFIED IN GRC]

CITED INDIVIDUAL (Acknowledgement of Receipt & Safety Breach):
I acknowledge that I failed to wear my protective helmet inside the active laser cutting bay, understand 
the danger of serious injury, and commit to 100% compliance.
Name: Nguyen Van Tam                 ID: CTR-VNG-88412           Date: 2026-09-29 09:00:00 UTC
Signature: [DIGITALLY SIGNED ON SHOP FLOOR TABLET]

CONTRACTOR SAFETY SUPERINTENDENT (Employer Notification):
Name: Le Manh Cuong                  Phone: +84-908-112-998      Date: 2026-09-29 09:15:00 UTC
Signature: [NOTIFIED VIA GRC SMS/EMAIL & DIGITALLY CONFIRMED]
CITATION STATUS: [ OFFICIALLY FILED & EXECUTED IN GRC / ERP ]
```
