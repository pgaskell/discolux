#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════
# install.sh – Deploy DiscoLux on a fresh Raspberry Pi
#
# Target: Raspberry Pi 5 (or 4) running Raspberry Pi OS Bookworm / Trixie
#         with labwc Wayland compositor and LightDM.
#
# What this script does:
#   1. Installs system packages (SDL2, PortAudio, Plymouth, fonts, etc.)
#   2. Installs Python dependencies via pip
#   3. Configures LightDM autologin
#   4. Configures labwc for kiosk mode (no desktop, no panel)
#   5. Installs the Plymouth boot splash theme
#   6. Configures boot cmdline & config.txt for clean silent boot
#   7. Makes the launcher script executable
#   8. Rebuilds initramfs with the new Plymouth theme
#
# Usage:
#   cd /home/rpi/discolux_ctrl
#   chmod +x install.sh
#   sudo ./install.sh
#
# After installation, reboot to see the splash screen + auto-launch.
# ═══════════════════════════════════════════════════════════════════════════

set -euo pipefail

# ── Must run as root ────────────────────────────────────────────────────
if [[ $EUID -ne 0 ]]; then
    echo "ERROR: This script must be run with sudo."
    echo "  sudo ./install.sh"
    exit 1
fi

# ── Resolve paths ───────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# The user who will autologin and run the app
TARGET_USER="${SUDO_USER:-rpi}"
TARGET_HOME="$(eval echo "~${TARGET_USER}")"

echo "═══════════════════════════════════════════════════════════════"
echo "  DiscoLux Installer"
echo "═══════════════════════════════════════════════════════════════"
echo "  App directory : ${SCRIPT_DIR}"
echo "  Target user   : ${TARGET_USER}"
echo "  Home directory: ${TARGET_HOME}"
echo ""

# ═══════════════════════════════════════════════════════════════════════════
# 1. System packages
# ═══════════════════════════════════════════════════════════════════════════
echo "[1/8] Installing system packages..."
apt-get update -qq
apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv \
    libsdl2-2.0-0 libsdl2-image-2.0-0 libsdl2-mixer-2.0-0 libsdl2-ttf-2.0-0 \
    libportaudio2 \
    plymouth plymouth-themes plymouth-label \
    lightdm \
    labwc \
    pipewire pipewire-pulse pipewire-bin \
    fonts-nunito-sans \
    git

echo "  ✓ System packages installed"

# ═══════════════════════════════════════════════════════════════════════════
# 2. Python dependencies
# ═══════════════════════════════════════════════════════════════════════════
echo "[2/8] Installing Python dependencies..."
sudo -u "${TARGET_USER}" pip3 install --break-system-packages --user \
    pygame numpy sounddevice Pillow PyYAML scipy

echo "  ✓ Python packages installed"

# ═══════════════════════════════════════════════════════════════════════════
# 3. LightDM autologin
# ═══════════════════════════════════════════════════════════════════════════
echo "[3/8] Configuring LightDM autologin..."
LIGHTDM_CONF="/etc/lightdm/lightdm.conf"

# Ensure [Seat:*] section exists and has autologin settings
if grep -q "^autologin-user=" "$LIGHTDM_CONF" 2>/dev/null; then
    sed -i "s/^autologin-user=.*/autologin-user=${TARGET_USER}/" "$LIGHTDM_CONF"
else
    # Add under [Seat:*] section
    if grep -q '^\[Seat:\*\]' "$LIGHTDM_CONF" 2>/dev/null; then
        sed -i "/^\[Seat:\*\]/a autologin-user=${TARGET_USER}" "$LIGHTDM_CONF"
    else
        echo -e "\n[Seat:*]\nautologin-user=${TARGET_USER}" >> "$LIGHTDM_CONF"
    fi
fi

if grep -q "^autologin-session=" "$LIGHTDM_CONF" 2>/dev/null; then
    sed -i "s/^autologin-session=.*/autologin-session=rpd-labwc/" "$LIGHTDM_CONF"
else
    sed -i "/^autologin-user=/a autologin-session=rpd-labwc" "$LIGHTDM_CONF"
fi

echo "  ✓ LightDM set to autologin as ${TARGET_USER} with labwc"

# ═══════════════════════════════════════════════════════════════════════════
# 4. labwc kiosk config (autostart + dark desktop)
# ═══════════════════════════════════════════════════════════════════════════
echo "[4/8] Configuring labwc kiosk mode..."

LABWC_DIR="${TARGET_HOME}/.config/labwc"
mkdir -p "$LABWC_DIR"

# Autostart – only launch DiscoLux, no desktop or panel
cat > "${LABWC_DIR}/autostart" << EOF
# DiscoLux kiosk mode – no desktop, no panel, just the app

# Launch DiscoLux immediately
${SCRIPT_DIR}/start_discolux.sh &
EOF

# rc.xml – touch mapping (adjust device name if needed)
if [[ ! -f "${LABWC_DIR}/rc.xml" ]]; then
    cat > "${LABWC_DIR}/rc.xml" << 'EOF'
<?xml version="1.0"?>
<openbox_config xmlns="http://openbox.org/3.4/rc">
        <touch deviceName="10-0038 generic ft5x06 (00)" mapToOutput="DSI-1" mouseEmulation="yes"/>
</openbox_config>
EOF
fi

# environment
if [[ ! -f "${LABWC_DIR}/environment" ]]; then
    cat > "${LABWC_DIR}/environment" << 'EOF'
XKB_DEFAULT_MODEL=pc105
XKB_DEFAULT_LAYOUT=us
XKB_DEFAULT_VARIANT=
XKB_DEFAULT_OPTIONS=
EOF
fi

# Dark desktop background (in case pcmanfm ever runs)
PCMANFM_DIR="${TARGET_HOME}/.config/pcmanfm/default"
mkdir -p "$PCMANFM_DIR"
cat > "${PCMANFM_DIR}/desktop-items-DSI-1.conf" << 'EOF'
[*]
desktop_bg=#0a0a0f
desktop_shadow=#0a0a0f
desktop_fg=#0a0a0f
desktop_font=Nunito Sans Light 12
wallpaper=
wallpaper_mode=color
show_documents=0
show_trash=0
show_mounts=0
EOF

chown -R "${TARGET_USER}:${TARGET_USER}" "${TARGET_HOME}/.config"

echo "  ✓ labwc configured for kiosk mode"

# ═══════════════════════════════════════════════════════════════════════════
# 5. Plymouth boot splash theme
# ═══════════════════════════════════════════════════════════════════════════
echo "[5/8] Installing Plymouth splash theme..."

THEME_DIR="/usr/share/plymouth/themes/discolux"
mkdir -p "$THEME_DIR"

# Generate splash.png (800×480) with Python/Pillow
sudo -u "${TARGET_USER}" python3 << 'PYEOF'
from PIL import Image, ImageDraw, ImageFont
import colorsys, os

W, H = 800, 480
img = Image.new("RGB", (W, H), (10, 10, 15))
draw = ImageDraw.Draw(img)

# Rainbow "DiscoLux" title
title = "DiscoLux"
try:
    title_font = ImageFont.truetype("/usr/share/fonts/truetype/nunito/NunitoSans_7pt-Light.ttf", 72)
except:
    title_font = ImageFont.load_default()
bbox = draw.textbbox((0, 0), title, font=title_font)
tw = bbox[2] - bbox[0]
tx = (W - tw) // 2
ty = 140
for i, ch in enumerate(title):
    r, g, b = [int(c * 255) for c in colorsys.hsv_to_rgb(i / len(title), 0.8, 1.0)]
    cw = draw.textbbox((0, 0), ch, font=title_font)[2]
    draw.text((tx, ty), ch, fill=(r, g, b), font=title_font)
    tx += cw

# Subtitle
try:
    sub_font = ImageFont.truetype("/usr/share/fonts/truetype/nunito/NunitoSans_7pt-Light.ttf", 22)
except:
    sub_font = ImageFont.load_default()
sub = "LED Wall Controller"
sb = draw.textbbox((0, 0), sub, font=sub_font)
draw.text(((W - sb[2]) // 2, 230), sub, fill=(120, 120, 140), font=sub_font)

# "by DJ Pjotr"
byline = "by DJ Pjotr"
bb = draw.textbbox((0, 0), byline, font=sub_font)
draw.text(((W - bb[2]) // 2, 380), byline, fill=(80, 80, 100), font=sub_font)

img.save("/tmp/_discolux_splash.png")
PYEOF

cp /tmp/_discolux_splash.png "${THEME_DIR}/splash.png"
rm -f /tmp/_discolux_splash.png

# Generate bar_fill.png (296×4 solid blue bar)
sudo -u "${TARGET_USER}" python3 << 'PYEOF'
from PIL import Image
img = Image.new("RGB", (296, 4), (80, 80, 180))
img.save("/tmp/_discolux_bar.png")
PYEOF

cp /tmp/_discolux_bar.png "${THEME_DIR}/bar_fill.png"
rm -f /tmp/_discolux_bar.png

# Theme descriptor
cat > "${THEME_DIR}/discolux.plymouth" << 'EOF'
[Plymouth Theme]
Name=DiscoLux
Description=DiscoLux LED Wall Controller splash
ModuleName=script

[script]
ImageDir=/usr/share/plymouth/themes/discolux
ScriptFile=/usr/share/plymouth/themes/discolux/discolux.script
EOF

# Plymouth script
cat > "${THEME_DIR}/discolux.script" << 'EOF'
/*  DiscoLux Plymouth splash – animated progress bar  */

Window.SetBackgroundTopColor(0.04, 0.04, 0.06);
Window.SetBackgroundBottomColor(0.04, 0.04, 0.06);

/* Centre the splash image */
logo = Image("splash.png");
logo_sprite = Sprite(logo);
logo_x = Window.GetX() + (Window.GetWidth()  - logo.GetWidth())  / 2;
logo_y = Window.GetY() + (Window.GetHeight() - logo.GetHeight()) / 2;
logo_sprite.SetX(logo_x);
logo_sprite.SetY(logo_y);
logo_sprite.SetZ(10);

/* Progress bar – use pre-rendered bar_fill.png, position absolutely
   relative to screen centre.  Bar sits at image-relative y=280,
   image is 480px tall centred on screen. */
bar_full = Image("bar_fill.png");
bar_max_w = bar_full.GetWidth();
bar_h     = bar_full.GetHeight();
bar_x = Window.GetX() + (Window.GetWidth()  - bar_max_w) / 2;
bar_y = logo_y + 280;

bar_sprite = Sprite();
bar_sprite.SetPosition(bar_x, bar_y, 20);
bar_sprite.SetImage(bar_full.Scale(2, bar_h));

fun boot_progress_cb(duration, progress) {
    fill_w = Math.Int(bar_max_w * progress);
    if (fill_w < 2) fill_w = 2;
    if (fill_w > bar_max_w) fill_w = bar_max_w;
    bar_sprite.SetImage(bar_full.Scale(fill_w, bar_h));
}
Plymouth.SetBootProgressFunction(boot_progress_cb);

/* Suppress all prompts for a clean boot */
fun message_callback(text)  { }
fun display_password_callback(prompt, bullets) { }
fun display_question_callback(prompt, entry) { }
fun display_normal()  { }

Plymouth.SetMessageFunction(message_callback);
Plymouth.SetDisplayPasswordFunction(display_password_callback);
Plymouth.SetDisplayQuestionFunction(display_question_callback);
Plymouth.SetDisplayNormalFunction(display_normal);
EOF

# Set as default Plymouth theme
plymouth-set-default-theme -R discolux 2>/dev/null || true

echo "  ✓ Plymouth theme installed"

# ═══════════════════════════════════════════════════════════════════════════
# 6. Boot configuration (silent boot, no Pi branding)
# ═══════════════════════════════════════════════════════════════════════════
echo "[6/8] Configuring silent boot..."

CMDLINE="/boot/firmware/cmdline.txt"
if [[ -f "$CMDLINE" ]]; then
    # Read current cmdline
    CURRENT=$(cat "$CMDLINE")

    # Add flags if missing
    for flag in "quiet" "splash" "vt.global_cursor_default=0" "logo.nologo" "loglevel=0"; do
        if ! echo "$CURRENT" | grep -q "$flag"; then
            CURRENT="$CURRENT $flag"
        fi
    done

    # Move console to tty3 (hide boot messages from main display)
    CURRENT=$(echo "$CURRENT" | sed 's/console=tty[0-9]*/console=tty3/g')

    # Add plymouth serial console ignore if missing
    if ! echo "$CURRENT" | grep -q "plymouth.ignore-serial-consoles"; then
        CURRENT="$CURRENT plymouth.ignore-serial-consoles"
    fi

    echo "$CURRENT" > "$CMDLINE"
    echo "  ✓ cmdline.txt updated"
fi

CONFIG_TXT="/boot/firmware/config.txt"
if [[ -f "$CONFIG_TXT" ]]; then
    # Disable GPU rainbow splash
    if ! grep -q "^disable_splash=1" "$CONFIG_TXT"; then
        echo "disable_splash=1" >> "$CONFIG_TXT"
    fi
    echo "  ✓ config.txt updated"
fi

# ═══════════════════════════════════════════════════════════════════════════
# 7. Make launcher executable
# ═══════════════════════════════════════════════════════════════════════════
echo "[7/8] Setting permissions..."

chmod +x "${SCRIPT_DIR}/start_discolux.sh"
chmod +x "${SCRIPT_DIR}/launch_remote.py" 2>/dev/null || true
chmod +x "${SCRIPT_DIR}/discolux.py"

# Ensure the patches directory exists
mkdir -p "${SCRIPT_DIR}/patches"
chown -R "${TARGET_USER}:${TARGET_USER}" "${SCRIPT_DIR}"

echo "  ✓ Permissions set"

# ═══════════════════════════════════════════════════════════════════════════
# 8. Rebuild initramfs (includes Plymouth theme)
# ═══════════════════════════════════════════════════════════════════════════
echo "[8/8] Rebuilding initramfs (this may take a minute)..."
update-initramfs -u -k all 2>&1 | tail -3

echo "  ✓ initramfs rebuilt"

# ═══════════════════════════════════════════════════════════════════════════
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  ✅ DiscoLux installation complete!"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "  What happens on reboot:"
echo "    1. Custom splash screen with progress bar"
echo "    2. Auto-login as '${TARGET_USER}'"
echo "    3. labwc starts (no desktop icons, no taskbar)"
echo "    4. DiscoLux launches fullscreen on the display"
echo ""
echo "  To reboot now:  sudo reboot"
echo ""
echo "  To configure WLED IP, edit: ${SCRIPT_DIR}/discolux_settings.yaml"
echo "    wled_host: <IP address of your WLED controller>"
echo ""
echo "  To launch manually from SSH:"
echo "    cd ${SCRIPT_DIR} && python3 launch_remote.py"
echo ""
