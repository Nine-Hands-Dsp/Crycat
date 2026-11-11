"""Crycat v2 : remise en forme des calques de potard fournis (ChatGPT, nov. 2026).
Défauts mesurés : calques ovales (rapport 1,033, plus hauts que larges), centrés en (536, 534) au lieu de (512, 512),
index décalé de 6,5 px à droite de l'axe et trop long (déborde sur la couronne), chapeau qui recouvre toute la couronne
(même diamètre extérieur), dégradés coniques du chapeau qui tourneraient avec lui, reflets éclairés d'en haut à DROITE.
Corrections : recentrage + mise au rond (étirement horizontal x1,033 autour du centre), index recentré et raccourci,
chapeau découpé au diamètre intérieur de la couronne et aplani (variations angulaires retirées, stries gardées),
reflets tournés de -90° (lumière en haut à gauche, à 45°)."""
import os, sys, math
import numpy as np, cv2
from PIL import Image

IN = sys.argv[1]; OUT = sys.argv[2]
N = 1024
CX, CY = 536.3, 534.6            # centre mesuré (ellipses du chapeau, de la couronne et de l'ombre)
KX = 903.6 / 874.4               # mise au rond : largeur ramenée à la hauteur
R_OUT = 903.6 / 2                # rayon extérieur (après mise au rond)
SC = 0.96 * 512 / R_OUT * 0.92   # le potard occupe ~88 % du cadre : marge pour l'ombre décalée

def load(name): return np.asarray(Image.open(os.path.join(IN, name)).convert('RGBA')).astype(np.float32)

def canon(a, cx=CX, cy=CY, extra_rot=0.0):
    """centre (cx, cy) -> centre du cadre, étirement horizontal KX (mise au rond), échelle SC, rotation éventuelle"""
    pm = a.copy(); pm[..., :3] *= pm[..., 3:4] / 255.0
    c, s = math.cos(math.radians(extra_rot)), math.sin(math.radians(extra_rot))
    # M = T(512) . S(SC) . R . Sx(KX) . T(-c)
    A = np.array([[SC * KX * c, -SC * s], [SC * KX * s, SC * c]])
    t = np.array([512, 512]) - A @ np.array([cx, cy])
    M = np.hstack([A, t[:, None]]).astype(np.float32)
    o = cv2.warpAffine(pm, M, (N, N), flags=cv2.INTER_CUBIC, borderValue=0)
    o = np.clip(o, 0, 255)
    al = o[..., 3:4] / 255.0
    o[..., :3] = np.where(al > 1e-4, o[..., :3] / np.maximum(al, 1e-4), 0)
    return o

def save(a, name): Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGBA').save(os.path.join(OUT, name))

yy, xx = np.mgrid[0:N, 0:N].astype(np.float32)
rr = np.hypot(xx - 511.5, yy - 511.5)
R1 = R_OUT * SC                                   # rayon extérieur dans le cadre
crown = canon(load('c5add56f-image.png'))
# rayon intérieur de la couronne (bord du trou) mesuré dans le cadre
al = crown[..., 3] > 128
prof = [al[(rr > r - 0.5) & (rr < r + 0.5)].mean() for r in range(0, 512)]
R_IN = next(r for r in range(0, 512) if prof[r] > 0.5)
print('rayon ext', round(R1, 1), 'rayon int couronne', R_IN)

cap = canon(load('e0a095ca-image.png'))
# découpe au rayon intérieur de la couronne (+2 px sous la couronne), bord adouci
cap[..., 3] *= np.clip((R_IN + 2.0 - rr) / 1.2, 0, 1)
# aplanir : retirer la variation angulaire basse fréquence (reflets coniques), garder les stries et le profil radial
L = cap[..., :3].mean(2)
th = np.arctan2(yy - 511.5, xx - 511.5)
ri = np.clip(rr.astype(int), 0, 511)
m = cap[..., 3] > 200
rad_mean = np.bincount(ri[m], L[m], minlength=512) / np.maximum(np.bincount(ri[m], minlength=512), 1)
rad_mean = cv2.GaussianBlur(rad_mean.reshape(1, -1).astype(np.float32), (0, 0), 2).ravel()
low = cv2.GaussianBlur(L, (0, 0), 18)
low_rad = cv2.GaussianBlur(rad_mean[ri], (0, 0), 18)
gain = np.where(m, low_rad / np.maximum(low, 1), 1.0)[..., None]
cap[..., :3] = np.clip(cap[..., :3] * gain, 0, 255)
save(cap, 'knob_cap.png'); save(crown, 'knob_crown.png')

sh = canon(load('365953a6-image.png'))
sh[..., 3] = np.clip(sh[..., 3] * 1.9, 0, 255)   # ombre lisible sur la peinture noire
save(sh, 'knob_shadow.png')
hl = canon(load('109e8263-image.png'), extra_rot=-90.0)
hl[..., 3] *= 0.55          # reflets dosés : l'index noir reste noir sous la lumière
save(hl, 'knob_highlight.png')

mk = load('2307b301-image.png')
# index : recentré sur l'axe vertical (x = 536,3) puis raccourci pour rester sur le chapeau
ys, xs = np.where(mk[..., 3] > 128)
mk = np.roll(mk, int(round(CX - xs.mean())), axis=1)
mk = canon(mk)
mk[..., 3] *= np.clip((R_IN - 14 - rr) / 2.0, 0, 1)
save(mk, 'knob_marker.png')
ys, xs = np.where(mk[..., 3] > 128)
print('index x', round(xs.mean(), 1), 'y', ys.min(), ys.max())

# contrôles : ellipses ajustées et direction des reflets
for name, arr, thr in (('chapeau', cap, 128), ('couronne', crown, 128), ('ombre', sh, 50)):
    c, _ = cv2.findContours((arr[..., 3] > thr).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    (x, y), (a, b), _ = cv2.fitEllipse(max(c, key=cv2.contourArea))
    print(f'{name}: centre ({x:.1f}, {y:.1f}) axes {a:.1f} x {b:.1f} rapport {max(a, b) / min(a, b):.4f}')
a = hl[..., 3]
for deg in (-135, -90, -45, 0, 45, 90, 135, 180):
    t = math.radians(deg)
    v = np.mean([a[int(512 + r * math.sin(t)), int(512 + r * math.cos(t))] for r in range(int(R_IN * 0.75), int(R1), 3)])
    print('reflet', deg, round(float(v), 1))
