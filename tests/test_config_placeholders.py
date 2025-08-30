import yaml

def test_identifier_systems_loads():
    with open('config/identifier_systems.yaml', 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    assert 'mrn' in data and 'visit' in data

def test_partner_config_loads():
    with open('config/partners/example.yaml', 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    assert 'package_ids' in data
