import board
import digitalio
import rotaryio
import usb_midi
import time
import adafruit_midi
from adafruit_midi.note_on import NoteOn
from adafruit_midi.note_off import NoteOff
from adafruit_midi.control_change import ControlChange

# ---------------- MIDI ----------------
midi = adafruit_midi.MIDI(midi_out=usb_midi.ports, out_channel=0)

# ---------------- MX MATRIX PINS (5x5) ----------------
# 5 Rows and 5 Columns for 25 keys
ROWS = [board.GP2, board.GP3, board.GP4, board.GP5, board.GP6]
COLS = [board.GP7, board.GP8, board.GP9, board.GP10, board.GP11]

row_pins = []
for r in ROWS:
    pin = digitalio.DigitalInOut(r)
    pin.direction = digitalio.Direction.OUTPUT
    pin.value = True
    row_pins.append(pin)

col_pins = []
for c in COLS:
    pin = digitalio.DigitalInOut(c)
    pin.direction = digitalio.Direction.INPUT
    pin.pull = digitalio.Pull.UP
    col_pins.append(pin)

# State tracking for 25 keys
pressed = [[False]*5 for _ in range(5)]

# ---------------- NOTE MAP (C2 to C4) ----------------
NOTES = [i for i in range(36, 61)]

# ---------------- ENCODERS & SWITCHES ----------------
encs = [
    rotaryio.IncrementalEncoder(board.GP12, board.GP13),
    rotaryio.IncrementalEncoder(board.GP14, board.GP15),
    rotaryio.IncrementalEncoder(board.GP16, board.GP17)
]

# Encoder internal switches
sw_pins = [board.GP18, board.GP19, board.GP20]
switches = []
for p in sw_pins:
    sw = digitalio.DigitalInOut(p)
    sw.direction = digitalio.Direction.INPUT
    sw.pull = digitalio.Pull.UP
    switches.append(sw)

last_enc_pos = [e.position for e in encs]
last_sw_state = [True, True, True]

# ---------------- SCANNING FUNCTIONS ----------------

def scan_matrix():
    for r in range(5):
        row_pins[r].value = False  # Set current row to Ground
        for c in range(5):
            # Check if MX Switch is closed
            if not col_pins[c].value:
                if not pressed[r][c]:
                    note = NOTES[r * 5 + c]
                    midi.send(NoteOn(note, 100))
                    pressed[r][c] = True
            else:
                if pressed[r][c]:
                    note = NOTES[r * 5 + c]
                    midi.send(NoteOff(note, 0))
                    pressed[r][c] = False
        row_pins[r].value = True  # Reset row to High

def read_reaper_controls():
    global last_enc_pos, last_sw_state
    
    for i in range(3):
        # 1. Encoders: Relative Mode (Reaper 'Relative 1')
        curr_pos = encs[i].position
        if curr_pos != last_enc_pos[i]:
            # Send 65 for turn-right, 63 for turn-left
            val = 65 if curr_pos > last_enc_pos[i] else 63
            midi.send(ControlChange(20 + i, val))
            last_enc_pos[i] = curr_pos

        # 2. Switches: Momentary CC
        curr_sw = switches[i].value
        if curr_sw != last_sw_state[i]:
            val = 127 if not curr_sw else 0
            midi.send(ControlChange(30 + i, val))
            last_sw_state[i] = curr_sw

# ---------------- MAIN LOOP ----------------
while True:
    scan_matrix()
    read_reaper_controls()
    # A tiny sleep helps debounce physical MX switch contacts
    time.sleep(0.005)
