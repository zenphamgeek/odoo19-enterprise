# STANDARD OPERATING PROCEDURE: HAZARD IDENTIFICATION, 5X5 QUANTITATIVE RISK ASSESSMENT & BOWTIE BARRIER ANALYSIS

**Document Identifier**: `INSILOS-SOP-HSE-002`  
**Revision Number**: `3.0`  
**Effective Date**: `2026-10-01`  
**Review Cycle**: `Annual`  
**Standard Compliance**: `ISO 45001:2018 (Clause 6.1.2), ISO 31000:2018, IEC 61508 / IEC 61511, Vietnam Law on OSH No. 84/2015/QH13, Decree 39/2016/ND-CP, Decree 44/2016/ND-CP`  
**System Integrations**: `Insilos GRC (Risk Models & Barrier Management) <-> Insilos ERP (Insilos ERP Preventive Maintenance & Safety Interlocks)`  

---

## 1. PURPOSE & OBJECTIVES

1.1. This Standard Operating Procedure (SOP) defines the mandatory corporate protocol for proactively identifying occupational, physical, chemical, mechanical, and process safety hazards, quantifying operational risks via a calibrated 5x5 risk matrix, and constructing dynamic Bowtie barrier defense models across all industrial facilities of Insilos Group.

1.2. The primary objectives are:
- Establish a rigorous, repeatable methodology for evaluating risk to achieve the ALARP (As Low As Reasonably Practicable) standard.
- Bridge qualitative hazard recognition and quantitative risk governance by maintaining an active digital risk register in Insilos GRC (`risk_models` and `hse_risk_register`).
- Deploy barrier-based thinking (Bowtie methodology) to protect high-hazard operations against Major Accident Hazards (MAH) through continuous monitoring of preventive and mitigating barriers.
- Prevent organizational blindness to barrier degradation by integrating maintenance health telemetry from Insilos ERP into GRC safety dashboards.

---

## 2. SCOPE & FIELD OF APPLICATION

2.1. This procedure applies across the complete operational lifecycle of all facilities, plant assets, logistics yards, and maritime berths operated by Insilos, including:
- Routine manufacturing operations (e.g., CNC laser cutting, robotic welding, stamping, shot blasting).
- Non-routine activities (e.g., turnaround overhauls, equipment commissioning, chemical tank de-sludging).
- Simultaneous operations (SIMOPS) and contractor management.
- Design modifications, equipment retrofits, and process changes under Management of Change (MOC).

---

## 3. NORMATIVE REFERENCES

This SOP directly implements and complies with:
- **ISO 45001:2018**: Clauses 6.1.2.1 (Hazard identification), 6.1.2.2 (Assessment of OH&S risks and other risks to the OH&S management system), and 8.1.2 (Eliminating hazards and reducing OH&S risks).
- **ISO 31000:2018**: Risk Management — Guidelines (Principles, Framework, and Process).
- **IEC 61508 / IEC 61511**: Functional safety of electrical/electronic/programmable electronic safety-related systems in the process industry sector.
- **Law on Occupational Safety and Health No. 84/2015/QH13 (Vietnam)**.
- **Decree No. 39/2016/ND-CP**: Detailing the implementation of a number of articles of the Law on Occupational Safety and Health.
- **Center for Chemical Process Safety (CCPS)**: Guidelines for Initiating Events and Independent Protection Layers in Layer of Protection Analysis (LOPA) and Concept Book on Bow Ties in Risk Management.

---

## 4. DEFINITIONS & CORE CONCEPTS

| Term / Acronym | Technical Definition |
| :--- | :--- |
| **Hazard** | A source, situation, or act with an inherent potential for causing human injury, occupational illness, structural damage, environmental harm, or a combination thereof. |
| **Hazardous Event** | An incident or abnormal deviation where control over a hazard is lost, resulting in the realization of potential harm. |
| **Inherent Risk** | The baseline level of risk present in an activity or system in the complete absence of any safeguards, controls, or safety barriers. |
| **Residual Risk** | The quantitative risk level remaining after the application and verification of active engineering, administrative, and protective control barriers. |
| **ALARP** | As Low As Reasonably Practicable: The risk management standard asserting that risk must be reduced until the financial, temporal, or physical cost of further reduction is grossly disproportionate to the safety benefit achieved. |
| **Bowtie Analysis** | A visual, barrier-centric risk assessment methodology combining Fault Tree Analysis (threats leading to Top Event) and Event Tree Analysis (Top Event propagating to consequences). |
| **Top Event** | The specific critical point in time when operational control over a hazard is lost (e.g., loss of containment, structural collapse, uncommanded robotic movement), occurring prior to actual harm or damage. |
| **Preventive Barrier** | A designated physical, automated, or procedural safeguard positioned on the threat pathway (left side of the Bowtie) to stop a threat from causing the Top Event. |
| **Mitigating Barrier** | A safeguard positioned on the consequence pathway (right side of the Bowtie) that suppresses, arrests, or lessens the severity of the consequences after the Top Event has occurred. |
| **Degradation Factor** | A condition, operational failure, or environmental element that degrades or invalidates the operational readiness or integrity of a safety barrier. |

---

## 5. ROLES & RESPONSIBILITIES (RACI MATRIX)

| Activity / Task | Risk Assessor (Lead Engineer) | Area Authority (Workshop Head) | Frontline Technician / Operator | HSE Officer / Safety Specialist | Plant Director / GM |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Hazard Identification Workshops | **R** | **R** | C | **A** | I |
| 5x5 Inherent Risk Scoring | **R** | C | C | **A** | I |
| Hierarchy of Controls Selection | **R** | **R** | C | **A** | I |
| Bowtie Model Construction | **R** | C | I | **A** | I |
| Barrier Health Telemetry Setup in GRC/ERP | **R** | C | I | **A** | I |
| 5x5 Residual Risk Verification | C | **R** | I | **A** | I |
| Approval of Low/Medium Risk Activities | I | **A / R** | I | C | I |
| Approval of High/Critical Risk Activities | I | C | I | C | **A / R** |
| Post-Incident HIRA Re-evaluation | **R** | C | C | **A** | I |

---

## 6. HIERARCHY OF CONTROLS PROTOCOL

When determining corrective actions or selecting risk-reducing barriers, the multi-disciplinary assessment team must strictly apply the **Hierarchy of Controls** under ISO 45001:2018 Clause 8.1.2. Administrative controls and PPE are acceptable only as temporary interim measures or secondary back-up layers.

```
       +-------------------------------------------------------+
       | 1. ELIMINATION                                        |  MOST EFFECTIVE
       | Physically remove the hazard completely               |
       +-------------------------------------------------------+
             |
             v
       +-------------------------------------------------------+
       | 2. SUBSTITUTION                                       |
       | Replace the hazard with a lower-risk alternative      |
       +-------------------------------------------------------+
             |
             v
       +-------------------------------------------------------+
       | 3. ENGINEERING CONTROLS                               |
       | Isolate people from the hazard (Interlocks, Guards)   |
       +-------------------------------------------------------+
             |
             v
       +-------------------------------------------------------+
       | 4. ADMINISTRATIVE CONTROLS                            |
       | Change the way people work (SOPs, e-PTW, Training)    |
       +-------------------------------------------------------+
             |
             v
       +-------------------------------------------------------+
       | 5. PERSONAL PROTECTIVE EQUIPMENT (PPE)                |  LEAST EFFECTIVE
       | Protect worker with equipment (Helmet, Harness, Boots)|
       +-------------------------------------------------------+
```

1. **Elimination**: Redesign the process to eliminate the danger entirely (e.g., replacing manual high-altitude silo inspections with automated drone photogrammetry).
2. **Substitution**: Replace hazardous substances or processes with less dangerous variants (e.g., substituting toxic trichloroethylene degreaser with biodegradable aqueous citrus-based solvents).
3. **Engineering Controls**: Implement physical safeguards, mechanical interlocks, safety light curtains, localized exhaust ventilation (LEV), acoustic dampening enclosures, and automated shut-off valves that operate independently of human action.
4. **Administrative Controls**: Implement rigorous standard operating procedures, e-PTW systems, Lockout-Tagout protocols, safety signage, job rotation to limit exposure times, and accredited competency training.
5. **Personal Protective Equipment (PPE)**: Provide certified equipment (safety helmets conforming to EN 397, high-visibility garments conforming to ISO 20471 Class 3, fall-arrest harnesses conforming to EN 361) to shield personnel from residual hazards.

---

## 7. THE 5X5 QUANTITATIVE RISK ASSESSMENT MATRIX

Risk ($R$) is quantitatively defined as the mathematical product of the Probability of Occurrence ($P$) and the Severity / Consequence of Harm ($S$):

$$R = P \times S$$

### 7.1. Probability (Likelihood) Criteria (Scale 1 to 5)

| Level | Classification | Operational Frequency / Statistical Probability | Historical Occurrence Benchmark |
| :---: | :--- | :--- | :--- |
| **1** | **Improbable / Rare** | Less than once every 10 years across the global enterprise industry ($< 10^{-5}$ per operating hour). Unprecedented in local plant history. | Theoretical possibility only under multiple compounding failures. |
| **2** | **Remote** | Occurs between once every 3 years and once every 10 years within the industrial sector ($10^{-5} \text{ to } 10^{-4}$ per operating hour). | Has occurred elsewhere in comparable maritime or heavy mechanical facilities. |
| **3** | **Occasional** | Expected to occur once per year to once every 3 years within the local facility ($10^{-4} \text{ to } 10^{-3}$ per operating hour). | Has occurred within Insilos operations in the past 36 months. |
| **4** | **Frequent** | Expected to occur several times per year (monthly to quarterly frequency) during standard operations ($10^{-3} \text{ to } 10^{-2}$ per operating hour). | Observed repeatedly during regular manufacturing or logistics shifts. |
| **5** | **Continuous / Certain** | Occurs daily, weekly, or is almost certain to occur during the execution of the activity ($> 10^{-2}$ per operating hour). | Near-guaranteed occurrence without specialized barrier intervention. |

### 7.2. Severity (Consequence) Criteria (Scale 1 to 5)

To ensure comprehensive organizational impact evaluation, Severity must be assessed across four distinct impact dimensions: People, Assets, Environment, and Legal/Reputational. The highest score among the four dimensions determines the overall Severity Level.

| Level | Severity Class | People (Health & Safety) | Assets & Financial Impact | Environmental Impact | Legal, Statutory & Reputational |
| :---: | :--- | :--- | :--- | :--- | :--- |
| **1** | **Negligible** | Superficial injury, minor scratch, bruise. First-aid treatment on site; zero lost workdays (LTI = 0). | Financial damage $< 10,000,000$ VND ($< \$400$). Zero equipment downtime. | Localized minor spillage ($< 5$ liters) entirely contained within concrete bunding. | Zero regulatory non-conformance. No external community attention. |
| **2** | **Minor** | Reversible injury (minor laceration, sprain, foreign particle in eye) requiring professional medical treatment. Lost Time Injury (LTI) 1 to 3 days. | Financial loss $10,000,000$ to $100,000,000$ VND. Equipment downtime $< 12$ hours. | Spillage between 5 and 50 liters; easily neutralized on site without ground contamination. | Minor internal non-conformance. Standard statutory reporting without fines. |
| **3** | **Moderate** | Severe reversible injury (bone fracture, second-degree burn, localized dislocation). LTI 4 to 30 days. Restricted work case. | Financial loss $100,000,000$ to $500,000,000$ VND. Downtime 12 to 72 hours. | Contained release of hazardous chemical affecting $< 50\text{ m}^2$ soil or local drainage; remediated in 24 hours. | Statutory inspection audit triggered; administrative citation with fine $< 50,000,000$ VND under Decree 12/2022. |
| **4** | **Major** | Permanent partial disability, amputation, loss of vision, systemic poisoning, or single fatality. LTI $> 30$ days. | Financial loss $500,000,000$ to $2,500,000,000$ VND. Production line halted for 3 to 14 days. | Significant environmental contamination exceeding national discharge standards; ground/water migration. | Formal government inquiry; facility suspension; major regional media coverage; fine up to $200,000,000$ VND. |
| **5** | **Catastrophic** | Multiple fatalities (>= 2 workers), permanent total disability of multiple individuals. Acute community impact. | Financial loss $> 2,500,000,000$ VND ($> \$100,000$). Total destruction of critical asset (crane, CNC cell). | Massive off-site toxic release, extensive river/marine oil spill requiring national disaster intervention. | Criminal prosecution of corporate officers; permanent revocation of operating license; international brand damage. |

### 7.3. The 5x5 Quantitative Scoring Grid

The intersection of Likelihood ($P$) and Severity ($S$) yields the quantitative Risk Score ($R = 1 \text{ to } 25$):

```
+---------------------------------------------------------------------------------+
|                                5x5 RISK MATRIX GRID                             |
+-------------------+-------------------------------------------------------------+
|    PROBABILITY    |                      SEVERITY (S)                           |
|        (P)        |   1 (Negligible) | 2 (Minor) | 3 (Moderate) | 4 (Major) | 5 (Catastrophic) |
+-------------------+------------------+-----------+--------------+-----------+------------------+
| 5 (Continuous)    |     5 (YELLOW)   | 10 (AMBER)|  15 (RED)    |  20 (RED) |     25 (RED)     |
| 4 (Frequent)      |     4 (GREEN)    |  8 (YELLOW)| 12 (AMBER)  |  16 (RED) |     20 (RED)     |
| 3 (Occasional)    |     3 (GREEN)    |  6 (YELLOW)|  9 (YELLOW) |  12 (AMBER)|    15 (RED)     |
| 2 (Remote)        |     2 (GREEN)    |  4 (GREEN)|  6 (YELLOW)  |   8 (YELLOW)|   10 (AMBER)    |
| 1 (Improbable)    |     1 (GREEN)    |  2 (GREEN)|  3 (GREEN)   |   4 (GREEN) |    5 (YELLOW)    |
+-------------------+------------------+-----------+--------------+-----------+------------------+
```

### 7.4. Risk Tolerability & Escalation Governance

| Risk Score Band | Risk Level & Color | Operational Status & Action Mandate | Approval Authority Level | Mandatory Review Frequency |
| :---: | :---: | :--- | :--- | :---: |
| **1 to 4** | **LOW (Green)** | **Acceptable**: Standard operational procedures and baseline PPE are adequate. Normal management supervision. | Area Authority (Workshop Supervisor) | Annual or upon process revision |
| **5 to 9** | **MEDIUM (Yellow)** | **Tolerable if ALARP**: Specific risk reduction measures must be verified. A formal Job Safety Analysis (JSA) is required. Operations proceed with vigilance. | Workshop Superintendent & HSE Lead | Semi-annual (6 months) |
| **10 to 14** | **HIGH (Amber)** | **Undesirable / Controlled Risk**: Substantial risk requiring engineered mitigation. Work cannot commence without an active e-PTW and approved Method Statement. | Operations Director & Head of Corporate HSE | Quarterly (3 months) |
| **15 to 25** | **CRITICAL (Red)** | **Unacceptable**: Strict prohibition of activity. Immediate work stoppage (SWA). Redesign or engineered substitution mandatory before proceeding. | Managing Director / CEO & Executive Board | Monthly barrier health audit |

---

## 8. BOWTIE BARRIER METHODOLOGY

### 8.1. Architectural Structure of the Bowtie Model

The Bowtie model provides a visual, barrier-centric depiction of the operational risk profile, mapping how specific hazards could escalate into Major Accident Hazards and illustrating the independent protective barriers deployed to interrupt that progression.

```
       THREATS (Causes)                                              CONSEQUENCES (Outcomes)
   +-----------------------+                                     +-------------------------------+
   | Threat 1: Over-press. |                                     | Consequence 1: Flying Shrapnel|
   +-----------+-----------+                                     +---------------+---------------+
               |                                                                 ^
               v                                                                 |
     [Preventive Barrier 1]                                           [Mitigating Barrier 1]
     (PSV Relief Valve)                                               (Blast Enclosure Wall)
               |                                                                 ^
               v                                                                 |
   +-----------+-----------+                                     +---------------+---------------+
   | Threat 2: Corrosion   |           +---------------+         | Consequence 2: Toxic Inhalat. |
   +-----------+-----------+ --------> |   TOP EVENT   | ------> +---------------+---------------+
               |                       | Loss of Gas   |                         ^
               v                       |  Containment  |                         |
     [Preventive Barrier 2]            +---------------+              [Mitigating Barrier 2]
     (Ultrasonic Thickness)                                           (Deluge & Scrubbing System)
```

### 8.2. Core Components of the Insilos Bowtie Engine

1. **Hazard**: The dangerous condition or material in its controlled state (e.g., *High-Pressure Cryogenic Nitrogen Storage Tank at 30 bar*).
2. **Top Event**: The moment control is lost over the hazard, immediately preceding actual damage (e.g., *Uncontrolled Release of Nitrogen Gas from Ruptured Manifold*).
3. **Threats**: Credible initiating mechanisms capable of precipitating the Top Event (e.g., *Mechanical over-pressurization during truck transfer; Internal corrosion of vessel wall; External impact by transport forklift*).
4. **Preventive Barriers**: Safeguards that prevent a specific threat from culminating in the Top Event. Must meet the **ACIE** criteria: **A**chievable, **C**lear, **I**ndependent, **E**ffective.
5. **Consequences**: Severe negative outcomes resulting from the uncontrolled Top Event (e.g., *Personnel asphyxiation in enclosed workshop; Catastrophic structural rupture causing shrapnel injuries; Plant shutdown*).
6. **Mitigating Barriers**: Protective systems that minimize the propagation, intensity, or consequences of the Top Event once it occurs (e.g., *Emergency localized exhaust extraction; Continuous oxygen depletion alarm sensors; Blast deflector shields; Evacuation muster protocols*).
7. **Degradation Factors & Degradation Controls**:
   - A degradation factor weakens a barrier (e.g., *Calibration drift in nitrogen pressure relief valve*).
   - A degradation control maintains the barrier's health (e.g., *Insilos ERP monthly computerized preventive maintenance work order for recalibration*).

### 8.3. Barrier Health Monitoring Integration (GRC & Insilos ERP)

Every critical barrier identified in the Bowtie model is registered in Insilos GRC as a safety-critical element (SCE) and assigned an operational health index:
- **Green (Healthy - 100%)**: Inspection is up to date in Insilos ERP, zero maintenance backlog, physical sensors communicating via MQTT.
- **Yellow (Degraded - 60% to 90%)**: Inspection overdue by $< 15$ days, minor redundancy loss (e.g., 1 of 2 dual relief valves tagged out).
- **Red (Impaired - $< 60\%$)**: Barrier offline, bypassed, or failed during test. GRC automatically flags all associated e-PTWs with `CRITICAL_BARRIER_IMPAIRMENT` and blocks permit approvals until Insilos ERP confirms work order completion.

---

## 9. CONCRETE BOWTIE INDUSTRIAL CASE STUDIES

### 9.1. Case Study 1: SS400 Laser CNC Nitrogen Manifold Over-Pressurization
- **Hazard**: High-pressure assist nitrogen gas manifold system operating at 30 bar feeding three 20kW fiber laser cutters.
- **Top Event**: Rupture of high-pressure manifold pipe causing explosive decompression and gas release.
- **Threat Line 1: Supply Truck Over-Filling**:
  - *Preventive Barrier 1*: Dual independent spring-loaded Pressure Safety Valves (PSV-101A/B) calibrated to crack at 33 bar.
  - *Preventive Barrier 2*: Automated high-pressure emergency shut-off solenoid (ESD-101) interlocked to digital pressure transmitter PT-101 at 32 bar.
- **Threat Line 2: Fatigue Cracking from Cyclic Pressure Transients**:
  - *Preventive Barrier*: Quarterly ultrasonic non-destructive testing (NDT) inspection tracked via Insilos ERP Maintenance Asset `AST-CNC-MANIFOLD-01`.
- **Consequence 1: Atmospheric Oxygen Depletion / Personnel Asphyxiation**:
  - *Mitigating Barrier 1*: Ambient electrochemical $O_2$ sensors (ATEX Zone 2) alarming at 19.5% (amber strobe) and 18.0% (red siren + automated roof vent dump).
  - *Mitigating Barrier 2*: Self-Contained Breathing Apparatus (SCBA) stations installed at Workshop Exit Doors 2 and 4.
- **Consequence 2: High-Velocity Metal Shrapnel Impact**:
  - *Mitigating Barrier*: Reinforced 6mm polycarbonate-steel composite perimeter safety screens surrounding the manifold perimeter.

### 9.2. Case Study 2: Marine Container Gantry Crane Heavy Load Drop (Cát Lái Terminal)
- **Hazard**: Suspended 40-foot intermodal shipping container (gross mass up to 30.5 metric tons) hoisted 25 meters above dock deck.
- **Top Event**: Loss of mechanical load suspension; uncontrolled drop of container during vessel discharging.
- **Threat Line 1: Wire Rope Hoist Tensile Failure**:
  - *Preventive Barrier 1*: Automated electronic load cell with Load Moment Indicator (LMI) cutting off hoist hoist circuit at 105% SWL.
  - *Preventive Barrier 2*: Daily pre-shift visual wire rope inspection and monthly magneto-inductive NDT wire rope testing.
- **Threat Line 2: Twistlock Disengagement in Mid-Air**:
  - *Preventive Barrier*: Mechanical and electrical dual-interlock on spreader beam requiring zero-load contact sensors before unlocking twistlocks.
- **Consequence 1: Crushing Fatalities of Ground Marshaling Personnel**:
  - *Mitigating Barrier 1*: Physical exclusion zone barricades and AI CCTV camera intrusion detection (SOP-04) halting crane travel if personnel enter.
  - *Mitigating Barrier 2*: Mandatory 10-meter stand-off perimeter protocol enforced by terminal marshals.

---

## 10. AUDIT, REVIEW & CONTINUOUS IMPROVEMENT

10.1. **Mandatory Review Triggers**: The HIRA Register (`Form-05`) and all associated Bowtie models must be reviewed and re-approved under the following mandatory conditions:
- Following any High Potential (HiPo) near-miss, lost-time injury, or process safety event (SOP-03).
- Introduction of new machinery, industrial robots, or hazardous chemicals.
- Modifications to operational layout or physical workshop boundaries.
- Every twelve (12) months as part of the corporate ISO 45001 management review.

10.2. **Document Control**: Changes to risk assessments must be version-controlled in Insilos GRC, retaining full cryptographic audit trails of author, validator, and approver identities.
