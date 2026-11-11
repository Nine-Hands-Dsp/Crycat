"""Potard v2 (calques fournis, nov. 2026) : chapeau alu « spun », bague noire, ombre, index.
Corrections : chaque calque est ramené à un cercle parfait centré en 512 (les PNG fournis sont ovales de ~2 % et
décentrés de ~4 px), uniquement par réduction (aucun agrandissement), bague posée 2 px sur le bord du chapeau,
index recentré exactement sur l'axe de rotation. Sortie : assets/knob2/knob_{shadow,ring,cap,marker}.png"""
import os
import numpy as np, cv2
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'in', 'knob2'); OUT = os.path.join(ROOT, 'assets', 'knob2'); os.makedirs(OUT, exist_ok=True)
load = lambda n: np.asarray(Image.open(os.path.join(SRC, n + '.png')).convert('RGBA')).astype(np.float32)

def ellipses(al, th=128):
    cs, _ = cv2.findContours((al > th).astype(np.uint8), cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    return [cv2.fitEllipse(c) for c in sorted(cs, key=cv2.contourArea, reverse=True)[:2]]

def warp(a, c, sx, sy, dx=0.0):
    """prémultiplié : T(512).S(sx,sy).T(-c)"""
    M = np.float32([[sx, 0, 512 - sx * c[0] + dx], [0, sy, 512 - sy * c[1]]])
    p = a.copy(); p[..., :3] *= p[..., 3:4] / 255
    w = cv2.warpAffine(p, M, (1024, 1024), flags=cv2.INTER_AREA if max(sx, sy) <= 1 else cv2.INTER_CUBIC, borderValue=0)
    w[..., :3] = np.where(w[..., 3:4] > 0.5, w[..., :3] / np.maximum(w[..., 3:4], 1e-3) * 255, 0)
    return np.clip(w, 0, 255)

cap, ring, sh, mk = load('cap'), load('ring'), load('shadow'), load('marker')
(cc, (cw, chh), _), = ellipses(cap[..., 3])[:1]
(ro, (row, roh), _), (ri, (riw, rih), _) = ellipses(ring[..., 3])
D_CAP = min(cw, chh)                                   # diamètre du chapeau : son petit axe -> aucune mise à l'échelle > 1
D_RIN = D_CAP - 4                                       # la bague recouvre 2 px du bord du chapeau
csx, csy = D_CAP / cw, D_CAP / chh
rsx, rsy = D_RIN / riw, D_RIN / rih
cap2 = warp(cap, cc, csx, csy)
ring2 = warp(ring, ri, rsx, rsy)
sh2 = warp(sh, ri, rsx, rsy)                            # l'ombre suit la bague (son décalage bas-droite d'origine est gardé)
# index : même transformation que le chapeau, puis recentré sur l'axe
mk2 = warp(mk, cc, csx, csy)
ys, xs = np.nonzero(mk2[..., 3] > 128); mx = 0.5 * (xs.min() + xs.max())
mk2 = warp(mk2, (512, 512), 1.0, 1.0, dx=512 - mx)
# teinte du footswitch (nickel légèrement chaud), mesurée en Lab sur l'aperçu : chapeau L 57,5 -> 54,7, contraste x0,91,
# a +0,6, b +2,2
def tint(a, L0=57.46, L1=54.72, k=12.45 / 13.64, da=0.60, db=2.20):
    lab = cv2.cvtColor(np.ascontiguousarray(a[..., :3] / 255.0, np.float32), cv2.COLOR_RGB2LAB)
    lab[..., 0] = np.clip((lab[..., 0] - L0) * k + L1, 0, 100); lab[..., 1] += da; lab[..., 2] += db
    out = a.copy(); out[..., :3] = np.clip(cv2.cvtColor(lab, cv2.COLOR_LAB2RGB) * 255, 0, 255); return out
cap2 = tint(cap2)
for n, a in (('cap', cap2), ('ring', ring2), ('shadow', sh2), ('marker', mk2)):
    Image.fromarray(a.astype(np.uint8), 'RGBA').save(os.path.join(OUT, f'knob_{n}.png'))
# contrôle
for n, a in (('cap', cap2), ('ring', ring2)):
    for (c, (w, h), _) in ellipses(a[..., 3]): print(n, 'centre', np.round(c, 2), 'axes', round(w, 1), round(h, 1), 'ovale', round(max(w, h) / min(w, h), 4))
ys, xs = np.nonzero(mk2[..., 3] > 128); print('index x', 0.5 * (xs.min() + xs.max()), 'y', ys.min(), ys.max())
print('rayon extérieur / cadre', round(max(row * rsx, roh * rsy) / 2 / 512, 4))
