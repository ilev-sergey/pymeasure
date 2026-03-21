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

import struct

import pytest

from pymeasure.instruments.agilent import AgilentB1500, ALWGPattern
from pymeasure.instruments.agilent.agilentB1500 import (
    CMU,
    SPGU,
    ControlMode,
    MFCMUMeasurementMode,
    PgSelectorConnectionStatus,
    PgSelectorPort,
    SCUUPath,
    SPGUChannelOutputMode,
    SPGUOperationMode,
    SPGUOutputMode,
    SweepMode,
    _encode_alwg_pattern_data,
    _encode_alwg_sequence_data,
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


class AgilentB1500Mock(AgilentB1500):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.spgu1 = SPGU(self, 1)
        self.cmu = CMU(self, 2)


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

    def test_set_alwg_pattern(self):
        """Test set_alwg_pattern sends correct ALW binary data."""
        pattern = ALWGPattern(
            initial_voltage=0.0,
            voltages=[1.0, 0.0],
            times=[100e-9, 100e-9],
        )
        data = _encode_alwg_pattern_data([pattern])
        expected = f"ALW {self.id}, {len(data)}\n".encode() + data
        with expected_protocol(
            AgilentB1500Mock,
            [(expected, None)],
        ) as inst:
            inst.spgu1.ch1.set_alwg_pattern([pattern])

    @pytest.mark.parametrize("state", [0, 1, 2, 3])
    def test_trigger_output(self, state):
        """Test trigger_output setting."""
        with expected_protocol(
            AgilentB1500Mock,
            [(f"STGP {self.id}, {state}", None)],
        ) as inst:
            inst.spgu1.ch1.trigger_output = state

    def test_set_pulse_switch_basic(self):
        """Test set_pulse_switch with state and normal only."""
        with expected_protocol(
            AgilentB1500Mock,
            [(f"ODSW {self.id}, 1, 0", None)],
        ) as inst:
            inst.spgu1.ch1.set_pulse_switch(state=1, normal=0)

    def test_set_pulse_switch_with_timing(self):
        """Test set_pulse_switch with PG-mode delay and width."""
        with expected_protocol(
            AgilentB1500Mock,
            [(f"ODSW {self.id}, 1, 1, 1e-06, 2e-06", None)],
        ) as inst:
            inst.spgu1.ch1.set_pulse_switch(state=1, normal=1, delay=1e-6, width=2e-6)


class TestSPGUALWG:
    """Tests for SPGU ALWG functionality."""

    def test_alwg_pattern_data_encoding(self):
        """Test binary encoding of ALWGPattern data matches expected format."""
        pattern = ALWGPattern(
            initial_voltage=0.0,
            voltages=[1.0],
            times=[100e-9],
            switch_states=[False],
        )
        data = _encode_alwg_pattern_data([pattern])

        # Header: 20 bytes
        assert data[:2] == bytes([0, 0])
        assert struct.unpack(">H", data[2:4])[0] == 1  # num_patterns = 1
        assert data[4:20] == bytes(16)  # reserved zeros

        # Initial data: N_i=1 (2B), initial_voltage=0 (4B)
        assert struct.unpack(">H", data[20:22])[0] == 1
        assert struct.unpack(">i", data[22:26])[0] == 0

        # Vector: voltage=1V → 1_000_000 counts, time=100ns → 100 counts, switch=off
        assert struct.unpack(">i", data[26:30])[0] == 1_000_000
        switch_and_time = struct.unpack(">I", data[30:34])[0]
        assert switch_and_time >> 31 == 0  # switch open
        assert switch_and_time & 0x7FFFFFFF == 100  # 100 ns

        assert len(data) == 20 + 6 + 8  # header + initial + 1 vector

    def test_alwg_pattern_switch_close(self):
        """Test that switch=True sets the MSB in the time field."""
        pattern = ALWGPattern(0.0, [0.0], [10e-9], switch_states=[True])
        data = _encode_alwg_pattern_data([pattern])
        switch_and_time = struct.unpack(">I", data[30:34])[0]
        assert switch_and_time >> 31 == 1  # switch closed

    def test_alwg_sequence_data_encoding(self):
        """Test binary encoding of ALWG sequence data."""
        data = _encode_alwg_sequence_data([(2, 2), (1, 3)])

        # Header
        assert data[:2] == bytes([0, 0])
        assert struct.unpack(">H", data[2:4])[0] == 2  # num_cycles = 2
        assert data[4:20] == bytes(16)

        # Cycle 1: pattern 2, repeat 2
        assert struct.unpack(">H", data[20:22])[0] == 2
        assert struct.unpack(">I", data[22:26])[0] == 2

        # Cycle 2: pattern 1, repeat 3
        assert struct.unpack(">H", data[26:28])[0] == 1
        assert struct.unpack(">I", data[28:32])[0] == 3

        assert len(data) == 20 + 6 * 2

    def test_set_alwg_sequence(self):
        """Test set_alwg_sequence sends correct ALS binary data."""
        pattern_cycles = [(2, 2), (1, 3)]
        data = _encode_alwg_sequence_data(pattern_cycles)
        expected = f"ALS {len(data)}\n".encode() + data
        with expected_protocol(
            AgilentB1500Mock,
            [(expected, None)],
        ) as inst:
            inst.spgu1.set_alwg_sequence(pattern_cycles)

    def test_alwg_pattern_too_many_patterns(self):
        """Test that > 512 patterns raises ValueError."""
        patterns = [ALWGPattern(0.0, [0.0], [10e-9]) for _ in range(513)]
        with pytest.raises(ValueError, match="512"):
            _encode_alwg_pattern_data(patterns)

    def test_alwg_pattern_time_too_short(self):
        """Test that time < 10 ns raises ValueError."""
        pattern = ALWGPattern(0.0, [0.0], [5e-9])
        with pytest.raises(ValueError, match="out of range"):
            _encode_alwg_pattern_data([pattern])

    def test_alwg_pattern_time_not_multiple_of_10ns(self):
        """Test that time not a multiple of 10 ns raises ValueError."""
        pattern = ALWGPattern(0.0, [0.0], [15e-9])
        with pytest.raises(ValueError, match="multiple of 10 ns"):
            _encode_alwg_pattern_data([pattern])

    def test_alwg_sequence_invalid_repeat_count(self):
        """Test that repeat_count > 1,048,576 raises ValueError."""
        with pytest.raises(ValueError, match="repeat_count"):
            _encode_alwg_sequence_data([(1, 1_048_577)])
