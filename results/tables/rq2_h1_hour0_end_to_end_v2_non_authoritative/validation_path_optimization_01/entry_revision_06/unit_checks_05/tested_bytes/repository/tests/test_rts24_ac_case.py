import pytest
from pypower.api import case24_ieee_rts
from pypower.idx_bus import BUS_I, BUS_TYPE, PD, PV, QD, REF
from pypower.idx_gen import GEN_BUS, GEN_STATUS, PG

from src.grid import load_rts24, scale_rts24_demand
from src.grid.ac_case import configure_rts24_ac_case


def test_ac_case_maps_scaled_load_commitment_and_reference_bus():
    data = scale_rts24_demand(load_rts24(), 0.5)
    source_case = case24_ieee_rts()
    case = case24_ieee_rts()
    commitment = {
        generator.index: (
            generator.in_service
            and generator.p_max_mw > 0.0
            and generator.index not in {11, 12, 13}
        )
        for generator in data.generators
    }

    active_indices, reference_bus = configure_rts24_ac_case(
        case,
        data,
        generator_commitment=commitment,
    )

    assert sum(case["bus"][:, PD]) == pytest.approx(1425.0)
    assert sum(case["bus"][:, QD]) == pytest.approx(290.0)
    for source_row, mapped_row in zip(source_case["bus"], case["bus"]):
        assert mapped_row[PD] == pytest.approx(0.5 * source_row[PD])
        assert mapped_row[QD] == pytest.approx(0.5 * source_row[QD])
    assert reference_bus != 13
    assert sum(case["bus"][:, BUS_TYPE] == REF) == 1
    assert case["gen"][14, GEN_STATUS] == 1
    assert case["gen"][14, PG] == pytest.approx(0.0)
    assert 14 in active_indices
    assert all(case["gen"][index, GEN_STATUS] == 0 for index in (11, 12, 13))
    active_buses = {
        int(case["gen"][index, GEN_BUS]) for index in active_indices
    }
    assert any(
        generator.index in active_indices
        and generator.p_max_mw > 0.0
        and generator.bus == reference_bus
        for generator in data.generators
    )
    for row in case["bus"]:
        if int(row[BUS_I]) in active_buses:
            assert int(row[BUS_TYPE]) in (PV, REF)


def test_ac_case_rejects_commitment_without_real_power_generation():
    data = load_rts24()
    case = case24_ieee_rts()
    commitment = {generator.index: False for generator in data.generators}

    with pytest.raises(ValueError, match="active real-power generator"):
        configure_rts24_ac_case(
            case,
            data,
            generator_commitment=commitment,
        )
