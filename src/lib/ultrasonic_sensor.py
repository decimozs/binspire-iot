import RPi.GPIO as GPIO
import time


class UltrasonicSensor:
    def __init__(self, trig_pin: int, echo_pin: int, timeout: float = 1.0):
        self.TRIG = trig_pin
        self.ECHO = echo_pin
        self.timeout = timeout

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.TRIG, GPIO.OUT)
        GPIO.setup(self.ECHO, GPIO.IN)
        GPIO.output(self.TRIG, False)
        time.sleep(0.05)

    def get_distance(self) -> float | None:
        GPIO.output(self.TRIG, True)
        time.sleep(0.00001)
        GPIO.output(self.TRIG, False)

        start_time = time.time()
        while GPIO.input(self.ECHO) == 0:
            if time.time() - start_time > self.timeout:
                return None
        pulse_start = time.time()

        start_time = time.time()
        while GPIO.input(self.ECHO) == 1:
            if time.time() - start_time > self.timeout:
                return None
        pulse_end = time.time()

        pulse_duration = pulse_end - pulse_start
        distance = pulse_duration * 17150
        return round(distance, 2)
