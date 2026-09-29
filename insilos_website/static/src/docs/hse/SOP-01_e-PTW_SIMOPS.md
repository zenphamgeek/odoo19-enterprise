# STANDARD OPERATING PROCEDURE: ELECTRONIC PERMIT-TO-WORK (e-PTW) & SIMOPS CO-LOCATION MANAGEMENT

**Document Identifier**: `INSILOS-SOP-HSE-001`  
**Revision Number**: `3.0`  
**Effective Date**: `2026-10-01`  
**Review Cycle**: `Annual`  
**Standard Compliance**: `ISO 45001:2018 (Clauses 8.1.1, 8.1.2, 8.1.3), Vietnam Law on OSH No. 84/2015/QH13, Decree 44/2016/ND-CP, Decree 12/2022/ND-CP, QCVN 03:2011/BLDTBXH, QCVN 34:2018/BLDTBXH`  
**System Integrations**: `Insilos ERP (Insilos ERP) <-> Insilos GRC (Vertical GRC Resilience)`  

---

## 1. PURPOSE & OBJECTIVES

1.1. This Standard Operating Procedure (SOP) defines the mandatory corporate governance framework and technical execution protocol for issuing, approving, monitoring, suspending, and closing Electronic Permits-to-Work (e-PTW) across all industrial manufacturing, heavy mechanical fabrication, and marine terminal logistics facilities operated by Insilos and its subsidiaries.

1.2. The primary objective is the total elimination of catastrophic process incidents, fatal injuries, electrical shock occurrences, toxic atmospheric exposures, and mechanical entrapments through:
- Automated cryptographic interlocking between Enterprise Resource Planning (ERP Insilos ERP) maintenance work orders and Governance, Risk & Compliance (GRC) safety permits.
- Rigorous pre-job hazard evaluation, energy isolation verification (Lockout-Tagout), and certified gas testing.
- Systematic detection, spatial-temporal conflict resolution, and perimeter enforcement for Simultaneous Operations (SIMOPS) occurring in shared industrial zones.

---

## 2. SCOPE & FIELD OF APPLICATION

2.1. This procedure applies unconditionally to all employees, resident engineering contractors, specialized service vendors, transport operators, and third-party inspectors working within:
- **Zone A**: High-power CNC Fiber Laser cutting cells (SS400 carbon steel, 12kW-30kW resonators, high-pressure nitrogen and oxygen manifold networks).
- **Zone B**: Automated robotic welding and plasma cutting stations (6-axis Yaskawa/ABB robotic manipulators, flux-cored arc welding cells, shielding gas storage).
- **Zone C**: Logistics container marshaling yards, gantry crane rails, heavy forklift lanes, and marine berths (Cát Lái maritime logistics terminal).
- **Zone D**: Central electrical substations (22kV/0.4kV transformers, switchgear rooms, motor control centers) and fluid storage tank farms.

2.2. Work undertaken without a validated, digitally signed, and active e-PTW where this procedure mandates one constitutes a Class A Gross Safety Violation, resulting in immediate site expulsion, contractor disqualification, and statutory disciplinary action under Decree 12/2022/ND-CP.

---

## 3. NORMATIVE REFERENCES & REGULATORY FRAMEWORK

The requirements within this SOP are aligned with and enforce compliance with:
- **ISO 45001:2018**: Occupational Health and Safety Management Systems — Requirements with guidance for use (Clause 8.1: Operational planning and control; Clause 8.1.2: Eliminating hazards and reducing OH&S risks).
- **Law on Occupational Safety and Health No. 84/2015/QH13** enacted by the National Assembly of Vietnam.
- **Government Decree No. 44/2016/ND-CP**: Detailing statutory regulations on labor safety training, technical inspection of machinery with strict occupational safety requirements, and working environment monitoring.
- **Government Decree No. 12/2022/ND-CP**: Sanctions for administrative violations against regulations on labor, social insurance, and Vietnamese workers working abroad under contracts.
- **QCVN 03:2011/BLDTBXH**: National technical regulation on safe work in confined spaces.
- **QCVN 34:2018/BLDTBXH**: National technical regulation on occupational safety for working at height.
- **TCVN 5334:2007**: Electrical equipment safety requirements in hazardous zones.

---

## 4. DEFINITIONS & ABBREVIATIONS

| Acronym / Term | Technical Definition |
| :--- | :--- |
| **e-PTW** | Electronic Permit-to-Work: A legally binding, tamper-evident digital certificate authorizing specific personnel to perform designated high-risk tasks within an approved time envelope and geographical boundary. |
| **SIMOPS** | Simultaneous Operations: Two or more distinct operational, construction, maintenance, or testing activities occurring simultaneously within the same physical zone or adjacent impact perimeters, capable of generating compounded risk. |
| **LOTO** | Lockout-Tagout: Physical placement of padlocks, hasps, and warning tags on hazardous energy isolation points (breakers, valves, pneumatic lines) to prevent accidental energization. |
| **PA** | Performing Authority: The qualified supervisor, lead engineer, or contractor foreman directly in charge of executing the work on site. |
| **AA** | Area Authority: The designated facility manager, workshop superintendent, or terminal operations supervisor with custodial custody of the physical work location. |
| **AGT** | Authorized Gas Tester: A certified technical specialist possessing valid calibration certificates and training to sample, quantify, and certify atmospheric conditions. |
| **IA** | Isolation Authority: The certified electrical or mechanical technician authorized to manipulate, lock, test, and tag isolation boundaries. |
| **HSE Officer** | Health, Safety & Environment Officer: The compliance auditor responsible for validating risk controls, approving complex permits, and conducting field audits. |
| **Work Order Safety Lock** | The automated software interlock in Insilos ERP preventing maintenance technicians or machine operators from commencing work orders until GRC confirms an approved e-PTW. |

---

## 5. ROLES & RESPONSIBILITIES (RACI MATRIX)

| Operational Phase | Performing Authority (PA) | Area Authority (AA) | Isolation Authority (IA) | Authorized Gas Tester (AGT) | HSE Officer | Authorizing Authority (Approver) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| e-PTW Initiation & Scope Definition | **A / R** | C | I | I | C | I |
| JSA / HIRA Risk Assessment Input | **R** | C | C | C | **A** | I |
| LOTO Plan Execution & Zero Energy Verification | C | C | **A / R** | I | C | I |
| Confined Space Gas Testing & Certification | I | C | I | **A / R** | C | I |
| SIMOPS Conflict Matrix Screening | C | **R** | I | I | **A** | I |
| Pre-Job Toolbox Talk (TBT) Execution | **A / R** | I | I | I | C | I |
| Final e-PTW Authorization & Digital Sign-off | I | C | C | C | C | **A / R** |
| Active Work Site Monitoring | **R** | **R** | I | I | **A** | I |
| De-isolation, Work Handback & Permit Closeout | **R** | **A** | **R** | I | C | I |

*Legend: A = Accountable; R = Responsible; C = Consulted; I = Informed.*

---

## 6. PERMIT CLASSIFICATION & THRESHOLDS

Every hazardous activity requires a primary general e-PTW linked to one or more specialized high-risk sub-certificates:

```
+-------------------------------------------------------------------------------------------------+
|                                 PRIMARY GENERAL e-PTW (Form-01)                                 |
+-------------------------------+-------------------------------+---------------------------------+
                                |
        +-----------------------+-----------------------+-----------------------+
        |                       |                       |                       |
        v                       v                       v                       v
+---------------+       +---------------+       +---------------+       +---------------+
| HOT WORK      |       | CONFINED      |       | WORKING AT    |       | ELECTRICAL    |
| CERTIFICATE   |       | SPACE CERT    |       | HEIGHT CERT   |       | ISOLATION &   |
| (Class A / B) |       | (Form-03)     |       | (>= 2.0m)     |       | LOTO (Form-04)|
+---------------+       +---------------+       +---------------+       +---------------+
```

### 6.1. Hot Work Certificate (Class A & Class B)
- **Class A (High Explosion / Combustible Risk)**: Any open flame, electric arc welding, oxy-fuel cutting, carbon arc gouging, or abrasive disc grinding within 15 meters of flammable gas manifolds (O2, N2, LPG), fuel depots, chemical storehouses, or maritime cargo holds. Maximum validity: 8 hours (single shift).
- **Class B (Controlled Shop Environment)**: Hot work conducted in permanent, designated welding booths equipped with fixed localized exhaust ventilation (LEV), spark arrestor flash screens, and fire-resistant curtains. Maximum validity: 24 hours.
- **Mandatory Controls**: Minimum two 9kg ABC dry chemical fire extinguishers and one 5kg CO2 extinguisher staged within 3 meters; combustible floor coverings shielded with verified fire blankets (1,200 deg C rating); dedicated Fire Watch deployed during work and for a continuous 60-minute thermal cool-down monitoring period post completion.

### 6.2. Confined Space Entry Certificate (QCVN 03:2011/BLDTBXH)
- Applicable to any fully or partially enclosed space not designed for continuous human occupancy, possessing restricted egress/ingress, and prone to atmospheric contamination or engulfment (e.g., fuel tanks, ballast tanks, water cisterns, underground utility trenches > 1.2m depth, baghouse dust collectors, laser machine exhaust ductwork).
- **Mandatory Controls**: Mechanical positive-pressure forced ventilation delivering minimum 20 air changes per hour; continuous multi-gas monitoring ($O_2, LEL, H_2S, CO$); calibrated intrinsically safe lighting (<= 24V DC); full-body harness with retrieval lifeline connected to an OSHA-compliant tripod and retrieval winch; dedicated external Standby Attendant equipped with emergency siren and breathing apparatus.

### 6.3. Working at Height Certificate (QCVN 34:2018/BLDTBXH)
- Applicable to any task where personnel are exposed to an potential fall of 2.0 meters or greater above the ground, floor, or solid working deck, including work on pipe racks, crane bridges, building roofs, scaffolding, and mobile elevated work platforms (MEWPs).
- **Mandatory Controls**: Full-body safety harness with twin energy-absorbing lanyards anchored to certified anchor points rated for >= 22.2 kN (5,000 lbf); 100% tie-off compliance; edge protection comprising top rail (1.1m), mid rail (0.6m), and toe board (0.15m); exclusion barricade at ground level spanning 1.5 times the working height to eliminate dropped object risks; certified trauma suspension relief straps attached to every harness.

### 6.4. Electrical Isolation & LOTO Certificate
- Applicable to any service, inspection, repair, or cleaning of electrical switchboards, CNC machines, high-voltage transformers, or motorized mechanical equipment where unexpected energization or release of stored residual energy (pneumatic, hydraulic, gravity, spring tension) could cause harm.
- **Mandatory Controls**: Execution of 6-Step LOTO (Notify, Shutdown, Isolate, Lock/Tag, Dissipate Stored Energy, Zero-Energy Verification Try-Step); master hasp with red individual padlocks; voltage detector verification; hydraulic pressure accumulator bleed-off; physical pipe blinding or double-block-and-bleed valve configuration.

---

## 7. ELECTRONIC PERMIT LIFECYCLE & ERP/GRC INTEGRATION WORKFLOW

The e-PTW system enforces a strict state-machine architecture synchronized between Insilos ERP Enterprise and Vertical GRC:

```
[Insilos ERP]                        [Connector Engine]                 [Vertical GRC Platform]
Work Order Created (Maintenance)
         |
         v
Status: 'Pending Safety Permit' 
(SAFETY LOCK ACTIVE)
         |
         +------------------------> POST /items/hse_permits ----------> e-PTW Draft Created
                                                                                |
                                                                                v
                                                                        JSA & Risk Scoring (HIRA)
                                                                                |
                                                                                v
                                                                        SIMOPS Spatial Conflict Check
                                                                                |
                                                                                v
                                                                        Gas Test & LOTO Tag Attachment
                                                                                |
                                                                                v
                                                                        Authorizing Approver Signs (HMAC)
                                                                                |
                                                                                v
                                    POST /webhooks/hse-events <--------- Status: 'Approved' (ACTIVE)
                                    (Signed HMAC-SHA256)
                                             |
                                             v
Work Order UNLOCKED -------------------------+
Status: 'Ready for Execution'
         |
         v
Work Executed Safely
         |
         v
Work Completed & LOTO Cleared
         |
         +------------------------> POST /items/hse_permits/closeout -> e-PTW Closed & Archived
```

### Step 1: Work Order Initiation & Automatic Safety Lock
1. When a maintenance engineer, production planner, or contractor initiates a work order in Insilos ERP (`maintenance.request`, `mrp.production`, or `fleet.vehicle.log.services`) involving high-risk operations, Insilos ERP automatically tags the record with `is_high_risk = True`.
2. The work order is automatically locked in the state `pending_safety_permit`. The system disables all action buttons (`Start Work`, `Consume Parts`, `Mark as Done`) and displays a prominent safety banner: `"OPERATION LOCKED: Awaiting Approved e-PTW from Insilos GRC"`.

### Step 2: Automated Transmission to Insilos GRC
1. The Insilos ERP connector dispatches an authenticated JSON payload to Vertical GRC (`POST /items/hse_permits`) containing:
   - `work_order_id` and `work_order_name`.
   - `equipment_id`, `functional_location`, and `workshop_zone` (e.g., `ZONE-B-WELDING-03`).
   - `planned_start_time` and `planned_end_time`.
   - `subcontractor_id` and assigned `lead_technician`.
2. GRC instantiates an `hse_permits` record in state `draft` and generates a unique tracking code (e.g., `ePTW-2026-09-00412`).

### Step 3: Hazard Identification, Pre-Requisite Certificates & JSA
1. The Performing Authority (PA) accesses the GRC mobile/desktop portal, completes the Job Safety Analysis (JSA), and selects required sub-certificates.
2. If Confined Space is checked, GRC blocks submission until an Authorized Gas Tester completes `Form-03_Gas_Testing_Certificate.md` with oxygen levels between 19.5% and 23.5% and flammable gas < 5% LEL.
3. If Electrical Isolation is checked, GRC blocks submission until the Isolation Authority inputs the unique padlock serial numbers and signs `Form-04_LOTO_Certificate_Tag.md`.

### Step 4: Automated SIMOPS Spatial-Temporal Conflict Screening
1. The GRC SIMOPS algorithm parses the spatial coordinates, workshop zone ID, and scheduled timeframe against all currently active and pending permits.
2. If conflict rules are triggered (e.g., Hot Work scheduled within 15 meters of an active Chemical Cleaning or Solvent Degreasing permit), GRC flags the permit with `SIMOPS_CONFLICT_ALERT` and demands formal SIMOPS resolution (Section 8).

### Step 5: Pre-Job Toolbox Talk (TBT) Field Verification
1. Prior to digital approval, the PA convenes all assigned personnel at the physical work location.
2. The PA reviews every hazard line item, inspects PPE (safety helmet, safety glasses, steel-toe boots, flame-retardant coveralls, fall harness), confirms emergency escape routes, and logs crew signatures into the GRC tablet interface.

### Step 6: Multi-Tier Digital Authorization & Cryptographic Sign-Off
1. Formal approval requires sequential cryptographic signing:
   - **Tier 1 (Technical Verification)**: Area Authority (AA) validates plant isolation and ambient conditions.
   - **Tier 2 (HSE Compliance)**: HSE Officer audits JSA depth and contractor safety badge validity.
   - **Tier 3 (Executive Authority)**: Plant Director or Operations Manager issues digital approval utilizing HMAC-SHA256 signature tokens.
2. Upon Tier 3 sign-off, the GRC permit transitions to `approved`.

### Step 7: Webhook Dispatch & Insilos ERP Work Order Unlock
1. GRC emits an outbound secure webhook (`POST http://localhost:28069/webhooks/hse-events`) carrying header `X-HSE-Signature` and payload:
   ```json
   {
     "event": "permit_approved",
     "permit_id": "ePTW-2026-09-00412",
     "work_order_id": 1042,
     "valid_from": "2026-09-29T08:00:00Z",
     "valid_until": "2026-09-29T17:00:00Z",
     "issued_to": "Vanguard Marine Services Ltd"
   }
   ```
2. The ERP webhook handler verifies the HMAC signature, matches the work order ID, transitions status from `pending_safety_permit` to `ready_for_execution`, logs a chatter notification, and enables technician action buttons.

### Step 8: Permit Suspension, Handback & Final Closeout
1. **Immediate Suspension Triggers**: A permit is automatically suspended if:
   - Field AI Vision cameras detect severe PPE violations (SOP-04).
   - An ambient atmospheric gas alarm triggers or ventilation fails.
   - Unscheduled emergency sirens sound across the facility.
   - Adverse weather conditions arise (wind speed > 10.8 m/s for crane lifts or height work; lightning within 10 km).
2. **Handback Protocol**:
   - PA verifies all tools, scrap, and scaffolding are cleared, housekeeping is restored, and personnel are safely evacuated.
   - Isolation Authority verifies equipment guards are reinstalled and performs controlled de-isolation.
   - PA and AA complete digital handback in GRC; GRC emits `permit_closed` webhook; Insilos ERP marks the maintenance request as ready for operational post-repair testing.

---

## 8. SIMOPS (SIMULTANEOUS OPERATIONS) CO-LOCATION PROTOCOL

### 8.1. Principles of Spatial-Temporal Co-Location
SIMOPS occurs when two or more distinct industrial teams operate within a proximity where their activities can create mutual hazards. When evaluating SIMOPS, the primary rule is: **Process Safety and Life Safety Supersede Maintenance and Production Deadlines**.

### 8.2. Geographical Separation Radii
- **Hot Work Exclusion Radius**: A 15-meter horizontal radius around any hot work operation must be cleared of all combustible materials, solvent handling, paint spraying, and fuel decanting.
- **Vertical Drop Zone (Working at Height)**: The footprint directly beneath any overhead work plus an expanding conical perimeter equal to $H \times 0.5$ (where $H$ is elevation in meters) is designated an absolute Exclusion Zone. No concurrent ground work is permitted beneath elevated crews.
- **Heavy Lift Radial Sweep**: The complete boom swing radius of mobile or gantry cranes plus 5 meters safety margin. Personnel access is physically barricaded with magnetic chain links and flashing red beacons.

### 8.3. SIMOPS Interaction Decision Matrix

The interaction between concurrent activities is governed by the following strict rule matrix:

| Activity Code / Activity Name | ACT-01 Hot Work (Arc/Flame) | ACT-02 Confined Space Entry | ACT-03 Working at Height | ACT-04 Electrical Substation Testing | ACT-05 Heavy Crane Tandem Lift | ACT-06 Chemical Line Flushing |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **ACT-01 Hot Work** | **Y** | **R** | **Y** | **R** | **R** | **R** |
| **ACT-02 Confined Space** | **R** | **G** | **Y** | **Y** | **R** | **R** |
| **ACT-03 Height Work** | **Y** | **Y** | **Y** | **G** | **R** | **Y** |
| **ACT-04 Electrical Test** | **R** | **Y** | **G** | **Y** | **Y** | **R** |
| **ACT-05 Heavy Crane Lift** | **R** | **R** | **R** | **Y** | **R** | **R** |
| **ACT-06 Chemical Flushing** | **R** | **R** | **Y** | **R** | **R** | **G** |

**Matrix Classification Key**:
- **R (RED - STRICTLY PROHIBITED)**: The simultaneous execution of these two activities within the same zone or separation buffer is strictly prohibited. One activity must be fully completed, suspended, or re-scheduled before the second can commence.
- **Y (YELLOW - CONDITIONAL APPROVAL WITH COMPENSATORY CONTROLS)**: Permitted only with written authorization from the HSE Director, implementation of specific engineered barriers (e.g., solid steel spark deflector panels, dedicated cross-communicating watchmen with VHF radios, continuous automated gas sniffers).
- **G (GREEN - PERMITTED WITH STANDARD CONTROLS)**: Routine concurrent operations permitted subject to standard individual e-PTW precautions and spatial awareness.

### 8.4. SIMOPS Review & Resolution Procedure
1. When the GRC engine detects a "Yellow" combination, an automated notification is sent to both Performing Authorities and the Area Authority.
2. A mandatory physical SIMOPS Coordination Meeting is held at the site boundary.
3. The parties complete `Form-02_SIMOPS_Matrix.md`, formalizing:
   - Shared radio communication frequencies (Channel 4 on Industrial VHF).
   - Emergency shutdown hierarchy (which team ceases work first upon alarm).
   - Designated physical barrier placement.
4. If a "Red" conflict occurs, GRC locks both permits from approval until one work order is moved to an alternate time slot on the master operational schedule.

---

## 9. EMERGENCY RESPONSE & STOP WORK AUTHORITY (SWA)

9.1. **Universal Stop Work Authority**: Every individual on site—regardless of rank, employer, or contractual relationship—possesses absolute, non-negotiable Stop Work Authority (SWA) whenever an uncontrolled hazard, permit deviation, or SIMOPS breach is observed.

9.2. **Zero Retaliation Guarantee**: Invoking Stop Work Authority in good faith will never result in disciplinary action, contractual penalty, or financial retribution. Any supervisor attempting to penalize a worker for exercising SWA is subject to immediate termination.

9.3. **SWA Escalation Procedure**:
1. Verbally call out: *"STOP WORK - SAFETY HOLD!"*
2. Immediately de-energize tools, secure equipment into a safe state, and escort personnel outside the hazard boundary.
3. Notify the Area Authority and HSE Officer immediately.
4. The permit is marked `suspended_under_swa` in GRC.
5. Work may only resume after an on-site joint investigation validates corrective controls and the Authorizing Authority signs a digital re-validation certificate.

---

## 10. DOCUMENT CONTROL & REVISION HISTORY

| Rev | Date | Author / Title | Approver / Title | Scope of Modification |
| :---: | :---: | :--- | :--- | :--- |
| 1.0 | 2024-03-15 | Senior HSE Engineer | VP Manufacturing | Initial corporate release of manual PTW system. |
| 2.0 | 2025-05-20 | Lead Process Safety Architect | COO Insilos Group | Introduction of digital forms and basic LOTO matrix. |
| 3.0 | 2026-10-01 | HSE Documentation Specialist | Group HSE Director & CEO | Comprehensive e-PTW transformation, Insilos ERP safety lock integration, automated Vertical GRC SIMOPS matrix, AI Vision safety trigger. |
