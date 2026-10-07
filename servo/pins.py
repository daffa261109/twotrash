"""Pin BCM sesuai docs/wiring.md. Nomor physical mengikuti header 40 pin Pi Zero."""

# OLED I2C. Physical pin 3 dan 5.
OLED_SDA_PIN = 2
OLED_SCL_PIN = 3

# HC-SR04. ECHO masuk lewat pembagi 1 kΩ / 2 kΩ, bukan langsung ke GPIO.
TRIG_PIN = 17  # physical pin 11
ECHO_PIN = 27  # physical pin 13

# MG996R, kabel sinyal. Physical pin 12. Daya merah dari 5 V eksternal.
SERVO_PIN = 18

# LED indikator. Anoda lewat resistor, katoda ke GND.
LED_GREEN_PIN = 22  # physical pin 15
LED_RED_PIN = 23  # physical pin 16

# Buzzer, kaki sinyal. Physical pin 29.
BUZZER_PIN = 5
