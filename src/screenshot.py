"""Export the map and canvas overlays to PNG without desktop capture."""
import io
import math
import subprocess
from functools import lru_cache
from PIL import Image, ImageDraw, ImageFont
from map_renderer import map_ppm


@lru_cache(maxsize=32)
def font(size):
    try:
        path = subprocess.check_output(['fc-match', '-f', '%{file}', 'sans:lang=zh'],
                                       text=True, timeout=2).strip()
        return ImageFont.truetype(path, size)
    except (OSError, subprocess.SubprocessError):
        try:
            return ImageFont.truetype('DejaVuSans.ttf', size)
        except OSError:
            return ImageFont.load_default(size=size)


def capture_map(app):
    side = app.render_side
    width = max(640, side + 40)
    # Wrap by rendered width, including city names without spaces.
    measure = ImageDraw.Draw(Image.new('RGB', (1, 1)))
    def wrap(text, size):
        lines, line = [], ''
        for char in text:
            if char == '\n' or measure.textlength(line+char, font=font(size)) > width-40:
                lines.append(line)
                line = '' if char == '\n' else char
            else:
                line += char
        return lines+[line]
    header = [('Make A Fire In Forest', 26), (app.city_text.get(), 18),
              (app.weather_text.get(), 15)]
    header_lines = [(line, size) for text, size in header for line in wrap(text, size)]
    top = 20 + sum(size+10 for _, size in header_lines)
    footer = [f'Map: {app.coverage.side_km} × {app.coverage.side_km} km · Step {app.forest.steps}',
              app.burn_stats.get()]
    footer_lines = [line for text in footer for line in wrap(text, 15)]
    image = Image.new('RGB', (width, top+side+30+len(footer_lines)*25), '#111d19')
    draw = ImageDraw.Draw(image)
    y = 15
    for line, size in header_lines:
        draw.text((20, y), line, font=font(size), fill='#e4eee5')
        y += size+10
    left = (width-side)//2
    terrain = Image.open(io.BytesIO(map_ppm(app.forest, side))).convert('RGB')
    image.paste(terrain, (left, top))
    ox, oy = app.offset
    canvas = app.canvas
    for item in canvas.find_all():
        if not set(canvas.gettags(item)) & {'overlay', 'precipitation'}:
            continue
        kind = canvas.type(item)
        coords = canvas.coords(item)
        coords = [v+(left-ox if i%2==0 else top-oy) for i,v in enumerate(coords)]
        fill = canvas.itemcget(item, 'fill') or None
        if kind in ('rectangle', 'oval'):
            outline = canvas.itemcget(item, 'outline') or None
            getattr(draw, 'rectangle' if kind=='rectangle' else 'ellipse')(
                coords, fill=fill, outline=outline, width=max(1, round(float(canvas.itemcget(item, 'width')))))
        elif kind == 'line':
            draw.line(coords, fill=fill, width=max(1, round(float(canvas.itemcget(item, 'width')))))
            if canvas.itemcget(item, 'arrow') == 'last':
                x0,y0,x1,y1 = coords
                length=math.hypot(x1-x0,y1-y0)
                if length:
                    ux,uy=(x1-x0)/length,(y1-y0)/length
                    a,b,c=map(float, canvas.itemcget(item, 'arrowshape').split())
                    draw.polygon([(x1,y1),(x1-b*ux+c*uy,y1-b*uy-c*ux),
                                  (x1-a*ux,y1-a*uy),(x1-b*ux-c*uy,y1-b*uy+c*ux)],fill=fill)
        elif kind == 'text':
            from tkinter.font import Font
            tkfont=Font(root=app.root, font=canvas.itemcget(item,'font'))
            size=tkfont.actual('size')
            size=round(size*app.root.winfo_fpixels('1i')/72) if size>0 else abs(size)
            anchor={'center':'mm','w':'lm','e':'rm','nw':'lt','n':'mt','ne':'rt',
                    's':'mb','sw':'lb','se':'rb'}[canvas.itemcget(item,'anchor')]
            draw.text(tuple(coords), canvas.itemcget(item,'text'),font=font(size),fill=fill,anchor=anchor)
    y=top+side+15
    for line in footer_lines:
        draw.text((20,y),line,font=font(15),fill='#f1bc72')
        y+=25
    return image
