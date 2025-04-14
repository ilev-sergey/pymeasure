#
# This file is part of the PyMeasure package.
#
# Copyright (c) 2013-2025 PyMeasure Developers
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

import numpy as np

from pymeasure.instruments import Instrument
from pymeasure.instruments.agilent import Agilent33500
from pymeasure.instruments.agilent.agilent33500 import Agilent33500Channel
from pymeasure.instruments.validators import strict_discrete_set, strict_range

WF_SHAPES = ["SIN", "SQU", "RAMP", "PULS", "NOIS", "DC", "USER"]
FREQUENCY_SIN_RANGE = [1e-6, 500e6]
FREQUENCY_RANGE = [1e-6, 330e6]
AMPLITUDE_RANGE = [0.05, 5]
OFFSET_RANGE = [-4.995, 4.995]
VOLTAGE_HIGH_RANGE = [-4.95, 5.0]
VOLTAGE_LOW_RANGE = [-5, 4.95]
SQUARE_DUTYCYCLE_RANGE = [0.0001515, 99.9998485]
PULSE_PERIOD_RANGE = [2e-9, 1e6]
PULSE_WIDTH_RANGE = [1.5e-9, 1e6]
PULSE_DUTYCYCLE_RANGE = [1.5e-1, 99.99]
PULSE_TRANSITION_RANGE = [1e-9, 1e3]
BURST_PERIOD = [3.03e-9, 1e6]
BURST_NCYCLES = [2, 2.147483647e9]
TRIGGER_COUNT = [1, 2.147483647e9]
LIMIT_HIGH_RANGE = [-9.99, 10]
LIMIT_LOW_RANGE = [-10, 9.99]
BOOLEANS = [True, False]
IMPEDANCE_RANGE = [3e-1, 1e6]
TRIGGER_MODES = ["IMM", "INT2", "EXT", "MAN"]
MAX_VOLTAGE = 5.0
SIN_AMPL_BORDER = 3.0
MAX_DAC_VALUE = 8191


class Keysight81160AChannel(Agilent33500Channel):
    shape_values = WF_SHAPES
    shape_get_command = ":FUNC{ch}?"
    shape_set_command = ":FUNC{ch} %s"

    frequency_values = FREQUENCY_SIN_RANGE
    frequency_get_command = ":FREQ{ch}?"
    frequency_set_command = ":FREQ{ch} %f"

    amplitude_values = AMPLITUDE_RANGE
    amplitude_get_command = ":VOLT{ch}?"
    amplitude_set_command = ":VOLT{ch} %f"

    amplitude_unit_get_command = ":VOLT{ch}:UNIT?"
    amplitude_unit_set_command = ":VOLT{ch}:UNIT %s"

    offset_values = OFFSET_RANGE
    offset_get_command = ":VOLT{ch}:OFFS?"
    offset_set_command = ":VOLT{ch}:OFFS %f"

    voltage_high_values = VOLTAGE_HIGH_RANGE
    voltage_high_get_command = ":VOLT{ch}:HIGH?"
    voltage_high_set_command = ":VOLT{ch}:HIGH %f"

    voltage_low_values = VOLTAGE_LOW_RANGE
    voltage_low_get_command = ":VOLT{ch}:LOW?"
    voltage_low_set_command = ":VOLT{ch}:LOW %f"

    square_dutycycle_values = SQUARE_DUTYCYCLE_RANGE
    square_dutycycle_set_command = ":FUNC{ch}:SQU:DCYC %f"
    square_dutycycle_get_command = ":FUNC{ch}:SQU:DCYC?"

    ramp_symmetry_set_command = ":FUNC{ch}:RAMP:SYMM %f"
    ramp_symmetry_get_command = ":FUNC{ch}:RAMP:SYMM?"

    pulse_period_values = PULSE_PERIOD_RANGE
    pulse_period_set_command = ":PULS:PER{ch} %e"
    pulse_period_get_command = ":PULS:PER{ch}?"

    pulse_hold_set_command = ":PULS:HOLD{ch} %s"
    pulse_hold_get_command = ":PULS:HOLD{ch}?"

    pulse_width_values = PULSE_WIDTH_RANGE
    pulse_width_set_command = ":PULS:WIDT{ch} %e"
    pulse_width_get_command = ":PULS:WIDT{ch}?"

    pulse_dutycycle_values = PULSE_DUTYCYCLE_RANGE
    pulse_dutycycle_set_command = ":PULS:DCYC{ch} %f"
    pulse_dutycycle_get_command = ":PULS:DCYC{ch}?"

    pulse_transition_values = PULSE_TRANSITION_RANGE
    pulse_transition_set_command = ":FUNC{ch}:PULS:TRAN %e"
    pulse_transition_get_command = ":FUNC{ch}:PULS:TRAN?"

    output_load_values = IMPEDANCE_RANGE
    output_load_set_command = ":OUTP{ch}:LOAD %e"
    output_load_get_command = ":OUTP{ch}:LOAD?"

    burst_state_values = BOOLEANS
    burst_state_set_command = ":BURS{ch}:STAT %s"
    burst_state_get_command = ":BURS{ch}:STAT?"

    burst_mode_set_command = ":BURS{ch}:MODE %s"
    burst_mode_get_command = ":BURS{ch}:MODE?"

    burst_period_values = BURST_PERIOD
    burst_period_set_command = ":BURS{ch}:INT:PER %e"
    burst_period_get_command = ":BURS{ch}:INT:PER?"

    burst_ncycles_values = BURST_NCYCLES
    burst_ncycles_set_command = ":BURS{ch}:NCYC %d"
    burst_ncycles_get_command = ":BURS{ch}:NCYC?"

    limit_state_enabled = Instrument.control(
        ":VOLT{ch}:LIM:STAT?",
        ":VOLT{ch}:LIM:STAT %s",
        """Control the limit state (string).""",
        validator=strict_discrete_set,
        map_values=True,
        values={True: 1, False: 0},
        dynamic=True,
    )

    limit_high = Instrument.control(
        ":VOLT{ch}:LIM:HIGH?",
        ":VOLT{ch}:LIM:HIGH %f",
        """Control the high-level voltage limit (float).""",
        validator=strict_range,
        values=LIMIT_HIGH_RANGE,
        dynamic=True,
    )

    limit_low = Instrument.control(
        ":VOLT{ch}:LIM:LOW?",
        ":VOLT{ch}:LIM:LOW %f",
        """Control the low-level voltage limit (float).""",
        validator=strict_range,
        values=LIMIT_LOW_RANGE,
        dynamic=True,
    )

    memory_free = Instrument.measurement(
        ":DATA{ch}:NVOL:FREE?",
        """Get the number of free non-volatile memory slots to store user waveforms (int).""",
        dynamic=True,
    )

    coupling_enabled = Instrument.control(
        ":TRAC:CHAN{ch}?",
        ":TRAC:CHAN{ch} %s",
        """Control the channel coupling (string). ``:TRAC:CHAN1 ON`` to copy values from
        channel 1 to channel 2.""",
        validator=strict_discrete_set,
        map_values=True,
        values={True: 1, False: 0},
        dynamic=True,
    )

    waveforms = Instrument.measurement(
        ":DATA{ch}:NVOL:CAT?",
        """Get the available user waveforms in memory (list[str]).""",
        preprocess_reply=lambda v: v.replace('"', "").replace("\n", ""),
        dynamic=True,
    )

    trigger_mode = Instrument.control(
        ":ARM:SOUR{ch}?",
        ":ARM:SOUR{ch} %s",
        """Control the triggering mode (string).""",
        validator=strict_discrete_set,
        values=TRIGGER_MODES,
        dynamic=True,
    )

    trigger_count = Instrument.control(
        ":TRIG{ch}:COUN?",
        ":TRIG{ch}:COUN %d",
        """Control the number of cycles to be output when a burst is triggered (int). Enable burst
        state if number > 1.

        Short form of burst_ncycles and burst_state = True""",
        validator=strict_range,
        values=TRIGGER_COUNT,
        dynamic=True,
    )

    def _preprocess_waveform(self, data):
        """
        Convert a waveform data to int values (from -'MAX_DAC_VALUE' to 'MAX_DAC_VALUE').

        :param data: waveform voltage data (array-like).
        :return: waveform voltage data as int values (array-like).
        """
        data_normed = data / data.max()
        data_int = np.round(data_normed * MAX_DAC_VALUE).astype(int)

        return data_int

    @property
    def waveform_volatile(self):
        """
        Get volatile waveform data.

        :return: waveform data (array-like).
        """
        return self._waveform_volatile

    @waveform_volatile.setter
    def waveform_volatile(self, waveform):
        """
        Set volatile waveform data for arbitrary waveform generation.

        :param waveform: The waveform data to be set (array-like).
        """
        self._waveform_volatile = np.array(waveform, dtype=np.float64)
        waveform_int = self._preprocess_waveform(self._waveform_volatile)
        self.write_binary_values(
            command=f":DATA{self.id}:DAC VOLATILE,",
            values=waveform_int,
            datatype="h",
            is_big_endian=True,
        )

    def save_waveform(self, waveform, name):
        """
        Save a waveform to the generator's nonvolatile memory.

        :param waveform: The waveform data.
        :param name: The name of the waveform.
        """
        self.waveform_volatile = waveform
        self.write(f":DATA{self.id}:COPY {name}, VOLATILE")

    def delete_waveform(self, name):
        """
        Delete a waveform from the generator's nonvolatile memory.

        :param name: The name of the waveform.
        """
        self.write(f":DATA{self.id}:DEL {name.upper()}")

    def apply_dc(self, voltage):
        self.write(f":APPL{self.id}:DC DEF, DEF, {voltage}")

    def apply_noise(self, amplitude, offset):
        self._check_voltages(amplitude, offset)
        self.write(f":APPL{self.id}:NOIS DEF, {amplitude}, {offset}")

    def apply_pulse(self, frequency, amplitude, offset):
        self._check_voltages(amplitude, offset)
        self.write(f":APPL{self.id}:PULS {frequency}, {amplitude}, {offset}")

    def apply_sin(self, frequency, amplitude, offset):
        self._check_voltages(amplitude, offset)
        self._check_sin_params(frequency, amplitude)
        self.write(f":APPL{self.id}:SIN {frequency}, {amplitude}, {offset}")

    def apply_square(self, frequency, amplitude, offset):
        self._check_voltages(amplitude, offset)
        self.write(f":APPL{self.id}:SQU {frequency}, {amplitude}, {offset}")

    def apply_user_waveform(self, frequency, amplitude, offset):
        self._check_voltages(amplitude, offset)
        self.write(f":APPL{self.id}:USER {frequency}, {amplitude}, {offset}")

    def _check_voltages(self, amplitude, offset):
        if abs(amplitude) + abs(offset) > MAX_VOLTAGE:
            raise ValueError(f"Amplitude + offset exceed maximal voltage of {MAX_VOLTAGE} V.")

    def _check_sin_params(self, frequency, amplitude):
        if frequency > FREQUENCY_RANGE[-1] and amplitude > SIN_AMPL_BORDER:
            raise ValueError(
                f"Frequency of higher than {FREQUENCY_RANGE[-1]} Hz is only supported for sin with"
                + f" amplitude below {SIN_AMPL_BORDER} V."
            )


class Keysight81160A(Agilent33500):
    ch_1 = Instrument.ChannelCreator(Keysight81160AChannel, 1)
    ch_2 = Instrument.ChannelCreator(Keysight81160AChannel, 2)

    shape_values = WF_SHAPES
    frequency_values = FREQUENCY_SIN_RANGE
    amplitude_values = AMPLITUDE_RANGE
    offset_values = OFFSET_RANGE
    voltage_high_values = VOLTAGE_HIGH_RANGE
    voltage_low_values = VOLTAGE_LOW_RANGE
    square_dutycycle_values = SQUARE_DUTYCYCLE_RANGE
    pulse_period_values = PULSE_PERIOD_RANGE
    pulse_period_get_command = ":PULS:PER?"
    pulse_period_set_command = ":PULS:PER %e"
    pulse_width_values = PULSE_WIDTH_RANGE
    pulse_dutycycle_values = PULSE_DUTYCYCLE_RANGE
    pulse_transition_values = PULSE_TRANSITION_RANGE
    pulse_transition_set_command = ":FUNC:PULS:TRAN %e"
    burst_period_values = BURST_PERIOD
    burst_ncycles_values = BURST_NCYCLES
    arb_file_get_command = ":FUNC:USER?"


#####################
# UTILITY FUNCTIONS #
#####################


def generate_pulse_sequence(pulse_voltage, dc_voltage, return_to_zero=False, plot=False):
    max_dac = 2**13 - 1
    if pulse_voltage < 0 and dc_voltage <= 0:
        max_dac = -max_dac

    dc_dac = int(dc_voltage / pulse_voltage * max_dac)

    total_num = 20000  # number of points in the waveform
    rise_num = 100 // 30  # number of points in the rump
    hold_num = (500 // 3) * 100 // 84  # number of points in the hold
    fall_num = int(
        rise_num / pulse_voltage * (pulse_voltage - dc_voltage)
    )  # number of points in the fall

    points = np.zeros(total_num)

    pulse_rise_start = 100
    pulse_rise_end = pulse_rise_start + rise_num

    pulse_hold_start = pulse_rise_end
    pulse_hold_end = pulse_hold_start + hold_num

    pulse_fall_start = pulse_hold_end
    pulse_fall_end = pulse_fall_start + fall_num

    points[pulse_rise_start:pulse_rise_end] = np.linspace(0, max_dac, rise_num)
    points[pulse_hold_start:pulse_hold_end] = max_dac
    points[pulse_fall_start:pulse_fall_end] = np.linspace(max_dac, dc_dac, fall_num)

    points[pulse_fall_end:] = dc_dac

    if return_to_zero:
        points[-1] = 0

    if plot:
        import matplotlib.pyplot as plt

        plt.plot(points)

    return points


def array_to_string(array):
    return ",".join(map(lambda x: str(round(x)), array))
