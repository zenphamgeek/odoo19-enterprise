# INSILOS INDUSTRIAL GROUP — STANDARD OPERATING FORM
## FORM-03: ATMOSPHERIC GAS TESTING & CONFINED SPACE ENTRY CERTIFICATE

**Document Identifier**: `INSILOS-FRM-HSE-003`  
**Revision**: `3.0`  
**Governing Standard**: `QCVN 03:2011/BLDTBXH, ISO 45001:2018 Clause 8.1, Vietnam Law on OSH No. 84/2015/QH13`  
**Cross-Reference**: `SOP-01 (INSILOS-SOP-HSE-001 §6.2) & Form-01 e-PTW`  
**GRC Permitting Collection**: `hse_gas_certificates`  

---

### SECTION 1: CERTIFICATE ADMINISTRATIVE SPECIFICATION

| Administrative Parameter | Certified Entry Record / Telemetry |
| :--- | :--- |
| **Gas Testing Certificate ID** | `GTC-2026-09-00318` |
| **Associated e-PTW Permit No**| `ePTW-2026-09-00842` (Linked Insilos ERP WO: `WO-MAIN-2026-04192`) |
| **Testing Date & Shift** | `2026-09-29` — Morning / Day Operational Shift |
| **Facility / Plant Location** | Insilos Heavy Mechanical Complex — Workshop 02 |
| **Confined Space Identification**| `TNK-N2-RECIRC-02` (High-Pressure Nitrogen Recovery Buffer Cistern) |
| **Enclosure Physical Dimensions**| Cylindrical carbon steel vessel, Diameter: 3.2m, Height: 4.8m, Volume: $38.6\text{ m}^3$ |
| **Specific Entry Purpose** | Internal weld seam visual inspection, ultrasonic wall thickness measurement, and residual sludge cleanout |
| **Authorized Gas Tester (AGT)**| Dang Quoc Cuong (Certified Senior Gas Tester — Certification ID: `AGT-VNM-2024-8891`) |
| **Dedicated Standby Attendant** | Nguyen Van Thang (Certified Confined Space Safety Attendant — Badge: `INS-EMP-11304`) |

---

### SECTION 2: MULTI-GAS DETECTOR INSTRUMENTATION & CALIBRATION RECORD

*Gas testing must be conducted solely with certified, intrinsically safe multi-gas detectors equipped with internal motorized sampling pumps.*

| Equipment Specification | Instrument Calibration & Verification Data |
| :--- | :--- |
| **Detector Manufacturer & Model** | RAE Systems MultiRAE Pro (Model PGM-6248, Intrinsically Safe Class I, Div 1) |
| **Instrument Serial Number** | `S/N: MR-6248-994120-V` |
| **Factory Calibration Expiry Date**| `2027-04-18` (Annual certified lab calibration certificate on file: `CAL-LAB-2026-041`) |
| **Daily Bump Test Timestamp** | `2026-09-29 06:15:30 UTC` — Result: **PASSED (100% Sensor Response)** |
| **Calibration Gas Canister Lot No**| Calgas Quad-Mix Lot: `LOT-CAL-99412-EXP2027-08` |
| **Test Gas Target Concentrations** | $O_2: 18.0\text{ vol\%}$, $\text{CH}_4 (\text{LEL}): 50\%$, $CO: 50\text{ ppm}$, $H_2S: 25\text{ ppm}$, Isobutylene (VOC): $10\text{ ppm}$ |
| **Fresh Air Zeroing Verification** | Completed outdoors in clean marine atmospheric air at `06:20:00 UTC` ($O_2 = 20.9\%$, $VOC = 0.0\text{ ppm}$) |
| **Sampling Hose & Probe Spec** | 5.0-meter anti-static Teflon-lined sampling hose with water-trap particulate filter probe |

---

### SECTION 3: STATUTORY SAFE ENTRY LIMITS (QCVN 03:2011/BLDTBXH)

Every measured gas parameter must fall strictly within the statutory safe envelope prior to permitting human entry:

| Gas Parameter | Chemical Symbol | Mandatory Safe Entry Threshold Envelope | Alarm Threshold (Amber Warning) | Evacuation Threshold (Red Siren) |
| :--- | :---: | :---: | :---: | :---: |
| **Oxygen Concentration** | $O_2$ | **19.5% to 23.5% vol** | $< 20.0\%$ or $> 22.5\%$ | $< 19.5\%$ (Asphyxiation) or $> 23.5\%$ (Fire) |
| **Flammable / Explosive Gas**| LEL | **$< 5.0\%$ LEL** | $\ge 5.0\%$ LEL | $\ge 10.0\%$ LEL (Immediate Evacuate) |
| **Carbon Monoxide** | $CO$ | **$< 25\text{ ppm}$ (8h TWA)** | $\ge 15\text{ ppm}$ | $\ge 25\text{ ppm}$ |
| **Hydrogen Sulfide** | $H_2S$ | **$< 5\text{ ppm}$ (8h TWA)** | $\ge 3\text{ ppm}$ | $\ge 5\text{ ppm}$ (Ceiling: $10\text{ ppm}$) |
| **Volatile Organic Compounds**| VOC (PID) | **$< 1.0\text{ ppm}$** | $\ge 0.5\text{ ppm}$ | $\ge 1.0\text{ ppm}$ |

---

### SECTION 4: STRATIFIED SAMPLING MEASUREMENT LOG

*Confined spaces exhibit atmospheric stratification: gases heavier than air ($H_2S$, heavy hydrocarbons) settle at the sump floor; lighter gases ($CH_4$) rise to the ceiling dome; nitrogen displaces oxygen evenly. Sampling must test all three levels.*

```
+---------------------------------------------------------------------------------------------------------+
| STRATIFIED SAMPLING LOG — INITIAL & PERIODIC INTERVAL MONITORING                                        |
+----------+-----------------------+--------+---------+--------+---------+-------+--------+---------------+
| Test Time| Sampling Location &   |  O2    |  LEL    |   CO   |   H2S   |  VOC  | Entry  | AGT Signature |
|  (UTC)   | Elevation Depth       | (%vol) |  (%)    |  (ppm) |  (ppm)  | (ppm) | Status | & Badge ID    |
+----------+-----------------------+--------+---------+--------+---------+-------+--------+---------------+
| 06:45:00 | Tank Top Manway (+4.5m)| 20.9%  |  0.0%   |  0.0   |   0.0   |  0.0  | SAFE   | D.Q. Cuong    |
| 06:47:00 | Tank Mid Zone (+2.2m) | 20.8%  |  0.0%   |  0.0   |   0.0   |  0.0  | SAFE   | D.Q. Cuong    |
| 06:50:00 | Tank Sump Floor (+0.2m)| 20.9%  |  0.0%   |  1.0   |   0.0   |  0.1  | SAFE   | D.Q. Cuong    |
+----------+-----------------------+--------+---------+--------+---------+-------+--------+---------------+
| 09:00:00 | Re-test: Mid-Space    | 20.8%  |  0.0%   |  0.0   |   0.0   |  0.0  | SAFE   | D.Q. Cuong    |
| 11:00:00 | Re-test: Sump Floor   | 20.9%  |  0.0%   |  0.0   |   0.0   |  0.0  | SAFE   | D.Q. Cuong    |
| 13:30:00 | Re-test: Post-Lunch   | 20.8%  |  0.0%   |  1.0   |   0.0   |  0.1  | SAFE   | D.Q. Cuong    |
| 15:30:00 | Final Re-test: Sump   | 20.9%  |  0.0%   |  0.0   |   0.0   |  0.0  | SAFE   | D.Q. Cuong    |
+----------+-----------------------+--------+---------+--------+---------+-------+--------+---------------+
```

---

### SECTION 5: VENTILATION & EMERGENCY RESCUE APPARATUS

1. **Forced Mechanical Ventilation**:
   - [x] Explosion-proof positive pressure axial blower (Airflow rate: $3,200\text{ m}^3/\text{h}$, exceeding the required 20 air changes per hour).
   - [x] Flexible spiral anti-static ducting inserted into tank vessel, discharging fresh ambient air directly to the sump base (0.3m above floor).
   - [x] Blower intake positioned 10 meters upwind from vehicle exhaust, laser cutting vents, and chemical sources.
   - [x] Ventilation running continuously for minimum 30 minutes prior to initial entry and operating non-stop throughout occupancy.

2. **Emergency Extraction & Personal Rescue Equipment**:
   - [x] Certified aluminum rescue tripod (rated SWL: 500 kg, EN 795 Class B) erected centrally over top manway.
   - [x] Retractable fall-arrester wire lifeline winch with mechanical rescue raising/lowering handle (length: 20m).
   - [x] Full-body safety harnesses (EN 361) with dorsal D-ring attached to recovery lifeline worn by all entering personnel.
   - [x] Two Emergency Escape Breathing Apparatus (EEBA / ELSA 15-minute compressed air hoods) staged directly at the entrance manway.
   - [x] Continuous intrinsically safe personal 4-gas clip-on monitor worn on chest by lead entering technician (Tran Van Duc).

---

### SECTION 6: STANDBY ATTENDANT VERIFICATION & COMMUNICATION PROTOCOL

The Standby Attendant (Nguyen Van Thang) confirms the following duties and responsibilities:
- [x] **Continuous Stationing**: Will remain stationed continuously at the tank manway opening; will under no circumstances leave the station or enter the space.
- [x] **Entry / Egress Log**: Maintaining accurate, real-time head count logging of all personnel inside `TNK-N2-RECIRC-02`.
- [x] **Communication**: Maintaining verbal and visual contact with workers inside at intervals not exceeding 5 minutes.
- [x] **Emergency Alarm**: Equipped with high-decibel compressed air horn and direct industrial radio link to Central Medical Emergency (Ext: 115).
- [x] **Order Evacuation Immediately** if any detector alarms, ventilation halts, or unusual worker behavior is observed.

---

### SECTION 7: AUTHORIZED ENDORSEMENT & CERTIFICATE ISSUANCE

```
AUTHORIZED GAS TESTER (AGT) CERTIFICATION:
I hereby certify that I have personally sampled and analyzed the atmosphere of the confined space designated 
above. The atmospheric conditions are within statutory safe limits and forced ventilation is active.
Name: Dang Quoc Cuong                Certification No: AGT-VNM-2024-8891
Date & Time: 2026-09-29 07:00:00 UTC Signature: [DIGITALLY ENDORSED & SIGNED IN GRC]

CONFINED SPACE STANDBY ATTENDANT:
Name: Nguyen Van Thang               Employee Badge: INS-EMP-11304
Date & Time: 2026-09-29 07:05:00 UTC Signature: [DIGITALLY ENDORSED & SIGNED IN GRC]

PERFORMING AUTHORITY (Acceptance of Conditions):
Name: Tran Van Duc                   Employee Badge: INS-EMP-10492
Date & Time: 2026-09-29 07:10:00 UTC Signature: [DIGITALLY ENDORSED & SIGNED IN GRC]

GAS TESTING CERTIFICATE STATUS: [ ACTIVE - ENTRY PERMITTED ]
```
