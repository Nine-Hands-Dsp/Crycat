"""Assemble les calques du potard (ombre décalée à 45°, couronne, chapeau, index, reflets fixes) à un angle donné."""
import os, math
import numpy as np, cv2
from PIL import Image
K = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets', 'knob')
L = {n: Image.open(os.path.join(K, f'knob_{n}.png')).convert('RGBA') for n in ('shadow', 'crown', 'cap', 'marker', 'highlight')}

def knob(angle_deg, size, shadow_off=0.025, blur_deg=0.0):
    out = Image.new('RGBA', (1024, 1024), (0, 0, 0, 0))
    def rot(im, a): return im.rotate(-a, resample=Image.BICUBIC, center=(511.5, 511.5))
    d = int(round(shadow_off * 1024))
    sh = rot(L['shadow'], angle_deg); s2 = Image.new('RGBA', (1024, 1024), (0, 0, 0, 0)); s2.alpha_composite(sh, (d, d))
    out.alpha_composite(s2)
    stack = Image.new('RGBA', (1024, 1024), (0, 0, 0, 0))
    for n in ('crown', 'cap', 'marker'): stack.alpha_composite(L[n])
    if blur_deg > 0:
        n = max(4, int(math.ceil(blur_deg / 3)) + 1)
        acc = np.zeros((1024, 1024, 4))
        for k in range(n):
            im = np.asarray(rot(stack, angle_deg - blur_deg * k / (n - 1))).astype(float); im[..., :3] *= im[..., 3:4] / 255
            acc += im / n
        a = acc[..., 3:4]; acc[..., :3] = np.where(a > 0, acc[..., :3] / np.maximum(a, 1e-3) * 255, 0)
        out.alpha_composite(Image.fromarray(np.clip(acc, 0, 255).astype(np.uint8), 'RGBA'))
    else:
        out.alpha_composite(rot(stack, angle_deg))
    out.alpha_composite(L['highlight'])
    return out.resize((size, size), Image.LANCZOS)

# ---- potard v2 : ombre, chapeau « spun » et bague fixes (symétriques, les reflets du métal tourné restent face à la
# lumière), seul l'index tourne, avec flou de mouvement
K2 = os.path.join(os.path.dirname(K), 'knob2')
L2 = {n: Image.open(os.path.join(K2, f'knob_{n}.png')).convert('RGBA') for n in ('shadow', 'ring', 'cap', 'marker')}
OUTER2 = 0.8535
def knob2(angle_deg, size, blur_deg=0.0):
    out = Image.new('RGBA', (1024, 1024), (0, 0, 0, 0))
    for n in ('shadow', 'cap', 'ring'): out.alpha_composite(L2[n])
    rot = lambda a: L2['marker'].rotate(-a, resample=Image.BICUBIC, center=(512, 512))
    if blur_deg > 0:
        n = max(4, int(math.ceil(blur_deg / 3)) + 1); acc = np.zeros((1024, 1024, 4))
        for k in range(n):
            im = np.asarray(rot(angle_deg - blur_deg * k / (n - 1))).astype(float); im[..., :3] *= im[..., 3:4] / 255; acc += im / n
        a = acc[..., 3:4]; acc[..., :3] = np.where(a > 0, acc[..., :3] / np.maximum(a, 1e-3) * 255, 0)
        out.alpha_composite(Image.fromarray(np.clip(acc, 0, 255).astype(np.uint8), 'RGBA'))
    else:
        out.alpha_composite(rot(angle_deg))
    return out.resize((size, size), Image.LANCZOS)

def knob2_static(size):
    """ombre + chapeau + bague (fixes) : cuits dans le fond du plugin ; l'index est dessiné par l'éditeur"""
    out = Image.new('RGBA', (1024, 1024), (0, 0, 0, 0))
    for n in ('shadow', 'cap', 'ring'): out.alpha_composite(L2[n])
    return out.resize((size, size), Image.LANCZOS)
