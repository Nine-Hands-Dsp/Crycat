"""Crycat v2 (NINE HANDS | DSP), aperçu n° 2 : image 1870 x 1800, disposition d'origine de Crycat
(logo en haut à gauche, inverseur en haut à droite, RANGE + écran, Q / PURR / BOOST, footswitch + LED, nom en bas),
footswitch sans halo, logo et nom plus petits.
La façade fournie (2350 x 1800) est ramenée à la largeur voulue SANS étirement : trois bandes verticales sont retirées
là où la matière est uniforme (milieu du plateau, panneau à gauche de l'écran, partie noire de la vitre), avec un fondu
de raccord ; l'écran est ensuite descendu à côté de RANGE et sa place d'origine est rebouchée avec le grain du panneau."""
import os, sys, math
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, '/home/claude/nine-hands-dsp/strong-pickle/tools'); sys.path.insert(0, os.path.join(ROOT, 'tools'))
import photo_controls as pc, toggle_photo as tp
from knob_preview import knob, knob2, OUTER2

FONTS = '/home/claude/crycat/fonts'
FM, FR, FB, FL = (os.path.join(FONTS, f'Poppins-{w}.ttf') for w in ('Medium', 'Regular', 'Bold', 'Light'))
INK = (226, 224, 222); AMBER = (255, 176, 64)
W_OUT, H = 1870, 1800

# ------------------------------------------------------------------ façade : alpha plein dans la silhouette
fac = np.asarray(Image.open(os.path.join(ROOT, 'in', 'b8eb1ad7-image.png')).convert('RGBA')).astype(np.float32)
sil = (fac[..., 3] > 128).astype(np.uint8)
cnts, _ = cv2.findContours(sil, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
full = np.zeros_like(sil); cv2.drawContours(full, [max(cnts, key=cv2.contourArea)], -1, 1, -1)
fac[..., 3] = np.where(full > 0, 255, fac[..., 3])

# ------------------------------------------------------------------ coins du boîtier refaits : arc de cercle exact (R 145)
# la bordure (chanfrein + grain) est « déroulée » depuis les bords droits voisins et balayée autour de l'arc, sur 56 px
# de profondeur ; l'intérieur (plateau, panneau) n'est pas touché ; extérieur de l'arc transparent, bord lissé
def redo_corners(fac, R=145.0, BAND=56.0, FE=12.0):
    al = fac[..., 3] > 128; Hh, Ww = al.shape
    # bords droits réels (médiane hors des coins et des jacks), pas la boîte englobante
    rows = [y for y in range(300, Hh - 300, 7) if abs(y - 900) > 160]
    bx0 = int(round(np.median([np.argmax(al[y]) for y in rows])))
    bx1 = int(round(np.median([Ww - np.argmax(al[y, ::-1]) for y in rows])))
    cols = range(300, Ww - 300, 7)
    by0 = int(round(np.median([np.argmax(al[:, x]) for x in cols])))
    by1 = int(round(np.median([Hh - np.argmax(al[::-1, x]) for x in cols])))
    print('bords', bx0, bx1, by0, by1)
    src = fac.copy(); Rn = int(R) + 2
    for sx, sy in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
        ex = bx0 if sx > 0 else bx1; ey = by0 if sy > 0 else by1
        cx, cy = ex + sx * R, ey + sy * R
        xa, xb = (ex, ex + Rn) if sx > 0 else (ex - Rn, ex)
        ya, yb = (ey, ey + Rn) if sy > 0 else (ey - Rn, ey)
        gy, gx = np.mgrid[ya:yb, xa:xb].astype(np.float32); gx += 0.5; gy += 0.5
        dx, dy = (gx - cx) * sx, (gy - cy) * sy                  # < 0 vers le coin
        inq = (dx < 0) & (dy < 0)
        d = np.hypot(dx, dy); depth = R - d
        phi = np.arctan2(-dy, -dx)                                # 0 = vers le bord vertical, pi/2 = vers le bord horizontal
        # échantillon sur le bord vertical (x = bord + profondeur, y = au-delà du coin) et sur le bord horizontal
        vx = ex + sx * depth; vy = cy + sy * (R * phi + 90)
        hx = cx + sx * (R * (np.pi / 2 - phi) + 90); hy = ey + sy * depth
        sv = cv2.remap(src, (vx - 0.5).astype(np.float32), (vy - 0.5).astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        shh = cv2.remap(src, (hx - 0.5).astype(np.float32), (hy - 0.5).astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        t = np.clip((phi - (np.pi / 4 - 0.18)) / 0.36, 0, 1)[..., None]
        new = sv * (1 - t) + shh * t
        w = (np.clip((BAND - depth) / FE, 0, 1) * inq)[..., None]   # 1 dans la bordure, fondu vers l'intérieur
        reg = fac[ya:yb, xa:xb]
        rgb = reg[..., :3] * (1 - w) + new[..., :3] * w
        alpha = np.where(inq, np.clip(depth + 0.5, 0, 1) * 255, reg[..., 3])
        reg[..., :3] = np.where(alpha[..., None] > 0, rgb, 0); reg[..., 3] = alpha
        # prolongement : 90 px de bord droit après l'arc, recopiés depuis plus loin sur le même bord (rattrape les bords
        # d'origine légèrement rentrés près des coins), fondu vers l'original au bout
        L = 90
        for vert in (True, False):
            if vert:
                y_a, y_b = (int(cy), int(cy) + L) if sy > 0 else (int(cy) - L, int(cy))
                x_a, x_b = (ex - 2, ex + int(BAND)) if sx > 0 else (ex - int(BAND), ex + 2)
            else:
                x_a, x_b = (int(cx), int(cx) + L) if sx > 0 else (int(cx) - L, int(cx))
                y_a, y_b = (ey - 2, ey + int(BAND)) if sy > 0 else (ey - int(BAND), ey + 2)
            y_a, y_b, x_a, x_b = max(0, y_a), min(Hh, y_b), max(0, x_a), min(Ww, x_b)
            if y_b <= y_a or x_b <= x_a: continue
            gy2, gx2 = np.mgrid[y_a:y_b, x_a:x_b].astype(np.float32)
            dep = ((gx2 + 0.5 - ex) * sx) if vert else ((gy2 + 0.5 - ey) * sy)
            along = (np.abs(gy2 + 0.5 - cy) if vert else np.abs(gx2 + 0.5 - cx)) / L
            mx = gx2 if not vert else gx2; my = gy2 + sy * L if vert else gy2
            if not vert: mx = gx2 + sx * L
            smp = cv2.remap(src, mx.astype(np.float32), my.astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
            ww = (np.clip((BAND - dep) / FE, 0, 1) * np.clip((1 - along) / 0.35, 0, 1))[..., None]
            rg = fac[y_a:y_b, x_a:x_b]
            a2 = np.clip(dep + 0.5, 0, 1) * 255
            rg[..., :3] = np.where(a2[..., None] > 0, rg[..., :3] * (1 - ww) + smp[..., :3] * ww, 0)
            rg[..., 3] = np.where(ww[..., 0] > 0, a2 * ww[..., 0] + rg[..., 3] * (1 - ww[..., 0]), rg[..., 3])
    return fac
fac = redo_corners(fac)

# ------------------------------------------------------------------ jacks (kit) : saillie -> largeur de façade voulue
JACK_LEN, JACK_Y = 248.0 * 0.85 * 0.90, 900.0
jin, jw, jh = pc.jack_sprite(JACK_LEN, 1, +1)
jout, _, _ = pc.jack_sprite(JACK_LEN, 1, -1)
P = int(math.ceil(jw)) - 6
FW_T = W_OUT - 2 * P                                # largeur de façade voulue (1778)

# bandes retirées (x de la façade d'origine) : uniformes dans le sens vertical de la coupe
CUTS = [(700, 860), (1250, 1484), (1985, 2163)]
need = fac.shape[1] - FW_T
have = sum(b - a for a, b in CUTS)
CUTS[1] = (CUTS[1][0], CUTS[1][1] + (need - have))  # ajustement exact sur la bande du panneau
FEATHER = 24

def remove_band(a, x0, x1):
    """retire les colonnes [x0, x1) ; raccord en fondu sur FEATHER px (les deux bords se superposent)"""
    left, right = a[:, :x0 + FEATHER // 2], a[:, x1 - FEATHER // 2:]
    t = np.linspace(0, 1, FEATHER)[None, :, None]
    blend = left[:, -FEATHER:] * (1 - t) + right[:, :FEATHER] * t
    return np.concatenate([left[:, :-FEATHER], blend, right[:, FEATHER:]], 1)

for a_, b_ in sorted(CUTS, reverse=True):
    fac = remove_band(fac, a_, b_)
assert fac.shape[1] == FW_T, fac.shape
def nx(x):                                           # x d'origine -> x après coupes
    return x - sum(b - a for a, b in CUTS if b <= x)

# ------------------------------------------------------------------ écran descendu à côté de RANGE
SX0, SY0, SX1, SY1 = nx(1656) - 0, 104, nx(2240) - 0, 440       # vitre + cadre + leur ombre
SX1 = nx(2236)
scr_obj = fac[SY0:SY1, SX0:SX1].copy()
sh_, sw_ = scr_obj.shape[:2]
# rebouche la place d'origine : teinte basse fréquence par inpainting + grain du panneau repris plus bas
E_ = 44
ry0, ry1, rx0, rx1 = SY0 - E_, SY1 + E_, SX0 - E_, SX1 + E_
hole = np.zeros(fac.shape[:2], np.uint8); hole[ry0:ry1, rx0:rx1] = 1
# teinte : plan ajusté sur l'anneau de panneau autour du trou (aucune tache)
R2 = 26
yy_, xx_ = np.mgrid[ry0 - R2:ry1 + R2, rx0 - R2:rx1 + R2].astype(np.float32)
ring = np.ones(yy_.shape, bool); ring[R2:-R2, R2:-R2] = False
blk = cv2.GaussianBlur(fac[ry0 - R2:ry1 + R2, rx0 - R2:rx1 + R2, :3], (0, 0), 8)
A = np.stack([np.ones(ring.sum()), xx_[ring], yy_[ring]], 1)
low = np.zeros(fac.shape[:2] + (3,), np.float32)
gy, gx = np.mgrid[0:fac.shape[0], 0:fac.shape[1]].astype(np.float32)
for c in range(3):
    co, *_ = np.linalg.lstsq(A, np.median(blk[..., c][ring]) * 0 + blk[..., c][ring], rcond=None)
    low[..., c] = co[0] + co[1] * gx + co[2] * gy
src = fac[1180:1180 + (ry1 - ry0), rx0:rx1, :3]
detail = src - cv2.GaussianBlur(src, (0, 0), 12)
fill = low[ry0:ry1, rx0:rx1] + detail
m = np.zeros((ry1 - ry0, rx1 - rx0), np.float32); m[22:-22, 22:-22] = 1; m = cv2.GaussianBlur(m, (0, 0), 10)[..., None]
fac[ry0:ry1, rx0:rx1, :3] = fac[ry0:ry1, rx0:rx1, :3] * (1 - m) + fill * m
# nouvel écran : vitre plus grande, encastrée dans la coque, sans cadre
GLASS = (1240, 358, 1664, 782)          # carré : hauteur = largeur
gx0_, gy0_, gx1_, gy1_ = GLASS
SSg = 4
Mh = Image.new('L', (fac.shape[1] * 1, fac.shape[0] * 1), 0)
mk_ = Image.new('L', ((gx1_ - gx0_ + 80) * SSg, (gy1_ - gy0_ + 80) * SSg), 0)
ImageDraw.Draw(mk_).rounded_rectangle((40 * SSg, 40 * SSg, (gx1_ - gx0_ + 40) * SSg, (gy1_ - gy0_ + 40) * SSg), 18 * SSg, fill=255)
M = np.asarray(mk_.resize((gx1_ - gx0_ + 80, gy1_ - gy0_ + 80), Image.LANCZOS), np.float32) / 255.0
def shift(a, dx, dy):
    return cv2.warpAffine(a, np.float32([[1, 0, dx], [0, 1, dy]]), (a.shape[1], a.shape[0]), borderValue=0)
reg = fac[gy0_ - 40:gy1_ + 40, gx0_ - 40:gx1_ + 40, :3]
hh_, ww_ = M.shape
yy2, xx2 = np.mgrid[0:hh_, 0:ww_].astype(np.float32)
# vitre : noir profond + reflet diagonal doux venant du haut à gauche
u = ((xx2 - 40) / (ww_ - 80) + (yy2 - 40) / (hh_ - 80)) / 2
glass = np.zeros_like(reg) + np.array([5.0, 5.0, 6.0])
glass += (np.clip(1 - u / 0.55, 0, 1) ** 2 * 16)[..., None]
glass += (np.exp(-((u - 0.30) / 0.035) ** 2) * 5)[..., None]
# ombre portée par le bord haut-gauche de la découpe sur la vitre (lumière en haut à gauche)
shd = cv2.GaussianBlur(np.clip(1 - shift(M, 7, 7), 0, 1), (0, 0), 5) * M
glass *= (1 - 0.85 * shd)[..., None]
# paroi basse-droite éclairée, paroi haute-gauche sombre (fin chanfrein)
lit = np.clip(M - shift(M, -2.5, -2.5), 0, 1); dark = np.clip(M - shift(M, 2.5, 2.5), 0, 1)
glass = glass + (lit * 70)[..., None]
glass = glass * (1 - 0.5 * dark)[..., None]
# lèvre du panneau juste autour de la découpe : arête haute-gauche accrochant la lumière
lip = np.clip(shift(M, 2, 2) - M, 0, 1)
out_ = reg * (1 + 0.6 * lip)[..., None]
fac[gy0_ - 40:gy1_ + 40, gx0_ - 40:gx1_ + 40, :3] = out_ * (1 - M[..., None]) + glass * M[..., None]
GLASS = (gx0_ + 8, gy0_ + 8, gx1_ - 8, gy1_ - 8)       # zone d'affichage

W = W_OUT
img = np.zeros((H, W, 4), np.float32)
img[:, P:P + FW_T] = fac
X0 = P

def over(dst, spr, x, y):
    h, w = spr.shape[:2]; x, y = int(round(x)), int(round(y))
    xa, ya, xb, yb = max(0, x), max(0, y), min(dst.shape[1], x + w), min(dst.shape[0], y + h)
    s = spr[ya - y:yb - y, xa - x:xb - x].astype(np.float32); a = s[..., 3:4] / 255.0
    d = dst[ya:yb, xa:xb]; da = d[..., 3:4] / 255.0
    oa = a + da * (1 - a)
    d[..., :3] = np.where(oa > 1e-4, (s[..., :3] * a + d[..., :3] * da * (1 - a)) / np.maximum(oa, 1e-4), 0)
    d[..., 3:4] = oa * 255

over(img, jout, 0, JACK_Y - jh / 2)
over(img, jin, W - jin.shape[1], JACK_Y - jh / 2)

# ------------------------------------------------------------------ disposition (repère façade après coupes)
PANEL = (nx(1080), 76, nx(2268), 1724)            # 920 .. 1696
PCX = 0.5 * (PANEL[0] + PANEL[2])
LOGO_W, LOGO_C = 262, (PANEL[0] + 40, 150)        # logo : haut gauche, plus petit
TOG_C, TOG_WR = (PANEL[2] - 130, 215), 44         # inverseur : haut droite (MAN en haut, AUTO en bas)
RANGE_C, RANGE_R = (1072, 570), 84
SMALL_Y, SMALL_R = 960, 73.6
SMALL_X = (PANEL[0] + 150, PCX, PANEL[2] - 150)
PILL = (SMALL_X[0] - SMALL_R, 1172, SMALL_X[2] + SMALL_R, 1248)         # pastille : hauteur et police de référence, largeur réduite au panneau
FS_C, FS_FLATS = (PCX, 1410), 153
LED_C, LED_R = (PCX + 170, 1410), 17
NAME_X, NAME_Y = PANEL[0] + 40, 1600

def F(x, y): return (x + X0, y)

SS = 2
txt = Image.new('L', (W * SS, H * SS), 0); dt = ImageDraw.Draw(txt)
amb = Image.new('L', (W * SS, H * SS), 0); da_ = ImageDraw.Draw(amb)
sep = Image.new('L', (W * SS, H * SS), 0); sep_d = ImageDraw.Draw(sep)
def font(p, s): return ImageFont.truetype(p, int(round(s * SS)))
def T(x, y, s, size, fp=FM, anchor='mm', spacing=0.0, d=dt):
    f = font(fp, size); x, y = F(x, y)
    if not spacing:
        d.text((x * SS, y * SS), s, font=f, fill=255, anchor=anchor); return
    total = sum(f.getlength(c) for c in s) + spacing * SS * (len(s) - 1)
    cx = x * SS - (total / 2 if anchor[0] == 'm' else 0)
    for c in s:
        d.text((cx, y * SS), c, font=f, fill=255, anchor='l' + anchor[1]); cx += f.getlength(c) + spacing * SS
def line(x0, y0, x1, y1, w, d=dt):
    (a, b), (c, e) = F(x0, y0), F(x1, y1)
    d.line((a * SS, b * SS, c * SS, e * SS), fill=255, width=int(round(w * SS)))

for i in range(6):
    a = math.radians(-125 + 50 * i); sx, sy = math.sin(a), -math.cos(a); cx, cy = RANGE_C
    line(cx + sx * (RANGE_R + 10), cy + sy * (RANGE_R + 10), cx + sx * (RANGE_R + 22), cy + sy * (RANGE_R + 22), 3.5)
    T(cx + sx * (RANGE_R + 42), cy + sy * (RANGE_R + 42), str(i + 1), 28, FM, d=(da_ if i == 2 else dt))
T(RANGE_C[0] - (RANGE_R + 30), RANGE_C[1] + (RANGE_R + 38), 'LOW', 21, FR)
T(RANGE_C[0] + (RANGE_R + 30), RANGE_C[1] + (RANGE_R + 38), 'HIGH', 21, FR)
T(RANGE_C[0], RANGE_C[1] + RANGE_R + 72, 'RANGE', 26, FM, spacing=5)
for (cx, name) in zip(SMALL_X, ('Q', 'PURR', 'BOOST')):
    for k in range(11):
        a = math.radians(-135 + 27 * k); sx, sy = math.sin(a), -math.cos(a)
        r0, r1 = SMALL_R + 9, SMALL_R + (23 if k in (0, 5, 10) else 17)
        line(cx + sx * r0, SMALL_Y + sy * r0, cx + sx * r1, SMALL_Y + sy * r1, 2.6)
    T(cx, SMALL_Y + SMALL_R + 52, name, 26, FM, spacing=3.5)
T(TOG_C[0], TOG_C[1] - 98, 'MAN', 28, FM, spacing=3)
T(TOG_C[0], TOG_C[1] + 98, 'AUTO', 28, FM, spacing=3)
for y in (820,):                         # filets fins comme sur le design d'origine
    x0_ = PANEL[0] + 40 if y != 230 else PANEL[0] + 40
    x1_ = PANEL[2] - 40 if y != 230 else PANEL[0] + 40 + LOGO_W + 160
    line(x0_, y, x1_, y, 2, d=sep_d)
fw_ = FW_T
for s_, x_, rot in (('OUT', 30, 90), ('IN', fw_ - 36, -90)):
    f = font(FM, 33); tw = int(f.getlength(s_)) + 10; th = 52 * SS
    lay = Image.new('L', (tw, th), 0); ImageDraw.Draw(lay).text((tw / 2, th / 2), s_, font=f, fill=255, anchor='mm')
    lay = lay.rotate(rot, expand=True); x, y = F(x_, JACK_Y)
    txt.paste(Image.new('L', lay.size, 255), (int(x * SS - lay.width / 2), int(y * SS - lay.height / 2)), lay)

# ------------------------------------------------------------------ occlusion ambiante sur la coque (jamais sur l'écran)
# assombrissement doux qui part du bord de chaque pièce, un peu décalé vers le bas à droite (lumière en haut à gauche)
_yy, _xx = np.mgrid[0:H, 0:W].astype(np.float32)
occ = np.zeros((H, W), np.float32)
def ao_disc(c, r, k=0.55, w=0.22):
    cx, cy = X0 + c[0] + 0.05 * r, c[1] + 0.06 * r
    d = np.hypot(_xx - cx, _yy - cy) - r
    v = k * np.exp(-np.maximum(d, 0) / (w * r)) * np.clip(1 + d / (0.15 * r), 0, 1)
    np.maximum(occ, v, out=occ)
ao_disc(RANGE_C, RANGE_R * 1.02)
for x in SMALL_X: ao_disc((x, SMALL_Y), SMALL_R * 1.02)
ao_disc(FS_C, FS_FLATS * 0.55, k=0.6, w=0.25)
ao_disc(TOG_C, TOG_WR * 1.25, k=0.55, w=0.35)
ao_disc(LED_C, LED_R * 1.25, k=0.5, w=0.45)
for xe in (X0, X0 + FW_T):                             # jacks : contre la tranche, côté coque
    d = np.hypot((_xx - xe) / 1.0, (_yy - JACK_Y) / (jh * 0.42))
    np.maximum(occ, 0.45 * np.exp(-np.abs(_xx - xe) / 16.0) * np.clip(1.25 - d, 0, 1) * (np.abs(_xx - xe) < 60), out=occ)
gx0o, gy0o, gx1o, gy1o = GLASS
occ[gy0o - 18:gy1o + 18, X0 + gx0o - 18:X0 + gx1o + 18] = 0
img[..., :3] *= (1 - occ[..., None])
def apply(layer, col, k):
    a = np.asarray(layer.resize((W, H), Image.LANCZOS), np.float32)[..., None] / 255.0 * k
    img[..., :3] = img[..., :3] * (1 - a) + np.array(col, np.float32) * a
apply(txt, INK, 0.92); apply(amb, AMBER, 1.0); apply(sep, INK, 0.30)

# logo NINE HANDS | DSP noir, centré sur la barre chromée basse du plateau (entre les deux vis) ; il bougera avec le plateau
PLATE_CX = 0.5 * (95 + 894) - X0; LOGO_BAR_Y = 1717; LOGO_W = 330
logo = Image.open(os.path.join(ROOT, 'assets', 'logo_black.png')).convert('RGBA')
logo = logo.crop(logo.getbbox()); logo = logo.resize((LOGO_W, round(LOGO_W * logo.height / logo.width)), Image.LANCZOS)
lg = np.asarray(logo).astype(np.float32); lg[..., 3] *= 0.86
over(img, lg, X0 + PLATE_CX - lg.shape[1] / 2, LOGO_BAR_Y - lg.shape[0] / 2)
# logo Crycat (SVG fourni, tracés en blanc pour se lire sur la coque noire), centré sous le footswitch
CRY_W, CRY_CY = 430, 1608
cl = Image.open(os.path.join(ROOT, 'assets', 'crycat_logo_white.png')).convert('RGBA'); cl = cl.crop(cl.getbbox())
cl = cl.resize((CRY_W, round(CRY_W * cl.height / cl.width)), Image.LANCZOS)
cla = np.asarray(cl).astype(np.float32); cla[..., :3] = np.array(INK, np.float32); cla[..., 3] *= 0.92
over(img, cla, X0 + FS_C[0] - cla.shape[1] / 2, CRY_CY - cla.shape[0] / 2)

# ------------------------------------------------------------------ écran (affichage ambre ajouté sous le reflet de la vitre)
gx0, gy0, gx1, gy1 = GLASS
gw, gh = gx1 - gx0, gy1 - gy0
scr = Image.new('RGB', (gw * SS, gh * SS), (0, 0, 0)); ds = ImageDraw.Draw(scr)
def st(x, y, s, size, fp=FB, col=AMBER, anchor='lm'):
    ds.text((x * SS, y * SS), s, font=font(fp, size), fill=col, anchor=anchor)
M_ = 26
st(M_, 0.085 * gh, 'RANGE 3  GCB95', 26); st(gw - M_, 0.085 * gh, 'ON', 26, anchor='rm')
ds.line((M_ * SS, 0.15 * gh * SS, (gw - M_) * SS, 0.15 * gh * SS), fill=(70, 46, 16), width=SS)
px0, py0, px1, py1 = M_, 0.19 * gh, gw - M_, 0.52 * gh
yz = (py0 + py1) / 2
for f_ in (100, 1000):
    x = px0 + (px1 - px0) * math.log(f_ / 80) / math.log(5000 / 80); ds.line((x * SS, py0 * SS, x * SS, py1 * SS), fill=(60, 40, 14), width=SS)
ds.line((px0 * SS, yz * SS, px1 * SS, yz * SS), fill=(60, 40, 14), width=SS)
fc, Q = 700.0, 4.6; pts = []
for i in range(120):
    f_ = 80 * (5000 / 80) ** (i / 119); u = f_ / fc
    re_, im_ = 1 - u * u, u / Q
    bp = complex(im_ * im_, im_ * re_) / (re_ * re_ + im_ * im_)
    v = f_ / (0.7 * fc); lp = complex(1, -v) / (1 + v * v)
    db = 20 * math.log10(max(abs(2.2 * (Q / 4.4) ** 0.35 * bp + 0.45 * lp), 1e-6))
    pts.append((px0 + (px1 - px0) * i / 119, yz - (py1 - py0) / 2 * max(-1, min(1, db / 24))))
poly = [(x * SS, y * SS) for x, y in pts]
ds.polygon(poly + [(px1 * SS, py1 * SS), (px0 * SS, py1 * SS)], fill=(70, 40, 8))
ds.line(poly, fill=(255, 214, 144), width=int(2.8 * SS), joint='curve')
st(gw / 2, 0.635 * gh, '700 Hz', 58, FB, (255, 241, 220), 'mm')
st(gw / 2, 0.75 * gh, 'Q 4.6  ·  BOOST +0.0 dB', 22, FM, AMBER, 'mm')
for i in range(16):
    t = (i + 0.5) / 16; hh = 9 + 21 * t; lit = t < 0.45
    x = M_ + i * ((gw - 2 * M_) / 16); ds.rectangle((x * SS, (gh - 22 - hh) * SS, (x + (gw - 2 * M_) / 16 - 5) * SS, (gh - 22) * SS), fill=AMBER if lit else (50, 32, 10))
scr = np.asarray(scr.resize((gw, gh), Image.LANCZOS), np.float32)
mk = Image.new('L', (gw, gh), 0); ImageDraw.Draw(mk).rounded_rectangle((2, 2, gw - 3, gh - 3), 16, fill=255)
mk = np.asarray(mk, np.float32)[..., None] / 255.0
reg = img[gy0:gy1, X0 + gx0:X0 + gx1, :3]
img[gy0:gy1, X0 + gx0:X0 + gx1, :3] = np.clip(reg + scr * mk, 0, 255)

# ------------------------------------------------------------------ pastille presets
pill = Image.new('RGBA', (W * SS, H * SS), (0, 0, 0, 0)); dp = ImageDraw.Draw(pill)
x0, y0 = F(PILL[0], PILL[1]); x1, y1 = F(PILL[2], PILL[3])
dp.rounded_rectangle((x0 * SS, y0 * SS, x1 * SS, y1 * SS), (y1 - y0) / 2 * SS, fill=(8, 7, 7, 240), outline=(120, 118, 116, 200), width=SS)
dp.text(((x0 + x1) / 2 * SS, (y0 + y1) / 2 * SS), 'GCB95 Classic', font=font(FM, 40), fill=(236, 234, 232, 255), anchor='mm')
for sgn, xa in ((-1, x0 + 34), (1, x1 - 34)):
    cy = (y0 + y1) / 2; s_ = 11
    dp.polygon([((xa - sgn * s_ / 2) * SS, (cy - s_) * SS), ((xa - sgn * s_ / 2) * SS, (cy + s_) * SS), ((xa + sgn * s_ * 0.9) * SS, cy * SS)], fill=(160, 158, 156, 255))
over(img, np.asarray(pill.resize((W, H), Image.LANCZOS), np.float32), 0, 0)

# ------------------------------------------------------------------ potards, inverseur, footswitch (sans halo), LED
def drop(spr, x, y, off, blur, k):
    """ombre portée d'après l'alpha du sprite, vers le bas à droite (lumière en haut à gauche à 45°), sur ce qui est dessous"""
    h, w = spr.shape[:2]; pad = int(off + 3 * blur) + 2
    a = np.zeros((h + 2 * pad, w + 2 * pad), np.float32); a[pad:pad + h, pad:pad + w] = spr[..., 3] / 255.0
    a = cv2.GaussianBlur(cv2.warpAffine(a, np.float32([[1, 0, off], [0, 1, off]]), (a.shape[1], a.shape[0])), (0, 0), blur) * k
    x0, y0 = int(round(x)) - pad, int(round(y)) - pad
    ya, xa = max(0, y0), max(0, x0); yb, xb = min(H, y0 + a.shape[0]), min(W, x0 + a.shape[1])
    img[ya:yb, xa:xb, :3] *= (1 - a[ya - y0:yb - y0, xa - x0:xb - x0, None])
def put_knob(c, R, ang):
    size = int(round(2 * R / OUTER2)); k = np.asarray(knob2(ang, size)).astype(np.float32)
    drop(k, X0 + c[0] - size / 2, c[1] - size / 2, 0.10 * R, 0.10 * R, 0.55)
    over(img, k, X0 + c[0] - size / 2, c[1] - size / 2)
put_knob(RANGE_C, RANGE_R, -25.0)
for x, v in zip(SMALL_X, (0.40, 0.20, 0.0)):
    put_knob((x, SMALL_Y), SMALL_R, -135 + 270 * v)
tg = tp.aligned_frames(TOG_WR, 3.6 * TOG_WR, 1)
spr = tg[0].astype(np.float32); drop(spr, X0 + TOG_C[0] - spr.shape[1] / 2, TOG_C[1] - spr.shape[0] / 2, 7, 5, 0.35); over(img, spr, X0 + TOG_C[0] - spr.shape[1] / 2, TOG_C[1] - spr.shape[0] / 2)
fs, refl, FSS, btnR = pc.footswitch_sprite(FS_FLATS, 1, refl_colour=(255.0, 160.0, 60.0))
drop(fs, X0 + FS_C[0] - fs.shape[1] / 2, FS_C[1] - fs.shape[0] / 2, 9, 8, 0.5)
over(img, fs, X0 + FS_C[0] - fs.shape[1] / 2, FS_C[1] - fs.shape[0] / 2)

led_off, led_on, LS = pc.led_sprites(LED_R, 1, colour='yellow')
lvl, glow = 1.0, 0.5
# la façade reçoit la lumière de la LED (calque additif, transparent ailleurs), puis la LED
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
d = np.hypot(xx - (X0 + LED_C[0]), yy - LED_C[1])
h1, h2 = 6.0, 20.0
E = (h1 ** 3 / (d ** 2 + h1 ** 2) ** 1.5 + 0.16 * h2 ** 3 / (d ** 2 + h2 ** 2) ** 1.5) * glow * lvl
E *= (d > LED_R * 1.05)
base = img[..., :3]
img[..., :3] = np.clip(base + (base * 2.4 + 10.0) * E[..., None] * np.array([1.0, 0.62, 0.20]), 0, 255)
drop(led_off, X0 + LED_C[0] - led_off.shape[1] / 2, LED_C[1] - led_off.shape[0] / 2, 3, 2.5, 0.45)
over(img, led_off, X0 + LED_C[0] - led_off.shape[1] / 2, LED_C[1] - led_off.shape[0] / 2)
on = led_on.copy(); on[..., 3] *= lvl
over(img, on, X0 + LED_C[0] - on.shape[1] / 2, LED_C[1] - on.shape[0] / 2)

out = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), 'RGBA')
out.save(os.path.join(ROOT, 'design', 'apercu_v2b.png'))
bg = Image.new('RGB', out.size, (24, 24, 26)); bg.paste(out, (0, 0), out); bg.save(os.path.join(ROOT, 'design', 'apercu_v2b_fond.png'))
print('image', W, 'x', H, 'façade', FW_T, 'coupes', CUTS)
