# STANDARD OPERATING PROCEDURE: AI COMPUTER VISION SAFETY SURVEILLANCE, PPE VIOLATION PROTOCOL & FIELD EMERGENCY RESPONSE

**Document Identifier**: `INSILOS-SOP-HSE-004`  
**Revision Number**: `3.0`  
**Effective Date**: `2026-10-01`  
**Review Cycle**: `Annual`  
**Standard Compliance**: `ISO 45001:2018 (Clauses 8.1.1, 8.2), Vietnam Law on OSH No. 84/2015/QH13, Decree 44/2016/ND-CP, Decree 12/2022/ND-CP (Article 32), TCVN 6407:1998, ISO 20471:2013`  
**System Integrations**: `Edge AI Computer Vision Nodes <-> Insilos GRC (hse_violations, hse_incidents) <-> Insilos ERP (Insilos ERP Shop Floor Tablet Alerts & Vendor PO Qualification)`  

---

## 1. PURPOSE & PRINCIPLES

1.1. This Standard Operating Procedure (SOP) defines the operational, technical, and response standards governing the deployment and operation of the Insilos Artificial Intelligence Computer Vision Safety Monitoring System. The system continuously audits real-time Closed-Circuit Television (CCTV) feeds across heavy manufacturing bays, automated robotics cells, and maritime terminal facilities to automatically detect non-compliance with Personal Protective Equipment (PPE) regulations and unauthorized intrusions into high-hazard exclusion zones.

1.2. **Zero Harm through Real-Time Automation**: Traditional periodic human safety patrols provide only intermittent sampling, leaving hazardous blind spots. The AI Vision system provides continuous, non-intrusive 24/7/365 vigilance, closing the gap between hazard emergence and field response by triggering acoustic sirens within 350 milliseconds and streaming digital evidence directly to enterprise governance platforms.

1.3. **Core Operational Objectives**:
- Achieve $\ge 99.5\%$ operational compliance for mandatory Personal Protective Equipment (Safety Helmets and High-Visibility Reflective Vests).
- Prevent catastrophic crush injuries and automated robotic collisions through instant virtual geofenced Danger Zone boundary enforcement.
- Automate the evidentiary audit trail by cryptographically signing violation frames and instantaneously generating standardized legal notices (`Form-06_AI_PPE_Violation_Notice.md`).
- Integrate directly with Insilos ERP to push emergency pause commands to Shop Floor tablets and automatically update contractor safety qualification ratings.

---

## 2. SCOPE & MONITORED FACILITY ZONES

2.1. This procedure applies to all industrial zones covered by the Insilos AI CCTV network:
- **Zone 1: CNC Laser Cutting Bay**: Three 20kW fiber laser cutters processing SS400 carbon steel plates; high-pressure nitrogen gas manifolds and automated shuttle loading tables.
- **Zone 2: Automated Robotic Welding Cells**: 6-axis industrial robot arms, rotary positioners, plasma arc torches, and intense ultraviolet/infrared radiation hazards.
- **Zone 3: Cát Lái Maritime Container Terminal**: Ship-to-shore gantry cranes, rubber-tyred gantry (RTG) container stacks, terminal tractor trailer lanes, and heavy forklift corridors.
- **Zone 4: Heavy Stamping & Press Lines**: 500-ton hydraulic forming presses, uncoiler feeds, and overhead coil crane staging bays.

2.2. All personnel entering these zones—including full-time machinists, maintenance technicians, logistics drivers, sub-contractors, management executives, and government auditors—are subject to continuous AI safety monitoring.

---

## 3. NORMATIVE REFERENCES & LEGAL FOUNDATION

This SOP enforces compliance with and references:
- **ISO 45001:2018**: Occupational Health and Safety Management Systems (Clause 8.1: Operational planning and control; Clause 8.2: Emergency preparedness and response).
- **Law on Occupational Safety and Health No. 84/2015/QH13 (Vietnam)**: Articles 16, 23, and 24 regarding workplace safety conditions, employer obligations, and worker responsibilities to wear provided PPE.
- **Government Decree No. 12/2022/ND-CP**: Article 32 on administrative penalties for violations of regulations on personal protective equipment (penalties ranging from 1,000,000 to 50,000,000 VND for individuals and employers).
- **Government Decree No. 44/2016/ND-CP**: Mandatory technical standards for working environment monitoring and high-risk equipment operation.
- **TCVN 6407:1998**: National standard for industrial safety helmets.
- **ISO 20471:2013 / EN ISO 20471**: High visibility clothing — Test methods and requirements (Class 2 / Class 3 high-concurrency retro-reflective tape).
- **IEC 62443**: Industrial communication networks — Network and system security for industrial automation and control systems.

---

## 4. SYSTEM ARCHITECTURE & EDGE INFERENCE PIPELINE

The Insilos AI Safety Surveillance engine operates on a decentralized edge computing architecture engineered for ultra-low latency and localized fail-safe resilience:

```
[4K Industrial IP Camera] (RTSP Stream, 25 FPS, H.265)
          |
          v
[Edge AI Inference Server (NVIDIA Jetson AGX Orin / RTX TensorRT)]
  - Frame Ingestion & Pre-processing (Letterboxing, Normalization)
  - Deep Neural Network Detection (Custom-Trained Insilos-YOLO-HSE)
  - Geofence Polygon Intersection Calculation (Point-in-Polygon Engine)
  - Temporal Persistence Filter (3-Frame Minimum Threshold)
          |
          +-------------------------------------------------------+
          |                                                       |
          | If Violation Confirmed (Persistence >= 3 Frames)      | Normal Flow
          v                                                       v
+-------------------------------+                       +-------------------+
| FIELD EMERGENCY ALARM SYSTEM  |                       | GRC Telemetry Bus |
| - Localized 95dB Siren Active |                       | (MQTT Keepalive)  |
| - Rotating Red Strobe Beacon  |                       +-------------------+
| - Shop Floor Tablet Broadcast |
+-------------------------------+
          |
          v
+-------------------------------+
| AUTOMATED ENTERPRISE SYNC     |
| 1. SHA-256 Evidentiary Hash   |
| 2. GRC Violation Creation     |
| 3. Insilos ERP Shop Floor Pause      |
| 4. Form-06 Citation Dispatch  |
+-------------------------------+
```

### 4.1. Detection Classes & Target Definitions

| Class ID | Target Class Identifier | Visual Annotation HUD | Strict Engineering Definition & Acceptance Criteria |
| :---: | :--- | :--- | :--- |
| **0** | `person` | Grey bounding box | Human entity detected within the camera field of view, establishing the root bounding anchor. |
| **1** | `helmet_compliant` | Green bounding box | Hard hat conforming to TCVN 6407 / EN 397 worn directly on crown of head with chin strap secured. |
| **2** | `helmet_violation` | **Flashing Red box** | Bare head, soft baseball cap, hoodie, or hard hat carried by hand or perched backwards without strap. |
| **3** | `vest_compliant` | Green bounding box | High-visibility fluorescent jacket/vest conforming to ISO 20471 Class 2/3 with dual retro-reflective bands. |
| **4** | `vest_violation` | **Flashing Red box** | Standard civilian clothing, dark workwear, or unzipped vest where reflective tape is obscured $> 30\%$. |
| **5** | `danger_zone_intrusion`| **Pulsing Red / Strobe**| Any portion of person bounding box intersecting a designated virtual geofence polygon (e.g., crane path). |
| **6** | `man_down_fall` | **Solid Red Warning** | Horizontal bounding box aspect ratio ($W/H > 2.0$) with zero centroid velocity for $\ge 5.0$ seconds. |

### 4.2. Precision Thresholds & Temporal Persistence Filtering
1. **Confidence Threshold**: The inference engine enforces a strict classification confidence cutoff:
   - $\text{Confidence}_{\text{PPE}} \ge 0.85$ (85.0% mathematical certainty).
   - $\text{Confidence}_{\text{Person}} \ge 0.80$ (80.0% mathematical certainty).
   - Non-Maximum Suppression (NMS) Intersection-over-Union (IoU) threshold = $0.45$.
2. **Temporal Persistence Filter**:
   - To eliminate false alarms caused by temporary camera occlusion, forklift mast passes, or transient optical flare, the engine utilizes a temporal sliding window.
   - An alarm state is triggered **ONLY** when a violation is detected in three (3) consecutive frames:
     $$\text{Alarm Condition} = \prod_{k=t-2}^{t} \mathbb{I}(\text{ClassViolation}_k) == 1$$
   - At 25 frames per second, this represents an ultra-fast verification window of 120 milliseconds.
3. **Latency Budgets**:
   - Camera frame capture and RTSP decoding: $\le 30$ ms.
   - TensorRT FP16 neural network inference: $\le 25$ ms.
   - Polygon collision check and logic validation: $\le 10$ ms.
   - Local GPIO siren and strobe relay trip: $\le 15$ ms.
   - **Total End-to-End Field Alarm Latency**: $\le 80$ ms (Guaranteed well beneath the 350 ms safety limit).

---

## 5. FIELD WARNING & SIREN ESCALATION PROTOCOL

When the persistence filter confirms an active safety violation, the system executes an automated, multi-tiered escalation protocol:

```
[PERSISTENCE VERIFIED (>= 120ms)]
          |
          +---> TIER 1: PHYSICAL FIELD ALARM (< 80ms)
          |     - 95dB Pulsed Horn Active (880 Hz <-> 1240 Hz)
          |     - Red LED Strobe Flashes at 2.5 Hz
          |
          +---> TIER 2: SHOP FLOOR TABLET NOTIFICATION (< 200ms)
          |     - Insilos ERP Shop Floor Screen Flashes Red Banner
          |     - Audible Chime on Workstation Tablet
          |
          +---> TIER 3: GRC AUTOMATION & CITATION (< 500ms)
          |     - High-Res Frame Captured & SHA-256 Hashed
          |     - Form-06_AI_PPE_Violation_Notice Auto-Generated
          |     - Push Alert Dispatched to Duty HSE Officer Phone
```

### 5.1. Tier 1: Localized Physical Siren & Visual Strobe Beacon
1. Every monitored workshop bay is equipped with an explosion-proof industrial sounder-strobe unit mounted 4 meters above the floor.
2. The acoustic siren emits a dual-frequency sweep alternating between 880 Hz and 1240 Hz at an output of 95 dB(A) at 1 meter, engineered to cut through ambient industrial background noise (metal cutting, stamping) without causing permanent hearing trauma.
3. Simultaneously, a high-intensity red LED strobe pulses at 2.5 Hz (150 flashes per minute), providing immediate visual warning to workers wearing hearing protection.

### 5.2. Tier 2: Insilos ERP Shop Floor Tablet Alert
1. The edge system emits an encrypted WebSocket event to the local Insilos ERP server (`http://localhost:28069/shopfloor/alert`).
2. The Shop Floor terminal mounted adjacent to the machine cell automatically freezes normal screen interactions and displays a high-visibility modal:
   ```
   ===========================================================
   [!] CRITICAL SAFETY ALERT: PPE NON-COMPLIANCE DETECTED [!]
   LOCATION: ZONE-A-LASER-CNC-01 | TIMESTAMP: 08:42:15.302 UTC
   VIOLATION: NO SAFETY HELMET DETECTED ON ACTIVE OPERATOR
   IMMEDIATE ACTION: STEP BACK TO SAFETY ZONE AND EQUIP HARD HAT
   ===========================================================
   ```
3. The machine operator must physically step back from the hazard line and press the illuminated amber "Acknowledge Hazard" button after equipping their PPE to clear the screen lock.

### 5.3. Tier 3: Vertical GRC Telemetry & Automated Citation Generation
1. The edge engine captures the pristine 1080p frame at the exact moment of alarm, overlays the bounding box HUD with timestamp and confidence metrics, and calculates the SHA-256 hash.
2. The engine executes an authorized REST call to Vertical GRC (`POST /items/hse_violations`), uploading the image asset and JSON telemetry.
3. Vertical GRC automatically renders and compiles `Form-06_AI_PPE_Violation_Notice.md`, linking the contractor profile or employee badge number via facial match or RFID proximity logs.
4. An automated alert is routed to the on-duty HSE Officer's mobile device via the Insilos Emergency Telegram Bot with deep links to the GRC violation record.

---

## 6. FIELD OFFICER IMMEDIATE INTERVENTION PROTOCOL

Upon sounding of an AI Vision siren or receipt of an automated push alert, the designated Zone Safety Officer or Area Supervisor must execute the following physical response protocol:

```
+---------------------------------------------------------------------------------------------------+
| STEP 1: IMMEDIATE PHYSICAL STAND-DOWN                                                             |
| Approach the violator immediately; issue verbal command: "SAFETY STAND-DOWN - WORK HALTED!"      |
+---------------------------------------------------------------------------------------------------+
                                                  |
                                                  v
+---------------------------------------------------------------------------------------------------+
| STEP 2: IMMEDIATE HAZARD REMOVAL                                                                  |
| Escort worker to the designated Green Safe Walkway; verify immediate donning of required PPE.    |
+---------------------------------------------------------------------------------------------------+
                                                  |
                                                  v
+---------------------------------------------------------------------------------------------------+
| STEP 3: DIGITAL BADGE AUDIT & FORM-06 CITATION                                                    |
| Scan worker RFID badge using GRC Mobile Terminal; verify pre-populated Form-06; issue citation.   |
+---------------------------------------------------------------------------------------------------+
                                                  |
                                                  v
+---------------------------------------------------------------------------------------------------+
| STEP 4: RETRAINING & SIGN-OFF                                                                     |
| Conduct on-the-spot 10-minute safety briefing; collect digital worker signature on tablet.       |
+---------------------------------------------------------------------------------------------------+
```

### 6.1. Step 1: Immediate Stand-Down & Equipment Neutralization
- If the violation involves **Danger Zone Intrusion** (e.g., worker stepping inside the rotating perimeter of a gantry crane or laser shuttle table), the Safety Officer must immediately strike the nearest physical Emergency Stop (E-Stop) button if the automated interlock has not already tripped.
- Order all concurrent work in the cell to cease immediately.

### 6.2. Step 2: Safe Relocation & PPE Donning
- Escort the individual outside the boundary of the hazard cell onto the painted green pedestrian safety walkway.
- Verify whether the worker possesses the required PPE on their person (e.g., hard hat hanging from tool belt) or if replacement gear must be retrieved from the safety station.
- Inspect the physical condition of the PPE for cracks, expired impact shells (exceeding 3-year manufacturer lifespan), or degraded reflective tape.

### 6.3. Step 3: Identity Verification & Digital Citation Sign-Off
- Scan the worker’s smart RFID badge or enter their employee/contractor ID into the Insilos GRC mobile app.
- Review the captured AI photographic evidence on the tablet with the worker.
- Present `Form-06_AI_PPE_Violation_Notice.md`. The worker and the Safety Officer must execute digital signatures directly on the mobile screen.

---

## 7. DISCIPLINARY ESCALATION & PENALTY STRUCTURE

Under Decree 12/2022/ND-CP Article 32 and Insilos Corporate HSE Policy, safety violations detected by AI computer vision are subjected to a progressive, three-strike disciplinary schedule:

| Offense Frequency | Disciplinary Action Category | Statutory & Corporate Penalty Measure | Administrative Consequence |
| :---: | :--- | :--- | :--- |
| **First Offense (Strike 1)** | **Formal Written Warning** | Corporate internal citation (`Form-06`); 500,000 VND internal compliance deduction. | Mandatory 2-hour safety retraining; logged in permanent HR/GRC safety record. |
| **Second Offense (Strike 2)** (Within 6 months) | **Suspension & Statutory Fine** | Statutory fine under Decree 12/2022/ND-CP (1,500,000 to 3,000,000 VND). | Immediate 3-day suspension from site access; contractor company receives formal demerit. |
| **Third Offense (Strike 3)** (Within 12 months) | **Revocation & Termination** | Permanent revocation of Insilos facility site access badge. Formal reporting to DOLISA. | Contract termination for internal employee; immediate disqualification and PO freeze for contractor in Insilos ERP. |

---

## 8. FALSE POSITIVE AUDIT & DISPUTE RESOLUTION PROTOCOL

8.1. **Worker Right to Appeal**: Any worker or sub-contractor who asserts that an automated AI detection was an erroneous false positive (e.g., hard hat color blended with machine background, specialized flame-retardant welding hood mistaken for bare head) has the absolute right to lodge a formal dispute within twenty-four (24) hours of citation issuance.

8.2. **Dispute Investigation Workflow**:
1. The worker or contractor submits an appeal via the Insilos Portal referencing the `Form-06` Citation ID.
2. The Corporate HSE Systems Engineer extracts the raw 10-second uncompressed video clip surrounding the trigger timestamp from the edge server archive.
3. The video is analyzed in the GRC Forensic Review tool:
   - Frame-by-frame bounding box confidence inspection.
   - Verification of lighting conditions, solar glare, or foreign object occlusion.
4. **Resolution Outcome**:
   - If the review committee confirms a false positive, the violation is formally overturned in GRC, the financial deduction is nullified, and the video frames are labeled and added to the machine learning retraining pipeline to improve future model accuracy.
   - The decision is communicated in writing to the worker within forty-eight (48) hours.

---

## 9. HARDWARE MAINTENANCE, CALIBRATION & GEOFENCE GOVERNANCE

To maintain target inference accuracy ($mAP50 \ge 92.5\%$), the following preventative maintenance schedule is mandatory:

| Frequency | Maintenance Activity | Responsible Party | Verification Protocol in Insilos ERP |
| :---: | :--- | :---: | :--- |
| **Daily (Shift Handover)** | Optical inspection and air-jet cleaning of camera lens protective glass enclosures. | Duty Shift Electrician | Logged on Insilos ERP Shift Checklist. |
| **Weekly** | Geofence virtual polygon alignment check against physical floor markings and robot travel limits. | HSE Systems Specialist | Completed in GRC Vision Admin Console. |
| **Monthly** | Audio decibel measurement of field sirens (verified $\ge 95\text{ dB}$ at 1 meter) and strobe lux output. | Facilities Maintenance | Insilos ERP Preventive Maintenance WO. |
| **Quarterly** | Neural network retraining and benchmark evaluation on newly collected site-specific edge cases. | Computer Vision AI Engineer | Accuracy validation report archived in GRC. |
