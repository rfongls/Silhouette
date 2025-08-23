// static/hl7_ui.js
const HL7_PRESETS = {
  "VXU^V04": {
    sending_app: "IMM", sending_facility: "SENDER",
    receiving_app: "IIS", receiving_facility: "STATE",
    patient_id: "123456", assigning_authority: "SENDER",
    family: "DOE", given: "JOHN", dob: "19800101", sex: "M",
    admin_date: "20240101",
    cvx_code: "208", cvx_text: "Influenza, injectable, quadrivalent",
    dose: "0.5", dose_unit: "mL",
    lot: "Lot123", exp: "20250101",
    route_id: "IM", route_text: "Intramuscular",
    site_id: "LD", site_text: "Left deltoid"
  },
  "RDE^O11": {
    sending_app: "PHARM", sending_facility: "HOSP",
    receiving_app: "EHR", receiving_facility: "HOSP",
    patient_id: "123456", assigning_authority: "HOSP",
    family: "DOE", given: "JOHN", dob: "19800101", sex: "M",
    order_number: "ORD1122",
    dose_value: "500", dose_unit: "mg",
    frequency: "BID",
    provider_id: "12345", provider_family: "PRESCRIBER", provider_given: "DOE",
    route_id: "PO", route_text: "Oral"
  },
  "ORM^O01": {
    sending_app: "LIS", sending_facility: "ACME",
    receiving_app: "EHR", receiving_facility: "ACME",
    patient_id: "123456", assigning_authority: "ACME",
    family: "DOE", given: "JOHN", dob: "19800101", sex: "M",
    order_number: "ORD7788",
    loinc: "718-7", loinc_text: "HEMOGLOBIN",
    obs_date: "202402091100"
  },
  "OML^O21": {
    sending_app: "LIS", sending_facility: "ACME",
    receiving_app: "EHR", receiving_facility: "ACME",
    patient_id: "123456", assigning_authority: "ACME",
    family: "DOE", given: "JOHN", dob: "19800101", sex: "M",
    order_number: "ORD7788",
    loinc: "4548-4", loinc_text: "HEMATOCRIT",
    priority: "routine"
  },
  "ORU^R01:RAD": {
    sending_app: "RIS", sending_facility: "ACME",
    receiving_app: "EHR", receiving_facility: "ACME",
    patient_id: "123456", assigning_authority: "ACME",
    family: "DOE", given: "JOHN", dob: "19800101", sex: "M",
    accession: "ACC123",
    loinc: "24606-6", loinc_text: "XR Chest 2 Views",
    result_text: "No acute cardiopulmonary disease identified.",
    result_date: "202402091200"
  },
  "MDM^T02": {
    sending_app: "TX", sending_facility: "HOSP",
    receiving_app: "EHR", receiving_facility: "HOSP",
    patient_id: "123456", assigning_authority: "HOSP",
    family: "DOE", given: "JOHN", dob: "19800101", sex: "M",
    doc_type: "RADRPT",
    doc_date: "202402091230",
    author_id: "DR", author_family: "RAY", author_given: "DIAN",
    attachment_contentType: "application/pdf",
    attachment_encoding: "Base64",
    attachment_data_base64: "VGhpcyBpcyBhIHNhbXBsZSByYWRpb2xvZ3kgcGRmLg=="
  },
  "ADT^A01": {
    sending_app: "ADT", sending_facility: "HOSP",
    receiving_app: "EHR", receiving_facility: "HOSP",
    patient_id: "123456", assigning_authority: "HOSP",
    family: "DOE", given: "JOHN", dob: "19800101", sex: "M",
    class_code: "I", admission_time: "202402091015"
  },
  "SIU^S12": {
    sending_app: "SCH", sending_facility: "CLINIC",
    receiving_app: "EHR", receiving_facility: "CLINIC",
    patient_id: "123456", assigning_authority: "CLINIC",
    family: "DOE", given: "JOHN", dob: "19800101", sex: "M",
    appt_start: "202402151000", appt_end: "202402151030",
    provider_id: "PR1", provider_family: "SMITH", provider_given: "ALICE",
    location: "ROOM-12"
  },
  "DFT^P03": {
    sending_app: "BILL", sending_facility: "HOSP",
    receiving_app: "EHR", receiving_facility: "HOSP",
    patient_id: "123456", assigning_authority: "HOSP",
    family: "DOE", given: "JOHN", dob: "19800101", sex: "M",
    charge_code: "99213", charge_desc: "Office/outpatient visit est",
    charge_amount: "125.00", charge_units: "1"
  }
};

function presetFor(messageType) {
  return HL7_PRESETS[messageType] || {};
}

function loadPresetIntoTextarea() {
  const sel = document.getElementById("message_type");
  const ta = document.getElementById("json_data");
  const mt = sel ? sel.value : "";
  const preset = presetFor(mt);
  ta.value = JSON.stringify(preset, null, 2);
  ta.dispatchEvent(new Event("input"));
}

document.addEventListener("DOMContentLoaded", () => {
  const btn = document.getElementById("load_example_btn");
  const sel = document.getElementById("message_type");
  if (btn) btn.addEventListener("click", (e) => {
    e.preventDefault();
    loadPresetIntoTextarea();
  });
  if (sel) sel.addEventListener("change", () => {
    const ta = document.getElementById("json_data");
    if (ta && ta.value.trim() === "") loadPresetIntoTextarea();
  });
});
