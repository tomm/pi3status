#!/usr/bin/python3
#
# A status bar app for the i3 window manager
#
import os
import json
import time
import re
import signal
import _thread

INTERVAL_SECONDS = 2.0

def blink(toggle=False):
    blink.on = not blink.on
    return blink.on
blink.on = True

def cpu_usage():
    while True:
        # 2 1 means: collect cpu usage over 2 seconds, taking 1 reading (and then exiting)
        idle_percent = float(list(filter(
            lambda l: l.startswith('Average:'),
            os.popen("mpstat 2 1").read().split("\n")
        ))[0].split()[-1])
        
        cpu_usage.percent = int(round(100.0-idle_percent))
        time.sleep(1)
cpu_usage.percent = 0
_thread.start_new_thread(cpu_usage, ())

ping_hosts = []
def _ping():
    while True:
        for host in ping_hosts:
            raw = os.popen('ping -c 1 {0}'.format(host)).read()
            latency = re.search(
                r'time=(\d+\.?\d* \w+)', raw
            )
            if latency is None:
                _ping.latency[host] = '∞'
            else:
                _ping.latency[host] = latency.groups()[0]
        time.sleep(30)
_ping.latency = {}
_thread.start_new_thread(_ping, ())

def backlight(label: str):
    raw = os.popen('xbacklight').read()
    percent = int(round(float(raw)))
    text = '{0}{1}%'.format(label, percent)
    return {
        "color": "#ffffff",
        "short_text": text,
        "full_text": text,
        "markup": "none",
        "separator": True
    }


def pa_volume(label: str, kind):  # kind: 'sources' | 'sinks'
    raw = os.popen('pactl list {0}'.format(kind)).read().split('\n')
    vol = re.search(
        r'(\d+)%',
        list(filter(lambda l: re.match(r'^Volume', l.strip()), raw))[0]
    ).groups()[0]
    muted = len(list(filter(lambda l: re.match(r'^Mute: yes$', l.strip()), raw)))

    text = '{0} {1}'.format(label, 'muted' if muted else vol+'%')
    return {
        "color": "#ffffff",
        "short_text": text,
        "full_text": text,
        "markup": "none",
        "separator": True
    }

def pa_mic_volume(label: str):
    return pa_volume(label, 'sources')

def pa_out_volume(label: str):
    return pa_volume(label, 'sinks')

def alsa_volume(format: str, control: str):
    raw = os.popen('amixer -c0 get {0}'.format(control)).read()
    volume = re.search(
        r'\[(\d+)%\]', raw
    ).groups()[0]
    maybe_muted = re.search(
        r'\[(on|off)\]', raw
    )
    muted = True if maybe_muted and maybe_muted.groups()[0] == 'off' else False

    text = format.format("{0}%".format(volume) if not muted else 'muted')
    return {
        "color": "#ffffff",
        "short_text": text,
        "full_text": text,
        "markup": "none",
        "separator": True
    }

def battery():
    RED_MINS = 30
    ORANGE_MINS = 60
    #Battery 0: Discharging, 19%, 01:08:26 remaining
    raw = os.popen('acpi -b').read()
    state, percent = re.search(
        r'(\w+), (\d+)%', raw
    ).groups()
    duration = re.search(
        r'(\d\d):(\d\d):(\d\d)', raw
    )

    percent = int(percent)
    if duration:
        hours, mins, secs = map(int, duration.groups())
        mins_left = hours*60 + mins
        if state == 'Discharging':
            color = "#000000" if mins_left <= RED_MINS and blink() else "#ff0000" if mins_left <= RED_MINS else "#ffaa00" if mins_left <= ORANGE_MINS else "#00ff00"
            background = "#ff0000" if mins_left <= RED_MINS and not blink() else "#000000"
            text = "🔋{0}%, {1}{2}m on bat".format(percent, "{0}h".format(hours) if hours else '', mins)
        else:
            color = "#00ff00"
            background = "#000000"
            text = "🔋{0}%, {1}{2}m to full".format(percent, "{0}h".format(hours) if hours else '', mins)
    elif state == 'Full':
        color = "#00ff00"
        background = "#000000"
        text = "🔋{0}% {1}".format(percent, state)
    else:
        color = "#00ff00"
        background = "#000000"
        text = "🔋{0}% {1}".format(percent, state)
    return {
        "color": color,
        "background": background,
        "short_text": text,
        "full_text": text,
        "markup": "none",
        "separator": True
    }

def net_latency(host, label=''):
    if host not in ping_hosts:
        ping_hosts.append(host)
    latency = _ping.latency[host] if host in _ping.latency else '?'
    text = "{0}{1}".format(label, latency)
    return {
        "color": "#ffffff",
        "short_text": text,
        "full_text": text,
        "markup": "none",
        "separator": True
    }

def cpu():
    percent = cpu_usage.percent
    text = "CPU {0}%".format(percent)
    return {
        "color": "#ffffff" if percent < 90 else '#ff0000',
        "short_text": text,
        "full_text": text,
        "markup": "none",
        "separator": True
    }

def vpn():
    vpn_up = os.path.isdir("/proc/sys/net/ipv4/conf/tun0")
    text = "VPN {0}".format("ON" if vpn_up else "OFF")
    return {
        "color": "#00ff00" if vpn_up else "#000000",
        "background": "#000000" if vpn_up else "#ff0000",
        "short_text": text,
        "full_text": text,
        "markup": "none",
        "separator": True
    }

def clock(fmt: str):
    return {
        "color": "#ffffff",
        "short_text": time.strftime(fmt),
        "full_text": time.strftime(fmt),
        "markup": "none",
        "separator": True
    }

def free_memory(label: str):
    lines = open('/proc/meminfo').read().split('\n')
    total = int([i.split()[1] for i in lines if re.search(r'^MemTotal:', i)][0])
    avail = int([i.split()[1] for i in lines if re.search(r'^MemAvailable:', i)][0])
    percent = 100-100*avail//total

    text = "{0}{1}%".format(label or '', percent)
    return {
        "color": "#ffffff" if percent < 80 else '#ff0000',
        "short_text": text,
        "full_text": text,
        "markup": "none",
        "separator": True
    }


def _get_up_dn_net_transferred(device: str):
    raw = list(filter(lambda line: line.split()[0:1]==[device+':'], open('/proc/net/dev').read().split('\n')))[0].split()
    down_bytes = int(raw[1])
    up_bytes = int(raw[9])
    return up_bytes, down_bytes, time.time()

def net(device: str, label: str=None):
    prev_tx = net.tx[device] if device in net.tx else _get_up_dn_net_transferred(device) 
    now_tx = _get_up_dn_net_transferred(device)
    elapsed = now_tx[2] - prev_tx[2]
    text = "{0}↓{1:,.0f} ↑{2:,.0f} KiB/s".format(
        label + ' ' if label else '',
        (now_tx[1] - prev_tx[1]) / (1024*elapsed),
        (now_tx[0] - prev_tx[0]) / (1024*elapsed)
    )
    net.tx[device] = now_tx

    return {
        "color": "#ffffff",
        "short_text": text,
        "full_text": text,
        "markup": "none",
        "separator": True
    }
net.tx = {}

def statusbar(*widgets):
    def safe_run(l):
        try:
            return l()
        except Exception as e:
            return {
                "color": "#ff0000",
                "full_text": "Error: {0}".format(e),
                "markup": "none",
                #"separator_block_width": 15,
                "separator": True
            }

    def update():
        print(
            json.dumps(
                list(map(safe_run, widgets))
            ),
            flush=True
        )
        print (',', end='')

    def handler(signum, frame):
        update()

    signal.signal(signal.SIGRTMIN+2, handler)

    print('{"version":1}')
    print('[')

    while True:
        update()
        time.sleep(INTERVAL_SECONDS)
        blink(toggle=True)

statusbar(
    lambda: backlight("🌞 "),
    lambda: net('wlp3s0', ''),
    lambda: net_latency('1.1.1.1', '🌏 '),
    lambda: alsa_volume('♪ {0}', 'Master'),
    lambda: alsa_volume('🎤 {0}', 'Mic'),
    lambda: pa_out_volume('♪PA'),
    #lambda: pa_mic_volume('🎤'),
    lambda: cpu(),
    lambda: free_memory('RAM '),
    lambda: vpn(),
    lambda: battery(),
    lambda: clock('%d %b %H:%M'),
)
