## Updated FHIR Resource Mappings and Transforms

This folder contains all of the YAML mapping files and the modified
`transforms.py` needed to translate HL7 v2.3–v2.5 messages into a
comprehensive set of FHIR resources.  In addition to the existing
mappings supplied with the Silhouette translator, the following
enhancements have been added:

### 1. Coverage of All HL7 Triggers

Earlier mapping bundles only supported a subset of HL7 triggers (e.g.
common ADT, SIU, ORM/ORU, RDE, DFT and MDM events).  Gap mappings
have been created so that every HL7 trigger event in versions 2.3
through 2.5 has a corresponding resource plan.  These mapping files
are:

- **`adt_others_uscore.yaml`** – covers all remaining ADT A‑code
  events by reusing the Patient/Encounter/Condition/AllergyIntolerance/
  Procedure plan from A01.
- **`siu_extended_uscore.yaml`** – extends SIU scheduling support to
  S13–S26 using the same Appointment‑centric mapping as S12.
- **`rde_extended_uscore.yaml`** – adds pharmacy administration
  (RAS^O17) and additional dispense/order triggers alongside the
  original RDE^O11, RDE^O25, RDS^O13 and RGV^O15 mappings.
- **`omx_uscore.yaml`** – maps general order messages (OMD/OMG/OML/OMN/OMP/OMS)
  to `ServiceRequest` resources.
- **`orx_uscore.yaml`** – handles observation‑result and specimen
  messages (ORF^R02/R04 and OUL^R21/R22) by producing bundles of
  `Patient`, `DiagnosticReport`, `Observation`, `Specimen`,
  `Condition`, `AllergyIntolerance` and `Procedure` as appropriate.
- **`dft_extended_uscore.yaml`** and **`bar_uscore.yaml`** – add
  support for the remaining DFT and BAR triggers by mapping FT1
  segments to `ChargeItem` and `Account` resources.
- **`mdm_extended_uscore.yaml`** – expands document management mappings
  to T01 and T03–T11 with `DocumentReference` and `Binary` resources.
- **`coverage_uscore.yaml`**, **`relatedperson_uscore.yaml`**, and
  **`research_uscore.yaml`** – create new resources from IN1
  (insurance), NK1 (next‑of‑kin) and clinical research triggers (CRM
  and CSU) using `Coverage`, `RelatedPerson`, `ResearchStudy` and
  `ResearchSubject`.
- **`misc_noresource_uscore.yaml`** – enumerates administrative and
  acknowledgement triggers (ACK/ADR/QRY/RSP/NMD/NMQ/NMR/CRM/CSU) that
  do not generate clinical resources.  These messages will still
  produce a `Device` and `Provenance` but no additional FHIR
  resources.

### 2. Additional FHIR Resource Coverage

Beyond the HL7 v2 triggers, the FHIR specification defines many
resources that may not be represented by HL7 segments but are still
critical for broader interoperability.  To support these, the
following changes were made:

- **`additional_resources_uscore.yaml`** – a mapping that attaches
  care‑coordination (`CarePlan`, `CareTeam`, `Goal`), family and
  risk assessments (`FamilyMemberHistory`, `RiskAssessment`),
  nutrition and supply workflows (`NutritionOrder`, `NutritionIntake`,
  `SupplyRequest`, `SupplyDelivery`), financial processing
  (`Claim`, `ClaimResponse`, `CoverageEligibilityRequest`,
  `CoverageEligibilityResponse`, `Invoice`, `PaymentNotice`,
  `PaymentReconciliation`), imaging and questionnaires
  (`ImagingStudy`, `Questionnaire`, `QuestionnaireResponse`), and
  device management (`DeviceRequest`, `DeviceDispense`, `DeviceUsage`)
  to every ADT event.  These resources are created with minimal
  information: they link back to the patient via `PID.3` and
  populate a default status using helper functions.
- **Enhancements in `transforms.py`** – new helper functions such as
  `default_careplan_status`, `default_careteam_status`,
  `default_goal_status`, `default_familymemberhistory_status`,
  `default_risk_assessment_status`, `default_nutritionorder_status`,
  `default_nutritionintake_status`, `default_supplyrequest_status`,
  `default_supplydelivery_status`, `default_claim_status`,
  `default_claimresponse_status`, `default_coverageeligibilityrequest_status`,
  `default_coverageeligibilityresponse_status`, `default_invoice_status`,
  `default_paymentnotice_status`, `default_paymentreconciliation_status`,
  `default_imagingstudy_status`, `default_questionnaire_status`,
  `default_questionnaireresponse_status`, `default_devicerequest_status`,
  `default_devicedispense_status`, and `default_deviceusage_status`.
  These return an appropriate default string (e.g., `"draft"`,
  `"active"`, `"unknown"`) for the corresponding resource.

### How to Use

1. **Copy the files** in this folder to the appropriate locations in your
   Silhouette repository:

   - All `.yaml` files in this directory should be placed into your
     project's `maps/` folder.
   - Replace the existing `silhouette_core/translators/transforms.py`
     with the one provided here.  The added helper functions are
     backwards‑compatible with the existing transforms.

2. **Run the translator** by specifying the path to the mapping file
   that covers the HL7 triggers you want to process.  For example:

   ```bash
   python -m silhouette_core.pipelines.hl7_to_fhir \
       --input your_hl7_message.hl7 \
       --map_path maps/adt_uscore.yaml  \
       --out out_dir/
   ```

   To exercise the gap mappings, use `adt_others_uscore.yaml` or any
   other mapping file depending on the message type.  The
   `additional_resources_uscore.yaml` can be used alongside the
   standard ADT mapping to produce the extra resources listed above.

3. **Validate the output** using a FHIR validator or by loading the
   resulting NDJSON bundles into a FHIR server.  Note that many of the
   additional resources created from ADT messages will contain only
   minimal data (a patient reference and status).  These are
   intentionally sparse to illustrate resource creation and may need
   enrichment from other workflows.

### Remaining Considerations

- **Resource completeness:**  Despite these additions, the FHIR
  specification includes many resources that are unrelated to
  HL7 v2 messages or are domain‑specific (e.g., genomics,
  manufacturing, public health).  These are not included here.
- **Data sparsity:**  Some resources (e.g., `Claim`, `CarePlan`)
  ordinarily require more detailed data than is available in a single
  HL7 v2 message.  In many cases, you will want to supplement
  information from other systems or extend the mapping rules to
  populate additional fields.
- **Merge/link events:**  Patient merge events (A30/A40/A41/A42)
  typically involve complex operations that may require `Person`
  resources and FHIR `$merge` operations rather than mere record
  creation.  This mapping simply reuses the A01 plan for these events.

By integrating these files, your translator will generate a wide
variety of FHIR resources across administrative, clinical, care
management, financial and research domains, ensuring that no HL7
triggers remain unmapped.