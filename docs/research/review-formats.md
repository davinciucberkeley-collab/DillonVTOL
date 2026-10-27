# Benchmark: comparable design reviews vs. our review page

All URLs checked 2026-10-26. "Opened" means the document text was read; "snippet" means only the search-engine summary was seen (page blocked by a TLS error or too large), so treat those notes as unverified.

Our page was assessed from `review/src/body.html` (h2/h3 headings plus spot reads of the requirements table, risk register, compliance checklist and cover).

## 1. Sources

| # | Name | Type | URL | What is notable | Read |
|---|------|------|-----|-----------------|------|
| 1 | NPR 7123.1D, Appendix G, Table G-6 (PDR) and Table G-7 (CDR) entrance and success criteria | NASA review guidance | https://explorers.larc.nasa.gov/APSMEX25/SMEX/pdf_files/NASA02_NPR_7123_1D.pdf | This is the official checklist for PDR and CDR. **Entrance:** previous RIDs, RFAs and action items are closed or have a closure plan; the agenda and success criteria are agreed before the review; a baselined V&V plan and integration plan exist. **PDR success:** the flow-down of verifiable requirements is complete; requirements trace to parent requirements and mission goals; margins and TPMs are reported; risks are "credibly assessed" with mitigation plans; interfaces are defined; new technology has backup options; safety and mission assurance are addressed. **CDR success:** the design meets requirements "with adequate margins"; ICDs are mature; the V&V plans are complete; the test approach is "comprehensive"; technical margins (mass, power) are adequate; FMEA and safety analysis are done. | Opened |
| 2 | NASA SE Handbook §6.7 Technical Assessment | NASA handbook (web) | https://www.nasa.gov/reference/6-7-technical-assessment/ | Every review needs a defined purpose and "entry and success criteria". Action items must be identified and resolved. Review minutes record results against the success criteria. PDR and CDR are where TPM trends are checked for "early warning signs". | Opened |
| 3 | NASA SE Handbook §3.5 (Phase B, PDR) and §3.6 (Phase C, CDR) | NASA handbook (web) | https://www.nasa.gov/reference/3-5-project-phase-b-preliminary-design-and-technology-completion/ ; https://www.nasa.gov/reference/3-6-project-phase-c-final-design-and-fabrication/ | PDR shows the design "complies with its requirements" and gives "unambiguous design-to specifications". CDR comes before fabrication and expects a data package, baselined V&V, manufacturing and assembly procedures, updated risks, and a safety data package. | Opened |
| 4 | NASA SE Handbook Appendix D, Requirements Verification Matrix | NASA handbook (web) | https://www.nasa.gov/reference/appendix-d-requirements-verification-matrix/ | Each "shall" gets a unique ID and its source is stated. The column layout is in an image I could not read; the standard methods (analysis, inspection, demonstration, test) are not in the page text. | Opened (table image not readable) |
| 5 | NASA SWEHB SWE-152, Review Requirements Mapping Matrices | NASA handbook (web) | https://swehb.nasa.gov/display/SWEHBVD/SWE-152+-+Review+Requirements+Mapping+Matrices | Traces forward (requirement to design to test) and backward (to source). Minimal columns: requirement ID, parent reference, description, design element, linked test case. | Opened |
| 6 | NASA S3001 Guidelines for Risk Management (ver G) | NASA risk guidance | https://www.nasa.gov/wp-content/uploads/2015/10/s3001_guidelines_for_risk_management_-_ver_g_-_10-25-2017.pdf | Uses a 5×5 likelihood × consequence matrix in which each cell carries a priority score. Each program defines its own category scales. | Snippet |
| 7 | AIAA DBF "Top 3 Design Reports 2026" | Competition, top-scoring reports | https://aiaa.org/wp-content/uploads/2026/06/Top-3-Design-Reports_2026.pdf | Compilation of the best-scored reports for 2026. The file is over 10 MB and could not be fetched; sources 8 and 9 stand in for the format. | Not opened (too large) |
| 8 | Cornell DBF 2022-23 Design Report | Competition design report | https://dbf.engineering.cornell.edu/reports/report_22-23.pdf | Standard DBF sequence: Executive Summary, Management Summary (team organisation, communication cadence, timeline and milestones), mission to design requirements, scoring sensitivity, configuration trades, preliminary design, detailed design, weight and balance, drawing package, manufacturing plan, test plan with a flight-test checklist, and a **predicted vs measured** comparison of thrust. A vice-lead doubles as safety officer. | Opened |
| 9 | Univ. of Washington DBF 2014-15 Design Report | Competition design report | https://www.aa.washington.edu/files/research/dbf/2015DBF_University%20of%20Washington.pdf | One-page executive summary that names the design drivers from the sensitivity study and states headline measured results (empty weight, laps flown, time). Includes a milestone flow chart, testing schedule, a "Performance Results" section (subsystem and flight), and references. | Opened (front matter) |
| 10 | SDSU "Quetzal" hybrid VTOL, Design Day 2026 | University capstone poster | https://electrical.sdsu.edu/design-day/files/2026/joint-quetzal.pdf | Gallery of every team member with their role (ME, AE and ECE leads; structures, avionics, controls, and so on). Has a Testing and Verification section. The conclusion says failure modes found in test drove a second iteration. | Opened |
| 11 | WPI MQP, fixed-wing/quadrotor hybrid with pusher (2020) | University senior design report (VTOL) | https://digital.wpi.edu/downloads/1c18dj389?locale=de | Closest analogue to our aircraft: a 1.54 m span with lift rotors plus a pusher, EPS wing with a carbon spar, and ArduPilot on a Pixhawk, built under a competition weight limit. | Snippet (TLS error) |
| 12 | SAE Aero Design oral-presentation score sheet (2017, via NAU capstone) | Competition judging rubric | https://www.cefns.nau.edu/capstone/projects/ME/2018/SAEAero/teaminfo/2017_Oral_Presentation_Score_Sheet_12_09_2016.pdf | Judges score "Demonstrate Understanding of Requirements", configuration selection, "Detailed Design and Test", performance prediction, **project management**, and presentation structure. | Snippet (TLS error) |
| 13 | ConvertibleUAV docs | Open-hardware VTOL project docs | https://convertibleuav.readthedocs.io/en/latest/README.html | Opens with the mission requirements as a bullet list. Docs build from source (Sphinx). Links to the issue tracker for contributions. Carries a licence and a liability disclaimer. | Opened |
| 14 | SimScale Project Library, "CFD-DRONE" | Public simulation project | https://www.simscale.com/projects/NHOBUU/cfd-drone/ | Organises the work as geometry, then mesh, then setup, then result, with counts at each stage (7 geometries, 5 meshes, 3 setups, 10 results). The provenance of each result is visible and the project can be copied. | Snippet |
| 15 | Onshape help, public documents | CAD platform public docs | https://cad.onshape.com/help/es/Content/Document/documents.htm | Public documents can be viewed and copied by any user. The forum shows peer comments attached to specific features. | Snippet |
| 16 | Purdue AAE 451 (Fall 2007) course schedule | University aircraft-design course | https://engineering.purdue.edu/~andrisan/Courses/AAE451_Fall_2007/AAE451_Buffer_F07/Schedule.pdf | Weekly "Quick Design Reviews" lead up to a PDR, so reviews are scheduled as a cadence rather than a single event. | Snippet |

## 2. Gap analysis

### What we already have that the benchmarks treat as expected
- **Revision record and sign-off block** (cover). This matches NASA review-record practice; DBF reports have nothing comparable.
- **Requirements table** R1–R20 with status chips and evidence links.
- **Risk register** with likelihood, impact, trigger, response and owner (Flight test §).
- **Regulatory compliance checklist** with rule citations and due dates (Schedule §).
- **Trade studies:** morphological chart, Pugh matrix, considered-and-dropped list, and MTOW sensitivity tornado.
- **Drawing set** (9 sheets), mass roll-up, CG envelope, and duty cycle.
- **Build-up flight test matrix** with entry, abort and success criteria; weakest-link ranking; crew roles.
- **Decisions for the client, closing ask, terms list**, and "What changed in v0.4".

### Where we go beyond the benchmarks
- Live numbers bound to `results.json`, regenerated by CI, so tables cannot go stale. No benchmark offers this.
- An interactive CAD model, CFD flow views, a thermal viewer and SITL scenarios, where DBF reports have static figures only.
- A GCI mesh study and independent verify.py checks. Student reports rarely quantify numerical uncertainty.
- Source lines under every table, which is finer-grained citation than any student report seen.
- Per-section "What the team must measure" lists, a distributed version of an open-items list.

### Gaps, against NPR 7123.1D Table G-6/G-7 and DBF/SAE practice
1. **No review entrance/success-criteria checklist.** NPR Table G-6 and G-7 structure the whole review around these criteria. A reviewer cannot tell which PDR or CDR criteria we claim to meet.
2. **Verification is not traced.** The requirements table has no verification-method column (analysis, inspection, demonstration, test), no parent or source column, and no link to a specific test card or measurement ID. NPR asks for "flow down of verifiable requirements" and for requirements "traceable to parent"; SWE-152 asks for requirement, design element and test case.
3. **No TPM and margin summary.** Margins on mass, T/W, stall, endurance, current, temperature and budget are spread across sections. NPR CDR criterion 6 asks for adequate technical margins, and §6.7 asks for TPM trends across issues.
4. **Risk register is weak.** It has six rows and every owner is "—". There is no 5×5 matrix plot, no risk IDs, no residual (post-mitigation) score and no trend. Technical risks (hover motor-out, stall margin, motor heat) sit in other sections and are not cross-linked. S3001 and NPR PDR criterion 7 expect risks to be "credibly assessed".
5. **No action-item or RID log.** Both NPR entrance criteria start with closing RIDs, RFAs and actions from the previous review. We have six issues and a six-reviewer audit, but no table of findings, dispositions and closure evidence.
6. **No safety or hazard analysis (FMEA).** The weakest-link table is close, but there is no hazard list with severity, controls and verification. CDR criterion 9 cites FMEA and system safety analysis.
7. **No predicted-vs-measured slots.** The DBF reports end with Performance Results comparing predicted and measured values. Our "must measure" items have no place for the measured value to land.
8. **No consolidated references list.** Sources are inline only. DBF and UW reports end with References, and the report/print view would benefit from a bibliography.
9. **No management summary or roles.** No team organisation, owners or RACI; crew "Names: —". DBF puts this in §2, and SAE scores project management.
10. **No executive summary in DBF form.** The Overview has key numbers and decision cards. It does not have a short prose summary of the design drivers, the chosen configuration, headline margins and the verdict, which is what DBF reports put on page 1.
11. **No interface definition (ICD).** We have a pins and wiring table and a fasteners section, but no mechanical, electrical and data interface list. NPR expects interface definition at PDR and mature ICDs at CDR.
12. **No lessons learned.** DBF gives a dedicated award for lessons learned (Stan Powell award, per AIAA results). The Iterations section tells what changed, not what the team learned.
13. **Nomenclature is partial.** There is a "Terms" list, but no symbol table with units (CL_max, T/W, FM·η, %MAC). DBF reports include one.
14. **Simulation provenance is not shown as a pipeline.** Following SimScale's geometry → mesh → setup → result chain, each CFD and FEA result could show its model revision, mesh and run date.
