# INSILOS INDUSTRIAL GROUP — STANDARD OPERATING FORM
## FORM-04: HAZARDOUS ENERGY ISOLATION (LOTO) CERTIFICATE & SAFETY LOCKOUT TAG

**Document Identifier**: `INSILOS-FRM-HSE-004`  
**Revision**: `3.0`  
**Governing Standard**: `OSHA 29 CFR 1910.147 (Control of Hazardous Energy), ISO 45001:2018 Clause 8.1, TCVN 5334:2007`  
**Cross-Reference**: `SOP-01 (INSILOS-SOP-HSE-001 §6.4) & Form-01 e-PTW`  
**Insilos ERP Integration**: `maintenance.equipment` LOTO Safety Lock  
**GRC Permitting Collection**: `hse_loto_isolations`  

---

### SECTION 1: LOTO ADMINISTRATIVE CERTIFICATION

| Administrative Field | Certified Field Record / Specification |
| :--- | :--- |
| **LOTO Certificate Number** | `LOTO-2026-09-00521` |
| **Associated e-PTW Permit No**| `ePTW-2026-09-00842` |
| **Insilos ERP Work Order Ref** | `WO-MAIN-2026-04192` |
| **Plant / Production Unit** | Insilos Heavy Mechanical Fabrication Complex — Workshop 02 |
| **Target Machine Asset Name**| 20kW Fiber Laser CNC Unit 01 (Bystronic / Insilos Mod) |
| **Insilos ERP Asset Tag Identifier** | `AST-LASER-CNC-01` |
| **Functional Location Code** | `FAC-W02-BAY03-CNC01` |
| **Lead Isolation Authority (IA)**| Dang Quoc Cuong (Certified Senior Electrical/LOTO Specialist — Badge: `INS-EMP-10811`) |
| **Performing Authority (PA)** | Tran Van Duc (Lead Automation Engineer — Badge: `INS-EMP-10492`) |
| **Isolation Execution Date** | `2026-09-29 07:15:00 UTC` |

---

### SECTION 2: HAZARDOUS ENERGY SOURCE INVENTORY & ISOLATION BOUNDARIES

The Isolation Authority has surveyed `AST-LASER-CNC-01` and identified the following energy hazards requiring positive mechanical lockout:

```
+---------------------------------------------------------------------------------------------------+
| HAZARDOUS ENERGY INVENTORY MATRIX                                                                 |
+--------+------------------+-----------------------+-----------------------+-----------------------+
| Ref ID | Energy Form      | Operating Magnitude   | Residual Hazard       | Required Isolation    |
+--------+------------------+-----------------------+-----------------------+-----------------------+
| ENG-01 | Electrical (AC)  | 400V AC, 3-Phase, 63A | Arc flash, electrocut.| Lockable MCC Breaker  |
| ENG-02 | Electrical (DC)  | 24V DC Control Logic  | Uncommanded PLC start | UPS Disconnect Switch |
| ENG-03 | Pneumatic Air    | 8.0 bar compressed air| Flying fittings, blast| 1/4-Turn Ball Valve   |
| ENG-04 | High-Pressure N2 | 30.0 bar assist gas   | Explosive release, N2 | Flanged Stainless Vlv |
| ENG-05 | Hydraulic Fluid  | 160 bar shuttle table | Crushing, injection   | Hydraulic Block Vlv   |
| ENG-06 | Stored Kinetic   | Shuttle table gravity | Mechanical entrapment | Physical Locking Pin  |
+--------+------------------+-----------------------+-----------------------+-----------------------+
```

---

### SECTION 3: ISOLATION SCHEDULE & LOCKOUT DEVICE APPLICATION REGISTER

*All isolations must follow the positive physical lockout standard: a physical hasp, dedicated red padlock, and danger tag applied to every energy point.*

| Iso Point Tag | Description & Physical Location | Energy Type | Applied Lockout Hardware Device | Padlock Serial Number | Applied Tag Number | Applied By (Name & ID) | Date & Time (UTC) |
| :---: | :--- | :---: | :--- | :---: | :---: | :--- | :---: |
| **ISO-E-01** | Substation 02 / MCC-B03 Breaker #CB-12 | 400V AC | Master Lock Clamp-On Breaker Lockout | `PL-RED-8821` | `TAG-00521-1` | D.Q. Cuong (`INS-EMP-10811`) | 07:18:00 |
| **ISO-E-02** | CNC Console Internal DC Isolator SW-01 | 24V DC | Rotary Dial Lockout Hasp + Lock | `PL-RED-8822` | `TAG-00521-2` | D.Q. Cuong (`INS-EMP-10811`) | 07:21:00 |
| **ISO-P-01** | Main Air Header Drop Valve V-PN-03 | 8.0 bar Air| Master Lock Ball Valve Lockout Clamp | `PL-RED-8823` | `TAG-00521-3` | D.Q. Cuong (`INS-EMP-10811`) | 07:24:00 |
| **ISO-G-01** | High-Pressure N2 Line Valve V-N2-30A | 30 bar N2 | Heavy-Duty Flanged Ball Valve Lockout | `PL-RED-8824` | `TAG-00521-4` | D.Q. Cuong (`INS-EMP-10811`) | 07:27:00 |
| **ISO-H-01** | Hydraulic Power Unit Supply Valve HV-01| 160 bar Hyd| Cable Lockout Device with 6-Hole Hasp | `PL-RED-8825` | `TAG-00521-5` | D.Q. Cuong (`INS-EMP-10811`) | 07:30:00 |
| **ISO-M-01** | Shuttle Table Frame Mechanical Interlock | Gravity | Steel Safety Locking Bar (Chock Pin)| `PL-RED-8826` | `TAG-00521-6` | D.Q. Cuong (`INS-EMP-10811`) | 07:33:00 |

*Master Lockout Box*: All six primary keys placed inside Insilos Master Lockout Box #MLB-03. Lead Technician Tran Van Duc applied Personal Blue Padlock `PL-BLU-4011` to the master box.

---

### SECTION 4: ZERO ENERGY STATE VERIFICATION & TRY-STEP PROTOCOL

*The Try-Step is mandatory: Never assume an isolation is effective without positive testing.*

```
+---------------------------------------------------------------------------------------------------+
| ZERO ENERGY STATE TEST VERIFICATION MATRIX                                                        |
+-------------+-----------------------------+-------------------------------+-----------------------+
| Point Ref   | Testing Method & Instrument | Measured Test Result          | Status Verified       |
+-------------+-----------------------------+-------------------------------+-----------------------+
| ISO-E-01    | Fluke 87V Digital Multimeter| L1-L2: 0.0V | L1-L3: 0.0V     | ZERO VOLTAGE CONFIRMED|
|             | (Calibrated: 2026-06-12)    | L2-L3: 0.0V | L1-PE: 0.0V     | Multimeter Bump-Tested|
+-------------+-----------------------------+-------------------------------+-----------------------+
| ISO-P-01    | Bleed Valve BV-01 Opened    | Pressure gauge drops to 0 bar | ZERO PNEUMATIC RESIDUAL|
+-------------+-----------------------------+-------------------------------+-----------------------+
| ISO-G-01    | Nitrogen Vent Needle Valve  | High-pressure vent opened;    | ZERO GAS PRESSURE     |
|             | NV-N2-02 Opened             | Digital gauge reads 0.00 bar  | Atmospheric vented    |
+-------------+-----------------------------+-------------------------------+-----------------------+
| ISO-H-01    | Hydraulic Accumulator Drain | Accumulator pressure dumped;  | ZERO HYDRAULIC FORCE  |
|             | Manual Dump Lever Actuated  | Analog gauge pinned at 0 bar  | Reservoir return open |
+-------------+-----------------------------+-------------------------------+-----------------------+
| TRY-STEP    | CNC Operator Panel          | Main CNC Start Pushbutton     | MACHINE COMPLETELY    |
| VERIFY      | Pushbutton Test             | pressed 3 times; E-Stop cycle | INERT & IMMOBILIZED   |
|             |                             | attempted -> ZERO RESPONSE    | (Zero Energy State)   |
+-------------+-----------------------------+-------------------------------+-----------------------+
```

---

### SECTION 5: PHYSICAL LOTO TAG SPECIFICATION (FRONT & REVERSE)

Every isolation point is affixed with a tear-resistant, chemical-resistant PVC safety tag conforming to the layout below:

```
+------------------------------------------+  +------------------------------------------+
|                 FRONT SIDE               |  |                REVERSE SIDE              |
+------------------------------------------+  +------------------------------------------+
|  [!] DANGER: DO NOT OPERATE / DO NOT MOVE|  |  ATTENTION: UNAUTHORIZED REMOVAL IS A    |
|                                          |  |  CRIMINAL AND GROSS SAFETY VIOLATION     |
|  THIS ENERGY SOURCE HAS BEEN LOCKED OUT  |  |  UNDER DECREE 12/2022/ND-CP ARTICLE 32   |
|                                          |  |                                          |
|  EQUIPMENT: 20kW Fiber Laser CNC Unit 01 |  |  DE-ISOLATION & RESTORATION PROCEDURE:   |
|  TAG NUMBER: TAG-00521-4                 |  |  1. Verify all personnel are clear.      |
|  ISO POINT: ISO-G-01 (N2 Line Valve)     |  |  2. Inspect machine for tool clearance.  |
|  PADLOCK SERIAL: PL-RED-8824             |  |  3. Reinstall all physical guards.       |
|                                          |  |  4. Notify Area Authority and Operator.  |
|  LOCKED BY: Dang Quoc Cuong              |  |  5. Return key to Master Lock Box.       |
|  EMPLOYEE BADGE: INS-EMP-10811           |  |                                          |
|  DEPARTMENT: Mechanical Maintenance      |  |  EMERGENCY LOCK CUTTING HOTLINE:         |
|  DATE APPLIED: 2026-09-29  TIME: 07:27   |  |  Plant Director Office: Ext 101          |
|  LINKED e-PTW: ePTW-2026-09-00842        |  |  Corporate Safety Desk: Ext 911          |
+------------------------------------------+  +------------------------------------------+
```

---

### SECTION 6: DE-ISOLATION, UNLOCKING & HANDBACK PROTOCOL

*(To be executed upon formal permit handback and work order completion)*

1. **Pre-Restoration Housekeeping Check**:
   - [x] All technicians, riggers, and apprentices accounted for and cleared from machine cell.
   - [x] All temporary tools, diagnostic leads, test pumps, and ground straps removed.
   - [x] All safety interlock door guards, polycarbonate screens, and cable trays re-bolted.

2. **Sequential Lock Removal & Re-Energization Sign-Off**:

| Step | Isolation Point | De-Isolation Action Taken | Removed By | Timestamp (UTC) |
| :-: | :---: | :--- | :--- | :---: |
| 1 | Personal Padlock | Lead Technician personal blue padlock removed from Master Box | Tran Van Duc | 16:35:00 |
| 2 | `ISO-M-01` | Steel safety chock pin removed from shuttle table | Dang Quoc Cuong | 16:38:00 |
| 3 | `ISO-H-01` | Hydraulic dump valve closed; supply valve opened | Dang Quoc Cuong | 16:40:00 |
| 4 | `ISO-G-01` | Nitrogen vent needle valve closed; main valve unlocked | Dang Quoc Cuong | 16:42:00 |
| 5 | `ISO-P-01` | Pneumatic drop valve unlocked and repressurized | Dang Quoc Cuong | 16:44:00 |
| 6 | `ISO-E-02` | 24V DC console logic switch turned ON and closed | Dang Quoc Cuong | 16:46:00 |
| 7 | `ISO-E-01` | MCC Breaker #CB-12 lock removed; breaker racked in & closed | Dang Quoc Cuong | 16:50:00 |

```
FINAL DE-ISOLATION SIGN-OFF:
Isolation Authority: Dang Quoc Cuong         Date/Time: 2026-09-29 16:52:00 UTC  Signature: [SIGNED]
Performing Authority: Tran Van Duc           Date/Time: 2026-09-29 16:55:00 UTC  Signature: [SIGNED]
Area Authority: Nguyen Hoang Nam             Date/Time: 2026-09-29 17:00:00 UTC  Signature: [SIGNED]
LOTO CERTIFICATE STATUS: [ DE-ISOLATED & SAFELY CLOSED OUT ]
```
