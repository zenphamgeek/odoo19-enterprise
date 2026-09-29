# INSILOS INDUSTRIAL GROUP — STANDARD OPERATING FORM
## FORM-05: MASTER HAZARD IDENTIFICATION & 5X5 QUANTITATIVE RISK ASSESSMENT (HIRA) REGISTRY

**Document Identifier**: `INSILOS-FRM-HSE-005`  
**Revision**: `3.0`  
**Governing Standard**: `ISO 45001:2018 Clause 6.1.2, ISO 31000:2018, SOP-02 (INSILOS-SOP-HSE-002), Decree 39/2016/ND-CP`  
**GRC Master Collections**: `risk_models` & `hse_risk_register`  
**ERP Integration**: Insilos ERP Preventive Maintenance (`maintenance.equipment`) Risk Multiplier  

---

### SECTION 1: REGISTRY ADMINISTRATIVE SPECIFICATION

| Administrative Parameter | Registry Record Data |
| :--- | :--- |
| **HIRA Registry ID** | `HIRA-REG-2026-Q4` |
| **Facility / Plant Complex** | Insilos Heavy Mechanical Fabrication & Cát Lái Maritime Logistics Terminal |
| **Governing Business Unit** | Insilos Operations, Industrial Automation & Logistics Division |
| **Effective Assessment Date** | `2026-10-01` (Mandatory Annual / Q4 Master Review) |
| **Lead Risk Assessment Engineer**| Tran Van Duc (Lead Automation & Reliability Engineer — Badge: `INS-EMP-10492`) |
| **HSE Compliance Reviewer** | Hoang Thi Mai (Senior HSE Compliance Officer — Badge: `INS-HSE-00088`) |
| **Executive Approval Authority** | Vu Dinh Quang (Director of Plant Operations — Badge: `INS-DIR-00004`) |

---

### SECTION 2: 5x5 QUANTITATIVE SCORING MATRIX CRITERIA

$$\text{Risk Score } (R) = \text{Probability } (P) \times \text{Severity } (S)$$

- **Probability Scale (1 to 5)**: 1 = Improbable ($< 1$ per 10 yrs); 2 = Remote (1 per 3-10 yrs); 3 = Occasional (1 per 1-3 yrs); 4 = Frequent (Monthly to Quarterly); 5 = Continuous (Daily / Weekly).
- **Severity Scale (1 to 5)**: 1 = Negligible (First aid, $< 10\text{M}$ VND); 2 = Minor (Medical treatment $\le 3$ lost days, $10\text{M}-100\text{M}$ VND); 3 = Moderate (Lost time $> 3$ days, $100\text{M}-500\text{M}$ VND); 4 = Major (Amputation, single fatality, $500\text{M}-2.5\text{B}$ VND); 5 = Catastrophic (Multiple fatalities, $> 2.5\text{B}$ VND).
- **Risk Classification Bands**:
  * **1 to 4: LOW (Green)** — Acceptable under routine operational controls.
  * **5 to 9: MEDIUM (Yellow)** — Tolerable if ALARP; supervisory oversight and JSA required.
  * **10 to 14: HIGH (Amber)** — Undesirable; engineered controls and mandatory e-PTW required.
  * **15 to 25: CRITICAL (Red)** — Strictly prohibited; immediate work stoppage until redesigned.

---

### SECTION 3: COMPREHENSIVE INDUSTRIAL RISK REGISTER

```
+----------------------------------------------------------------------------------------------------------------------------------------------------+
| INSILOS MASTER HIRA REGISTER — QUANTITATIVE 5x5 RISK EVALUATION & BOWTIE BARRIER CONTROL MATRIX                                                    |
+------------+-----------------------+-----------------------------+-------+--------------------+--------------------+-------+-----------------------+
| Risk ID /  | Work Activity &       | Hazard Description &        | Inh.  | Preventive         | Mitigating         | Res.  | Action Owner &        |
| Location   | Operational Step      | Hazardous Top Event         | P S R | Barriers (Left)    | Barriers (Right)   | P S R | Status in GRC         |
+------------+-----------------------+-----------------------------+-------+--------------------+--------------------+-------+-----------------------+
| RSK-W02-01 | Operation of 20kW     | High-pressure N2 line       | 4 4 16| 1. Dual PSV valves | 1. Ambient O2 dump | 1 4 4 | T. V. Duc             |
| Zone A     | Fiber Laser CNC       | rupture at 30 bar.          | (CRIT)|    calibrated 33bar|    ventilation fan | (LOW) | `INS-EMP-10492`       |
| Bay 03     | Assist Gas System     | Top Event: Gas explosion    |       | 2. Auto ESD shutoff| 2. Polycarbonate   |       | Status: ACTIVE        |
|            |                       | and sudden asphyxiation.    |       | 3. Quarterly NDT.  |    blast shield.   |       | GRC ID: `RSK-1049`    |
+------------+-----------------------+-----------------------------+-------+--------------------+--------------------+-------+-----------------------+
| RSK-W02-02 | Robotic Arc Welding   | 6-axis robot arm collision  | 4 4 16| 1. Interlocked dual| 1. High-speed E-Stop| 1 3 3 | D. T. Hieu            |
| Zone B     | Cell 02 (SS400 Frame  | with technician during teach| (CRIT)|    optical curtain |    cable trip.     | (LOW) | `INS-EMP-10933`       |
| Bay 02     | Jig Alignment)        | mode. Top Event: Blunt-force|       | 2. Deadman 3-pos   | 2. Impact-absorb   |       | Status: ACTIVE        |
|            |                       | mechanical crushing trauma. |       |    teach pendant.  |    padded vest.    |       | GRC ID: `RSK-1052`    |
+------------+-----------------------+-----------------------------+-------+--------------------+--------------------+-------+-----------------------+
| RSK-W02-03 | Confined Space Entry  | Nitrogen buildup & oxygen   | 3 5 15| 1. LOTO positive   | 1. Standby winch   | 1 4 4 | D. Q. Cuong           |
| Zone A     | in Recovery Buffer    | depletion in vessel.        | (CRIT)|    pipe blinding   |    tripod rescue.  | (LOW) | `INS-EMP-10811`       |
| Cistern    | Cistern (TNK-02)      | Top Event: Asphyxiation of  |       | 2. Continuous 4-gas| 2. 15-min EEBA     |       | Status: ACTIVE        |
|            |                       | technician inside cistern.  |       |    sniffing probe. |    escape packs.   |       | GRC ID: `RSK-1058`    |
+------------+-----------------------+-----------------------------+-------+--------------------+--------------------+-------+-----------------------+
| RSK-W02-04 | Working at Height on  | Technician slip/fall from   | 4 4 16| 1. Certified 4.5m  | 1. Dual shock-     | 1 3 3 | P. M. Tuan            |
| Zone A     | Elevated Laser Duct   | temporary scaffold platform.| (CRIT)|    scaffold with   |    absorbing lanyard| (LOW)| `INS-EMP-11450`       |
| Bay 03     | Mezzanine (+4.5m)     | Top Event: High-altitude    |       |    toe-boards.     | 2. Trauma relief   |       | Status: ACTIVE        |
|            |                       | worker fall to concrete.    |       | 2. Green Scafftag. |    suspension loop.|       | GRC ID: `RSK-1064`    |
+------------+-----------------------+-----------------------------+-------+--------------------+--------------------+-------+-----------------------+
| RSK-TRM-01 | Ship-to-Shore Gantry  | Heavy container hoist wire  | 3 5 15| 1. Auto LMI load   | 1. Automated AI    | 1 4 4 | P. V. Long            |
| Berth 03   | Crane 40-Ton Container| rope fatigue snapping.      | (CRIT)|    cell limiter.   |    CCTV geofence   | (LOW) | `INS-EMP-10651`       |
| Cát Lái    | Discharge Operation   | Top Event: Uncontrolled 30T |       | 2. Daily wire rope | 2. 10m physical    |       | Status: ACTIVE        |
|            |                       | container drop on dock.     |       |    magnetic NDT.   |    exclusion zone. |       | GRC ID: `RSK-1070`    |
+------------+-----------------------+-----------------------------+-------+--------------------+--------------------+-------+-----------------------+
| RSK-TRM-02 | Terminal Tractor &    | High-speed terminal tractor | 4 4 16| 1. Segregated green| 1. High-vis Class 3| 1 3 3 | N. T. Kien            |
| Marshaling | Heavy Forklift Mobile | collision with pedestrian.  | (CRIT)|    pedestrian lane |    reflective vest.| (LOW) | `INS-LOG-00412`       |
| Yard 02    | Traffic Co-Location   | Top Event: Person run-over  |       | 2. 15 km/h radar   | 2. Ultrasonic cab  |       | Status: ACTIVE        |
|            |                       | by 32-ton laden tractor.    |       |    speed governor. |    proximity horn. |       | GRC ID: `RSK-1075`    |
+------------+-----------------------+-----------------------------+-------+--------------------+--------------------+-------+-----------------------+
| RSK-W01-01 | Central Electrical    | High-energy electrical arc  | 3 5 15| 1. 6-Step LOTO with| 1. 40 cal/cm2 arc  | 1 4 4 | N. Q. Bao             |
| Substation | Switchgear Overhaul   | flash during breaker racking| (CRIT)|    master padlocks.|    flash suit & hood| (LOW)| `INS-EMP-11028`       |
| Sub-01     | (22kV / 0.4kV Bus)    | Top Event: Explosive arc-   |       | 2. Remote racking  | 2. Auto optical arc|       | Status: ACTIVE        |
|            |                       | blast plasma vapor release. |       |    robot motorized.|    detector trip.  |       | GRC ID: `RSK-1082`    |
+------------+-----------------------+-----------------------------+-------+--------------------+--------------------+-------+-----------------------+
| RSK-W03-01 | Chemical Surface      | Nitric acid bath heating    | 3 4 12| 1. Redundant RTD   | 1. Emergency safety| 1 3 3 | L. V. Hai             |
| Chemical   | Pickling & Passivation| coil runaway & boilover.    | (HIGH)|    temp shutoff.   |    deluge shower.  | (LOW) | `INS-EMP-10884`       |
| Bay 01     | for Stainless Steel   | Top Event: Acid splash &    |       | 2. 110% concrete   | 2. Full chemical   |       | Status: ACTIVE        |
|            |                       | toxic NOx plume release.    |       |    containment bund|    suit & respirator|      | GRC ID: `RSK-1089`    |
+------------+-----------------------+-----------------------------+-------+--------------------+--------------------+-------+-----------------------+
```

---

### SECTION 4: BARRIER DEGRADATION & PREVENTIVE MAINTENANCE TELEMETRY

In accordance with SOP-02 §8.3, every safety-critical barrier in this register is monitored dynamically via Insilos ERP Preventive Maintenance (`maintenance.equipment`):

| Critical Safety Barrier | Linked Insilos ERP Maintenance Asset | Preventive Maintenance Frequency | Failure Action Protocol |
| :--- | :--- | :--- | :--- |
| **PSV-101A/B Pressure Relief** | `AST-PSV-NITRO-01` | Semi-Annual Bench Test & Calibration | If test fails, e-PTW auto-blocked; line locked out. |
| **Robot Light Curtain Interlock** | `AST-ROBOT-WELD-02` | Monthly Optical & Response Time Audit | Light curtain bypass trips master production line halt. |
| **Crane Load Moment Limiter** | `AST-CRANE-STS-03` | Bi-Weekly Load Cell Deadweight Check | Crane lifting speed electronically restricted to 10%. |
| **Substation Optical Arc Trip** | `AST-SUB-01-SWG` | Annual Primary Injection & Lux Test | High-voltage feeder circuit breaker locked open. |

---

### SECTION 5: ANNUAL REVIEW & EXECUTIVE RE-CERTIFICATION

```
LEAD RISK ASSESSMENT ENGINEER:
I certify that the hazard evaluations and quantitative 5x5 scores accurately reflect physical plant conditions 
and adhere to the ISO 45001:2018 ALARP standard.
Name: Tran Van Duc                   Badge: INS-EMP-10492        Date: 2026-10-01 08:30:00 UTC
Signature: [DIGITALLY SIGNED & VERIFIED IN GRC]

CORPORATE HSE COMPLIANCE AUDITOR:
Name: Hoang Thi Mai                  Badge: INS-HSE-00088        Date: 2026-10-01 09:00:00 UTC
Signature: [DIGITALLY SIGNED & VERIFIED IN GRC]

DIRECTOR OF PLANT OPERATIONS & EXECUTIVE COMMITTEE:
Name: Vu Dinh Quang                  Badge: INS-DIR-00004        Date: 2026-10-01 09:30:00 UTC
Signature: [DIGITALLY SIGNED & VERIFIED IN GRC]
MASTER REGISTRY STATUS: [ VALIDATED & RELEASED TO GRC/ERP RUNTIME ]
```
