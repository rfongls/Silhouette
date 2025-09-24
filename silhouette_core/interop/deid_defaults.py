from __future__ import annotations

import os, glob, re, random
from datetime import datetime, timedelta
from collections import defaultdict

# Strings to insert based on the starting pattern
JVBER_string = "JVBERi0xLjQNCiX5abcdefghi0k"  # Example placeholder for PDF data
PD94_string  = "PD940xLjQNCiX5abcdefghi0k"    # Example placeholder for XML data

def random_address():
    address_samples = [
        ["124 Conch St", "Bikini Bottom", "PO", "62704", "USA"],
        ["1640 Riverside Drive", "Hill Valley", "CA", "90210", "USA"],
        ["1313 Webfoot Wal", "Duckburg", "CA", "10001", "USA"],
    ]
    address = random.choice(address_samples)
    return '^'.join(address)

def random_allergy_reaction():
    return random.choice(["Rash", "Itching", "Swelling", "Dizziness"])

def random_date():
    start_date = datetime(1970, 1, 1)
    end_date = datetime(1995, 12, 31)
    return (start_date + timedelta(days=random.randrange((end_date - start_date).days))).strftime('%Y%m%d')

def random_datetime():
    start_date = datetime(2000, 1, 1)
    end_date = datetime(2025, 12, 31)
    random_dt = start_date + timedelta(seconds=random.randint(0, int((end_date - start_date).total_seconds())))
    return random_dt.strftime('%Y%m%d%H%M%S')

def random_diagnosis_code(): return f"DX{random.randint(100, 999)}"
def random_event_reason():   return random.choice(["Routine", "Urgent", "Referral", "Emergency"])
def random_facility_code():  return f"FAC{random.randint(1000, 9999)}"
def random_guarantor_employer(): return random.choice(["Acme Corp", "Globex", "Soylent Corp", "Initech", "Umbrella Corp"])
def random_gender():         return random.choice(["M", "F"])
def random_language():       return random.choice(["English", "Chinese", "German", "Russian", "French"])
def random_mrn():            return f"{random.randint(100000, 999999)}"

def random_name():
    first_names = ["Donald", "Mickey", "Chris", "Laura", "Mike", "Linda", "Robert","Mary", "David", "Sarah", "James", "Karen", "Brian", "Nancy", "Jason"]
    last_names  = ["Mouse", "Duck", "Frankenstein", "Smith", "Doe", "Brown", "Johnson"]
    return f"{random.choice(first_names)}^{random.choice(last_names)}"

def random_observation_method(): return random.choice(["Manual", "Automated", "Computed", "Visual"])
def random_phone_number():       return f"({random.randint(100, 999)}){random.randint(100, 999)}-{random.randint(1000, 9999)}"

def random_primary_facility():
    facility_ids = ["99999", "88888", "77777"]
    facility_names = ["Healthcare Center", "Wellness Hospital", "Psychiatric Clinic"]
    facility_addresses = ["111 Gotham City, New York, USA", "222 Asgard, Valhalla, USA", "333 The Emerald City, Oz, USA"]
    return f"{random.choice(facility_ids)}^{random.choice(facility_names)}^{random.choice(facility_addresses)}"

def random_procedure_code(): return f"PROC{random.randint(100, 999)}"
def random_race():           return random.choice(["Caucasian", "Asian", "African American", "Hispanic or Latino", "Native American"])
def random_relationship():   return random.choice(["Parent", "Sibling", "Spouse", "Child", "Friend"])
def random_specimen_source():return random.choice(["Blood", "Urine", "Saliva", "Tissue"])
def random_status():         return random.choice(["Married", "Single", "Divorced"])
def random_transcriptionist(): return random.choice(["Transcriber A", "Transcriber B", "Transcriber C", "Transcriber D"])

def random_ssn(): return f"{random.randint(100, 999)}-{random.randint(10, 99)}-{random.randint(1000, 9999)}"

def deidentify_subcomponents(field_content: str, segment: str, field_number: int) -> str:
    """Handle SSN/MRN subcomponents etc."""
    ssn_pattern = re.compile(r'\b\d{3}-\d{2}-\d{4}\b|\b\d{9}\b')
    repetitions = field_content.split('~')
    for k, repetition in enumerate(repetitions):
        components = repetition.split('^')
        for i, comp in enumerate(components):
            if segment == 'PID' and field_number == 3 and i == 0:
                components[i] = random_mrn()
            else:
                subcomponents = comp.split('&')
                for j, subcomp in enumerate(subcomponents):
                    if ssn_pattern.match(subcomp):
                        subcomponents[j] = random_ssn()
                components[i] = '&'.join(subcomponents)
        repetitions[k] = '^'.join(components)
    return '~'.join(repetitions)

def deidentify_field(segment: str, field_number: int, field_content: str) -> str:
    """Segment/field aware randomization (baseline)."""
    if not field_content or field_content.strip() == '':
        return field_content

    if segment == 'PID' and field_number == 3:
        return deidentify_subcomponents(field_content, segment, field_number)

    if segment == 'MSH':
        if field_number == 7:  return random_datetime()
        if field_number == 10: return str(random.randint(100000000, 999999999))

    if segment == 'ACC' and field_number in [1,4]: return random_datetime()
    if segment == 'AL1' and field_number == 6:     return 'AL16'

    if segment == 'DG1':
        if field_number == 1:  return str(random.randint(1, 999))
        if field_number == 3:  return random_diagnosis_code()
        if field_number == 6:  return random_datetime()

    if segment == 'EVN':
        if field_number in (2,3): return random_datetime()
        if field_number == 6:     return random_event_reason()

    if segment == 'GT1':
        if field_number == 8:   return random_datetime()
        if field_number in (13,14): return random_phone_number()
        if field_number == 24:  return random_guarantor_employer()
        if field_number == 31:  return 'Guarantor Employer'

    if segment == 'IN1':
        if field_number in (3,4,16,28,36,49): return f"IN1{field_number}"
        if field_number == 12: return random_phone_number()
        if field_number == 13: return random_address()
        if field_number == 17: return random_date()

    if segment == 'IN2':
        if field_number == 44: return random_phone_number()
        if field_number == 45: return random_guarantor_employer()

    if segment == 'NK1':
        if field_number == 2:   return random_name()
        if field_number == 4:   return random_address()
        if field_number in (5,6): return random_phone_number()
        if field_number in (8,9):  return random_datetime()
        if field_number == 13:  return 'Generic Organization Name'
        if field_number == 16:  return random_status()
        if field_number == 30:  return random_name()
        if field_number == 31:  return random_phone_number()

    if segment == 'NTE':
        return f"Note {random.randint(1, 100)}: [De-identified data]"

    if segment == 'OBR':
        if field_number in (6,7,8,14,22): return random_datetime()
        if field_number == 16:
            rnd_id = str(random.randint(100000, 999999))
            name_parts = random_name().split('^')
            return f"{rnd_id}^{name_parts[0]}^{name_parts[1]}^{random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')}"
        if field_number == 17: return random_phone_number()
        if field_number == 32: return 'ProviderResultInterpreter'

    if segment == 'OBX':
        if field_number == 5:
            subcomponents = field_content.split('^')
            for i, subcomp in enumerate(subcomponents):
                if "JVBER" in subcomp: subcomponents[i] = JVBER_string
                elif "PD94" in subcomp: subcomponents[i] = PD94_string
            return '^'.join(subcomponents)
        if field_number == 14: return random_datetime()
        if field_number == 24: return random_address()

    if segment == 'ORC':
        if field_number == 9:  return random_datetime()
        if field_number == 15: return random_event_reason()

    if segment == 'PD1':
        if field_number == 5:  return f"{random_name()}^{random.randint(100000, 999999)}"
        if field_number == 7:  return random_primary_facility()
        if field_number == 12: return 'PD112'

    if segment == 'PID':
        if field_number in (1,2):  return random_mrn()
        if field_number == 3:       return deidentify_subcomponents(field_content, segment, field_number)
        if field_number == 5:       return random_name()
        if field_number == 7:       return random_date()
        if field_number == 8:       return random_gender()
        if field_number == 9:       return random_name()
        if field_number == 10:      return random_race()
        if field_number == 11:      return random_address()
        if field_number in (13,14): return random_phone_number()
        if field_number == 15:      return random_language()
        if field_number == 16:      return random_status()
        if field_number == 18:      return str(random.randint(100000, 999999))
        if field_number == 19:      return str(random.randint(100000000, 999999999))
        if field_number == 20:      return str(random.randint(100000, 999999))
        if field_number == 22:      return random_race()
        if field_number == 29:      return random_datetime()

    if segment == 'PV1':
        if field_number == 1:  return str(random.randint(1, 999))
        if field_number in (7,8,9,19):
            pv1_7_1 = str(random.randint(1000000000, 9999999999))
            pv1_7_2 = random_name().split('^')[0]
            pv1_7_3 = random_name().split('^')[1]
            pv1_7_4 = random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
            return f"{pv1_7_1}^{pv1_7_2}^{pv1_7_3}^{pv1_7_4}"
        if field_number == 17: return 'REDACTED'
        if field_number == 20: return 'Generic Financial Class'
        if field_number == 36: return 'Generic Discharge Disposition'
        if field_number == 39: return random_primary_facility()
        if field_number in (44,45): return random_datetime()
        if field_number == 52: return 'GenericCode'
        if field_number == 53: return 'GenericIndicator'

    if segment == 'PV2':
        if field_number in (8,9,14,26,28): return random_datetime()
        if field_number in (3,4): return random_event_reason()
        if field_number == 29:    return 'GenericIndicator'
        if field_number == 33:    return 'GenericPriority'

    if segment == 'TXA':
        if field_number == 8:  return 'TXA8'
        if field_number == 10: return 'TXA10'

    return field_content

def deidentify_hl7(hl7_message: str, deidentified_components_count: defaultdict) -> str:
    """Run baseline randomization over an HL7 message (by segment/field)."""
    segments = hl7_message.split('\n')
    for i, segment in enumerate(segments):
        parts = segment.split('|')
        segment_type = parts[0]
        for j in range(1, len(parts)):
            original_field = parts[j]
            new_field = deidentify_field(segment_type, j, original_field)
            if new_field != original_field:
                deidentified_components_count[segment_type].add(j)
            parts[j] = new_field
        segments[i] = '|'.join(parts)
    return '\n'.join(segments)
