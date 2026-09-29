# INSILOS INDUSTRIAL GROUP — STANDARD OPERATING FORM
## FORM-02: SIMOPS (SIMULTANEOUS OPERATIONS) CONFLICT EVALUATION & CO-LOCATION MATRIX

**Document Identifier**: `INSILOS-FRM-HSE-002`  
**Revision**: `3.0`  
**Governing Standard**: `ISO 45001:2018 Clause 8.1, SOP-01 (INSILOS-SOP-HSE-001 §8), Decree 44/2016/ND-CP`  
**GRC Permitting Collection**: `hse_simops_assessments`  
**ERP Integration**: Insilos ERP Maintenance & Manufacturing Schedule Validator  

---

### SECTION 1: ASSESSMENT ADMINISTRATIVE IDENTIFICATION

| Field Description | Parameter Specification / Data Record |
| :--- | :--- |
| **SIMOPS Evaluation Number** | `SIMOPS-2026-09-044` |
| **Assessment Date & Time** | `2026-09-29 06:45:00 UTC` |
| **Facility / Terminal Name** | Insilos Heavy Mechanical & Maritime Terminal Complex |
| **Primary Work Location** | Workshop 02 (Fabrication Bay) & Adjacent Logistics Staging Yard 02 |
| **Operational Period** | `2026-09-29 08:00:00 UTC` to `2026-09-29 18:00:00 UTC` |
| **Lead SIMOPS Coordinator** | Nguyen Hoang Nam (Workshop 02 Production Superintendent — Badge: `INS-MGR-00214`) |
| **Lead HSE Risk Assessor** | Hoang Thi Mai (Senior HSE Compliance Officer — Badge: `INS-HSE-00088`) |
| **Active Primary Permit 1** | `ePTW-2026-09-00842`: Nitrogen Manifold Overhaul & Brazing (Zone A / Bay 03) |
| **Active Concurrent Permit 2**| `ePTW-2026-09-00845`: 50-Ton Overhead Crane Track Alignment & Lifting (Bay 03-04) |
| **Active Concurrent Permit 3**| `ePTW-2026-09-00849`: Robotic Welding Cell 02 Jig Re-tooling (Zone B / Bay 02) |

---

### SECTION 2: SPATIAL ZONE BOUNDARY & SEPARATION RADII

```
+---------------------------------------------------------------------------------------------------+
| PHYSICAL WORKSHOP 02 GEOMETRIC LAYOUT & OVERLAPPING IMPACT RADII                                  |
|                                                                                                   |
|    +-----------------------------+               +-----------------------------+                  |
|    | ZONE B: ROBOTIC WELDING     |               | ZONE A: LASER CNC BAY 03    |                  |
|    | Activity: Robot Jig Retool  |               | Activity: N2 Line Brazing   |                  |
|    | Permit: ePTW-00849          |               | Permit: ePTW-00842          |                  |
|    | Buffer: 10m Exclusion       |               | Buffer: 15m Hot Work Radius |                  |
|    +--------------+--------------+               +--------------+--------------+                  |
|                   |                                             |                                 |
|                   |                   SHARED CRANE              |                                 |
|                   +=================== RUNWAY BEAM =============+                                 |
|                                       (BAY 03-04)                                                 |
|                                            ^                                                      |
|                                            |                                                      |
|                             +--------------+--------------+                                       |
|                             | 50-TON OVERHEAD CRANE LIFT  |                                       |
|                             | Permit: ePTW-00845          |                                       |
|                             | Sweep Radius: 25m Envelope  |                                       |
|                             +-----------------------------+                                       |
+---------------------------------------------------------------------------------------------------+
```

- **Zone A (Laser Cutting Bay 03)**: Defined by grid coordinates `[X: 120-160m, Y: 40-75m]`. Contains high-pressure nitrogen gas pipe rack, fiber laser bed, and elevated mezzanine.
- **Zone B (Robotic Welding Bay 02)**: Defined by grid coordinates `[X: 80-115m, Y: 40-75m]`. Separated by a 5-meter wide logistics aisle and 2.5m acoustic partition screen.
- **Overhead Runway (Bays 03-04)**: Crane hook path traverses directly overhead from `X: 100m` to `X: 220m` at elevation `+12.5m`.

---

### SECTION 3: SIMOPS 8x8 ACTIVITY INTERACTION EVALUATION MATRIX

The table below defines the corporate interaction constraints between any pair of simultaneous industrial operations occurring within a shared workshop or terminal zone:

| Activity Code / Activity Name | ACT-01 Hot Work (Arc/Brazing) | ACT-02 Confined Space Entry | ACT-03 Heavy Crane Lift (>10T) | ACT-04 Scaffolding Work (>4m) | ACT-05 Flammable Liquid Transfer | ACT-06 High Voltage Switchgear | ACT-07 Heavy Forklift / AGV Path | ACT-08 Shotblasting / Spray Paint |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **ACT-01 Hot Work** | **Y** | **R** | **R** | **Y** | **R** | **R** | **Y** | **R** |
| **ACT-02 Confined Space** | **R** | **G** | **R** | **Y** | **R** | **Y** | **R** | **R** |
| **ACT-03 Heavy Crane Lift**| **R** | **R** | **Y** | **R** | **R** | **Y** | **R** | **R** |
| **ACT-04 Scaffolding (>4m)**| **Y** | **Y** | **R** | **Y** | **Y** | **G** | **R** | **Y** |
| **ACT-05 Flammable Liquid**| **R** | **R** | **R** | **Y** | **G** | **R** | **Y** | **R** |
| **ACT-06 High Voltage (22kV)**| **R** | **Y** | **Y** | **G** | **R** | **Y** | **G** | **Y** |
| **ACT-07 Forklift / AGV** | **Y** | **R** | **R** | **R** | **Y** | **G** | **G** | **Y** |
| **ACT-08 Spray Painting** | **R** | **R** | **R** | **Y** | **R** | **Y** | **Y** | **G** |

**Interaction Constraint Definitions**:
- **R (RED - STRICTLY PROHIBITED)**: Direct operational collision. Total prohibition of co-location within the same zone or overlapping radial buffer. One operation must be completed or deferred before the other may start.
- **Y (YELLOW - CONDITIONAL APPROVAL WITH SPECIFIC CONTROLS)**: Permitted only when compensatory engineered barriers, administrative controls, and shared communication links are established and verified in Section 4.
- **G (GREEN - PERMITTED WITH STANDARD CONTROLS)**: Routine concurrent operations permitted under standard individual e-PTW rules.

---

### SECTION 4: SPECIFIC COMPENSATORY CONTROL PLAN FOR IDENTIFIED CONFLICTS

Based on active permits scheduled for 2026-09-29, the following **YELLOW** and potential **RED** conflicts have been analyzed and mitigated:

#### Conflict Pair 1: ACT-01 (Hot Work Brazing - ePTW-00842) vs. ACT-03 (Overhead Crane Lift - ePTW-00845)
- **Initial Classification**: **RED (Prohibited)** if crane carries load directly above brazing station.
- **Engineered & Operational Resolution**:
  1. The programmable electronic travel limits (PLC Geofence) on Overhead Crane 02 are programmed to restrict bridge travel, establishing a strict virtual buffer preventing the crane trolley from entering Bay 03 between coordinates `X: 120m` and `X: 160m`.
  2. Physical mechanical track stops are bolted to the crane rail at column line 18, physically arresting crane travel 5 meters prior to the brazing scaffold boundary.
  3. With physical and software barriers verified, the interaction is reclassified to **CONDITIONAL (YELLOW)** and authorized.

#### Conflict Pair 2: ACT-01 (Hot Work Brazing - ePTW-00842) vs. ACT-04 (Scaffolding Mezzanine Work)
- **Initial Classification**: **YELLOW (Conditional)** due to spark migration dropping onto lower platform levels.
- **Mandatory Controls**:
  1. Fire-retardant silica blankets (1,200 deg C rating) secured with steel C-clamps fully enveloping the underside and handrails of the 4.5m scaffold platform.
  2. Floor drains within 15 meters plugged with neoprene expansion plugs and covered with moist sandbags.
  3. Ground-level exclusion barricade (15m radius) manned continuously by dedicated watchman Le Van Hai.

#### Conflict Pair 3: ACT-01 (Hot Work - ePTW-00842) vs. ACT-07 (Automated Guided Vehicle / Forklift Traffic)
- **Initial Classification**: **YELLOW (Conditional)** due to collision risk with scaffold legs or gas hose severance.
- **Mandatory Controls**:
  1. The AGV automated transit route in Insilos ERP Fleet/Manufacturing module is dynamically detoured through Aisle C, completely bypassing Workshop 02 Bay 03.
  2. Heavy steel bollards (removable magnetic type, 1.2m height) deployed across Bay 03 forklift access gates.

---

### SECTION 5: EMERGENCY HIERARCHY & COMMUNICATIONS PROTOCOL

1. **Dedicated Radio Channel**: All concurrent work crews must maintain continuous monitoring on **Industrial VHF Channel 04 (Frequency: 457.550 MHz)**.
2. **Emergency Shutdown Hierarchy**:
   - If an alarm sounds, **Crews executing Hot Work (ePTW-00842)** must instantly close cylinder valves, kill torches, and stand down within 10 seconds.
   - **Overhead Crane Operators (ePTW-00845)** must immediately arrest motion, lower any suspended load to the deck if safe to do so, and engage parking brakes.
   - **Robotic Cells (ePTW-00849)** will automatically trip via software interlock or manual E-Stop strike.
3. **Evacuation Assembly Route**: All Workshop 02 crews must evacuate through Emergency Exit Door 04 directly to Primary Muster Point B (North Logistics Yard).

---

### SECTION 6: MULTI-AUTHORITY JOINT REVIEW & SIGN-OFF

*By signing below, all authorities confirm that the co-location controls detailed above are physically inspected, installed, and mutually agreed upon.*

```
LEAD SIMOPS COORDINATOR:
Name: Nguyen Hoang Nam               Badge: INS-MGR-00214        Date: 2026-09-29 07:15:00 UTC
Signature: [DIGITALLY SIGNED & VERIFIED IN GRC]

PERFORMING AUTHORITY 1 (Hot Work - ePTW-00842):
Name: Tran Van Duc                   Badge: INS-EMP-10492        Date: 2026-09-29 07:18:22 UTC
Signature: [DIGITALLY SIGNED & VERIFIED IN GRC]

PERFORMING AUTHORITY 2 (Crane Lift - ePTW-00845):
Name: Pham Van Long                  Badge: INS-EMP-10651        Date: 2026-09-29 07:20:10 UTC
Signature: [DIGITALLY SIGNED & VERIFIED IN GRC]

PERFORMING AUTHORITY 3 (Robotic Cell - ePTW-00849):
Name: Dinh Trong Hieu                Badge: INS-EMP-10933        Date: 2026-09-29 07:22:45 UTC
Signature: [DIGITALLY SIGNED & VERIFIED IN GRC]

SENIOR HSE COMPLIANCE AUDITOR:
Name: Hoang Thi Mai                  Badge: INS-HSE-00088        Date: 2026-09-29 07:25:00 UTC
Signature: [DIGITALLY SIGNED & VERIFIED IN GRC]
SIMOPS STATUS: [ OFFICIALLY CLEARED FOR EXECUTION ]
```
