readme = """
Unpack a J2A file

Will unpack a J2A file into a series of sprite sheet images, one per animset.

Existing files will be overwritten.
"""

import argparse
import pathlib
import yaml
import os

from j2a import J2A
from PIL import Image

cli = argparse.ArgumentParser(description=readme, prog="J2A Sheeter", formatter_class=argparse.RawDescriptionHelpFormatter)
cli.add_argument("--palettefile", "-p", default="Diamondus_2.pal", help="Palette file to use")
cli.add_argument("j2afile", help="The J2A file to extract")
cli.add_argument("--folder", "-f", default="?",
                 help="Where to extract the animation data. Defaults to current working directory.")
cli.add_argument('--melk', '-m', action='store_true')
cli.add_argument("--borderColor", "-b", default="255")
cli.add_argument("--unusedColor", "-u", default="0")
cli.add_argument("--style", "-s", default="1")
args = cli.parse_args()

# check if all files we need exist and can be opened properly
if args.folder == "?":
    args.folder = "-".join(args.j2afile.rsplit(".", 1))
destination_folder = pathlib.Path(args.folder)
if not destination_folder.exists():
    os.makedirs(destination_folder)
destination_file_stem = os.path.basename(args.j2afile).rsplit(".", 1)[0]

source_file = pathlib.Path(args.j2afile)
palette_file = pathlib.Path(args.palettefile)

borderColor = int(args.borderColor)
unusedColor = int(args.unusedColor)
outputStyle = int(args.style)
#0: save each row as a separate image
#1: put all rows in the same image, with each row deciding its own frame width/height (default)
#2: put all rows in the same image, with every frame in every row having the same width/height
borderSize = 2

maxTop = 0
maxBottom = 0
maxLeft = 0
maxRight = 0

for check_file in (source_file, palette_file):
    if not check_file.exists():
        print("File '%s' does not exist." % str(check_file))
        exit(1)

try:
    j2afile = J2A(str(source_file), palette=str(palette_file)).read(args.melk)
except Exception:
    print("Could not open J2A file %s. Is it a valid J2A file?" % source_file.name)
    exit(1)

j2afile.get_palette()

# loop through all animations and unpack their frames
for set_index, set in enumerate(j2afile.sets):
    print("Sheeting set %i..." % set_index)
    filename = pathlib.Path(destination_folder, destination_file_stem + "-" + str(set_index) + ".png")

    if args.melk:
        noalphas = list(set._palette)
        del noalphas[3::4]
        j2afile.palettesequence = noalphas

    if outputStyle == 2: #get frame size (including hotspot) for every frame in whole animset
        maxTop = 0
        maxBottom = 0
        maxLeft = 0
        maxRight = 0
        for frame in [x for xs in set.animations for x in xs.frames]:
            maxTop = max(maxTop, -frame.origin[1])
            maxBottom = max(maxBottom, frame.shape[1] + frame.origin[1])
            maxLeft = max(maxLeft, -frame.origin[0])
            maxRight = max(maxRight, frame.shape[0] + frame.origin[0])
        
    sheetRows = []
    for animation_index, animation in enumerate(set.animations):
        print("Unpacking animation %i..." % animation_index)
        if outputStyle != 2: #get frame size (including hotspot) for every frame in this animation
            maxTop = 0
            maxBottom = 0
            maxLeft = 0
            maxRight = 0

            for frame in animation.frames:
                maxTop = max(maxTop, -frame.origin[1])
                maxBottom = max(maxBottom, frame.shape[1] + frame.origin[1])
                maxLeft = max(maxLeft, -frame.origin[0])
                maxRight = max(maxRight, frame.shape[0] + frame.origin[0])

        frameWidth = maxLeft + maxRight
        frameHeight = maxTop + maxBottom
        frameWB = frameWidth + borderSize
        frameHB = frameHeight + borderSize
        sheetRow = Image.new("P", (frameWB * len(animation.frames) - borderSize, frameHeight), borderColor)
        sheetRow.putpalette(j2afile.palettesequence)
        for frame_index, frame in enumerate(animation.frames):
            xOrg = frameWB * frame_index
            if borderColor != unusedColor:
                sheetRow.paste(unusedColor, (xOrg, 0, xOrg + frameWidth, frameHeight))
            sheetRow.paste(j2afile.render_paletted_pixelmap(frame), (xOrg + maxLeft + frame.origin[0], maxTop + frame.origin[1]))
        if outputStyle == 0:
            sheetRow.save(pathlib.Path(destination_folder, destination_file_stem + "-" + str(set_index) + "-" + str(animation_index) + ".png"))
        else:
            sheetRows.append(sheetRow)

    if outputStyle != 0 and len(sheetRows) != 0:
        result = Image.new("P", (max(row.width for row in sheetRows), sum(row.height for row in sheetRows) + (borderSize - 1) * len(sheetRows)), borderColor)
        result.putpalette(j2afile.palettesequence)
        yOrg = 0
        for row in sheetRows:
            result.paste(row, (0,yOrg))
            yOrg += row.height + borderSize
        result.save(pathlib.Path(destination_folder, destination_file_stem + "-" + str(set_index) + ".png"))


print("Done!")
