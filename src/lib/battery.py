import subprocess
import smbus

_REG_CONFIG = 0x00
_REG_SHUNTVOLTAGE = 0x01
_REG_BUSVOLTAGE = 0x02
_REG_POWER = 0x03
_REG_CURRENT = 0x04
_REG_CALIBRATION = 0x05


class BusVoltageRange:
    RANGE_16V = 0x00
    RANGE_32V = 0x01


class Gain:
    DIV_1_40MV = 0x00
    DIV_2_80MV = 0x01
    DIV_4_160MV = 0x02
    DIV_8_320MV = 0x03


class ADCResolution:
    ADCRES_12BIT_32S = 0x0D


class Mode:
    SANDBVOLT_CONTINUOUS = 0x07


class INA219:
    def __init__(self, i2c_bus=1, addr=0x42):
        self.bus = smbus.SMBus(i2c_bus)
        self.addr = addr
        self._cal_value = 0
        self._current_lsb = 0
        self._power_lsb = 0
        self.set_calibration_32V_2A()

    def read(self, address):
        data = self.bus.read_i2c_block_data(self.addr, address, 2)
        return (data[0] << 8) + data[1]

    def write(self, address, data):
        temp = [(data >> 8) & 0xFF, data & 0xFF]
        self.bus.write_i2c_block_data(self.addr, address, temp)

    def set_calibration_32V_2A(self):
        self._current_lsb = 0.1  # 100 uA/bit
        self._cal_value = 4096
        self._power_lsb = 0.002  # 2 mW/bit
        self.write(_REG_CALIBRATION, self._cal_value)

        config = (
            (BusVoltageRange.RANGE_32V << 13)
            | (Gain.DIV_8_320MV << 11)
            | (ADCResolution.ADCRES_12BIT_32S << 7)
            | (ADCResolution.ADCRES_12BIT_32S << 3)
            | Mode.SANDBVOLT_CONTINUOUS
        )
        self.write(_REG_CONFIG, config)

    def getBusVoltage_V(self):
        self.write(_REG_CALIBRATION, self._cal_value)
        return (self.read(_REG_BUSVOLTAGE) >> 3) * 0.004

    def getShuntVoltage_mV(self):
        self.write(_REG_CALIBRATION, self._cal_value)
        value = self.read(_REG_SHUNTVOLTAGE)
        if value > 32767:
            value -= 65535
        return value * 0.01


def get_battery_status():
    try:
        ina219 = INA219(addr=0x42)
        bus_voltage = ina219.getBusVoltage_V()
        shunt_voltage = ina219.getShuntVoltage_mV() / 1000
        battery_voltage = bus_voltage + shunt_voltage

        percentage = (battery_voltage - 6.0) / (8.4 - 6.0) * 100
        percentage = max(0, min(percentage, 100))
        return round(percentage, 1)
    except Exception:
        try:
            output = subprocess.check_output(["acpi", "-b"]).decode("utf-8")
            battery_percentage = output.split(",")[1].strip().replace("%", "")
            return float(battery_percentage)
        except (subprocess.CalledProcessError, FileNotFoundError):
            return -1  # indicates failure to read
