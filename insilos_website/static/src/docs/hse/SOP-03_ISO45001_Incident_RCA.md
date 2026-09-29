# STANDARD OPERATING PROCEDURE: INCIDENT & NEAR-MISS REPORTING, CLASSIFICATION, INVESTIGATION & ROOT CAUSE ANALYSIS (RCA)

**Document Identifier**: `INSILOS-SOP-HSE-003`  
**Revision Number**: `3.0`  
**Effective Date**: `2026-10-01`  
**Review Cycle**: `Annual`  
**Standard Compliance**: `ISO 45001:2018 (Clause 10.2), Vietnam Law on OSH No. 84/2015/QH13, Decree 39/2016/ND-CP, Decree 12/2022/ND-CP, OSHA 29 CFR 1904`  
**System Integrations**: `Insilos GRC (hse_incidents, hse_capa) <-> Insilos ERP (Insilos ERP account.move Financial Reserves & maintenance.equipment Risk Profiling)`  

---

## 1. PURPOSE & PRINCIPLES

1.1. This Standard Operating Procedure (SOP) defines the mandatory corporate process for immediate notification, categorization, scene preservation, root cause investigation, corrective action tracking, and statutory reporting of all occupational injuries, illnesses, equipment damages, environmental releases, and Near-Miss events occurring across Insilos industrial assets and maritime operations.

1.2. **The "Just Culture" Principle**: Insilos enforces a fair, transparent, and non-punitive reporting culture. Personnel who report incidents, unsafe conditions, or near-misses in good faith shall be protected from disciplinary retaliation. Disciplinary proceedings under Decree 12/2022/ND-CP are strictly reserved for reckless disregard of safety rules, willful gross negligence, deliberate sabotage, failure to report an incident, or unauthorized tampering with physical evidence.

1.3. **Core Objectives**:
- Prevent incident recurrence by identifying and rectifying systemic organizational, engineering, and latent procedural deficiencies rather than merely assigning superficial worker blame.
- Comply with all statutory reporting deadlines mandated by the Vietnamese Ministry of Labor, Invalids and Social Affairs (MOLISA) under Decree 39/2016/ND-CP.
- Automate real-time synchronization between GRC safety incident logs and Insilos ERP financial accounting to record repair accruals, insurance claims, and asset reliability de-rating.

---

## 2. SCOPE & APPLICABILITY

2.1. This procedure applies without exception to:
- All permanent and temporary employees, direct sub-contractors, equipment vendors, transport drivers, logistics partners, and official facility visitors.
- All physical facilities, including laser CNC cutting bays, robotic welding workshops, mechanical assembly zones, container terminal yards, maritime gantry cranes, marine vessels docked at berths, chemical warehouses, and administrative headquarters.
- All incident types: Occupational Injuries, Occupational Illnesses, High Potential (HiPo) Near-Misses, Fires and Explosions, Process Chemical Spills, Mobile Plant Collisions, and Structural Collapses.

---

## 3. NORMATIVE REFERENCES & STATUTORY LAWS

This SOP is governed by and strictly adheres to:
- **ISO 45001:2018**: Occupational Health and Safety Management Systems — Requirements with guidance for use (Clause 10.2: Incident, non-conformity and corrective action; Clause 9.1.2: Evaluation of compliance).
- **Law on Occupational Safety and Health No. 84/2015/QH13**: Enacted by the National Assembly of the Socialist Republic of Vietnam (Articles 34, 35, 36 on reporting, investigation, and compensation for occupational accidents).
- **Government Decree No. 39/2016/ND-CP**: Guiding the implementation of the Law on Occupational Safety and Health, detailing investigation committees, notification timelines, and official dossier formats.
- **Government Decree No. 12/2022/ND-CP**: Regulations on penalties for administrative violations in the field of labor, occupational safety, and social insurance.
- **Circular No. 13/2016/TT-BLDTBXH**: Promulgating the list of occupational diseases eligible for social insurance benefits.
- **OSHA 29 CFR Part 1904**: Recording and Reporting Occupational Injuries and Illnesses.

---

## 4. DEFINITIONS & INCIDENT TAXONOMY

| Term / Acronym | Technical Definition |
| :--- | :--- |
| **Incident** | An unplanned, unexpected event arising out of or in the course of work that resulted in, or had the credible potential to result in, injury, illness, environmental damage, or asset loss. |
| **Near-Miss** | An unplanned event that did not result in injury, illness, or damage, but had the realistic potential to do so under slightly altered circumstances (e.g., a 2-ton steel plate slipping from a clamp and impacting the floor 1 meter from a worker). |
| **High Potential (HiPo)** | Any near-miss or minor incident where the realistic potential consequence, had one failure barrier failed, was a single or multiple fatality or catastrophic asset loss. |
| **First Aid Case (FAC)** | Minor injury requiring one-time treatment and subsequent observation (e.g., surface scratches, minor burns, eye flushing) that does not require professional medical intervention or lost workdays. |
| **Medical Treatment Case (MTC)** | An injury requiring clinical diagnosis and treatment by a licensed medical practitioner (e.g., suturing wounds, prescription medication, casting) beyond first aid, with or without lost time. |
| **Lost Time Injury (LTI)** | An occupational injury resulting in a worker being medically certified as unable to return to their regular job on any scheduled shift subsequent to the day of injury. |
| **Root Cause** | The fundamental, underlying organizational, technical, or design defect that, if eliminated, will permanently prevent recurrence of the event. |

---

## 5. ROLES & RESPONSIBILITIES (RACI MATRIX)

| Investigation Phase | Direct Witness / Involved Worker | Immediate Supervisor | Area Authority (Workshop Head) | HSE Lead Investigator | Plant Director / GM | Corporate Legal & HR |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| Emergency Care & Scene Quarantine | **R** | **A / R** | C | C | I | I |
| Initial Notification in Insilos GRC | **R** | **A / R** | C | I | I | I |
| Severity Triage & Statutory Notification | I | C | C | **R** | **A** | C |
| Forensic Evidence Collection (CCTV, Logs) | I | C | C | **A / R** | I | I |
| RCA Team Formation (5-Why & Fishbone) | C | C | C | **A / R** | I | I |
| ERP Financial Accrual Trigger (`account.move`) | I | I | I | C | **A** | **R** |
| CAPA Formulation & Action Assignment | I | C | **R** | **A** | I | I |
| 30/60/90-Day CAPA Effectiveness Audit | I | I | C | **A / R** | I | I |

---

## 6. INCIDENT SEVERITY CLASSIFICATION & NOTIFICATION MATRIX

Insilos classifies incidents into five distinct operational severity tiers (Level 1 to Level 5) to establish strict notification timelines and investigation depths:

```
[LEVEL 5: CATASTROPHIC] ----> Immediate MOLISA/DOLISA Notification (< 1h) | CEO Lead | Police/State Board
          ^
[LEVEL 4: SEVERE] -----------> Immediate Executive Escalation (< 15m) | DOLISA (< 2h) | Formal Committee
          ^
[LEVEL 3: MODERATE] ---------> Notification to VP Operations (< 1h) | Full RCA Team | Closure 14 Days
          ^
[LEVEL 2: MINOR] ------------> Workshop Head Notification (< 2h) | HSE Lead RCA | Closure 7 Days
          ^
[LEVEL 1: NEAR-MISS] --------> Shift Supervisor (< 4h) | Rapid 5-Why in GRC | Closure 48 Hours
```

| Severity Tier | Human Impact Threshold | Asset / Financial Damage | Environmental Contamination | Internal SLA Notification | External / Statutory SLA (Decree 39/2016) | Investigation Lead |
| :---: | :--- | :--- | :--- | :--- | :--- | :--- |
| **Level 1 (Near-Miss)** | Zero injury; unsafe condition or near-hit with low potential. | Financial loss $< 10,000,000$ VND ($< \$400$). | Zero off-containment release. | Within 4 hours via GRC portal. | None required. | Area Supervisor & HSE Officer. |
| **Level 2 (Minor)** | First Aid Case (FAC) or minor MTC with lost time $\le 3$ days. | Loss between $10,000,000$ and $100,000,000$ VND. | Localized chemical spill $< 50$ liters neutralized within shift. | Within 2 hours to Area Authority & HSE Lead. | Internal logging; periodic semi-annual DOLISA statistics. | HSE Specialist & Workshop Lead. |
| **Level 3 (Moderate)** | LTI $> 3$ days, reversible bone fracture, second-degree burn. | Loss between $100,000,000$ and $500,000,000$ VND. | Contained release requiring external hazardous waste disposal. | Within 1 hour to Plant Director and Corporate HSE. | Internal investigation report filed within 30 days. | Multi-disciplinary RCA Team led by Senior HSE Engineer. |
| **Level 4 (Severe)** | Amputation, loss of eye, permanent partial disability, or single critical condition. | Loss between $500,000,000$ and $2,500,000,000$ VND. | Toxic release beyond site boundary requiring municipal notice. | Within 15 minutes to CEO and Executive Board. | **Within 2 hours** to DOLISA, Police Investigation Agency, and Health Dept. | Formal Internal Board of Inquiry appointed by Managing Director. |
| **Level 5 (Catastrophic)**| Single or multiple fatalities, permanent total disability of $\ge 2$ workers. | Asset destruction $> 2,500,000,000$ VND ($> \$100,000$). | Major marine/river oil slick or regional toxic plume. | **Immediate (within 10 minutes)** to Executive Leadership. | **Immediate / within 1 hour** to Central MOLISA, DOLISA, and Provincial People's Committee. | State Investigation Committee under Decree 39/2016/ND-CP Article 13. |

---

## 7. AUTOMATED GRC-TO-ERP INTEGRATION WORKFLOW

To prevent disconnects between health/safety records and financial balance sheets, Insilos maintains an automated bi-directional integration bridge between Vertical GRC and Insilos ERP:

```
[Incident Occurs on Site]
          |
          v
Logged in Insilos GRC (`POST /items/hse_incidents`)
          |
          +-------------------------> Webhook Trigger: `incident_created`
                                                   |
                                                   v
                                     [Insilos Connector Service]
                                                   |
                                                   v
                               [Insilos ERP Accounting Engine]
                               1. Instantiates Draft `account.move` on Journal `MISC`:
                                  - Dr: 811000 (Occupational Safety Incident Losses)
                                  - Cr: 352000 (Provisions for Liabilities & Claims)
                               2. Elevates Machine Risk Factor on `maintenance.equipment`:
                                  - Doubled preventive inspection frequency.
                                  - Auto-suspends related equipment work orders.
```

### 7.1. Financial Accrual Processing
1. When a Level 3, 4, or 5 incident is created in GRC, GRC transmits a signed webhook payload to Insilos ERP.
2. The connector calls Insilos ERP XML-RPC to generate a draft journal entry (`account.move`) capturing:
   - Estimated primary medical expenses and hospitalization reserves.
   - Statutory compensation reserves under Article 38 of Vietnam Law on OSH.
   - Asset write-down or mechanical replacement estimates.
3. As actual invoices arrive in Insilos ERP Accounts Payable (vendor repairs, hospital billing), they are tagged with the specific `grc_incident_id` analytic distribution tag, allowing real-time comparison between estimated and actual incident losses.

### 7.2. Asset Reliability & Maintenance Elevation
1. Insilos ERP locates the machine asset record linked to the incident location (e.g., `AST-LASER-CNC-01`).
2. The connector modifies the equipment risk index (`hse_risk_multiplier = 2.0`), which automatically halves the operational run-hours interval before mandatory preventive maintenance overhauls.

---

## 8. INVESTIGATION PROTOCOL & EVIDENCE PRESERVATION

### 8.1. Immediate Scene Quarantine (The "Golden 48 Hours")
1. The Area Authority must immediately erect physical red barricade tape around the incident perimeter spanning a minimum 10-meter radius.
2. Under Decree 39/2016/ND-CP Article 18, altering the scene of a serious or fatal occupational accident is strictly prohibited by law, except where necessary to rescue injured victims or prevent immediate secondary disaster.
3. If equipment must be moved for life-saving operations, the investigator must photograph the undisturbed positions, mark tire/component resting points with spray paint, and document original valve and breaker positions.

### 8.2. Digital Telemetry & Video Evidence Extraction
1. **AI Vision Archive**: The Lead Investigator requests an immediate data pull from the edge AI server (SOP-04). The 30 minutes of footage preceding the incident and 15 minutes post-incident are exported in uncompressed 1080p MP4 format along with the JSON telemetry metadata (bounding boxes, confidence values, alarm logs).
2. **Cryptographic Sealing**: The digital video file is hashed using SHA-256 (`sha256sum incident_cctv.mp4`) and recorded in the GRC evidence register to preserve chain of custody for court and labor inspection proceedings.
3. **Control System Logs**: Extract PLC event logs, SCADA historian graphs (pressures, temperatures, flow rates), and Insilos ERP work order records.

### 8.3. Witness Interview Protocol
1. Conduct interviews individually within 12 hours of the event to capture fresh, uncorrupted recollections.
2. Structure interviews using open-ended questions: *"Walk me through the sequence of events leading up to the sound of the alarm,"* rather than leading questions.
3. Maintain an empathetic, non-accusatory environment to encourage transparent disclosure of operational shortcuts and latent systemic pressures.

---

## 9. ROOT CAUSE ANALYSIS (RCA) METHODOLOGY

Insilos mandates a two-pronged investigative analysis for all Level 2 and above incidents: **The Ishikawa Fishbone Analysis** (for broad multi-factorial discovery) followed by **The 5-Why Root Cause Interrogation** (for deep causal penetration).

### 9.1. The Ishikawa (Fishbone) 6M Framework

```
                 ISHIKAWA 6M CAUSAL DIAGRAM
  MAN (Personnel)            MACHINE (Equipment)         METHOD (Procedures)
       \                          \                           \
        \   Fatigue (Overtime)     \   Interlock Bypassed      \   Ambiguous SOP
         \                          \                           \
          +--------------------------+---------------------------+-----> [INCIDENT /
         /                          /                           /        TOP EVENT]
        /   Incorrect Raw Mat.     /   Uncalibrated Sensor     /   Poor Illum.
       /                          /                           /
  MATERIAL                   MEASUREMENT                 MILIEU (Environment)
```

The investigation team must populate every branch of the 6M diagram:
1. **Man (Personnel & Ergonomics)**: Were workers qualified, trained, rested, and physically capable? Were cognitive overloads or commercial pressures present?
2. **Machine (Equipment & Hardware)**: Did any component suffer mechanical fatigue, electrical breakdown, or software failure? Was the machine properly maintained in Insilos ERP?
3. **Material (Substances & Parts)**: Did raw steel plates, hydraulic oils, shielding gases, or consumable cutting nozzles meet engineering specifications?
4. **Method (Procedures & Work Instructions)**: Did a valid SOP exist? Was the e-PTW properly issued? Did workers deviate from standard instructions, and if so, why?
5. **Measurement (Inspection & Instrumentation)**: Did pressure gauges, torque wrenches, gas sniffers, or AI vision systems provide accurate, calibrated data?
6. **Milieu (Environment & Working Conditions)**: Were ambient temperatures, lighting levels (lux), noise, ventilation, wet surfaces, or rain factors in the event?

### 9.2. The 5-Why Root Cause Interrogation Protocol

The team must take the critical contributing factors identified in the Fishbone and drive them through a rigorous, linear 5-Why chain until arriving at an **Actionable Organizational Root Cause**. Blaming "Human Error" or "Carelessness" as a root cause is strictly prohibited.

#### Exemplary 5-Why Analysis: Robotic Welder Arm Collision Incident
- **Event**: A 6-axis robotic welding manipulator struck a maintenance technician's shoulder inside Welding Cell 3, causing a clavicle fracture (Level 3 Incident).
- **Why 1**: Why did the robotic arm move while the technician was inside the cell?  
  *Answer*: The robot was executing an automatic tip-cleaning cycle while the technician was adjusting the wire spool.
- **Why 2**: Why was the cell energized and active while the technician was inside?  
  *Answer*: The safety interlock gate switch had been physically bypassed with an external jumper bypass key.
- **Why 3**: Why was the safety interlock bypassed?  
  *Answer*: The technician needed to visually monitor wire feeding under load, and the standard safety interlock killed total power upon door opening.
- **Why 4**: Why was there no safe, slow-speed "Teach / Inspection Mode" provided to the technician?  
  *Answer*: The engineering procurement specification for the robot cell did not mandate a three-position enabling switch (dead-man switch) pendant for jog mode.
- **Why 5 (Root Cause)**: Why was the engineering procurement specification lacking this functional safety requirement?  
  *Answer*: The plant Management of Change (MOC) procedure failed to mandate a functional safety engineer sign-off on new automated machinery purchases before issuing purchase orders in Insilos ERP.

---

## 10. CORRECTIVE AND PREVENTIVE ACTIONS (CAPA) LIFECYCLE

10.1. **SMART Action Formulation**: Every identified root cause must have at least one assigned CAPA complying with the SMART criteria:
- **S**pecific: Concrete engineering or procedural modification.
- **M**easurable: Verifiable completion criteria (e.g., *Install dual-channel safety relay and re-test trip logic*).
- **A**chievable: Technically and operationally feasible within site constraints.
- **R**elevant: Directly addresses the root cause identified in the 5-Why chain.
- **T**ime-bound: Strict deadline assigned in Insilos GRC (Level 1: 14 days; Level 2: 30 days; Level 3/4/5: 45 days).

10.2. **Post-Implementation Effectiveness Audits**:
- Closing a CAPA requires more than merely checking a box upon implementation.
- The HSE Lead must perform three formal verification audits:
  - **30-Day Check**: Confirm physical installation and operator comprehension.
  - **60-Day Check**: Verify no operational workarounds have developed.
  - **90-Day Audit**: Validate sustained performance and lack of repeat occurrences.
- GRC will not archive an incident record until the 90-day effectiveness audit is signed off by the Corporate HSE Director.

---

## 11. STATUTORY REPORTING & LEGAL DOSSIER (DECREE 39/2016/ND-CP)

11.1. For all Level 4 and Level 5 occupational accidents, the Corporate Legal and HSE Department must compile the statutory accident investigation dossier within the statutory timeframes:
- **Deadlines**: 4 days for light accidents; 7 days for serious accidents causing injuries to 1 worker; 20 days for serious accidents causing injuries to $\ge 2$ workers; 30 days for fatal accidents (extendable to 45 days for complex engineering failures).
- **Dossier Contents**:
  1. Minute of scene examination (Form 01 - Decree 39).
  2. Scene photographic scheme and diagram.
  3. Minute of autopsy / medical injury assessment.
  4. Written testimony of the victim (if conscious), witnesses, and supervisors.
  5. Technical verification and forensic calculation reports.
  6. Final Occupational Accident Investigation Minutes (Form 06 - Decree 39).
