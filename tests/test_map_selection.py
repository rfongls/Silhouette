from fastapi import FastAPI
from fastapi.testclient import TestClient
import api.interop as interop


def test_pick_map_for_known_triggers():
    pick = interop._pick_map_for_trigger
    assert pick("ADT_A01").endswith("maps/adt_uscore.yaml")
    assert pick("ADT_A08").endswith("maps/adt_update_uscore.yaml")
    assert pick("ADT_A31").endswith("maps/adt_merge_uscore.yaml")
    assert pick("ORM_O01").endswith("maps/orm_uscore.yaml")
    assert pick("ORU_R01").endswith("maps/oru_uscore.yaml")
    assert pick("RDE_O11").endswith("maps/rde_uscore.yaml")
    assert pick("VXU_V04").endswith("maps/vxu_uscore.yaml")
    assert pick("MDM_T02").endswith("maps/mdm_uscore.yaml")
    assert pick("SIU_S12").endswith("maps/siu_uscore.yaml")
    assert pick("DFT_P03").endswith("maps/dft_uscore.yaml")
    assert pick("BAR_P01").endswith("maps/bar_uscore.yaml")
    assert pick("COVERAGE").endswith("maps/coverage_uscore.yaml")


def test_pick_map_wildcards_and_fallback():
    pick = interop._pick_map_for_trigger
    assert pick("OMX_O01").endswith("maps/omx_uscore.yaml")
    assert pick("ORX_O42").endswith("maps/orx_uscore.yaml")
    assert pick("RESEARCH_ABC").endswith("maps/research_uscore.yaml")
    assert pick("UNKNOWN_XYZ").endswith("maps/adt_uscore.yaml")


def test_quickstart_uses_trigger_to_report_map(monkeypatch):
    def fake_which(cmd):
        return None
    monkeypatch.setattr(interop, "_which", fake_which)
    out, note = interop._hl7_to_fhir_via_cli("MSH|^~\\&|...||...||...||ADT^A01|X|P|2.4\r\nPID|1||123||DOE^JOHN", trigger="ADT_A01")
    assert "maps/adt_uscore.yaml" in note
    assert out.strip().startswith("{")
