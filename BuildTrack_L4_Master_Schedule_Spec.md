# BuildTrack — L4 Construction Schedule / BOQ / Progress Tracking Master Spec

**Deliverable:** Single-sheet Excel workbook — quantity-driven, location-aware, progress-control database for a hypothetical G+6 residential RCC building. Serves as the baseline master dataset for **BuildTrack**, a future multi-tenant construction-progress application (PostgreSQL backend, React/FastAPI app).

Sheet name: **`BUILDTRACK_L4_MASTER`** — one sheet only. Structured, filterable, sortable, formula-driven, and suitable for direct conversion into a database table.

---

## 1. Project Assumptions (DEMO / ASSUMED)

| Item | Value |
|---|---|
| Project | BuildTrack Demo Residential Development |
| Building | G+6 RCC framed residential building |
| Floors | Ground + 6 upper floors |
| Units per residential floor | 2 |
| Total residential units | 14 |
| Unit types | Type A, Type B |
| Plot area (illustrative) | ~2,500 m² |
| Building footprint (illustrative) | ~750 m² |

Each residential unit conceptually contains: Living/Dining, Kitchen, Bedroom 1, Bedroom 2, Study, Toilet 1, Toilet 2, Balcony, Utility area, Internal circulation.

Common/core spaces: Entrance lobby, Common corridors, Staircase, Lift lobby, Lift shaft, Electrical room, Plumbing/service shaft, Fire-fighting/service areas, Pump room, Water tank, Terrace, Roof/service area.

All assumed quantities must be clearly labeled **"DEMO / ASSUMED"**. The architecture must allow these to be swapped for actual project quantities without restructuring.

---

## 2. Physical Location Hierarchy

```
Project → Building/Tower → Level → Zone → Unit/Common Area → Room/Element
```

- **Building/Tower:** Tower A
- **Levels:** Ground Floor, Level 1–6, Level 7 / Terrace (where applicable)
- **Units:** A101, A102, A201, A202, A301, A302, A401, A402, A501, A502, A601, A602, A701, A702
- **Common area codes:** COM-GF, COM-L01…COM-L06, COM-L07, COM-EXT

Do not force unit-specific activities into a unit where the work is actually common/core.

---

## 3. Work Breakdown Structure — L2 Phases

| Code | Phase |
|---|---|
| 01 | Preconstruction, Mobilization & Approvals |
| 02 | Site Preparation & Survey |
| 03 | Earthwork & Excavation |
| 04 | Foundation & Substructure |
| 05 | RCC Superstructure |
| 06 | Masonry & Internal Partitions |
| 07 | Building Envelope & External Façade |
| 08 | Waterproofing |
| 09 | MEP First Fix |
| 10 | Internal Plastering, Screeding & Surface Preparation |
| 11 | Doors, Windows & Glazing |
| 12 | Flooring & Wall Finishes |
| 13 | Ceiling & Drywall |
| 14 | Painting |
| 15 | MEP Second Fix |
| 16 | External Works & Landscape |
| 17 | Vertical Transportation |
| 18 | Testing & Commissioning |
| 19 | Snagging & Defect Rectification |
| 20 | Handover & Closeout |

Each L2 phase decomposes into L3 zones and L4 measurable activities (full breakdown below).

---

## 4. L3 / L4 Detail by Phase

### 01 — Preconstruction, Mobilization & Approvals
**L3:** 01.01 Design & Engineering · 01.02 Statutory Approvals · 01.03 Mobilization · 01.04 Temporary Facilities · 01.05 Safety & QA/QC Setup

**L4:** IFC architectural drawings · IFC structural drawings · IFC MEP drawings · Shop drawing approval · Method statement approval · ITP approval · Material approval · Site office setup · Temporary electrical connection · Temporary water supply · Site fencing · Security setup · Temporary access road · Material storage yard · Safety signage · Emergency arrangements · QA/QC laboratory/setup · Survey equipment mobilization

### 02 — Site Preparation & Survey
**L3:** 02.01 Survey & Setting Out · 02.02 Site Clearance · 02.03 Existing Utilities · 02.04 Temporary Works · 02.05 Ground Preparation

**L4:** Site boundary demarcation · Topographical survey · Benchmark establishment · Temporary benchmark establishment · Gridline establishment · Building axis setting out · Building footprint setting out · Column grid setting out · Existing level verification · Site clearance · Vegetation removal · Debris removal · Existing obstruction removal · Existing utility identification · Temporary drainage · Temporary road · Site fencing · Ground stripping · Topsoil removal · Ground compaction · Formation preparation

### 03 — Earthwork & Excavation
**L3:** 03.01 Bulk Excavation · 03.02 Foundation Excavation · 03.03 Trench Excavation · 03.04 Dewatering · 03.05 Shoring / Slope Protection · 03.06 Backfilling

**L4:** Bulk excavation · Footing excavation · Raft excavation · Basement excavation (where applicable) · Column footing excavation · Service trench excavation · Drainage trench excavation · Disposal of excavated soil · Dewatering · Shoring · Slope protection · Formation level preparation · Soil replacement · Selected filling · Backfilling around foundations · Layer-wise compaction

### 04 — Foundation & Substructure
**L3:** 04.01 Piling · 04.02 PCC/Blinding · 04.03 Isolated Footings · 04.04 Raft Foundation · 04.05 Pile Caps · 04.06 Foundation Columns/Pedestals · 04.07 Basement Structure · 04.08 Retaining Walls · 04.09 Foundation Waterproofing · 04.10 Underground Drainage · 04.11 Backfilling

- **Piling L4** (only where applicable): Pile setting out · Boring · Temporary casing · Reinforcement cage · Tremie pipe installation · Concrete placement · Pile integrity testing · Pile load testing · Pile head breaking · Pile cut-off
- **PCC L4:** Surface preparation · PCC laying · Level checking · Finishing · Curing
- **Footing L4:** Footing reinforcement · Footing formwork · Embedded items · Pre-pour inspection · Concrete pouring · Concrete compaction · Concrete curing · De-shuttering · Waterproofing · Backfilling
- **Raft L4:** Formation preparation · Blinding concrete · Waterproofing · Reinforcement · Formwork · MEP sleeves · Pre-pour inspection · Concrete pouring · Concrete curing
- **Retaining wall L4:** Reinforcement · Formwork · Water stops · Embedded services · Concrete · Waterproofing · Drainage layer · Protection board · Backfilling

### 05 — RCC Superstructure
Floor-specific activities for Ground Floor through Level 7, as applicable.

**L3:** 05.01 Columns · 05.02 Beams · 05.03 Slabs · 05.04 Staircases · 05.05 Lift Core · 05.06 Shear Walls · 05.07 Roof/Terrace Structure · 05.08 Parapets · 05.09 Water Tank/Service Structures

- **Columns L4:** Column reinforcement · Column formwork · Column pre-pour inspection · Column concrete · Column curing · Column de-shuttering · Column dimensional inspection
- **Beams L4:** Beam reinforcement · Beam formwork · Beam MEP sleeves · Beam pre-pour inspection · Beam concrete · Beam curing · Beam de-shuttering
- **Slabs L4:** Slab formwork · Slab level checking · Slab reinforcement · Electrical conduits · Plumbing sleeves · Embedded items · Pre-pour inspection · Concrete pouring · Slump testing · Cube sampling · Concrete vibration · Surface finishing · Curing · De-shuttering · Post-pour inspection
- **Staircases L4:** Reinforcement · Formwork · Concrete · Curing · Finishing preparation
- **Lift core L4:** Reinforcement · Formwork · Concrete · Embedded plates · Openings

### 06 — Masonry & Internal Partitions
**L3:** 06.01 External Masonry · 06.02 Internal Masonry · 06.03 Toilet Partitions · 06.04 Service Shafts · 06.05 Lintels & Sills · 06.06 Openings

**L4:** AAC blockwork · Brickwork · Internal partition wall · External wall · Toilet partition · Kitchen partition · Utility partition · Shaft wall · Lintel · Sill · Wall opening · Door opening · Window opening · MEP sleeves · Wall chasing (where applicable)

### 07 — Building Envelope & External Façade
**L3:** 07.01 External Plaster · 07.02 Façade · 07.03 External Cladding · 07.04 Railings · 07.05 Louvers · 07.06 External Sealants

**L4:** External plaster · Texture coating · External paint preparation · Cladding panels · Stone/cladding · Balcony railing · Staircase railing · Window perimeter sealing · Façade sealant · Louvers · External architectural elements

### 08 — Waterproofing
**L3:** 08.01 Basement Waterproofing · 08.02 Toilet Waterproofing · 08.03 Balcony Waterproofing · 08.04 Terrace Waterproofing · 08.05 Roof Waterproofing · 08.06 Water Tank Waterproofing · 08.07 External Waterproofing

**L4:** Surface preparation · Primer · Waterproofing membrane · Protective coating · Corner treatment · Pipe penetration treatment · Drain outlet treatment · Flood test · Protection screed · Slope verification · Final waterproofing inspection

### 09 — MEP First Fix
**L3:** 09.01 Plumbing · 09.02 Drainage · 09.03 Electrical · 09.04 Fire Fighting · 09.05 HVAC · 09.06 ELV/ICT

- **Plumbing L4:** Water supply pipe · Hot water pipe · Soil pipe · Waste pipe · Vent pipe · Floor trap · Sleeve · Pressure testing
- **Electrical L4:** Conduit · Junction box · Switch box · DB box · Cable tray · Earthing · Sleeves
- **Fire L4:** Fire pipe · Sprinkler pipe · Hydrant pipe · Fire alarm conduit · Fire pump connection
- **ELV L4:** CCTV conduit · Data conduit · Access-control conduit · Intercom conduit

### 10 — Internal Plastering, Screeding & Surface Preparation
**L3:** 10.01 Internal Wall Plaster · 10.02 Ceiling Plaster · 10.03 External Plaster Preparation · 10.04 Floor Screed · 10.05 Toilet Screed · 10.06 Balcony Screed

Track by: Tower → Floor → Unit → Room. Rooms: Living, Kitchen, Bedroom 1, Bedroom 2, Study, Toilet 1, Toilet 2, Utility, Balcony, Corridor, Lobby.

### 11 — Doors, Windows & Glazing
**L3:** 11.01 Door Frames · 11.02 Door Shutters · 11.03 Windows · 11.04 Glazing · 11.05 Hardware · 11.06 Fire Doors

**L4:** Main door frame · Internal door frame · Toilet door frame · Door shutter · Door hardware · Aluminium window frame · Glass installation · Sealant · Balcony door · Fire-rated door

### 12 — Flooring & Wall Finishes
**L3:** 12.01 Floor Tiles · 12.02 Wall Tiles · 12.03 Stone Flooring · 12.04 Skirting · 12.05 Kitchen Counter · 12.06 Toilet Finishes

Track separately per room. **L4 example:** Living floor tile · Bedroom floor tile · Kitchen floor tile · Toilet floor tile · Balcony tile · Kitchen wall tile · Toilet wall tile · Skirting · Granite/marble · Kitchen countertop

### 13 — Ceiling & Drywall
**L3:** 13.01 Gypsum Ceiling · 13.02 False Ceiling · 13.03 Drywall · 13.04 Access Panels

**L4:** Ceiling framework · Ceiling board · Joint treatment · Access panel · Bulkhead · Service enclosure · Drywall partition

### 14 — Painting
**L3:** 14.01 Internal Walls · 14.02 Internal Ceiling · 14.03 External Paint · 14.04 Texture · 14.05 Touch-Up

**L4:** Surface preparation · Primer · Putty coat 1 · Putty coat 2 · Sanding · First coat · Second coat · Final touch-up

### 15 — MEP Second Fix
**L3:** 15.01 Electrical Fixtures · 15.02 Plumbing Fixtures · 15.03 Sanitary Fixtures · 15.04 Fire Fighting Fixtures · 15.05 HVAC Equipment · 15.06 ELV Devices

- **Electrical L4:** Switch · Socket · Light fixture · DB installation · Fan point · Distribution board
- **Plumbing L4:** WC · Wash basin · Sink · Mixer · Shower · Water heater · Floor trap
- **ELV L4:** CCTV · Access control · Data outlet · Intercom · Fire alarm devices

### 16 — External Works & Landscape
**L3:** 16.01 Roads · 16.02 Paving · 16.03 Stormwater · 16.04 Sewerage · 16.05 Water Supply · 16.06 Landscape · 16.07 External Electrical · 16.08 Compound Wall · 16.09 Gates

**L4:** Subgrade preparation · Road base · Paving · Kerbs · Stormwater drains · Manholes · Sewer line · Water line · Landscape soil · Plantation · Irrigation · External lighting · Compound wall · Gate installation

### 17 — Vertical Transportation
**L3:** 17.01 Lift Shaft Readiness · 17.02 Lift Installation · 17.03 Lift Testing · 17.04 Escalator (if applicable)

**L4:** Shaft readiness · Embedded plates · Guide rails · Lift machine · Cabin · Doors · Electrical connection · Testing · Commissioning

### 18 — Testing & Commissioning
**L3:** 18.01 Electrical Testing · 18.02 Plumbing Testing · 18.03 Fire System Testing · 18.04 HVAC Testing · 18.05 Lift Testing · 18.06 Emergency Systems · 18.07 Integrated Testing

**L4:** Insulation resistance · Earthing resistance · Pressure testing · Drainage testing · Fire pump testing · Sprinkler testing · Fire alarm testing · Emergency lighting · Generator testing · HVAC testing · Lift testing · Integrated MEP testing

### 19 — Snagging & Defect Rectification
**L3:** 19.01 Architectural Snags · 19.02 Civil Snags · 19.03 MEP Snags · 19.04 Waterproofing Snags · 19.05 Final Inspection

Every snag is location-specific, e.g. `Tower A → Level 4 → Unit A402 → Master Bedroom → Wall → Crack`.

**Tracked fields:** Snag ID · Description · Responsible contractor · Date raised · Target date · Status · Date closed · Photo reference

### 20 — Handover & Closeout
**L3:** 20.01 Documentation · 20.02 As-Built Drawings · 20.03 O&M Manuals · 20.04 Warranty · 20.05 Client Inspection · 20.06 Handover

**L4:** As-built architectural drawings · As-built structural drawings · As-built MEP drawings · O&M manuals · Equipment manuals · Warranty certificates · Test certificates · Inspection records · Material certificates · Final snag closure · Client handover · Facility management handover

---

## 5. One-Sheet Column Structure

| Col | Field | Col | Field | Col | Field | Col | Field |
|---|---|---|---|---|---|---|---|
| A | Project_ID | O | WBS_L3 | AC | Planned_Quantity | AQ | Predecessor |
| B | Project_Name | P | WBS_L4 | AD | Reported_Quantity | AR | Dependency_Type |
| C | Building_ID | Q | WBS_Code | AE | Inspected_Quantity | AS | Responsible_Contractor |
| D | Building_Name | R | Activity_ID | AF | Accepted_Quantity | AT | Responsible_Engineer |
| E | Floor_ID | S | Activity_Name | AG | Balance_Quantity | AU | Planned_Manpower |
| F | Floor_Name | T | Activity_Description | AH | Physical_Progress_% | AV | Actual_Manpower |
| G | Unit_ID | U | Trade | AI | Activity_Weight_% | AW | Planned_Cost |
| H | Unit_Type | V | Discipline | AJ | Weighted_Progress_% | AX | Actual_Cost |
| I | Zone_ID | W | BOQ_Item_Code | AK | Baseline_Start | AY | Cost_Progress_% |
| J | Zone_Name | X | BOQ_Description | AL | Baseline_Finish | AZ | Schedule_Status |
| K | Room_ID | Y | Specification_Reference | AM | Actual_Start | BA | Progress_Status |
| L | Room_Name | Z | Drawing_Reference | AN | Actual_Finish | BB | Inspection_Status |
| M | WBS_L1 | AA | Location_Code | AO | Planned_Duration_Days | BC | RFI_Status |
| N | WBS_L2 | AB | UOM | AP | Actual_Duration_Days | BD | NCR_Status |

...continuing:

| Col | Field | Col | Field |
|---|---|---|---|
| BE | Material_Status | BJ | Photo_Count |
| BF | Drawing_Status | BK | Evidence_Status |
| BG | Constraint_Status | BL | Remarks |
| BH | Risk_Status | BM | Last_Updated |
| BI | Photo_Required | BN | Updated_By |
| | | BO | Data_Source |
| | | BP | Record_Status |

---

## 6. UOM Standardization

Controlled list: `m · m² · m³ · kg · MT · Nos · Set · Lot · Point · RM · Cum · Sqm · Litre · Hour · Day · %`

| Activity type | UOM |
|---|---|
| Excavation | m³ |
| PCC / RCC | m³ |
| Reinforcement | MT |
| Formwork | m² |
| AAC blockwork | m² |
| Plaster | m² |
| Waterproofing | m² |
| Floor tile | m² |
| Doors | Nos |
| Windows | m² or Nos (per BOQ structure) |
| Sanitary fixtures | Nos |
| Electrical points | Nos |
| Cable | m |
| Piping | m |
| Equipment | Nos |
| Testing | Nos / Lot |
| Painting | m² |

---

## 7. BOQ Principle

Do not assign one generic quantity to the whole building where the activity can be measured by location. Break down along:

```
Project → Tower → Floor → Unit → Room
```

Example — Internal plaster:
- Tower A → Level 1 → Unit A101 → Living → 120 m²
- Tower A → Level 1 → Unit A101 → Bedroom 1 → 45 m²
- Tower A → Level 1 → Unit A101 → Bedroom 2 → 42 m²

The same activity may repeat many times, each with a distinct location code — this is expected.

---

## 8. Progress Calculation (formula-driven, not typed values)

- **Physical Progress %** = Accepted Quantity / Planned Quantity × 100 (never above 100% without an approved variation)
- **Balance Quantity** = Planned Quantity − Accepted Quantity
- **Weighted Progress** = Physical Progress % × Activity Weight %
- Total activity weights across the project must sum to **100%**
- Where Planned Quantity = 0 → Physical Progress = 0
- Where activity is Not Applicable → excluded from weighted progress calculations

---

## 9. Acceptance Workflow

```
Reported → Inspected → Accepted
```

Official project progress is based on **Accepted Quantity**, never Reported Quantity.

**Example:** Planned = 100 m², Reported = 80 m², Inspected = 75 m², Accepted = 70 m² → **Official progress = 70%**

---

## 10. Activity Weighting

Weight = Activity BOQ Value / Total Applicable BOQ Value (not equal-distribution).

Where cost data is unavailable in the demo dataset, use a reasonable assumed structure clearly marked:
**"DEMO WEIGHT — REPLACE WITH APPROVED BOQ WEIGHT"**

Final normalized project weight must equal **100%**.

---

## 11. Schedule Information

Every L4 activity carries: Baseline Start, Baseline Finish, Duration, Predecessor, Dependency Type (`FS / SS / FF / SF`).

**Typical sequencing:**
- Foundation: Excavation → PCC → Reinforcement → Formwork → Pre-pour inspection → Concrete → Curing → Backfill
- RCC columns: Reinforcement → Formwork → Inspection → Concrete → Curing
- Slabs: Formwork → Reinforcement → MEP sleeves → Pre-pour inspection → Concrete pour → Curing → De-shuttering
- Interiors: Masonry → MEP first fix → Plaster → Waterproofing (where applicable) → Screed → Ceiling → Flooring → Painting → MEP second fix → Final inspection

---

## 12. Status Fields

| Field | Values |
|---|---|
| Progress Status | Not Started · In Progress · Reported · Under Inspection · Accepted · Completed · On Hold · Delayed · Not Applicable |
| Inspection Status | Pending · Compliant · Non-Compliant · Not Applicable |
| Material Status | Not Required · Pending Approval · Approved · Ordered · Delivered · Rejected |
| Drawing Status | Not Available · For Review · Approved · Revision Required · IFC |
| RFI Status | Not Required · Open · Submitted · Answered · Closed |
| NCR Status | None · Open · Under Rectification · Closed |

---

## 13. Quality / Inspection Integration

For every activity requiring inspection: Inspection_Required, Inspection_Status, Inspection_Date, Inspector, RFI_Reference, NCR_Reference, Evidence_Status, Photo_Count, Inspection_Remarks.

Status model: **Pending · OK/Compliant · NC/Non-Compliant · NA**

Non-Compliant activities must not have their accepted quantity auto-increase until the acceptance condition is satisfied. Photo evidence attaches per activity. Should support summary reporting of total/checked/NC/OK/NA items.

---

## 14. Room-Level Tracking

Rooms: Living/Dining, Kitchen, Bedroom 1, Bedroom 2, Study, Toilet 1, Toilet 2, Balcony, Utility, Corridor.

**Example rows:**
- A401 | Unit A | Level 4 | Bedroom 1 | Internal Plaster | 45 m²
- A401 | Unit A | Level 4 | Kitchen | Wall Tiles | 32 m²
- A401 | Unit A | Level 4 | Toilet 1 | Waterproofing | 8 m²
- A401 | Unit A | Level 4 | Balcony | Floor Tiles | 12 m²

---

## 15. Common Area Tracking

Separate records for: Lobby, Lift lobby, Corridor, Staircase, Electrical room, Pump room, Fire room, Service shaft, Terrace, Roof, External area. **Never mix common-area quantities into unit quantities.**

---

## 16. Resource Tracking

Fields: Planned manpower, Actual manpower, Trade, Contractor, Supervisor, Equipment (where relevant).

Trades: Civil, Structural, Masonry, Plaster, Waterproofing, Electrical, Plumbing, HVAC, Fire Fighting, Painting, Flooring, Carpentry, Aluminium, Landscape.

---

## 17. Cost Integration

Fields: BOQ Rate, BOQ Amount, Planned Cost, Actual Cost, Committed Cost, Earned Value.

Dataset should be prepared so future BuildTrack functionality can calculate: **SPI, CPI, Schedule Variance, Cost Variance, EAC**.

---

## 18. Construction Evidence

Fields: Photo Required, Photo Count, Evidence Status, Last Photo Date, Inspection Reference, RFI Reference, NCR Reference.

Evidence Status: **Missing · Uploaded · Verified · Rejected**

Photos are stored separately (e.g. object storage); only metadata/reference lives in this master table.

---

## 19. Data Quality Rules

- WBS code must be unique
- Activity ID must be unique
- BOQ item code unique where applicable
- UOM must come from the controlled list
- Accepted ≤ Inspected ≤ Reported ≤ Planned (unless approved variation)
- Physical progress ≤ 100% unless approved variation
- Total normalized weights = 100%
- Every L4 activity belongs to an L3 zone; every L3 zone belongs to an L2 phase
- Location code must be valid
- Unit-specific activities must have a Unit_ID; common activities must use Common Area codes
- Completed activities must have appropriate evidence/inspection status
- Activities requiring inspection cannot be officially accepted without inspection
- Closed NCRs must be linked to evidence
- Delayed activities must have remarks/constraint information

---

## 20. Excel Formatting Requirements

- Freeze top row
- Filters enabled on every column
- Formatted as an Excel Table
- Visually distinguishable WBS columns
- Conditional formatting:
  - **Green** — Completed / Accepted / Compliant
  - **Blue** — In Progress
  - **Amber** — Under Inspection / Pending
  - **Red** — Delayed / Non-Compliant / NCR Open
  - **Grey** — Not Applicable
- Highlight: negative quantity variance, delayed activities, missing evidence, open NCR, open RFI, material shortage, unapproved drawings, constraints present
- No excessive color use

---

## 21. Sample Data Requirement

Populate with realistic **DEMONSTRATION** records (not a blank template) covering: site prep, survey, excavation, foundation, RCC, masonry, waterproofing, MEP, plaster, flooring, painting, doors/windows, external works, testing, handover — across multiple floors and units, with repeated activities to demonstrate location-based tracking.

---

## 22. Dashboard-Ready Data Design

Dataset must support future calculation of: Overall Project Progress, Phase/Tower/Floor/Unit/Room Progress, Trade Progress, Contractor Progress, BOQ Progress, Quantity Progress, Cost Progress, Schedule Progress, Inspection Progress, NCR Count, RFI Count, Delayed Activities, Material/Drawing/Safety-Quality Constraints.

**No merged cells inside the data table** — every row is an independent, atomic record.

---

## 23. Core Database Principle

Treat the spreadsheet as a **relational staging table**, not a presentation schedule. One row = one measurable L4 activity/location combination. Never create hierarchical merged rows (e.g. "RCC Works" → "Columns" → "Column Concrete"); instead, every row carries its full hierarchy (Project, Building, Floor, Unit, Zone, WBS L2/L3/L4, Activity, BOQ, Quantity, UOM, Schedule, Progress) so it can be ingested directly into PostgreSQL.

---

## 24. Final Quality Checklist (before producing the Excel file)

- [ ] All 20 major phases exist
- [ ] Each phase has L3 zones
- [ ] Each L3 zone has L4 measurable activities
- [ ] All activities have UOM
- [ ] Measurable activities have planned quantities
- [ ] Location hierarchy populated wherever applicable
- [ ] Floor and unit repetitions exist
- [ ] Activity weights present
- [ ] Total normalized weights equal 100%
- [ ] Formula-driven progress exists
- [ ] Accepted quantity drives official progress
- [ ] Inspection status exists
- [ ] Quality evidence fields exist
- [ ] Schedule fields exist
- [ ] Contractor/responsibility fields exist
- [ ] BOQ fields exist
- [ ] Cost fields exist
- [ ] Dependency fields exist
- [ ] No merged cells inside the data table
- [ ] Filters and freeze panes applied
- [ ] Demonstration assumptions clearly identified
- [ ] Dataset importable into PostgreSQL without restructuring
