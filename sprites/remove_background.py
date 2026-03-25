import sys
from PIL import Image

def parse_color(arg):
    if arg.startswith("#") and len(arg) == 7:
        return tuple(int(arg[i:i+2], 16) for i in (1, 3, 5))
    elif "," in arg:
        return tuple(int(x) for x in arg.split(","))
    elif arg.lower() == "white":
        return (255, 255, 255)
    else:
        raise ValueError("Color must be #RRGGBB, 'white', or 'R,G,B'")

if len(sys.argv) < 2:
    print("Usage: python gif_make_transparent.py <filename.gif> [color]")
    sys.exit(1)

filename = sys.argv[1]
color = (255, 255, 255)  # default to white
if len(sys.argv) > 2:
    color = parse_color(sys.argv[2])

im = Image.open(filename)
frames = []
for frame in range(im.n_frames):
    im.seek(frame)
    rgba = im.convert("RGBA")
    datas = rgba.getdata()
    newdata = []
    for item in datas:
        if item[:3] == color:
            newdata.append((255, 255, 255, 0))
        else:
            newdata.append(item)
    rgba.putdata(newdata)
    frames.append(rgba)

frames[0].save(
    filename,
    save_all=True,
    append_images=frames[1:],
    loop=im.info.get("loop", 0),
    duration=im.info.get("duration", 40),
    disposal=2,
    transparency=0
)
print(f"Processed and overwrote {filename}")