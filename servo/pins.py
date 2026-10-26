"""Pin BCM konfigurasi SERVO LAMA. PCB stepper baru: docs/pcb/pinmap.json.
Nomor physical mengikuti header 40 pin Pi Zero; jangan aktifkan JARM dengan driver servo ini.
"""

# OLED I2C. Physical pin 3 dan 5.
OLED_SDA_PIN = 2
OLED_SCL_PIN = 3

# HC-SR04. ECHO masuk lewat pembagi 2,2 kΩ / 2,7 kΩ, bukan langsung ke GPIO.
TRIG_PIN = 17  # physical pin 11
ECHO_PIN = 27  # physical pin 13

# MG996R, kabel sinyal. Physical pin 12. Daya merah dari 5 V eksternal.
SERVO_PIN = 18  # servo 1, putar 360°, physical pin 12
SERVO_TILT_PIN = 13  # servo 2, miring atas-bawah, physical pin 33

# LED indikator. Anoda lewat resistor, katoda ke GND.
LED_GREEN_PIN = 22  # physical pin 15
LED_RED_PIN = 23  # physical pin 16
ILLUMINATION_PIN = 24  # physical pin 18, lampu satu LED pada rakitan lama
# Cincin WS2812 12 LED di sekeliling kamera. Data saja; 5 V cincin dari catu bawah.
RING_DIN_PIN = 21  # physical pin 40

# Buzzer, kaki sinyal. Physical pin 29.
BUZZER_PIN = 5
