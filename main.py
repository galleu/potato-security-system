import time
import gpiod
import requests
import pygame.mixer
import time
import subprocess
import threading


# Configuration
CHIP = 1  # Using gpiochip1

# Configuration based on chosen pins
DOOR_PIN = 91   # 8
BUZZER_PIN = 92 # 10
ARMED_PIN = 93  # 16

# Webhook
WEBHOOK_URL = "" # At the moment it is using a DISCORD webhook. (Plan is it make it interact with discord or a custom webpage to arm and disarm) (NO PASSCODE/KEYPAD PLANS)

pygame.mixer.init()

# Initialize chip and lines
chip = gpiod.Chip('gpiochip{}'.format(CHIP))
door_line = chip.get_line(DOOR_PIN)
buzzer_line = chip.get_line(BUZZER_PIN)
armed_line = chip.get_line(ARMED_PIN)


# Set the system volume
subprocess.run("amixer -c 1 set PCM 100%", shell=True, text=True)

# Explicitly set the direction
door_line.request(consumer='door_sensor', type=gpiod.LINE_REQ_DIR_IN)
armed_line.request(consumer='armed_sensor', type=gpiod.LINE_REQ_DIR_IN)
buzzer_line.request(consumer='buzzer', type=gpiod.LINE_REQ_DIR_OUT)

def buzzer_toggle():
    buzzer_line.set_value(1)
    time.sleep(0.1)
    buzzer_line.set_value(0)
    time.sleep(0.1)

def playsound(file_name):
    sound = pygame.mixer.Sound(f'voice/{str(file_name)}.wav')
    sound.play()
    return sound

def playwords(words):
    for word in words:
        sound = playsound(word)
        time.sleep(sound.get_length())

def playwords_threaded(words):
    t = threading.Thread(target=playwords, args=(words,))
    t.start()


def playzone(number, status):
    sound = playsound('zone')
    time.sleep(sound.get_length())
    sound = playsound(number)
    time.sleep(sound.get_length())
    sound = playsound(status)
    time.sleep(sound.get_length())


alert_sent = False
alarm_triggered_time = None
unsecured_played = False

door_state = door_line.get_value()
armed_state = armed_line.get_value()

lockout = False

unsecured_state = False

# Buzzer and speaker on 
buzzer_toggle()
playwords_threaded(['system', 'on'])


while True:
    if door_state != door_line.get_value():
        print(f"Door state changed to: {'OPEN' if door_state else 'CLOSED'}")
        door_state = door_line.get_value()
        playwords_threaded(['zone', '1', 'open' if door_state else 'close'])

    if armed_state != armed_line.get_value():
        print(f"Alarm state changed to: {'DISARMED' if armed_state else 'ARMED'}")
        armed_state = armed_line.get_value()
        lockout = False
        unsecured_played = False
        if armed_state:
            playsound("armed")
        else:
            playsound("disarmed")


        if not armed_state:  # if system is disarmed
            alert_sent = False
            alarm_triggered_time = None
            buzzer_line.set_value(0)

    if door_state and armed_state and not lockout:
        lockout = True
    else:
        buzzer_line.set_value(0)
        unsecured_state = False
        

    if lockout:
        print("ALERT: Door opened while armed!")
        if not alert_sent:
            requests.post(WEBHOOK_URL, json={"content": "ALERT: Door opened while armed!"})
            playwords_threaded(['alert','system', 'armed'])
            alert_sent = True
            alarm_triggered_time = time.time()

        if alarm_triggered_time and time.time() - alarm_triggered_time > 20:
            buzzer_line.set_value(1)
            if not unsecured_state and not unsecured_played:  # Add the check for unsecured_played
                playzone(1, "unsecured")
                unsecured_state = True
                unsecured_played = True  # Set the flag after playing the sound
        else:
            buzzer_toggle()



    time.sleep(0.1)


