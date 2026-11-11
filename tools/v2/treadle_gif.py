"""Crycat v2 : animation du plateau (pédale d'expression), même principe que la v1 (TreadleWarp) :
perspective exacte du plateau (talon fixe sur la charnière, pointe qui monte et s'élargit), éclairage de la face qui suit
l'inclinaison (lumière en haut à gauche), reflet qui glisse sur le chrome, tranches visibles quand la pointe est levée,
ombre portée qui s'allonge avec la hauteur, fente de charnière qui s'ouvre. Sortie : GIF à 30 images/s."""
import os, math
import numpy as np, cv2
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
base = np.asarray(Image.open(os.path.join(ROOT, 'design', 'apercu_v2b.png')).convert('RGBA')).astype(np.float32)
H, W = base.shape[:2]

PL, PT, PR, PB, RAD = 95, 31, 894, 1762, 66        # plateau (chrome) dans l'image
U = (PR - PL) / 407.1                               # échelle v1 -> image (unités v1 par plateau)
RISE, WIDEN, THICK = 20.0, 1.02, 10.0               # pointe levée : +20 px, +2 % de large, tranche de 10 px

SSm = 4
mk = Image.new('L', (W * SSm, H * SSm), 0)
ImageDraw.Draw(mk).rounded_rectangle((PL * SSm, PT * SSm, (PR + 1) * SSm, (PB + 1) * SSm), RAD * SSm, fill=255)
mask = np.asarray(mk.resize((W, H), Image.LANCZOS), np.float32) / 255.0

plate = base.copy(); plate[..., 3] = mask * 255
pm = plate.copy(); pm[..., :3] *= mask[..., None]          # prémultiplié

def shift(a, dx, dy):
    return cv2.warpAffine(a, np.float32([[1, 0, dx], [0, 1, dy]]), (a.shape[1], a.shape[0]), flags=cv2.INTER_LINEAR, borderValue=0)

yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)

def frame(t):
    sTilt = float(np.clip((0.8 - t) / 0.8, -0.25, 1.0)); lift = max(0.0, sTilt)
    cx = 0.5 * (PL + PR); wid = 1 + (WIDEN - 1) * lift; rise = RISE * lift
    src = np.float32([[PL, PT], [PR, PT], [PR, PB], [PL, PB]])
    dst = np.float32([[cx - (cx - PL) * wid, PT - rise], [cx + (PR - cx) * wid, PT - rise], [PR, PB], [PL, PB]])
    Hm = cv2.getPerspectiveTransform(src, dst)
    wp = cv2.warpPerspective(pm, Hm, (W, H), flags=cv2.INTER_CUBIC, borderValue=0)
    A = np.clip(wp[..., 3] / 255.0, 0, 1)
    topY, botY = PT - rise, PB
    gy = np.clip((botY - yy) / (botY - topY), 0, 1)                 # 1 = pointe, 0 = charnière
    # 1) face : la pointe levée se tourne vers la lumière, enfoncée s'en détourne ; creux sombre près de la charnière
    gain = 1 + 0.13 * sTilt * gy ** 1.3 - 0.07 * lift * (1 - gy) ** 5
    rgb = np.minimum(wp[..., :3] * gain[..., None], wp[..., 3:4])
    bandC, bandW, bandK = 0.10 + 0.55 * t, 0.16, 0.16 + 0.10 * lift
    bpos = (1 - gy) + 0.22 * ((xx - PL) / (PR - PL) - 0.5)
    bnd = bandK * np.exp(-0.5 * ((bpos - bandC) / bandW) ** 2)
    lum = pm[..., :3].mean(-1)
    bnd = bnd * cv2.warpPerspective(np.clip(lum / 160.0, 0.2, 1.0).astype(np.float32), Hm, (W, H))  # le chrome brille, le caoutchouc reste mat
    rgb = rgb + (wp[..., 3:4] - rgb) * bnd[..., None]
    face = np.concatenate([rgb, wp[..., 3:4]], -1)
    # 2) tranches extrudées depuis la silhouette : pointe éclairée, gauche claire, droite dans l'ombre
    out = np.zeros_like(face)
    th = THICK * lift
    if th > 0.3:
        v = 1 - gy
        for k in range(1, int(math.ceil(th)) + 2):
            # pointe : vers le haut, épaisseur pleine au bord de pointe
            up = shift(A, 0, -k) * np.clip(th - (k - 1) + 0.3, 0, 1)
            up *= np.clip(1 - (yy - topY) / 30.0, 0, 1)
            uu = k / max(0.5, th); xr = (xx - PL) / (PR - PL)
            col_t = 208 - 100 * uu - 28 * xr
            fw = 0.55 * th * v
            cov = np.clip(fw - (k - 1) + 0.3, 0, 1)
            left = shift(A, -k, 0) * cov; right = shift(A, k, 0) * cov
            col_l = 178 - 72 * k / np.maximum(0.5, fw) - 25 * v; col_r = 64 - 24 * k / np.maximum(0.5, fw) + 10 * v
            for a_, c_ in ((up, col_t), (left, col_l), (right, col_r)):
                a_ = np.clip(a_ - out[..., 3] / 255.0 * 0, 0, 1) * (1 - A)
                out[..., :3] = out[..., :3] * (1 - a_[..., None]) + (np.clip(c_, 0, 255) * a_)[..., None] * np.array([1.0, 0.99, 1.02])
                out[..., 3] = out[..., 3] * (1 - a_) + 255 * a_
    # face posée sur les tranches (prémultiplié)
    out[..., :3] = face[..., :3] + out[..., :3] * (1 - A[..., None])
    out[..., 3] = face[..., 3] + out[..., 3] * (1 - A)
    # 3) charnière : fente sombre et axe éclairé
    gap = max(1.0, 3.5 * U * lift)
    x0, x1 = PL + 18 * U, PR - 18 * U
    edgeK = np.clip(np.minimum(xx - x0, x1 - xx) / (12 * U), 0, 1)
    ks = np.abs(yy - PB)
    slit = (0.75 * lift) * edgeK * np.clip(1 - ks / (gap + 1), 0, 1)
    axis = (0.35 * lift) * edgeK * np.clip(1 - np.abs(yy - (PB + gap + 1)), 0, 1)
    # 4) ombre portée : décalage et flou proportionnels à la hauteur (lumière en haut à gauche)
    Ao = out[..., 3] / 255.0
    # ombre portée identique à Wharry (PluginEditor.cpp, repère 1020 x 928 -> x WH dans cette image) :
    # décalage (2 + 8 lift, 3 + 11 lift), flou boîte de rayon 3 + 5 lift en 2 passes, force 0,32 + 0,30 lift (+0,10 x
    # pointe enfoncée au-delà du plat) ; contact serré à plat, plus large et décalée quand la pointe se lève
    WH = H / 928.0
    ox, oy = 2 * (2 + 8 * lift) * WH, 2 * (3 + 11 * lift) * WH       # ombre agrandie x2 (même angle que Wharry)
    rad = max(1, round(1.4 * (3 + 5 * lift) * WH))
    sh = cv2.warpAffine(Ao, np.float32([[1, 0, ox], [0, 1, oy]]), (W, H), flags=cv2.INTER_LINEAR, borderValue=0)
    for _ in range(2): sh = cv2.blur(sh, (2 * rad + 1, 2 * rad + 1))
    sh *= (0.32 + 0.30 * lift - 0.10 * min(0.0, sTilt))
    img = base.copy()
    img[..., :3] *= (1 - sh[..., None])
    img[..., :3] = out[..., :3] + img[..., :3] * (1 - Ao[..., None])
    img[..., :3] *= (1 - slit[..., None])
    img[..., :3] = img[..., :3] * (1 - axis[..., None]) + 208 * axis[..., None]
    return img

N = 46
ts = [0.5 - 0.5 * math.cos(2 * math.pi * i / N) for i in range(N)]     # talon -> pointe -> talon, en douceur
frames = []
for i, t in enumerate(ts):
    f = frame(t)
    bg = np.zeros((H, W, 3), np.float32) + np.array([24, 24, 26])
    a = f[..., 3:4] / 255.0
    rgb = f[..., :3] + bg * (1 - a)                                     # couleurs prémultipliées sur fond sombre
    frames.append(Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8)).resize((W * 2 // 5, H * 2 // 5), Image.LANCZOS))
    if i in (0, N // 2): frames[-1].save(os.path.join(ROOT, 'design', f'treadle_t{t:.1f}.png'))
pal = frames[0].quantize(colors=255, method=Image.Quantize.MEDIANCUT)
q = [f.quantize(palette=pal, dither=Image.Dither.FLOYDSTEINBERG) for f in frames]
q[0].save(os.path.join(ROOT, 'design', 'crycat_v2_pedale.gif'), save_all=True, append_images=q[1:], duration=33, loop=0, optimize=False)
print('ok', len(q))
