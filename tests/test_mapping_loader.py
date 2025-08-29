from translators.mapping_loader import load

def test_load_oru_map():
    spec = load("maps/oru_uscore.yaml")
    assert "ORU^R01" in spec.messageTypes
    resources = {rp.resource for rp in spec.resourcePlan}
    assert {"Patient", "DiagnosticReport", "Observation", "Specimen"} <= resources
