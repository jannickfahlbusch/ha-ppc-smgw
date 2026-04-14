"""Tests for the OBIS parser, catalog, and name builder."""

import pytest

from custom_components.ppc_smgw.obis import (
    OBIS_CATALOG,
    PHASE_ANGLE_NAMES,
    OBISMeasurementInfo,
    ParsedOBIS,
    build_obis_name,
    get_obis_info,
    parse_obis,
)
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass


# ---------------------------------------------------------------------------
# parse_obis: string format
# ---------------------------------------------------------------------------


class TestParseObisString:
    def test_basic(self):
        result = parse_obis("1-0:1.8.0")
        assert result == ParsedOBIS(1, 0, 1, 8, 0, None)

    def test_with_f_value(self):
        result = parse_obis("1-0:1.8.0*255")
        assert result == ParsedOBIS(1, 0, 1, 8, 0, 255)

    def test_channel_1(self):
        result = parse_obis("1-1:1.7.0")
        assert result == ParsedOBIS(1, 1, 1, 7, 0, None)

    def test_export_total(self):
        result = parse_obis("1-0:2.8.0")
        assert result == ParsedOBIS(1, 0, 2, 8, 0, None)

    def test_active_power(self):
        result = parse_obis("1-0:16.7.0")
        assert result == ParsedOBIS(1, 0, 16, 7, 0, None)

    def test_tariff_register(self):
        result = parse_obis("1-0:1.8.2")
        assert result == ParsedOBIS(1, 0, 1, 8, 2, None)

    def test_billing_period(self):
        result = parse_obis("1-0:1.8.0*1")
        assert result == ParsedOBIS(1, 0, 1, 8, 0, 1)

    def test_phase_angle(self):
        result = parse_obis("1-0:81.7.4")
        assert result == ParsedOBIS(1, 0, 81, 7, 4, None)

    def test_channel_and_tariff(self):
        result = parse_obis("1-2:1.8.3*1")
        assert result == ParsedOBIS(1, 2, 1, 8, 3, 1)


# ---------------------------------------------------------------------------
# parse_obis: COSEM hex format (12 chars)
# ---------------------------------------------------------------------------


class TestParseObisHex:
    def test_import_energy(self):
        result = parse_obis("0100010800ff")
        assert result == ParsedOBIS(1, 0, 1, 8, 0, 255)

    def test_export_energy(self):
        result = parse_obis("0100020800ff")
        assert result == ParsedOBIS(1, 0, 2, 8, 0, 255)

    def test_active_power(self):
        result = parse_obis("0100100700ff")
        assert result == ParsedOBIS(1, 0, 16, 7, 0, 255)

    def test_uppercase(self):
        result = parse_obis("0100010800FF")
        assert result == ParsedOBIS(1, 0, 1, 8, 0, 255)

    def test_mixed_case(self):
        result = parse_obis("0100010800Ff")
        assert result == ParsedOBIS(1, 0, 1, 8, 0, 255)

    def test_channel_1(self):
        result = parse_obis("0101010800ff")
        assert result == ParsedOBIS(1, 1, 1, 8, 0, 255)

    def test_voltage_l1(self):
        result = parse_obis("0100200700ff")
        assert result == ParsedOBIS(1, 0, 32, 7, 0, 255)


# ---------------------------------------------------------------------------
# parse_obis: dot-separated hex format
# ---------------------------------------------------------------------------


class TestParseObisDotHex:
    def test_basic(self):
        result = parse_obis("01.00.01.08.00.FF")
        assert result == ParsedOBIS(1, 0, 1, 8, 0, 255)

    def test_active_power(self):
        result = parse_obis("01.00.10.07.00.ff")
        assert result == ParsedOBIS(1, 0, 16, 7, 0, 255)


# ---------------------------------------------------------------------------
# parse_obis: invalid inputs
# ---------------------------------------------------------------------------


class TestParseObisInvalid:
    def test_empty_string(self):
        assert parse_obis("") is None

    def test_short_string(self):
        assert parse_obis("short") is None

    def test_garbage(self):
        assert parse_obis("not-a-valid-obis") is None

    def test_incomplete_hex(self):
        assert parse_obis("01000108") is None

    def test_hex_with_non_hex_chars(self):
        assert parse_obis("0100010800gg") is None

    def test_wrong_separator(self):
        assert parse_obis("1:0-1.8.0") is None


# ---------------------------------------------------------------------------
# to_obis_string
# ---------------------------------------------------------------------------


class TestToObisString:
    def test_basic(self):
        assert ParsedOBIS(1, 0, 1, 8, 0, None).to_obis_string() == "1-0:1.8.0"

    def test_f_255_suppressed(self):
        assert ParsedOBIS(1, 0, 1, 8, 0, 255).to_obis_string() == "1-0:1.8.0"

    def test_f_0_included(self):
        assert ParsedOBIS(1, 0, 1, 8, 0, 0).to_obis_string() == "1-0:1.8.0*0"

    def test_f_1_included(self):
        assert ParsedOBIS(1, 0, 1, 8, 0, 1).to_obis_string() == "1-0:1.8.0*1"

    def test_channel(self):
        assert ParsedOBIS(1, 1, 1, 7, 0, None).to_obis_string() == "1-1:1.7.0"

    def test_large_values(self):
        assert ParsedOBIS(1, 0, 81, 7, 26, None).to_obis_string() == "1-0:81.7.26"

    def test_roundtrip_string(self):
        """Parsing a string and converting back should produce the same result."""
        original = "1-0:1.8.0"
        parsed = parse_obis(original)
        assert parsed is not None
        assert parsed.to_obis_string() == original

    def test_roundtrip_hex_normalizes(self):
        """Parsing hex and converting should produce canonical string format."""
        parsed = parse_obis("0100010800ff")
        assert parsed is not None
        assert parsed.to_obis_string() == "1-0:1.8.0"


# ---------------------------------------------------------------------------
# get_obis_info / catalog
# ---------------------------------------------------------------------------


class TestCatalog:
    def test_energy_import(self):
        info = get_obis_info(ParsedOBIS(1, 0, 1, 8, 0, None))
        assert info is not None
        assert info.device_class == SensorDeviceClass.ENERGY
        assert info.state_class == SensorStateClass.TOTAL_INCREASING
        assert info.name == "Active import energy"

    def test_energy_export(self):
        info = get_obis_info(ParsedOBIS(1, 0, 2, 8, 0, None))
        assert info is not None
        assert info.device_class == SensorDeviceClass.ENERGY

    def test_power(self):
        info = get_obis_info(ParsedOBIS(1, 0, 16, 7, 0, None))
        assert info is not None
        assert info.device_class == SensorDeviceClass.POWER
        assert info.state_class == SensorStateClass.MEASUREMENT

    def test_voltage(self):
        info = get_obis_info(ParsedOBIS(1, 0, 32, 7, 0, None))
        assert info is not None
        assert info.device_class == SensorDeviceClass.VOLTAGE

    def test_current(self):
        info = get_obis_info(ParsedOBIS(1, 0, 31, 7, 0, None))
        assert info is not None
        assert info.device_class == SensorDeviceClass.CURRENT

    def test_frequency(self):
        info = get_obis_info(ParsedOBIS(1, 0, 14, 7, 0, None))
        assert info is not None
        assert info.device_class == SensorDeviceClass.FREQUENCY

    def test_reactive_energy_no_device_class(self):
        info = get_obis_info(ParsedOBIS(1, 0, 3, 8, 0, None))
        assert info is not None
        assert info.device_class is None
        assert info.unit == "kvarh"

    def test_unknown_returns_none(self):
        assert get_obis_info(ParsedOBIS(1, 0, 99, 99, 0, None)) is None

    def test_channel_does_not_affect_lookup(self):
        """Different channel (B value) should return same catalog entry."""
        info_ch0 = get_obis_info(ParsedOBIS(1, 0, 1, 8, 0, None))
        info_ch1 = get_obis_info(ParsedOBIS(1, 1, 1, 8, 0, None))
        assert info_ch0 == info_ch1

    def test_tariff_does_not_affect_lookup(self):
        """Different tariff (E value) should return same catalog entry."""
        info_e0 = get_obis_info(ParsedOBIS(1, 0, 1, 8, 0, None))
        info_e2 = get_obis_info(ParsedOBIS(1, 0, 1, 8, 2, None))
        assert info_e0 == info_e2


# ---------------------------------------------------------------------------
# build_obis_name
# ---------------------------------------------------------------------------


class TestBuildObisName:
    def test_known_basic(self):
        parsed = ParsedOBIS(1, 0, 1, 8, 0, None)
        info = get_obis_info(parsed)
        assert build_obis_name(parsed, info) == "Active import energy"

    def test_with_channel(self):
        parsed = ParsedOBIS(1, 1, 1, 8, 0, None)
        info = get_obis_info(parsed)
        assert build_obis_name(parsed, info) == "Active import energy (Ch 1)"

    def test_with_tariff(self):
        parsed = ParsedOBIS(1, 0, 1, 8, 2, None)
        info = get_obis_info(parsed)
        assert build_obis_name(parsed, info) == "Active import energy (Tariff 2)"

    def test_with_channel_and_tariff(self):
        parsed = ParsedOBIS(1, 2, 1, 8, 3, None)
        info = get_obis_info(parsed)
        assert build_obis_name(parsed, info) == "Active import energy (Ch 2, Tariff 3)"

    def test_with_billing_period(self):
        parsed = ParsedOBIS(1, 0, 1, 8, 0, 1)
        info = get_obis_info(parsed)
        assert build_obis_name(parsed, info) == "Active import energy (Period -1)"

    def test_with_channel_tariff_and_period(self):
        parsed = ParsedOBIS(1, 1, 1, 8, 2, 3)
        info = get_obis_info(parsed)
        assert (
            build_obis_name(parsed, info)
            == "Active import energy (Ch 1, Tariff 2, Period -3)"
        )

    def test_unknown_code(self):
        parsed = ParsedOBIS(1, 0, 99, 99, 0, None)
        assert build_obis_name(parsed, None) == "OBIS 1-0:99.99.0"

    def test_phase_angle_known_e(self):
        parsed = ParsedOBIS(1, 0, 81, 7, 4, None)
        info = get_obis_info(parsed)
        assert build_obis_name(parsed, info) == "Phase angle I(L1)-U(L1)"

    def test_phase_angle_unknown_e(self):
        parsed = ParsedOBIS(1, 0, 81, 7, 99, None)
        info = get_obis_info(parsed)
        assert build_obis_name(parsed, info) == "Phase angle (E=99)"

    def test_phase_angle_with_channel(self):
        parsed = ParsedOBIS(1, 1, 81, 7, 4, None)
        info = get_obis_info(parsed)
        assert build_obis_name(parsed, info) == "Phase angle I(L1)-U(L1) (Ch 1)"

    def test_e_255_no_tariff_qualifier(self):
        """E=255 should not add a tariff qualifier."""
        parsed = ParsedOBIS(1, 0, 1, 8, 255, None)
        info = get_obis_info(parsed)
        assert build_obis_name(parsed, info) == "Active import energy"

    def test_e_0_no_tariff_qualifier(self):
        """E=0 should not add a tariff qualifier."""
        parsed = ParsedOBIS(1, 0, 1, 8, 0, None)
        info = get_obis_info(parsed)
        assert build_obis_name(parsed, info) == "Active import energy"
