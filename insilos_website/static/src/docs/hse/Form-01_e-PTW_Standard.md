# INSILOS INDUSTRIAL GROUP — STANDARD OPERATING FORM
## FORM-01: ELECTRONIC PERMIT-TO-WORK (e-PTW) STANDARD CERTIFICATE

**Document Identifier**: `INSILOS-FRM-HSE-001`  
**Revision**: `3.0`  
**Governing Standard**: `ISO 45001:2018 Clause 8.1, Vietnam Law on OSH No. 84/2015/QH13, Decree 44/2016/ND-CP`  
**Insilos ERP Integration**: `maintenance.request / mrp.production` Safety Interlock  
**GRC Collection**: `hse_permits`  

---

### SECTION 1: PERMIT ADMINISTRATIVE IDENTIFICATION

| Field Label | Field Record Specification / Data Entry |
| :--- | :--- |
| **e-PTW Master Number** | `ePTW-2026-09-00842` |
| **Insilos ERP Work Order Ref** | `WO-MAIN-2026-04192` (Asset: `AST-LASER-CNC-01`) |
| **GRC Permitting ID** | `GRC-PRM-882109` |
| **Permit Issue Date & Time** | `2026-09-29 07:30:00 UTC` |
| **Valid From (Commencement)**| `2026-09-29 08:00:00 UTC` |
| **Valid Until (Expiry Time)** | `2026-09-29 17:00:00 UTC` (Single shift maximum: 9.0 hours) |
| **Facility / Plant Location** | Insilos Heavy Mechanical Fabrication Complex — Workshop 02 |
| **Specific Work Area / Bay** | Zone A: Bay 03 — CNC Laser Cutting & High-Pressure Manifold Station |
| **Performing Organization** | [x] Internal Insilos Maintenance &nbsp;&nbsp;&nbsp;&nbsp; [ ] Resident Contractor &nbsp;&nbsp;&nbsp;&nbsp; [ ] Specialist Vendor |
| **Contractor / Department** | Mechanical Automation & Reliability Engineering Department |
| **Performing Authority (PA)** | Tran Van Duc (Lead Automation Engineer — Badge: `INS-EMP-10492`) |
| **Area Authority (AA)** | Nguyen Hoang Nam (Workshop 02 Production Superintendent — Badge: `INS-MGR-00214`) |

---

### SECTION 2: SCOPE OF WORK & ACTIVITY SPECIFICATION

```
DETAILED DESCRIPTION OF WORK:
De-pressurization, structural overhaul, and internal valve pack replacement on High-Pressure Nitrogen 
Assist Gas Manifold Skid (Line PN-30-A) serving 20kW Fiber Laser CNC Unit 01. Work includes oxy-acetylene 
brazing of secondary copper bypass loops, bolt torquing on 300 ANSI flanges, and elevated scaffold inspection.
```

- **Primary Tools & Machinery**: Oxy-acetylene brazing torch set, pneumatic torque wrench, ultrasonic leak detector, calibrated digital pressure calibrator, fiberglass scaffold tower (4.5m).
- **Assigned Crew Count**: 4 certified technicians + 1 dedicated safety watchman.
- **Estimated Task Duration**: 6.5 active working hours.

---

### SECTION 3: HIGH-RISK SUB-CERTIFICATE DETERMINATION

The Performing Authority and Area Authority have evaluated the task scope and determined that the following specialized sub-permits are legally mandated and attached:

| Required? | Sub-Permit Category | Associated Document / Certificate Reference | Status |
| :---: | :--- | :--- | :---: |
| **[X] YES** | **Hot Work (Class A — High Risk)** | Certificate Attached: `HW-2026-09-00842-A` | VERIFIED |
| **[ ] NO**  | Hot Work (Class B — Controlled Booth) | N/A | EXEMPT |
| **[X] YES** | **Confined Space Entry** | Form-03 Gas Testing Cert: `GTC-2026-09-00318` | ATTACHED |
| **[X] YES** | **Working at Height ($\ge 2.0\text{m}$)** | Height Safety Plan: `WAH-2026-09-00114` | ATTACHED |
| **[X] YES** | **Electrical Isolation & LOTO** | Form-04 LOTO Certificate: `LOTO-2026-09-00521` | LOCKED |
| **[ ] NO**  | Critical Tandem Crane Lift ($> 15\text{T}$) | N/A | EXEMPT |
| **[X] YES** | **SIMOPS Spatial Conflict Screening** | Form-02 SIMOPS Matrix: `SIMOPS-2026-09-044` | CLEARED |

---

### SECTION 4: MANDATORY PRE-JOB SAFETY CHECKLIST

*Every control item must be physically verified on site by the Performing Authority (PA) and Area Authority (AA) prior to issuing authorization. Check [X] when verified.*

- [x] **CHK-01: Job Safety Analysis (JSA)**: Formal HIRA/JSA completed, residual risk rated $\le 9$ (Yellow/Green), reviewed with all workers.
- [x] **CHK-02: Pre-Job Toolbox Talk (TBT)**: Conducted on site with all 5 crew members; emergency escape routes and muster points reviewed.
- [x] **CHK-03: Stop Work Authority (SWA)**: Universal SWA explained to crew; all members confirmed right to stop work without penalty.
- [x] **CHK-04: Physical Barricading**: Heavy-duty red/white safety chain and warning signs (`DANGER - PERMIT WORK IN PROGRESS`) erected at 15m radius.
- [x] **CHK-05: Fire Protection**: Two 9kg ABC dry chemical fire extinguishers and one 5kg CO2 extinguisher staged within 3m; fully charged and inspected.
- [x] **CHK-06: Spark Containment**: Heavy fire blankets (silica cloth, 1,200 deg C rating) deployed beneath brazing area; drains sealed with water-tight plugs.
- [x] **CHK-07: Atmospheric Gas Verification**: Direct reading multi-gas detector confirms $O_2 = 20.9\%$, $\text{LEL} = 0\%$, $CO = 0\text{ ppm}$, $H_2S = 0\text{ ppm}$.
- [x] **CHK-08: Hazardous Energy Lockout**: Nitrogen supply upstream valve tagged and locked (Padlock #L-8821); bleed valve open; gauge reads 0.0 bar.
- [x] **CHK-09: Scaffolding Certification**: 4.5m mobile scaffold tower inspected, outriggers fully deployed, green Scafftag (`INSPECTED & SAFE`) displayed.
- [x] **CHK-10: Fall Arrest Equipment**: Full-body harnesses (EN 361) inspected; dual shock-absorbing lanyards anchored to certified 22.2 kN overhead beam.
- [x] **CHK-11: Specialized PPE**: Shade 5 oxy-fuel goggles, Kevlar cut-resistant gloves, welding leather spats, steel-toe boots (S3-SRC) verified on all workers.
- [x] **CHK-12: Dedicated Fire Watch**: Standby watchman (Le Van Hai) appointed; equipped with air horn, extinguisher, and direct VHF radio link.
- [x] **CHK-13: Ventilation**: Explosion-proof localized exhaust fan (capacity: 2,500 m3/h) operational and grounded; duct routed to safe exterior zone.
- [x] **CHK-14: Environmental Controls**: Spill kit (absorbent booms, chemical pads) staged on site; drain covers secured against fluid entry.
- [x] **CHK-15: Lighting**: Low-voltage 24V DC intrinsically safe LED floodlights deployed for internal manifold enclosure inspection.
- [x] **CHK-16: Emergency Communications**: Direct contact established with Insilos Medical Clinic (Ext: 115) and Central HSE Control Room (Ext: 911).

---

### SECTION 5: CREW COMPETENCY & ATTENDANCE REGISTER

| # | Crew Member Full Name | Employee / Contractor ID | Trade / Function | Safety Passport Exp. | Digital Acknowledgement Signature |
| :-: | :--- | :--- | :--- | :---: | :--- |
| 1 | Tran Van Duc | `INS-EMP-10492` | Performing Authority / Lead Eng. | 2027-04-15 | `[DIGITALLY SIGNED - 07:35:12]` |
| 2 | Nguyen Quoc Bao | `INS-EMP-11028` | Senior Piping Technician | 2027-01-20 | `[DIGITALLY SIGNED - 07:36:04]` |
| 3 | Pham Minh Tuan | `INS-EMP-11450` | Certified Welder / Brazing Tech | 2026-11-30 | `[DIGITALLY SIGNED - 07:36:45]` |
| 4 | Vuong Dinh Khoa | `INS-EMP-12019` | Mechanical Fitter / Rigger | 2027-08-10 | `[DIGITALLY SIGNED - 07:37:18]` |
| 5 | Le Van Hai | `INS-EMP-10884` | Dedicated Fire & Standby Watch | 2027-03-25 | `[DIGITALLY SIGNED - 07:38:00]` |

---

### SECTION 6: MULTI-TIER DIGITAL AUTHORIZATION & SIGN-OFF

*Digital permits are verified via cryptographic SHA-256 tokens and registered on Vertical GRC (`hse_permits`).*

```
[1] PERFORMING AUTHORITY (Request & Field Commitment)
I certify that the work scope, hazards, and control measures have been physically inspected, communicated 
in the Toolbox Talk, and all required pre-conditions are fully established.
Name: Tran Van Duc                         Title: Lead Automation Engineer
Timestamp: 2026-09-29 07:38:20 UTC         HMAC-SHA256: 7d4a89f2e30b1c5a894e6612df081c790b91a56e

[2] ISOLATION & GAS TESTING AUTHORITY (Technical Endorsement)
I verify that LOTO isolations have achieved zero energy state and atmospheric gas testing is compliant.
Name: Dang Quoc Cuong                      Title: Certified Gas Tester & Electrical Specialist
Timestamp: 2026-09-29 07:42:15 UTC         HMAC-SHA256: c38914ba08210f9488a011de54209931bfa82144

[3] AREA AUTHORITY (Custodial Clearance)
I confirm that the plant area is safe for the specified work and that adjacent operational activities 
will not create unacceptable SIMOPS conflicts.
Name: Nguyen Hoang Nam                     Title: Workshop 02 Superintendent
Timestamp: 2026-09-29 07:45:00 UTC         HMAC-SHA256: 55a01bc89421de77fa09312bca08991204eb5811

[4] HSE COMPLIANCE AUDITOR (Review & Permit Validation)
I have audited the risk evaluation, sub-certificates, and emergency preparations, confirming total ISO 45001 
and statutory compliance.
Name: Hoang Thi Mai                        Title: Senior HSE Compliance Officer
Timestamp: 2026-09-29 07:48:30 UTC         HMAC-SHA256: 9910ba77de024511ef90223bcda018247fca8820

[5] AUTHORIZING AUTHORITY (Final Permit Issuance & ERP Unlock)
I hereby authorize the commencement of work under e-PTW-2026-09-00842. The ERP Work Order Safety Lock 
is officially released.
Name: Vu Dinh Quang                        Title: Director of Plant Operations
Timestamp: 2026-09-29 07:50:00 UTC         HMAC-SHA256: 1845bb098231fa649011de8830bc55104aef7712
PERMIT STATUS: [ APPROVED - ACTIVE ]
```

---

### SECTION 7: WORK COMPLETION, RE-COMMISSIONING & CLOSEOUT

*(To be executed upon task completion or permit expiry)*

1. **Housekeeping & Equipment Clearance**:
   - [x] All portable tools, welding cylinders, hoses, and scaffolding removed from work area.
   - [x] Scrap metal, replaced valves, spent fire blankets, and waste disposed of in designated bins.
   - [x] Fire watch sustained continuous thermal monitoring for 60 minutes post hot work completion (Zero smoldering confirmed via infrared thermometer).

2. **De-Isolation & Plant Re-Commissioning**:
   - [x] Nitrogen line pressure test completed; zero leaks detected at 30 bar test pressure.
   - [x] Machine guards, enclosure panels, and interlock sensors fully reinstalled.
   - [x] All LOTO padlocks and tags removed in accordance with Form-04 de-isolation sequence.

```
CLOSEOUT SIGN-OFF:
Performing Authority: Tran Van Duc          Date/Time: 2026-09-29 16:30:00 UTC  Signature: [SIGNED]
Area Authority: Nguyen Hoang Nam            Date/Time: 2026-09-29 16:45:00 UTC  Signature: [SIGNED]
HSE Officer: Hoang Thi Mai                  Date/Time: 2026-09-29 17:00:00 UTC  Signature: [SIGNED]
FINAL PERMIT STATUS: [ COMPLETED & ARCHIVED IN GRC ]
```
