import socket
import ssl
from machine import Pin, Timer
import network
from utime import sleep
from settings import wifi_name, wifi_pass, pushover_user, pushover_token

    
PUSHOVER_HOST = 'api.pushover.net'
PUSHOVER_PORT = 443
PUSHOVER_PATH = '/1/messages.json'
SAFE_CHARS = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.- '

#####################################
#    SET THESE IN 'settings.py'!    #
#####################################

# WiFi Settings
ssid = wifi_name
netpass = wifi_pass

# Pushover Settings
user = pushover_user
token = pushover_token

## Optional Settings
beep_duration=1     # duration to beep for (secs); can be decimal, eg 0.5
alarm_frequency=10  # how often to beep (secs) when in an alert state
net_frequency=1800  # how often to beep (secs) when network is disconencted
restart_delay=30    # if in a failed state, wait this many seconds before starting back up
connect_count=60    # How frequently (secs) to retry network connection if it's down (too frequent will interrupt in-flight attempts!)

#####################################
#               END                 #
#####################################

## Setup pins
floatswitch = Pin(2, Pin.IN) ## Pulled high when OK. Goes low when water level too high (alert state)
buzzer = Pin(4, Pin.OUT, value=False) ## Off by default
powertail = Pin(18, Pin.OUT, value=True) ## On by default

### PINOUT:
# Float1: GPIO_2
# Float2: 3.3v
#
# Buzzer+: GPIO_4
# Buzzer-: GND
#
# Powertail+: GPIO_18
# Powertail-: GND

## Initial State
last_float_state=True  ## True is healthy (water level OK)
startup_message_sent=False
send_alert_message=False
sent_recovery_message=True
net_timer=Timer(0)
net_timer_init=True
alarm_timer=Timer(1)
alarm_timer_init=False

def make_safe(string):
    r = []
    for c in string:
        if c in SAFE_CHARS:
            r.append(c)
        else:
            r.append('%%%x' % ord(c))
    return (''.join(r)).replace(' ', '+')

def sendMessage(title, msg, highPriority=False):    
    data =  'token=' + make_safe(token)
    data += '&user=' + make_safe(user)
    data += '&title=' + make_safe(title)
    data += '&message=' + make_safe(msg)
    if highPriority:
        data += '&priority=1'
  
    r = None
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.settimeout(10)
        addr = [(socket.getaddrinfo(PUSHOVER_HOST, PUSHOVER_PORT)[0][-1], PUSHOVER_HOST)]
        s.connect(addr[0][0])
        s = ssl.wrap_socket(s)

        s.write('POST {} HTTP/1.0\r\n'.format(PUSHOVER_PATH).encode())
        s.write('Host: {}\r\n'.format(addr[0][1]).encode())
        s.write(b'Content-Type: application/x-www-form-urlencoded\r\n')
        s.write('Content-Length: {}\r\n'.format(len(data)).encode())
        s.write(b'\r\n')
        s.write('{}\r\n\r\n'.format(data))

        while s.readline() != b'\r\n':
            continue

        r = s.read()
    except Exception as e:
            print(e)
    finally:
        s.close()
    print("Response: {}".format(r))


### Float switch connected 1. GND, 2. Pin2
def get_float_state():
    value = floatswitch.value()
    # print("Float value: {}".format(value))
    return floatswitch.value()

def beep():
    buzzer.value(True)
    sleep(beep_duration)
    buzzer.value(False)

def pushover_alert(wlan):
    if wlan.isconnected():
        try:
            print("Aquarium Float Trigger: ALERT")
            sendMessage("Aquarium Float Trigger: ALERT", "The float switch has triggered. Check overflow!", True)
            return True
        except Exception as err:
            print("Encountered error sending pushover message: {}".format(err))
            return False
    else:
        print("No alert message sent; wifi not up")
        return False

def pushover_recovery(wlan):
    if wlan.isconnected():
        try:
            print("Aquarium Float Trigger: OK")
            sendMessage("Aquarium Float Trigger: OK", "The float switch state has been restored")
            return True
        except Exception as err:
            print("Encountered error sending pushover message: {}".format(err))
            return False
    else:
        print("No recovery message sent; wifi not up")
        return False

def pushover_started(wlan):
    if wlan.isconnected():
        try:
            print("Aquarium Float Trigger: STARTED")
            sendMessage("Aquarium Float Trigger: Started", "The float switch service has started up")
            return True
        except Exception as err:
            print("Encountered error sending pushover message: {}".format(err))
            return False
    else:
        print("No startup message sent; wifi not up")
        return False
## START

# Connect to network
wlan = network.WLAN(network.STA_IF)
wlan.active(True)

while True:
    # Send a startup message
    if not startup_message_sent:
        startup_message_sent = pushover_started(wlan)

    # Maintain network connection. Beep hourly if not connected.
    if not wlan.isconnected():
        if not net_timer_init:
            net_timer.init(mode=Timer.PERIODIC, period=net_frequency*1000, callback=lambda t:beep()) # Beep every 1hr
            net_timer_init=True
        connect_count += 1
        if connect_count > 60:
            connect_count = 0
            print('Connecting to Wifi...')
            wlan.connect(ssid, netpass) # We don't block on this.
    else:
        if net_timer_init:
            connect_count = 0
            net_timer.deinit()
            net_timer_init = False

    # monitor float switch (voltage_high when OK)
    current_float_state = get_float_state()  # See if state has changed from last reading
    if current_float_state != last_float_state:
        print("State Change!: {} to {}".format(last_float_state, current_float_state))
        last_float_state = current_float_state

        if current_float_state:
            # ensure pin0 (powertail) is high
            powertail.value(1)
            sent_alert_message = False
            sent_recovery_message = pushover_recovery(wlan)
            if alarm_timer_init:
                alarm_timer.deinit()
        else:
            # if float_switch == vlow:
            powertail.value(0)
            sent_recovery_message = False
            alarm_timer.init(mode=Timer.PERIODIC, period=alarm_frequency*1000, callback=lambda t:beep()) # Beep every 30s
            alarm_timer_init = True
            sent_alert_message = pushover_alert(wlan)
                
            ## Block further change state for 1minute to stop constant pump cycle loops
            print("Sleeping monitoring for {}s".format(restart_delay))
            sleep(restart_delay)
    else:
        # Retry sending recovery messages if it failed previously
        if not current_float_state and not sent_alert_message:
            sent_alert_message = pushover_alert(wlan)
        if current_float_state and not sent_recovery_message:
            sent_recovery_message = pushover_recovery(wlan)
        sleep(1)