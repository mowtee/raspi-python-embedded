# Top Sigrid ADXL345 Library
# Timo Ostlender, Franz Roessler, Timo Sirinyan
# Dies ist eine Raspberry Pi Python Library fuer den Accelerometer ADXL345
# Siehe Dokumentation

from typing import ValuesView
import smbus
import RPi.GPIO as GPIO
from time import sleep

# Korrekten I2C Bus für Raspberry Pi Version auswaehlen und SMBus initialisieren:
revision = GPIO.RPI_REVISION
if revision >= 2:
    busNumber = 1
else:
    busNumber = 0
bus = smbus.SMBus(busNumber)

# ADXL345 Register und Konstanten:

ADDRESS         = 0x53          # I2C Adresse auf dem System Management Bus

BW_RATE         = 0x2C          # Data rate and power mode control -> benutzt um Mess- und Outputrate festzulegen
POWER_CTL       = 0x2D          # Power-saving features control -> benutzt um Sensor zu aktivieren
DATA_FORMAT     = 0x31          # Data format control -> benutzt um Range und Format des Outputs festzulegen

BW_RATE_1600HZ  = 0x0F          # Bits in BW_RATE Byte, um eine bestimmte Mess- und Outputrate festzulegen
BW_RATE_800HZ   = 0x0E          # Siehe Table 7 in Datasheet
BW_RATE_400HZ   = 0x0D
BW_RATE_200HZ   = 0x0C
BW_RATE_100HZ   = 0x0B
BW_RATE_50HZ    = 0x0A
BW_RATE_25HZ    = 0x09

RANGE_2G        = 0x00          # Bits in DATA_FORMAT, um eine bestimmte Range festzulegen
RANGE_4G        = 0x01
RANGE_8G        = 0x02
RANGE_16G       = 0x03
FULL_RES        = 0x08          # Setzt Output in Full Resolution Mode / siehe unten

MEASURE         = 0x08          # Bit in POWER_CTL, um Sensor zu aktivieren
AXES_DATA       = 0x32          # bis 0x37 -> 6 bytes lang / 0x32 = DATAX0 = least significant byte, 0x33 = DATAX1 = most significant byte für X-Achse usw.

SCALE_FACTOR    = 0.0039        # Bei gesetztem FULL_RES bit in DATA_FORMAT steigt die Output Resolution mit der Range und die Auflösung betraegt 3.9 mg / LSB (siehe Datasheet Table 1)
G_TO_MS2_FACTOR = 9.80665       # Umrechnungsfaktor: 1 g = 9.80665 m/s^2


def fromtwos(value, wordsize):
    if(value & (1 << wordsize - 1)):
        value = value - (1<<wordsize)
    return value

def totwos(value, wordsize):
    if(value<0):
        value = bin((1<<wordsize)+value)
    return value

class SigridADXL345:

    address     = None
    rate        = None
    range       = None
    unit        = None

    def __init__(self, rate, measure_range, unit, address = ADDRESS):
        try:
            print("Initializing...")
            self.address = address
            self.rate = rate
            self.setRate(rate)
            print("rate set")
            self.measure_range = measure_range
            self.setRange(measure_range)
            print("range set")
            self.unit = unit
            self.startMeasurement()
            print("Done!")
        except:
            print("Error!")
            exit()


    def setRate(self):
        # Python dictionary mit moeglichen Werten für die Bandwidth und Output Data Rate
        # zum Mapping der Uebergabevariable verwenden:

        adxl345Rates = {
        1600:   BW_RATE_1600HZ,
        800:    BW_RATE_800HZ,
        400:    BW_RATE_400HZ,
        200:    BW_RATE_200HZ,
        100:    BW_RATE_100HZ,
        50:     BW_RATE_50HZ,
        25:     BW_RATE_25HZ
        }

        defaultRate = BW_RATE_100HZ
        if self.rate not in adxl345Rates:
            print ("Invalid Value for BW Rate! Set to default 100 Hz.")
        rateBits    = adxl345Rates.get(self.rate, defaultRate)

        bus.write_byte_data(self.address, BW_RATE, rateBits)


    def setRange(self):
        # Python dictionary mit moeglichen Werten für die g Range
        # zum Mapping der Uebergabevariable verwenden:
        adxl345Ranges = {
        16:     RANGE_16G,
        8:      RANGE_8G,
        4:      RANGE_4G,
        2:      RANGE_2G
        }

        defaultRange        = RANGE_2G
        if self.measure_range not in adxl345Ranges:
            print("Invalid Value for g-Range! Set to default 2g.")
        self.rangeBits           = adxl345Ranges.get(self.range, defaultRange)

        # FULL_RES bit fuer konstante Aufloesung grundsaetzlich setzen, dafür range mit FULL_RES Bit Oder-verknuepfen:
        rangeBitsFullRes    = self.rangeBits | FULL_RES

        bus.write_byte_data(self.address, DATA_FORMAT, rangeBitsFullRes)




    def startMeasurement(self):

        bus.write_byte_data(self.address, POWER_CTL, MEASURE)


    def getData(self):
        # Ab DATAX0 6 Bytes in einer Operation auslesen:
        # (Wichtig, damit Datensatz komplett aus einer Messung stammt)
        dataBytes = bus.read_i2c_block_data(self.address, AXES_DATA, 6)     # liefert ein 6 Werte langes Array mit den Bits aus DATAX0 bis DATAZ1 zurueck

        x = dataBytes[0] | ((dataBytes[1] << 8))        # verschiebt MSB um 8 bit nach links und Oder-verknuepft mit dem LSB
        x = fromtwos(x, 16)                             # wandelt aus Zweierkomplement um

        y = dataBytes[2] | ((dataBytes[3] << 8))
        y = fromtwos(y, 16)

        z = dataBytes[4] | ((dataBytes[5] << 8))
        z = fromtwos(z, 16)

        # Rohwerte in g's umsetzen:
        x *= SCALE_FACTOR
        y *= SCALE_FACTOR
        z *= SCALE_FACTOR

        adxl345Units = ['g', 'm2s']
        # Falls Werte in m/s^2 gewuenscht:
        if self.unit not in adxl345Units:
            print("Invalid Unit! Choose g or m2s. Defaulting to g.")
            self.unit = 'g'
        if self.unit == 'm2s':
            x *= G_TO_MS2_FACTOR
            y *= G_TO_MS2_FACTOR
            z *= G_TO_MS2_FACTOR

        return [x, y, z]

    def print(self):
        data = self.getData(self)
        print("X-Value:", data[0], sigridADXL345.unit)
        print("Y-Value:", data[1], sigridADXL345.unit)
        print("Z-Value:", data[2], sigridADXL345.unit,"\n")


if __name__ == "__main__":

    # Falls direkt aufgerufen, eine Instanz der Klasse erschaffen und Werte in Schleife ausgeben:

    print("ADXL345 Testprogram\n===================\n")
    print()
    rate    = int(input("Data Rate: "))
    measure_range   = int(input("G Range: "))
    unit    = input("Unit: ")
    print()

    sigridADXL345 = SigridADXL345(rate, measure_range, unit)

    try:
        while True:
            print(sigridADXL345)
            sleep(1)
    except KeyboardInterrupt:
        exit()
