#connect libraries
import RPi.GPIO as GPIO
import board 
import busio
import adafruit_tsl2561
from w1thermsensor import W1ThermSensor
import datetime
from datetime import timedelta
from datetime import date
import pytz
import time
from astral import Location
import subprocess
from subprocess import call

#set GPIO
GPIO.setmode(GPIO.BCM)
#GPIO.setwarnings(False)
GPIO.setup(17, GPIO.IN) #soil moisture
GPIO.setup(27, GPIO.IN) #button OFF
GPIO.setup(12, GPIO.OUT) #heating
GPIO.setup(16, GPIO.OUT) #lighting
GPIO.setup(22, GPIO.OUT) #indication
pwm_lighting = GPIO.PWM(16, 1000)
GPIO.setup(21, GPIO.OUT) #fertilizers
pwm_fertilizers = GPIO.PWM(21, 1000)
GPIO.setup(20, GPIO.OUT) #watering
pwm_watering = GPIO.PWM(20, 1000)

#set light_sensor
i2c = busio.I2C(board.SCL, board.SDA)
light_sensor = adafruit_tsl2561.TSL2561(i2c)

#set temperature_sensor
temp_sensor = W1ThermSensor()

#set time of sunrise and sunset
astr = Location()
astr.name = 'Saint-Petersburg'
astr.region = 'Saint-Petersburg'
astr.latitude = 60.0
astr.longitude = 30.0
astr.timezone = 'Europe/Moscow'
astr.elevation = 20

#set log
def tfl():
    return str(datetime.datetime.today())[:19]

def log_m(string):
    log_m_file = open(r'/var/www/html/log_m.txt', 'a')
    log_m_file.write(tfl() + ' ' + string + '\n')
    log_m_file.close()

def log_h(mode, sensor, need, now):
    log_h_file = open(r'/var/www/html/log_h.txt', 'a')
    log_h_file.write(tfl() + '|' + mode + '|' + sensor + '|' + need + '|' + now + '\n')
    log_h_file.close()

def log_l(mode, sensor, now):
    log_l_file = open(r'/var/www/html/log_l.txt', 'a')
    log_l_file.write(tfl() + '|' + mode + '|' + sensor + '|' + now + '\n')
    log_l_file.close()

def log_f(mode):
    log_f_file = open(r'/var/www/html/log_f.txt', 'a')
    log_f_file.write(tfl() + '|' + mode + '\n')
    log_f_file.close()
    
def log_w(mode, sensor):
    log_w_file = open(r'/var/www/html/log_w.txt', 'a')
    log_w_file.write(tfl() + '|' + mode + '|' + sensor + '\n')
    log_w_file.close()

def logCl():
    log_file = open(r'/var/www/html/log_m.txt', 'w')
    log_file.close()
    log_file = open(r'/var/www/html/log_h.txt', 'w')
    log_file.close()
    log_file = open(r'/var/www/html/log_l.txt', 'w')
    log_file.close()
    log_file = open(r'/var/www/html/log_f.txt', 'w')
    log_file.close()
    log_file = open(r'/var/www/html/log_w.txt', 'w')
    log_file.close()

#set other
season = [15, 16, 19, 19, 24, 25, 26, 24, 22, 19, 17, 15]
date_today = 0
last_watering = date.today() - timedelta(days = 6)
last_fertilizers = 0
flag_heating = False
flag_lighting = False
flag_off = False
flag_cl = False
log_m('Power ON')

#sub
def indication(count):
    for i in range(count):
        GPIO.output(22, 1)
        time.sleep(1)
        GPIO.output(22, 0)
        time.sleep(1)
    log_m('Indication ' + str(count))
    
def heating():
    if int(temp_sensor.get_temperature()) < season[int(date_today.month) - 1] and not flag_heating:
        GPIO.output(12, 1)
        log_h('ON ', str(int(temp_sensor.get_temperature())), str(season[int(date_today.month) - 1]), str(flag_heating))
        return True
    elif int(temp_sensor.get_temperature()) >= season[int(date_today.month) - 1] and flag_heating:
        GPIO.output(12, 0)
        log_h('OFF', str(int(temp_sensor.get_temperature())), str(season[int(date_today.month) - 1]), str(flag_heating))
        return False
    else:
        log_h('Non', str(int(temp_sensor.get_temperature())), str(season[int(date_today.month) - 1]), str(flag_heating))
        return flag_heating

def lighting():
    if light_sensor.lux == None:
        light = 0
    else:
        light = int(light_sensor.lux)
    
    if c_time >= sunrise and c_time <= sunset:
        if light < 55 and not flag_lighting:
            pwm_lighting.start(100 - light)
            log_l('ON ', str(light), str(flag_lighting))
            return True
        elif light >= 55 and flag_lighting:
            pwm_lighting.stop()
            log_l('OFF', str(light), str(flag_lighting))
            return False
        elif light < 55 and flag_lighting:
            pwm_lighting.ChangeDutyCycle(100 - light)
            log_l('Ch ', str(light), str(flag_lighting))
            return True
        else:
            log_l('Non', str(light), str(flag_lighting))
            return flag_lighting
    elif flag_lighting:
        pwm_lighting.stop()
        log_l('OFF', str(light), str(flag_lighting))
        return False
    else:
        log_l('NT ', str(light), str(flag_lighting))
        return flag_lighting

def fertilizers():
    if int(date_today.month) != 12 and int(date_today.month) != 1 and int(date_today.month) != 2:
        if int(date_today.day) == 1 and int(date_today.month) != last_fertilizers:
            pwm_fertilizers.start(70)
            time.sleep(2)
            pwm_fertilizers.stop()
            log_f('OK')
            return int(date_today.month)
        else:
            log_f('NT')
            return last_fertilizers
    else:
        log_f('NT')
        return last_fertilizers
            
def watering():
    if int(date_today.month) != 12 and int(date_today.month) != 1 and int(date_today.month) != 2 and int(date_today.day) != 1:
        if GPIO.input(17) == 1 and date_today >= (last_watering + timedelta(days = 5)):
            pwm_watering.start(70)
            time.sleep(2)
            pwm_watering.stop()
            log_w('OK ', str(GPIO.input(17)))
            return date_today
        else:
            log_w('Non', str(GPIO.input(17)))
            return last_watering
    elif int(date_today.day) == 15 and GPIO.input(17) == 1 and date_today != last_watering:
        pwm_watering.start(70)
        time.sleep(2)
        pwm_watering.stop()
        log_w('OK ', str(GPIO.input(17)))
        return date_today
    else:
        log_w('NT ', str(GPIO.input(17)))
        return last_watering

#main
indication(3)

while not flag_off:
    if date.today() !=  date_today:
        date_today = date.today()
        sun = astr.sun(date = datetime.date.today(), local = True)
        sunrise = str(sun['sunrise'])[11:16]
        sunrise = int(sunrise.replace(':', ''))
        sunset = str(sun['sunset'])[11:16]
        sunset = int(sunset.replace(':', ''))
        log_m('Sunrise = ' + str(sunrise) + '     sunset = ' + str(sunset))
    c_time = str(datetime.datetime.now())[11:16]
    c_time = int(c_time.replace(':', ''))
    
    flag_heating = heating() #heating
    
    flag_lighting = lighting() #lighting
    
    last_fertilizers = fertilizers() #fertilizers
    
    last_watering = watering() #watering
    
    for i in range(24): #frequency of check
        time.sleep(5)
        if GPIO.input(27) == 0:
            indication(1)
            for j in range(5):
                time.sleep(1)
                if GPIO.input(27) == 0:
                    indication(4)
                    logCl()
                    flag_cl = True
                    break
            if not flag_cl:
                flag_off = True
                break
            flag_cl = False

indication(2) #off
if flag_heating:
    GPIO.output(12, 0)
if flag_lighting:
    pwm_lighting.stop()
GPIO.cleanup()
log_m('Power OFF')
call("sudo shutdown -h now", shell=True)
