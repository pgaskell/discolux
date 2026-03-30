#!/bin/bash
HOST=10.0.0.2
PORT=21324
LEDS=640
CH_PER_LED=4
PKT_LEDS=120  # safe for MTU

for ((start=0; start<LEDS; start+=PKT_LEDS)); do
  count=$(( LEDS - start < PKT_LEDS ? LEDS - start : PKT_LEDS ))
  (
    # Header: protocol, timeout, start index hi, lo
    printf '\x04\x02'
    printf '\\x%02x\\x%02x' $((start>>8)) $((start&0xFF))
    # Data: R,G,B,W for each LED in this packet
    for ((i=0; i<count; i++)); do
      printf '\xff\x00\x00\x00'
    done
  ) | socat - UDP:$HOST:$PORT
done