"""Pin BCM konfigurasi SERVO LAMA. PCB stepper baru: docs/pcb/pinmap.json.
Nomor physical mengikuti header 40 pin Pi Zero; jangan aktifkan JARM dengan driver servo ini.
"""

# OLED I2C. Physical pin 3 dan 5.
OLED_SDA_PIN = 2
OLED_SCL_PIN = 3

# HC-SR04. VCC ke 5 V Pi pin 4, GND ke GND.
# TRIG langsung. ECHO lewat 2,2 kΩ ke pin ini, lalu 2,7 kΩ ke GND.
TRIG_PIN = 17  # physical pin 11
ECHO_PIN = 27  # physical pin 13

# Bekas uji E18. Pin yang sama dengan ECHO; jangan dipakai bersamaan dengan HC.
IR_OUT_PIN = 27

# Kabel sinyal. Daya merah dari catu 6,0 V 5 A di rak bawah, bukan pin 5 V Pi.
# MG996R yang rusak diganti TD8120MG 20 kg, 180°. Pulsa tetap 500–2500 µs.
SERVO_PIN = 18  # servo 1, pemilih jalur, physical pin 12
SERVO_TILT_PIN = 13  # servo 2, miring atas-bawah, physical pin 33

# LED indikator. Anoda lewat resistor, katoda ke GND.
LED_GREEN_PIN = 22  # physical pin 15
LED_RED_PIN = 23  # physical pin 16
ILLUMINATION_PIN = 24  # physical pin 18, lampu satu LED pada rakitan lama
# Cincin WS2812 tidak dipasang. Konstanta tetap ada untuk kode lama.
RING_DIN_PIN = 21  # physical pin 40, tidak disambung

# Buzzer, kaki sinyal. Physical pin 29.
BUZZER_PIN = 5
