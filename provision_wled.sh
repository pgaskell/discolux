#!/usr/bin/env bash
# provision_wled.sh — Configure a new WLED device via its default AP
#
# Usage:
#   1. Connect this machine's WiFi to the WLED AP (default: "WLED-AP", password: "wled1234")
#   2. Run this script
#   3. Enter the desired static IP, gateway, subnet, and mDNS hostname when prompted
#   4. The script will POST the modified config to the device, then it will reboot
#
# WLED AP default gateway: 4.3.2.1

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="$SCRIPT_DIR/govee_lightwall_config.json"
WLED_AP_IP="4.3.2.1"
TEMP_CONFIG="$(mktemp /tmp/wled_provision_XXXXXX.json)"
trap 'rm -f "$TEMP_CONFIG"' EXIT

# ── Helpers ───────────────────────────────────────────────────────────────────

die() { echo "ERROR: $*" >&2; exit 1; }

validate_ip() {
    local ip="$1"
    local re='^([0-9]{1,3}\.){3}[0-9]{1,3}$'
    [[ $ip =~ $re ]] || die "'$ip' is not a valid IPv4 address"
    IFS='.' read -r -a octets <<< "$ip"
    for o in "${octets[@]}"; do
        (( o >= 0 && o <= 255 )) || die "Octet $o out of range in '$ip'"
    done
}

ip_to_array() {
    # Converts "10.0.0.3" → [10,0,0,3]
    IFS='.' read -r a b c d <<< "$1"
    echo "[$a,$b,$c,$d]"
}

# ── Preflight ─────────────────────────────────────────────────────────────────

[[ -f "$CONFIG_FILE" ]] || die "Config file not found: $CONFIG_FILE"
command -v python3 >/dev/null || die "python3 is required"
command -v curl    >/dev/null || die "curl is required"

echo "Checking connectivity to WLED AP at $WLED_AP_IP ..."
curl --silent --max-time 5 "http://$WLED_AP_IP/json/info" >/dev/null \
    || die "Cannot reach $WLED_AP_IP — are you connected to the WLED-AP WiFi network?"

echo "Connected to WLED device."
echo

# ── Prompt for new network settings ──────────────────────────────────────────

read -rp "New static IP for this device  [e.g. 10.0.0.3]: " NEW_IP
validate_ip "$NEW_IP"

read -rp "Gateway IP                      [default: 10.0.0.1]: " NEW_GW
NEW_GW="${NEW_GW:-10.0.0.1}"
validate_ip "$NEW_GW"

read -rp "Subnet mask                     [default: 255.255.255.0]: " NEW_SN
NEW_SN="${NEW_SN:-255.255.255.0}"
validate_ip "$NEW_SN"

read -rp "mDNS hostname (no .local)       [default: wled]: " NEW_MDNS
NEW_MDNS="${NEW_MDNS:-wled}"

read -rp "Device friendly name            [default: WLED]: " NEW_NAME
NEW_NAME="${NEW_NAME:-WLED}"

echo
echo "Will configure:"
echo "  IP       : $NEW_IP"
echo "  Gateway  : $NEW_GW"
echo "  Subnet   : $NEW_SN"
echo "  mDNS     : $NEW_MDNS.local"
echo "  Name     : $NEW_NAME"
echo
read -rp "Proceed? [y/N] " CONFIRM
[[ "${CONFIRM,,}" == "y" ]] || { echo "Aborted."; exit 0; }

# ── Build modified config ─────────────────────────────────────────────────────

IP_ARR=$(ip_to_array "$NEW_IP")
GW_ARR=$(ip_to_array "$NEW_GW")
SN_ARR=$(ip_to_array "$NEW_SN")

python3 - "$CONFIG_FILE" "$TEMP_CONFIG" \
        "$IP_ARR" "$GW_ARR" "$SN_ARR" "$NEW_MDNS" "$NEW_NAME" <<'PYEOF'
import json, sys

src, dst, ip_arr, gw_arr, sn_arr, mdns, name = sys.argv[1:]

def parse_arr(s):
    return json.loads(s)  # e.g. "[10,0,0,3]"

with open(src) as f:
    cfg = json.load(f)

# Network interface (first entry in nw.ins)
nw_ins = cfg["nw"]["ins"][0]
nw_ins["ip"] = parse_arr(ip_arr)
nw_ins["gw"] = parse_arr(gw_arr)
nw_ins["sn"] = parse_arr(sn_arr)

# Identity
cfg["id"]["mdns"] = mdns
cfg["id"]["name"] = name

with open(dst, "w") as f:
    json.dump(cfg, f)

print("Config patch applied.")
PYEOF

# ── Push config to device ─────────────────────────────────────────────────────

echo
echo "Posting config to http://$WLED_AP_IP/json/cfg ..."
HTTP_CODE=$(curl --silent --output /dev/null --write-out "%{http_code}" \
    --max-time 15 \
    -X POST "http://$WLED_AP_IP/json/cfg" \
    -H "Content-Type: application/json" \
    -d @"$TEMP_CONFIG")

if [[ "$HTTP_CODE" == "200" ]]; then
    echo "Success (HTTP 200). The device will reboot and come up at $NEW_IP."
    echo
    echo "Next steps:"
    echo "  1. Disconnect from the WLED-AP and reconnect to your main network"
    echo "  2. Plug the device into ethernet"
    echo "  3. Test:  curl http://$NEW_IP/json/info"
else
    die "Unexpected HTTP response: $HTTP_CODE — config may not have been applied"
fi
