#!/usr/bin/env python3
"""PickoHoo reel generator v2 - JSON spec -> 1080x1920 30fps MP4 with music + SFX.

Usage:  python3 reel.py spec.json out.mp4
Preview frames only:  FRAMES="0:2.0,1:3.0" python3 reel.py spec.json out.mp4
Scene types: hook, pick, tip, quiz, reveal, cta  (see specs/*.json)
Rules baked in: product scenes always show "Ad" + feed-price note; never invent products/prices.
"""
import json, math, os, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 30
HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = "/usr/share/fonts/truetype/google-fonts/"
F_BOLD = FONT_DIR + "Poppins-Bold.ttf"
F_MED = FONT_DIR + "Poppins-Medium.ttf"

# Brand palette (from pickohoo.github.io)
G_TOP = (24, 74, 52)
G_BOT = (11, 38, 27)
AMBER = (242, 169, 59)
CREAM = (245, 243, 238)
WHITE = (255, 255, 255)
INK = (20, 33, 27)
MINT = (231, 242, 236)

_fonts = {}
def font(path, size):
    k = (path, int(size))
    if k not in _fonts:
        _fonts[k] = ImageFont.truetype(path, max(1, int(size)))
    return _fonts[k]

def clamp(t): return max(0.0, min(1.0, t))
def ease_out(t): t = clamp(t); return 1 - (1 - t) ** 3
def ease_back(t):
    t = clamp(t); c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2

# ---------------- background ----------------
def make_bg():
    y = np.linspace(0, 1, H)[:, None, None]
    arr = (np.array(G_TOP)[None, None] * (1 - y) + np.array(G_BOT)[None, None] * y) * np.ones((1, W, 1))
    img = Image.fromarray(arr.astype(np.uint8), "RGB").convert("RGBA")
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    g = ImageDraw.Draw(glow)
    g.ellipse((-350, 1250, 650, 2250), fill=(242, 169, 59, 55))
    g.ellipse((550, -250, 1500, 650), fill=(120, 200, 150, 45))
    img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(170)))
    rng = np.random.default_rng(3)
    flakes = [(rng.uniform(0, W), rng.uniform(0, H), rng.uniform(2, 6), rng.uniform(25, 70), rng.uniform(0, 6.28)) for _ in range(80)]
    return img, flakes

def snow(img, flakes, T):
    d = ImageDraw.Draw(img)
    for x, y, r, sp, ph in flakes:
        yy = (y + T * sp) % H
        xx = x + math.sin(T * 0.8 + ph) * 18
        d.ellipse((xx - r, yy - r, xx + r, yy + r), fill=(255, 255, 255, int(60 + r * 18)))

# ---------------- Hoo the owl ----------------
def draw_owl(scale=1.0, eyes="open", hat=False):
    S = 4
    w, h = 520, 600
    im = Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    E = lambda b, f: d.ellipse([v * S for v in b], fill=f)
    P = lambda pts, f: d.polygon([(x * S, y * S) for x, y in pts], fill=f)
    body, wing = (46, 120, 84), (31, 90, 62)
    P([(110, 175), (92, 60), (205, 130)], body)      # tufts
    P([(410, 175), (428, 60), (315, 130)], body)
    E((40, 260, 175, 500), wing)                       # wings
    E((345, 260, 480, 500), wing)
    E((75, 110, 445, 580), body)                       # body
    E((150, 330, 370, 565), CREAM)                     # belly
    for row, xs in ((390, (225, 295)), (440, (190, 260, 330)), (490, (225, 295))):
        for xx in xs:
            d.arc([(xx - 17) * S, (row - 10) * S, (xx + 17) * S, (row + 14) * S], 20, 160, fill=(214, 200, 170), width=4 * S)
    E((110, 150, 265, 305), CREAM)                     # heart face
    E((255, 150, 410, 305), CREAM)
    P([(118, 255), (402, 255), (260, 360)], CREAM)
    for cx in (190, 330):
        if eyes == "blink" or (eyes == "wink" and cx == 330):
            d.arc([(cx - 44) * S, 205 * S, (cx + 44) * S, 255 * S], 200, 340, fill=INK, width=10 * S)
        elif eyes == "happy":
            d.arc([(cx - 40) * S, 200 * S, (cx + 40) * S, 270 * S], 200, 340, fill=INK, width=10 * S)
        else:
            E((cx - 46, 180, cx + 46, 272), INK)
            E((cx - 14, 194, cx + 14, 222), WHITE)
            E((cx + 12, 236, cx + 24, 248), WHITE)
    P([(240, 282), (280, 282), (260, 322)], AMBER)     # beak
    E((125, 280, 172, 310), (255, 150, 150, 150))      # cheeks
    E((348, 280, 395, 310), (255, 150, 150, 150))
    for fx in (210, 310):                               # feet
        for k in (-18, 0, 18):
            E((fx + k - 11, 565, fx + k + 11, 597), AMBER)
    if hat:                                             # santa hat
        P([(150, 150), (370, 150), (330, 20)], (214, 40, 50))
        E((300, 0, 350, 50), WHITE)
        d.rounded_rectangle([140 * S, 135 * S, 380 * S, 175 * S], 20 * S, fill=WHITE)
    return im.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.LANCZOS)

_owl = {}
def owl(scale, eyes, hat):
    k = (round(scale, 2), eyes, hat)
    if k not in _owl:
        _owl[k] = draw_owl(k[0], eyes, hat)
    return _owl[k]

def paste_owl(img, cx, cy, scale, t, appear=0.0, eyes=None, hat=False, tilt=0):
    a = ease_back((t - appear) / 0.45)
    if a <= 0: return
    bob = math.sin(t * 2 * math.pi * 0.9) * 10
    e = eyes or ("blink" if (t % 2.7) < 0.12 else "open")
    spr = owl(scale * max(0.02, a), e, hat)
    if tilt:
        spr = spr.rotate(math.sin(t * 3) * tilt, resample=Image.BICUBIC, expand=True)
    img.alpha_composite(spr, (int(cx - spr.width / 2), int(cy - spr.height + bob)))

def bubble(img, text, x, y, t, start, size=46):
    a = ease_back((t - start) / 0.35)
    if a <= 0: return
    f = font(F_BOLD, size)
    tw = _d.textlength(text, font=f)
    bw, bh = tw + 70, size * 1.7
    layer = Image.new("RGBA", (int(bw + 40), int(bh + 50)), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle((0, 0, bw, bh), 36, fill=WHITE)
    d.polygon([(40, bh - 2), (90, bh - 2), (30, bh + 40)], fill=WHITE)
    d.text((35, bh * 0.16), text, font=f, fill=INK)
    layer = layer.resize((max(1, int(layer.width * a)), max(1, int(layer.height * a))), Image.LANCZOS)
    img.alpha_composite(layer, (int(x), int(y + (1 - a) * 40)))

# ---------------- text ----------------
_d = ImageDraw.Draw(Image.new("RGB", (1, 1)))
def wrap(text, f, maxw):
    out = []
    for para in text.split("\n"):
        cur = ""
        for w_ in para.split():
            test = (cur + " " + w_).strip()
            if _d.textlength(test, font=f) <= maxw: cur = test
            else: out.append(cur); cur = w_
        out.append(cur)
    return out

def text_block(img, text, f, y, t, start, color=WHITE, maxw=900, lh=1.14, pill=None, pill_ink=INK):
    lines = wrap(text, f, maxw)
    step = int(f.size * lh) + (24 if pill else 0)
    a = ease_out((t - start) / 0.4)
    if a <= 0: return y + len(lines) * step
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    off = int((1 - a) * 55)
    yy = y
    for ln in lines:
        tw = d.textlength(ln, font=f)
        x = W / 2 - tw / 2
        if pill:
            pad = 26
            d.rounded_rectangle((x - pad, yy + off - 10, x + tw + pad, yy + off + f.size * 1.34), 28, fill=pill)
            d.text((x, yy + off), ln, font=f, fill=pill_ink)
        else:
            d.text((x + 3, yy + off + 5), ln, font=f, fill=(0, 15, 8, 120))
            d.text((x, yy + off), ln, font=f, fill=color)
        yy += step
    if a < 1: layer.putalpha(layer.getchannel("A").point(lambda v: int(v * a)))
    img.alpha_composite(layer)
    return yy

def chrome(img, progress):
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((60, 150, W - 60, 160), 5, fill=(255, 255, 255, 45))
    d.rounded_rectangle((60, 150, 60 + max(10, int((W - 120) * progress)), 160), 5, fill=AMBER)
    f = font(F_BOLD, 40)
    parts = [("Pick", CREAM), ("o", AMBER), ("Hoo", CREAM)]
    x = (W - sum(d.textlength(p, font=f) for p, _ in parts)) / 2
    for p, c in parts:
        d.text((x, 182), p, font=f, fill=c); x += d.textlength(p, font=f)

def ad_note(img, t, start, text):
    a = ease_out((t - start) / 0.4)
    if a <= 0: return
    f = font(F_MED, 30)
    d = ImageDraw.Draw(img)
    tw = d.textlength(text, font=f)
    d.text(((W - tw) / 2, 1440), text, font=f, fill=(245, 243, 238, int(210 * a)))

# ---------------- scenes ----------------
def sc_hook(img, s, t):
    y = text_block(img, s["kicker"], font(F_BOLD, 46), 340, t, 0.05, pill=AMBER)
    y = text_block(img, s["title"], font(F_BOLD, 100), y + 50, t, 0.25)
    if s.get("sub"):
        text_block(img, s["sub"], font(F_MED, 54), y + 35, t, 0.85, color=MINT)
    paste_owl(img, W / 2, 1530, 0.9, t, appear=0.35, hat=s.get("hat", False), eyes=s.get("eyes"))
    if s.get("bubble"):
        bubble(img, s["bubble"], 640, 900, t, 1.1)

_imgs = {}
def product_card(img, path, cx, cy, size, t, start):
    a = ease_back((t - start) / 0.5)
    if a <= 0: return
    key = (path, size)
    if key not in _imgs:
        src = Image.open(os.path.join(HERE, path)).convert("RGBA")
        card = Image.new("RGBA", (size, size), WHITE)
        inner = int(size * 0.86)
        card.alpha_composite(src.resize((inner, inner), Image.LANCZOS), ((size - inner) // 2, (size - inner) // 2))
        mask = Image.new("L", (size, size), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, size - 1, size - 1), 48, fill=255)
        card.putalpha(mask)
        sh = Image.new("RGBA", (size + 80, size + 80), (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle((40, 55, size + 40, size + 55), 48, fill=(0, 0, 0, 110))
        sh = sh.filter(ImageFilter.GaussianBlur(22))
        sh.alpha_composite(card, (40, 40))
        _imgs[key] = sh
    spr = _imgs[key]
    zoom = a * (1 + 0.03 * max(0, t - start))
    spr2 = spr.resize((max(1, int(spr.width * zoom)), max(1, int(spr.height * zoom))), Image.BICUBIC)
    img.alpha_composite(spr2, (int(cx - spr2.width / 2), int(cy - spr2.height / 2)))

def price_sticker(img, text, cx, cy, t, start):
    a = ease_back((t - start) / 0.4)
    if a <= 0: return
    f = font(F_BOLD, 66)
    tw = _d.textlength(text, font=f)
    lay = Image.new("RGBA", (int(tw + 90), 130), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.rounded_rectangle((0, 0, tw + 90, 120), 60, fill=AMBER)
    d.text((45, 14), text, font=f, fill=INK)
    lay = lay.rotate(-7 + math.sin(t * 4) * 1.5, resample=Image.BICUBIC, expand=True)
    lay = lay.resize((max(1, int(lay.width * a)), max(1, int(lay.height * a))), Image.LANCZOS)
    img.alpha_composite(lay, (int(cx - lay.width / 2), int(cy - lay.height / 2)))

def sc_pick(img, s, t):
    text_block(img, s["label"], font(F_BOLD, 50), 300, t, 0.0, pill=AMBER)
    product_card(img, s["image"], W / 2, 760, 620, t, 0.15)
    price_sticker(img, s["price"], 830, 1050, t, 0.9)
    y = text_block(img, s["name"], font(F_BOLD, 62), 1125, t, 0.45, maxw=860)
    text_block(img, s["why"], font(F_MED, 44), y + 10, t, 0.8, color=MINT, maxw=860)
    ad_note(img, t, 0.9, s.get("note", "Ad · price from retailer feed, check before you buy"))
    paste_owl(img, 900, 1700, 0.42, t, appear=0.6, hat=s.get("hat", False), eyes=s.get("eyes"))

def sc_tip(img, s, t):
    d = ImageDraw.Draw(img)
    a = ease_back(t / 0.4)
    if a > 0:
        r = int(92 * a); cx, cy = W // 2, 460
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=AMBER)
        f = font(F_BOLD, 108 * a)
        n = str(s["num"]); tw = d.textlength(n, font=f)
        d.text((cx - tw / 2, cy - f.size * 0.64), n, font=f, fill=INK)
    y = text_block(img, s["title"], font(F_BOLD, 88), 620, t, 0.2)
    ca = ease_out((t - 0.7) / 0.4)
    if ca > 0:
        f = font(F_MED, 50)
        lines = wrap(s["body"], f, 800)
        ch = len(lines) * int(50 * 1.28) + 80
        top = y + 50 + int((1 - ca) * 40)
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        cd = ImageDraw.Draw(lay)
        cd.rounded_rectangle((90, top, W - 90, top + ch), 40, fill=(245, 243, 238, 240))
        yy = top + 40
        for ln in lines:
            tw = cd.textlength(ln, font=f); cd.text(((W - tw) / 2, yy), ln, font=f, fill=INK); yy += int(50 * 1.28)
        if ca < 1: lay.putalpha(lay.getchannel("A").point(lambda v: int(v * ca)))
        img.alpha_composite(lay)
    paste_owl(img, 880, 1640, 0.48, t, appear=0.5, eyes=("wink" if 1.5 < t < 1.8 else None), hat=s.get("hat", False))

def sc_quiz(img, s, t):
    y = text_block(img, s["kicker"], font(F_BOLD, 46), 300, t, 0.0, pill=AMBER)
    y = text_block(img, s["question"], font(F_BOLD, 74), y + 40, t, 0.2)
    f = font(F_BOLD, 50)
    y += 40
    for i, opt in enumerate(s["options"]):
        st = 0.9 + i * 0.45
        a = ease_back((t - st) / 0.4)
        if a > 0:
            lay = Image.new("RGBA", (W, 150), (0, 0, 0, 0))
            d = ImageDraw.Draw(lay)
            d.rounded_rectangle((90, 10, W - 90, 130), 34, fill=(245, 243, 238, 235))
            d.ellipse((115, 30, 195, 110), fill=AMBER)
            L = "ABC"[i]; lw = d.textlength(L, font=f)
            d.text((155 - lw / 2, 36), L, font=f, fill=INK)
            d.text((225, 40), opt, font=font(F_MED, 44), fill=INK)
            img.alpha_composite(lay, (int((1 - a) * -220), int(y)))
        y += 150
    if s.get("cta"):
        text_block(img, s["cta"], font(F_BOLD, 50), y + 30, t, 0.9 + len(s["options"]) * 0.45 + 0.2, color=AMBER)
    paste_owl(img, 880, 1690, 0.42, t, appear=0.4, eyes=s.get("eyes"))

def sc_reveal(img, s, t):
    d = ImageDraw.Draw(img)
    a = ease_back(t / 0.4)
    if a > 0:
        r = int(92 * a); cx, cy = W // 2, 460
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=AMBER)
        f = font(F_BOLD, 100 * a); L = s["letter"]; tw = d.textlength(L, font=f)
        d.text((cx - tw / 2, cy - f.size * 0.64), L, font=f, fill=INK)
    y = text_block(img, s["title"], font(F_BOLD, 86), 620, t, 0.2)
    y = text_block(img, s["body"], font(F_MED, 50), y + 40, t, 0.7, color=MINT, maxw=840)
    if s.get("fix"):
        text_block(img, s["fix"], font(F_BOLD, 46), y + 40, t, 1.3, pill=AMBER, maxw=820)
    paste_owl(img, 880, 1690, 0.42, t, appear=0.5, eyes=s.get("eyes"))

def sc_cta(img, s, t):
    paste_owl(img, W / 2, 1000, 1.05, t, appear=0.0, eyes=("happy" if t > 1.2 else None), hat=s.get("hat", False), tilt=4)
    y = text_block(img, s["title"], font(F_BOLD, 92), 1060, t, 0.3)
    if s.get("sub"):
        y = text_block(img, s["sub"], font(F_BOLD, 92), y - 10, t, 0.6, color=AMBER)
    text_block(img, s["button"], font(F_BOLD, 54), y + 50, t, 0.9, pill=CREAM)

SCENES = {"hook": sc_hook, "pick": sc_pick, "tip": sc_tip, "quiz": sc_quiz, "reveal": sc_reveal, "cta": sc_cta}
POPS = {"pick": lambda s: [0.15, 0.9], "quiz": lambda s: [0.9 + k * 0.45 for k in range(len(s["options"]))],
        "tip": lambda s: [0.0], "reveal": lambda s: [0.0], "hook": lambda s: [0.35], "cta": lambda s: [0.0]}

# ---------------- audio ----------------
SR = 44100
def add(mix, s0, sig):
    if s0 >= len(mix): return
    e = min(len(mix), s0 + len(sig)); mix[s0:e] += sig[: e - s0]

def music(total, cuts, pops, out, bpm=116, bells=False, key=0):
    n = int(total * SR); mix = np.zeros(n)
    beat = 60 / bpm; bar = 4 * beat
    semis = 2 ** (key / 12)
    chords = [[261.63, 329.63, 392.0], [220.0, 261.63, 329.63], [174.61, 220.0, 261.63], [196.0, 246.94, 293.66]]
    seg = np.arange(int(bar * SR)) / SR
    for i in range(int(total / bar) + 1):
        ch = [f * semis for f in chords[i % 4]]
        pad = sum(np.sin(2 * np.pi * f * seg) for f in ch) * np.minimum(1, seg / 0.08) * np.exp(-seg * 0.5)
        arp = np.zeros_like(seg)
        for k in range(8):
            a0 = int(k * beat / 2 * SR); f = ch[[0, 1, 2, 1][k % 4]] * 2; ss = seg[: len(seg) - a0]
            arp[a0:] += (np.sin(2 * np.pi * f * ss) + 0.25 * np.sin(6 * np.pi * f * ss)) * np.exp(-ss * 10)
        bass = np.sin(2 * np.pi * ch[0] / 2 * seg) * np.exp(-(seg % beat) * 4)
        add(mix, int(i * bar * SR), 0.04 * pad + 0.075 * arp + 0.12 * bass)
    for k in range(int(total / beat) + 1):
        kt = np.arange(int(0.25 * SR)) / SR
        add(mix, int(k * beat * SR), 0.32 * np.sin(2 * np.pi * (50 + 90 * np.exp(-kt * 30)) * kt) * np.exp(-kt * 12))
        rng = np.random.default_rng(k)
        if bells:
            for h in (0, 0.5):
                bl = int(0.09 * SR); bt = np.arange(bl) / SR
                sig = rng.standard_normal(bl); sig = sig - np.convolve(sig, np.ones(4) / 4, mode="same")
                add(mix, int((k + h) * beat * SR), 0.06 * sig * np.exp(-bt * 45))
        else:
            hl = int(0.05 * SR)
            add(mix, int((k + 0.5) * beat * SR), 0.045 * rng.standard_normal(hl) * np.exp(-np.arange(hl) / SR * 80))
    for c in cuts:
        wl = int(0.35 * SR); rng = np.random.default_rng(int(c * 100))
        lo = np.convolve(rng.standard_normal(wl), np.ones(30) / 30, mode="same")
        add(mix, max(0, int((c - 0.15) * SR)), 0.28 * lo * np.sin(np.linspace(0, np.pi, wl)) ** 2)
    for p in pops:
        pl = int(0.12 * SR); pt = np.arange(pl) / SR
        add(mix, int(p * SR), 0.22 * np.sin(2 * np.pi * (600 + 900 * pt / 0.12) * pt) * np.exp(-pt * 35))
    fade = int(0.4 * SR); mix[:fade] *= np.linspace(0, 1, fade)
    mix[-SR:] *= np.linspace(1, 0, SR)
    mix = mix / (np.max(np.abs(mix)) + 1e-9) * 0.8
    with wave.open(out, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((mix * 32767).astype(np.int16).tobytes())

# ---------------- render ----------------
def frame(bg, flakes, scene, t, T, progress, show_snow):
    img = bg.copy()
    if show_snow: snow(img, flakes, T)
    SCENES[scene["type"]](img, scene, t)
    chrome(img, progress)
    return img.convert("RGB")

def main(spec_path, out):
    spec = json.load(open(spec_path))
    scenes = spec["scenes"]; total = sum(s["dur"] for s in scenes)
    show_snow = spec.get("snow", False)
    bg, flakes = make_bg()
    work = os.path.join(os.path.dirname(os.path.abspath(out)), "_work", os.path.basename(out)[:-4])
    os.makedirs(work, exist_ok=True)
    if os.environ.get("FRAMES"):
        for item in os.environ["FRAMES"].split(","):
            i, tt = item.split(":"); i, tt = int(i), float(tt)
            st = sum(x["dur"] for x in scenes[:i])
            frame(bg, flakes, scenes[i], tt, st + tt, (st + tt) / total, show_snow).save(f"{work}/preview_{i}_{tt}.png")
        print(work); return
    files, el, cuts, pops = [], 0.0, [], []
    for i, s in enumerate(scenes):
        nf = int(round(s["dur"] * FPS))
        tmp, fin = f"{work}/s{i}.tmp.mp4", f"{work}/s{i}.mp4"
        p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                              "-c:v", "libx264", "-crf", "18", "-preset", "veryfast", "-pix_fmt", "yuv420p", tmp], stdin=subprocess.PIPE)
        for f_ in range(nf):
            t = f_ / FPS
            fr = frame(bg, flakes, s, t, el + t, (el + t) / total, show_snow)
            if f_ >= nf - 5 and i < len(scenes) - 1:
                fr = Image.blend(fr, Image.new("RGB", (W, H), G_BOT), (f_ - (nf - 5)) / 5 * 0.6)
            p.stdin.write(fr.tobytes())
        p.stdin.close()
        if p.wait() != 0: sys.exit(f"scene {i} failed")
        os.replace(tmp, fin); files.append(fin)
        pops += [el + x for x in POPS[s["type"]](s)]
        el += s["dur"]; cuts.append(el)
    with open(f"{work}/list.txt", "w") as fl:
        fl.writelines(f"file '{f}'\n" for f in files)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", f"{work}/list.txt", "-c", "copy", f"{work}/video.mp4"], check=True)
    m = spec.get("music", {})
    music(total, cuts[:-1], pops, f"{work}/music.wav", bpm=m.get("bpm", 116), bells=m.get("bells", False), key=m.get("key", 0))
    tmp = out[:-4] + ".tmp.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", f"{work}/video.mp4", "-i", f"{work}/music.wav", "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", tmp], check=True)
    os.replace(tmp, out)
    print("done", out, f"{total:.1f}s")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
