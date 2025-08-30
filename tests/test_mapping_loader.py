from translators.mapping_loader import load

def test_load_oru_map():
    spec = load("maps/oru_uscore.yaml")
    assert "ORU^R01" in spec.messageTypes
    resources = {rp.resource for rp in spec.resourcePlan}
    assert {"Patient", "DiagnosticReport", "Observation", "Specimen"} <= resources

def test_load_orm_map():
    spec = load("maps/orm_uscore.yaml")
    assert "ORM^O01" in spec.messageTypes
    resources = {rp.resource for rp in spec.resourcePlan}
    assert "ServiceRequest" in resources

def test_load_siu_map():
    spec = load("maps/siu_uscore.yaml")
    assert "SIU^S12" in spec.messageTypes
    resources = {rp.resource for rp in spec.resourcePlan}
    assert "Appointment" in resources

def test_load_vxu_map():
    spec = load("maps/vxu_uscore.yaml")
    assert "VXU^V04" in spec.messageTypes
    resources = {rp.resource for rp in spec.resourcePlan}
    assert "Immunization" in resources

def test_load_rde_map():
    spec = load("maps/rde_uscore.yaml")
    assert "RDE^O11" in spec.messageTypes
    resources = {rp.resource for rp in spec.resourcePlan}
    assert {"MedicationRequest", "MedicationDispense", "MedicationAdministration"} <= resources
