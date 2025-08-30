from typing import Dict, Any
import xml.etree.ElementTree as ET

class CDAToFHIRTranslator:
    """
    Minimal but real CCD → FHIR mapping for demographics + problems + meds + labs.
    Uses ElementTree; in production use a robust CDA lib.
    """

    NS = {"cda": "urn:hl7-org:v3"}

    def translate(self, ccd_xml: str) -> Dict[str, Any]:
        root = ET.fromstring(ccd_xml)
        bundle = {"resourceType": "Bundle", "type": "collection", "entry": []}

        def add(res):
            bundle["entry"].append({"resource": res})
            return res

        rec = root.find(".//cda:recordTarget/cda:patientRole", self.NS)
        if rec is not None:
            patient = {"resourceType": "Patient"}
            name = rec.find(".//cda:patient/cda:name", self.NS)
            if name is not None:
                given = [g.text for g in name.findall("cda:given", self.NS) if g.text]
                family = name.findtext("cda:family", default="", namespaces=self.NS)
                patient["name"] = [{"given": given, "family": family}]
            birth = rec.find(".//cda:patient/cda:birthTime", self.NS)
            if birth is not None:
                patient["birthDate"] = birth.attrib.get("value", "")[:8]
            add(patient)

        for section in root.findall(".//cda:section", self.NS):
            scode = section.find("cda:code", self.NS)
            if scode is None:
                continue
            code_val = scode.attrib.get("code")
            if code_val == "11450-4":
                for prob in section.findall(".//cda:entry/cda:act", self.NS):
                    code = prob.find(".//cda:code", self.NS)
                    if code is not None:
                        condition = {"resourceType": "Condition",
                                     "code": {"coding": [{"system": "http://snomed.info/sct",
                                                          "code": code.attrib.get("code")}]} }
                        add(condition)
            elif code_val == "10160-0":
                for med in section.findall(".//cda:substanceAdministration", self.NS):
                    code = med.find(".//cda:code", self.NS)
                    ms = {"resourceType": "MedicationStatement"}
                    if code is not None:
                        ms["medicationCodeableConcept"] = {"coding": [{"system":"http://www.nlm.nih.gov/research/umls/rxnorm",
                                                                       "code": code.attrib.get("code")}]}
                    add(ms)
            elif code_val == "30954-2":
                for obs in section.findall(".//cda:observation", self.NS):
                    code = obs.find("cda:code", self.NS)
                    val = obs.find("cda:value", self.NS)
                    ob = {"resourceType":"Observation"}
                    if code is not None:
                        ob["code"] = {"coding":[{"system":"http://loinc.org", "code":code.attrib.get("code")}]} 
                    if val is not None and "value" in val.attrib:
                        ob["valueQuantity"] = {"value": float(val.attrib["value"])}
                    add(ob)

        return bundle
