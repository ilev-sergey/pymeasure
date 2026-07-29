#
# This file is part of the PyMeasure package.
#
# Copyright (c) 2013-2026 PyMeasure Developers
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#

import math

import pytest

from pymeasure.instruments.agilent import AgilentB1500
from pymeasure.instruments.agilent.agilentB1500 import (
    CMU,
    SMU,
    SPGU,
    ADCMode,
    ADCType,
    ControlMode,
    MFCMUMeasurementMode,
    PgSelectorConnectionStatus,
    PgSelectorPort,
    SCUUPath,
    SPGUChannelOutputMode,
    SPGUOperationMode,
    SPGUOutputMode,
    SpotCMU,
    SpotCMUMonitor,
    SpotIV,
    SweepMode,
    TimedSpotCMU,
    TimedSpotCMUMonitor,
    TimedSpotCurrent,
    TimedSpotIV,
    TimedSpotVoltage,
)
from pymeasure.test import expected_protocol


class TestB1500:
    """Tests for B1500 functionality."""

    def test_restore_settings(self):
        """Test restore_settings method."""
        with expected_protocol(
            AgilentB1500,
            [("RZ", None)],
        ) as inst:
            inst.restore_settings()

    @pytest.mark.parametrize("io_control_mode", list(ControlMode))
    def test_io_control_mode(self, io_control_mode):
        """Test io_control_mode property."""
        with expected_protocol(
            AgilentB1500,
            [(f"ERMOD {io_control_mode.value}", None), ("ERMOD?", io_control_mode.value)],
        ) as inst:
            inst.io_control_mode = io_control_mode
            assert inst.io_control_mode == io_control_mode

    @pytest.mark.parametrize("port", list(PgSelectorPort))
    @pytest.mark.parametrize("status", list(PgSelectorConnectionStatus))
    def test_set_port_connection(self, port, status):
        """Test set_port_connection method."""
        with expected_protocol(
            AgilentB1500,
            [(f"ERSSP {port.value}, {status.value}", None)],
        ) as inst:
            inst.set_port_connection(port, status)

    def test_unit_names(self):
        """Test that unit_names covers all initialized units."""
        with expected_protocol(AgilentB1500Mock, []) as inst:
            assert inst.unit_names == {
                inst.spgu1.id: "SPGU1",
                inst.cmu.id: "CMU",
                inst.smu1.id: "SMU1",
            }

    def test_smu_names(self):
        """Test that smu_names is the SMU-only subset of unit_names."""
        with expected_protocol(AgilentB1500Mock, []) as inst:
            assert inst.smu_names == {inst.smu1.id: "SMU1"}

    def test_adc_setup(self):
        with expected_protocol(
            AgilentB1500,
            [("AIT 0, 1", None), ("ERRX?", '0,"No error"')],
        ) as inst:
            inst.adc_setup(ADCType.HSADC, mode=ADCMode.MANUAL)


class AgilentB1500Mock(AgilentB1500):
    """B1500 with one unit per slot: SPGU in slot 1, CMU in slot 2, SMU in slot 3."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_child(SPGU, id=1, collection="spgus", prefix="spgu")
        self.add_child(CMU, id=2, collection="cmu", prefix=None)
        self.add_child(SMU, id=1, collection="smus", prefix="smu", smu_type="HRSMU", slot=3)


def binary_element(parameter, range_code, count, measurement=True, status=0, channel=1):
    """Build a single 8 byte FMT14 data element.

    :param parameter: Parameter code (B) defining the kind of data
    :param range_code: Range code (C) the value was measured or output with
    :param count: Data count (D)
    :param measurement: Type (A), False for source output data
    :param status: Status (E)
    :param channel: Channel number (F)
    """
    return (
        bytes([(int(measurement) << 7) | parameter, range_code])
        + count.to_bytes(4, "big", signed=True)
        + bytes([status, channel])
    )


def binary_time_element(count, channel=1):
    """Build a single 8 byte FMT14 time data element with time count (H) ``count``."""
    return bytes([3]) + count.to_bytes(6, "big", signed=True) + bytes([channel])


class TestBinaryDataFormat:
    """Tests for the 8 byte binary FMT14 data format."""

    #: Formatting of a B1500 with an SMU in slot 1 and a CMU in slot 2, as
    #: assumed by the examples of the programming guide
    formatting = AgilentB1500._data_formatting_FMT14({1: "SMU1", 2: "CMU"})

    def test_data_format(self):
        """Test that data_format selects the binary formatting."""
        with expected_protocol(
            AgilentB1500Mock,
            [("FMT 14, 0", None), ("ERRX?", '+0,"No Error."')],
        ) as inst:
            inst.data_format(14)
            assert inst._data_format.format == "FMT14"
            assert inst._data_format.binary is True
            assert inst._data_format.size == 8

    @pytest.mark.parametrize(
        "element, expected",
        [
            # examples of the programming guide, section "8 Bytes Data Elements"
            (bytes.fromhex("810b000186a00001"), ("0", "SMU1", "Current Measurement (A)", 100e-12)),
            (bytes.fromhex("030000000186a001"), ("", "SMU1", "Time (s)", 0.1)),
            # negative data counts are two's complements
            (binary_element(1, 11, -100000), ("0", "SMU1", "Current Measurement (A)", -100e-12)),
            # voltage of the 2 V range, source data has no error status
            (
                binary_element(0, 11, 2000000, measurement=False, status=1),
                ("1", "SMU1", "Voltage Output (V)", 4.0),
            ),
            # CMU data of the 10 kOhm range is scaled by 2**24 instead of 1e6
            (binary_element(12, 4, 2**24, channel=2), ("0", "CMU", "Resistance (Ohm)", 10e3)),
            (binary_element(14, 4, 2**24, channel=2), ("0", "CMU", "Conductance (S)", 100e-6)),
            # the CMU DC bias output is scaled by 1e3 regardless of the range
            (
                binary_element(9, 0, 1500, measurement=False, channel=2),
                ("0", "CMU", "DC Bias Output (V)", 1.5),
            ),
            # the sampling index is the data count itself
            (binary_element(6, 0, 7, measurement=False), ("0", "SMU1", "Sampling index", 7)),
            # channel numbers above 10 address subchannel 2 of the same slot
            (
                binary_element(1, 11, 100000, channel=11),
                ("0", "SMU1", "Current Measurement (A)", 100e-12),
            ),
            (binary_time_element(100000, channel=26), ("", "MISC", "Time (s)", 0.1)),
        ],
    )
    def test_format_single(self, element, expected):
        """Test formatting of single binary measurement values."""
        assert self.formatting.format_single(element) == expected

    @pytest.mark.parametrize(
        "element",
        [
            binary_element(1, 31, 100000),  # range code 31: invalid data
            binary_time_element(-(2**47)),  # smallest time count: invalid data
        ],
    )
    def test_format_single_invalid_data(self, element):
        """Test that invalid measurement values are returned as NaN."""
        assert math.isnan(self.formatting.format_single(element)[3])

    def test_format_single_instrument_response(self):
        """Test formatting of a ``TTC`` response of a B1500 with a CMU in slot 8.

        The CMU reports the range of the measurement data as a signed exponent
        (252 is -4), and marks the time data as measurement data even though the
        programming guide describes it as source data.
        """
        formatting = AgilentB1500._data_formatting_FMT14({8: "CMU"})
        response = bytes.fromhex(
            "83 00000d11b946 08"  # time
            "8e fc fcd2e6ad 00 48"  # conductance
            "8f fc fa473433 00 48"  # susceptance
            "8a 04 000000ea 00 48"  # AC level monitor
            "8b 03 000002bb 00 48"  # DC bias monitor
        )
        values = [
            formatting.format_single(response[index : index + 8])
            for index in range(0, len(response), 8)
        ]
        assert [(value[1], value[2]) for value in values] == [
            ("CMU", "Time (s)"),
            ("CMU", "Conductance (S)"),
            ("CMU", "Susceptance (S)"),
            ("CMU", "AC Level Monitor (V)"),
            ("CMU", "DC Bias Monitor (V)"),
        ]
        assert values[0][3] == pytest.approx(219.26535)
        assert values[3][3] == pytest.approx(3.744e-6)
        assert values[4][3] == pytest.approx(5.592e-3)

    def test_status_sum(self, caplog):
        """Test that a status which is a sum of status values logs all of them."""
        # 12 is the sum of 4 (another channel in compliance) and 8 (this channel)
        with caplog.at_level("INFO"):
            self.formatting.format_single(binary_element(1, 11, 100000, status=12))
        assert "Another channel reached its compliance setting." in caplog.text
        assert "This channel reached its compliance setting." in caplog.text

    def test_status_discrete_code(self, caplog):
        """Test that the force saturation status is not decomposed into 1 and 4."""
        with caplog.at_level("INFO"):
            self.formatting.format_single(binary_element(1, 11, 100000, status=5))
        assert "force saturation" in caplog.text
        assert "over the measurement range" not in caplog.text

    def test_status_of_source_data(self, caplog):
        """Test that the sweep step status of source data is not logged as an error."""
        with caplog.at_level("INFO"):
            self.formatting.format_single(
                binary_element(0, 11, 2000000, measurement=False, status=2)
            )
        assert caplog.text == ""

    def test_format_single_unknown_parameter(self):
        """Test that an unassigned parameter code is rejected."""
        with pytest.raises(ValueError, match="parameter code 4"):
            self.formatting.format_single(binary_element(4, 0, 0))

    def test_format_single_wrong_size(self):
        """Test that an element of the wrong size is rejected."""
        with pytest.raises(ValueError, match="instead of 8 bytes"):
            self.formatting.format_single(binary_element(1, 11, 100000)[:-1])

    def test_read_channels(self):
        """Test read_channels with binary data."""
        response = binary_element(1, 11, 100000, channel=3) + binary_element(
            0, 11, 2000000, channel=3
        )
        with expected_protocol(
            AgilentB1500Mock,
            [
                ("FMT 14, 0", None),
                ("ERRX?", '+0,"No Error."'),
                (None, response),
            ],
        ) as inst:
            inst.data_format(14)
            assert inst.read_channels(2) == (
                ("0", "SMU1", "Current Measurement (A)", 100e-12),
                ("0", "SMU1", "Voltage Measurement (V)", 4.0),
            )

    def test_read_data(self):
        """Test that read_data queries the number of values before reading them."""
        response = b"".join(
            binary_element(1, 11, 100000 * point, channel=3)
            + binary_element(0, 11, 2000000 * point, measurement=False, channel=3)
            for point in (1, 2)
        )
        with expected_protocol(
            AgilentB1500Mock,
            [
                ("FMT 14, 0", None),
                ("ERRX?", '+0,"No Error."'),
                ("NUB?", "4"),
                (None, response),
            ],
        ) as inst:
            inst.data_format(14)
            data = inst.read_data(2)
            assert list(data.columns) == [
                "SMU1 Current Measurement (A)",
                "SMU1 Voltage Output (V)",
            ]
            assert data["SMU1 Current Measurement (A)"].tolist() == [100e-12, 200e-12]
            assert data["SMU1 Voltage Output (V)"].tolist() == [4.0, 8.0]

    def test_read_data_incomplete(self):
        """Test that a response which is no multiple of the element size is rejected."""
        with expected_protocol(
            AgilentB1500Mock,
            [
                ("FMT 14, 0", None),
                ("ERRX?", '+0,"No Error."'),
                ("NUB?", "1"),
                (None, binary_element(1, 11, 100000, channel=3)[:-1]),
            ],
        ) as inst:
            inst.data_format(14)
            with pytest.raises(ValueError, match="not a multiple"):
                inst.read_data(1)

    def test_measure_current(self):
        """Test that a spot measurement reads the expected number of bytes."""
        current = binary_element(1, 11, 100000, channel=3)
        with expected_protocol(
            AgilentB1500Mock,
            [
                ("FMT 14, 0", None),
                ("ERRX?", '+0,"No Error."'),
                ("TI 3", current),
                ("TTI 3", binary_time_element(123000, channel=3) + current),
            ],
        ) as inst:
            inst.data_format(14)
            assert inst.smu1.measure_current() == 100e-12
            assert inst.smu1.measure_current(timestamp=True) == (0.123, 100e-12)

    @pytest.mark.parametrize("monitor", [True, False])
    def test_cmu_measure(self, monitor):
        """Test that a spot C measurement accounts for the voltage monitor values."""
        response = binary_element(12, 4, 2**24, channel=2) + binary_element(13, 4, 2**24, channel=2)
        if monitor:
            # AC level monitor of the 16 mV range and DC bias monitor of the 25 V range
            response += binary_element(10, 4, 1875000, channel=2) + binary_element(
                11, 5, 40000, channel=2
            )
        with expected_protocol(
            AgilentB1500Mock,
            [
                ("FMT 14, 0", None),
                ("ERRX?", '+0,"No Error."'),
                ("*LRN? 71", f"LMN{int(monitor)}"),
                ("TC 2, 0", response),
            ],
        ) as inst:
            inst.data_format(14)
            result = inst.cmu.measure()
            if monitor:
                assert isinstance(result, SpotCMUMonitor)
                assert result == (10e3, 10e3, 0.03, 1.0)
            else:
                assert isinstance(result, SpotCMU)
                assert result == (10e3, 10e3)


class TestCheckStatus:
    """Tests for the numeric status decomposition of the ASCII formats."""

    formatting = AgilentB1500._data_formatting_FMT21({1: "SMU1"})

    def test_status_sum(self, caplog):
        """Test that a status which is a sum of status values logs all of them."""
        # 6 is the sum of 2 (oscillation) and 4 (another unit in compliance)
        with caplog.at_level("INFO"):
            self.formatting.check_status("006", name="SMU1")
        assert "Oscillation of force or saturation current." in caplog.text
        assert "Another unit reached its compliance setting." in caplog.text
        assert "A/D converter overflowed." not in caplog.text

    def test_status_unassigned_value(self, caplog):
        """Test that a status value which is not assigned for CMUs is reported."""
        with caplog.at_level("INFO"):
            self.formatting.check_status("008", name="CMU", cmu=True)
        assert "check_status not possible" in caplog.text


class TestSMU:
    """Tests for SMU module functionality."""

    channel = 3

    def test_enable(self):
        """Test enable method."""
        with expected_protocol(
            AgilentB1500Mock,
            [(f"CN {self.channel}", None)],
        ) as inst:
            inst.smu1.enable()

    def test_disable(self):
        """Test disable method."""
        with expected_protocol(
            AgilentB1500Mock,
            [(f"CL {self.channel}", None)],
        ) as inst:
            inst.smu1.disable()

    def test_measure_current(self):
        """Test measure_current method."""
        with expected_protocol(
            AgilentB1500Mock,
            [
                ("FMT 1, 0", None),
                ("ERRX?", '+0,"No Error."'),
                (f"TI {self.channel}", "NAI+000.005E-09"),
                (f"TTI {self.channel}, 11", "NAT+000.123E+00,NAI+000.005E-09"),
            ],
        ) as inst:
            inst.data_format(1)
            assert inst.smu1.measure_current() == 5e-12
            result = inst.smu1.measure_current("1 nA", timestamp=True)
            assert isinstance(result, TimedSpotCurrent)
            assert result == (0.123, 5e-12)
            assert result.time == 0.123
            assert result.current == 5e-12

    def test_measure_voltage(self):
        """Test measure_voltage method."""
        with expected_protocol(
            AgilentB1500Mock,
            [
                ("FMT 1, 0", None),
                ("ERRX?", '+0,"No Error."'),
                (f"TV {self.channel}", "NAV+001.500E+00"),
                (f"TTV {self.channel}, 20", "NAT+000.123E+00,NAV+001.500E+00"),
            ],
        ) as inst:
            inst.data_format(1)
            assert inst.smu1.measure_voltage() == 1.5
            result = inst.smu1.measure_voltage("2 V", timestamp=True)
            assert isinstance(result, TimedSpotVoltage)
            assert result == (0.123, 1.5)
            assert result.voltage == 1.5

    def test_measure_iv(self):
        """Test measure_iv method."""
        with expected_protocol(
            AgilentB1500Mock,
            [
                ("FMT 1, 0", None),
                ("ERRX?", '+0,"No Error."'),
                (f"TIV {self.channel}", "NAI+000.005E-09,NAV+001.000E+00"),
                (
                    f"TTIV {self.channel}, 11, 0",
                    "NAT+000.123E+00,NAI+000.005E-09,NAV+001.000E+00",
                ),
            ],
        ) as inst:
            inst.data_format(1)
            result = inst.smu1.measure_iv()
            assert isinstance(result, SpotIV)
            assert result == (5e-12, 1.0)
            assert result.current == 5e-12
            assert result.voltage == 1.0
            timed_result = inst.smu1.measure_iv("1 nA", 0, timestamp=True)
            assert isinstance(timed_result, TimedSpotIV)
            assert timed_result == (0.123, 5e-12, 1.0)
            assert timed_result.time == 0.123

    def test_measure_iv_requires_both_ranges(self):
        """Test that measure_iv rejects current_range without voltage_range and vice versa."""
        with expected_protocol(AgilentB1500Mock, []) as inst:
            with pytest.raises(ValueError):
                inst.smu1.measure_iv(current_range="1 nA")
            with pytest.raises(ValueError):
                inst.smu1.measure_iv(voltage_range="2 V")


class TestSPGU:
    """Tests for SPGU module functionality."""

    @pytest.mark.parametrize("output", [True, False])
    def test_output(self, output):
        """Test output property."""
        expected_command = "SRP" if output else "SPP"
        with expected_protocol(
            AgilentB1500Mock,
            [(expected_command, None)],
        ) as inst:
            inst.spgu1.output = output

    @pytest.mark.parametrize("operation_mode", list(SPGUOperationMode))
    def test_operation_mode(self, operation_mode):
        """Test operation_mode property."""
        with expected_protocol(
            AgilentB1500Mock,
            [(f"SIM {operation_mode.value}", None), ("SIM?", operation_mode.value)],
        ) as inst:
            inst.spgu1.operation_mode = operation_mode
            assert inst.spgu1.operation_mode == operation_mode

    def test_period(self):
        """Test period property."""
        with expected_protocol(
            AgilentB1500Mock,
            [(f"SPPER {0.5:.6f}", None), ("SPPER?", 0.5)],
        ) as inst:
            inst.spgu1.period = 0.5
            assert inst.spgu1.period == 0.5

    @pytest.mark.parametrize(
        "output_mode, condition", [(mode, 1) for mode in list(SPGUOutputMode)[1:]]
    )
    def test_output_mode(self, output_mode, condition):
        """Test set_output_mode and get_output_mode methods."""
        print(output_mode, condition)
        with expected_protocol(
            AgilentB1500Mock,
            [
                (f"SPRM {output_mode.value}, {condition}", None),
                ("SPRM?", f"{output_mode.value}, {condition}"),
            ],
        ) as inst:
            inst.spgu1.set_output_mode(output_mode, condition)
            assert inst.spgu1.get_output_mode() == (output_mode, condition)

    def test_complete(self):
        """Test complete property."""
        with expected_protocol(
            AgilentB1500Mock,
            [("SPST?", "0"), ("SPST?", "1")],
        ) as inst:
            assert inst.spgu1.complete
            assert not inst.spgu1.complete


class TestSPGUChannel:
    """Tests for SPGU channel functionality."""

    channel = 101

    @pytest.mark.parametrize("enabled", [True, False])
    def test_enabled(self, enabled):
        """Test enabled property."""
        expected_command = "CN" if enabled else "CL"
        with expected_protocol(
            AgilentB1500Mock,
            [(f"{expected_command} {self.channel}", None)],
        ) as inst:
            inst.spgu1.ch1.enabled = enabled

    def test_load_impedance(self):
        """Test load_impedance property."""
        with expected_protocol(
            AgilentB1500Mock,
            [(f"SER {self.channel}, {100:.6f}", None), (f"SER? {self.channel}", 100)],
        ) as inst:
            inst.spgu1.ch1.load_impedance = 100
            assert inst.spgu1.ch1.load_impedance == 100

    def test_output_voltage(self):
        """Test set_output_voltage and get_output_voltage methods."""
        with expected_protocol(
            AgilentB1500Mock,
            [
                (f"SPV {self.channel}, 1, 0.5, 2.0", None),
                (f"SPV? {self.channel}, 1", "0.5, 2.0"),
            ],
        ) as inst:
            inst.spgu1.ch1.set_output_voltage(source=1, base_voltage=0.5, peak_voltage=2.0)
            assert inst.spgu1.ch1.get_output_voltage(source=1) == (0.5, 2.0)

    @pytest.mark.parametrize("output_mode", list(SPGUChannelOutputMode))
    def test_output_mode(self, output_mode):
        """Test output_mode property."""
        with expected_protocol(
            AgilentB1500Mock,
            [
                (f"SPM {self.channel}, {output_mode.value}", None),
                (f"SPM? {self.channel}", str(output_mode.value)),
            ],
        ) as inst:
            inst.spgu1.ch1.output_mode = output_mode
            assert inst.spgu1.ch1.output_mode == output_mode

    def test_pulse_timings(self):
        """Test set_pulse_timings and get_pulse_timings methods."""
        with expected_protocol(
            AgilentB1500Mock,
            [
                (f"SPT {self.channel}, 1, 0.0, 1e-07, 2e-08, 3e-08", None),
                (f"SPT? {self.channel}, 1", "0.0,1e-07,2e-08,3e-08"),
            ],
        ) as inst:
            inst.spgu1.ch1.set_pulse_timings(
                source=1, delay=0.0, width=1e-7, rise_time=2e-8, fall_time=3e-8
            )
            delay, width, rise_time, fall_time = inst.spgu1.ch1.get_pulse_timings(source=1)
            assert delay == 0.0
            assert width == 1e-7
            assert rise_time == 2e-8
            assert fall_time == 3e-08

    def test_apply_setup(self):
        """Test apply_setup method."""
        with expected_protocol(
            AgilentB1500Mock,
            [(f"SPUPD {self.channel}", None)],
        ) as inst:
            inst.spgu1.ch1.apply_setup()


class TestCMU:
    """Tests for CMU module functionality."""

    @pytest.mark.parametrize("enabled", [True, False])
    def test_enabled(self, enabled):
        """Test enabled property."""
        expected_command = "CN" if enabled else "CL"
        with expected_protocol(
            AgilentB1500Mock,
            [(f"{expected_command} 2", None)],
        ) as inst:
            inst.cmu.enabled = enabled

    @pytest.mark.parametrize("voltage", [0.0, 0.25])
    def test_voltage_ac(self, voltage):
        """Test voltage_ac setting with boundary values."""
        with expected_protocol(
            AgilentB1500Mock,
            [(f"ACV 2, {voltage:f}", None)],
        ) as inst:
            inst.cmu.voltage_ac = voltage

    @pytest.mark.parametrize("frequency", [1e3, 5e6])
    def test_frequency_ac(self, frequency):
        """Test frequency_ac setting with boundary values."""
        with expected_protocol(
            AgilentB1500Mock,
            [(f"FC 2, {frequency:f}", None)],
        ) as inst:
            inst.cmu.frequency_ac = frequency

    @pytest.mark.parametrize("measurement_mode", list(MFCMUMeasurementMode))
    def test_set_measurement_mode(self, measurement_mode):
        """Test set_measurement_mode method."""
        with expected_protocol(
            AgilentB1500Mock,
            [(f"IMP {measurement_mode.value}", None)],
        ) as inst:
            inst.cmu.set_measurement_mode(measurement_mode)

    @pytest.mark.parametrize("enabled", [True, False])
    def test_voltage_monitor_enabled(self, enabled):
        """Test voltage_monitor_enabled property."""
        with expected_protocol(
            AgilentB1500Mock,
            [
                (f"LMN {int(enabled)}", None),
                ("*LRN? 71", f"LMN{int(enabled)}"),
            ],
        ) as inst:
            inst.cmu.voltage_monitor_enabled = enabled
            assert inst.cmu.voltage_monitor_enabled == enabled

    def test_measure(self):
        """Test measure method."""
        with expected_protocol(
            AgilentB1500Mock,
            [
                ("FMT 1, 0", None),
                ("ERRX?", '+0,"No Error."'),
                ("TC 2, 0", "NBC+001.000E-12,NBY+002.000E-06"),
                ("TTC 2, 2, 1000", "NBT+000.123E+00,NBC+001.000E-12,NBY+002.000E-06"),
            ],
        ) as inst:
            inst.data_format(1)
            result = inst.cmu.measure()
            assert isinstance(result, SpotCMU)
            assert result == (1e-12, 2e-6)
            primary, secondary = result
            assert (primary, secondary) == (1e-12, 2e-6)
            timed_result = inst.cmu.measure(meas_range=1000, timestamp=True)
            assert isinstance(timed_result, TimedSpotCMU)
            assert timed_result == (0.123, 1e-12, 2e-6)
            assert timed_result.time == 0.123

    def test_measure_with_monitor(self):
        """Test that measure captures AC/DC voltage values (:attr:`voltage_monitor_enabled`)."""
        with expected_protocol(
            AgilentB1500Mock,
            [
                ("FMT 1, 0", None),
                ("ERRX?", '+0,"No Error."'),
                ("TC 2, 0", "NBC+001.000E-12,NBY+002.000E-06,NBV+000.030E+00,NBV+001.000E+00"),
                (
                    "TTC 2, 0",
                    ("NBT+000.123E+00,NBC+001.000E-12,NBY+002.000E-06,"
                    "NBV+000.030E+00,NBV+001.000E+00"),
                ),
            ],
        ) as inst:
            inst.data_format(1)
            result = inst.cmu.measure()
            assert isinstance(result, SpotCMUMonitor)
            assert result == (1e-12, 2e-6, 0.03, 1.0)
            primary, secondary, ac_voltage, dc_voltage = result
            assert (primary, secondary, ac_voltage, dc_voltage) == (1e-12, 2e-6, 0.03, 1.0)
            assert result.ac_voltage == 0.03
            assert result.dc_voltage == 1.0
            timed_result = inst.cmu.measure(timestamp=True)
            assert isinstance(timed_result, TimedSpotCMUMonitor)
            assert timed_result == (0.123, 1e-12, 2e-6, 0.03, 1.0)

    def test_measure_invalid_range(self):
        """Test that measure rejects a range not in MEASUREMENT_RANGES."""
        with expected_protocol(AgilentB1500Mock, []) as inst, pytest.raises(ValueError):
            inst.cmu.measure(meas_range=500)

    def test_read_data_cmu(self):
        """Test read_data labels MFCMU data with the CMU unit name."""
        with expected_protocol(
            AgilentB1500Mock,
            [
                ("FMT 1, 0", None),
                ("ERRX?", '+0,"No Error."'),
                (None, "NBC+001.000E-12,NBY+002.000E-06"),
            ],
        ) as inst:
            inst.data_format(1)
            data = inst.read_data(1)
            assert data.iloc[0]["CMU Capacitance (F)"] == 1e-12
            assert data.iloc[0]["CMU Admittance (S)"] == 2e-6

    def test_set_cv_timings(self):
        """Test set_cv_timings method."""
        with expected_protocol(
            AgilentB1500Mock,
            [("WTDCV 2, 0.5, 0.1, 0.0, 0.0", None)],
        ) as inst:
            inst.cmu.set_cv_timings(hold_time=0.5, delay_time=0.1)

    def test_set_cv_timings_all_params(self):
        """Test set_cv_timings with all parameters."""
        with expected_protocol(
            AgilentB1500Mock,
            [("WTDCV 2, 1.0, 0.5, 0.2, 0.1", None)],
        ) as inst:
            inst.cmu.set_cv_timings(
                hold_time=1.0,
                delay_time=0.5,
                step_delay_time=0.2,
                step_source_trigger_delay_time=0.1,
            )

    @pytest.mark.parametrize("mode", [SweepMode.LINEAR_SINGLE, SweepMode.LINEAR_DOUBLE])
    def test_set_cv_parameters(self, mode):
        """Test set_cv_parameters method."""
        with expected_protocol(
            AgilentB1500Mock,
            [(f"WDCV 2, {mode.value}, -5, 5, 100", None)],
        ) as inst:
            inst.cmu.set_cv_parameters(mode=mode, start=-5, stop=5, steps=100)

    def test_force_dc_bias(self):
        """Test force_dc_bias method."""
        with expected_protocol(
            AgilentB1500Mock,
            [("DCV 2, 1.5", None)],
        ) as inst:
            inst.cmu.force_dc_bias(1.5)

    @pytest.mark.parametrize("path", list(SCUUPath))
    def test_set_scuu_path(self, path):
        """Test set_scuu_path method."""
        with expected_protocol(
            AgilentB1500Mock,
            [(f"SSP 2, {path.value}", None)],
        ) as inst:
            inst.cmu.set_scuu_path(path)

