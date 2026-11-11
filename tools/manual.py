# CRYCAT (NINE HANDS | DSP) - notice PDF en francais, illustree avec le rendu reel du plugin (couverture minimale commune).
# Usage : python3 tools/manual.py <dossier des captures (tools/render)> <fichier PDF de sortie>
import os, sys, json
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import (BaseDocTemplate, PageTemplate, NextPageTemplate, Frame, Paragraph, Spacer, Image as RLImage,
                                Table, TableStyle, PageBreak, KeepTogether)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOTS, OUT = sys.argv[1], sys.argv[2]
VERSION = "2.0.0"
TMP = os.path.join(ROOT, "tools", "manual_assets"); os.makedirs(TMP, exist_ok=True)
FONTS = os.path.join(ROOT, "assets", "fonts")
for n, f in (("Pop", "Poppins-Regular"), ("PopL", "Poppins-Light"), ("PopM", "Poppins-Medium"), ("PopB", "Poppins-Bold"),
             ("Title", "BarlowCondensed-ExtraBold")):
    pdfmetrics.registerFont(TTFont(n, os.path.join(FONTS, f + ".ttf")))

ACC = colors.HexColor("#D9821C"); ACC_L = colors.HexColor("#FFB040")        # ambre de l'écran et de la LED
DARK = colors.HexColor("#1B1814"); GREY = colors.HexColor("#6B645C"); LIGHT = colors.HexColor("#F7EFE4")

# repères du plugin (unités = image de fond / 2 : 935 x 900), écrits par tools/v2/make_art_v2.py
LAY = json.load(open(os.path.join(ROOT, "tools", "layout_v2.json")))
UW, UH = LAY["units"]

def shot(name): return Image.open(os.path.join(SHOTS, name)).convert("RGB")
src = shot("crycat_100pc_presets.png")
k = src.height / UH

# ---------- capture annotée ----------
rx, ry, rr = LAY["range"]; sm = LAY["small"]; tgx, tgy, _ = LAY["toggle"]; fx, fy = LAY["fs"][:2]; lx, ly = LAY["led"][:2]
g = LAY["glass"]; pl = LAY["pill"]; jy = LAY["jackY"]; bx0, bx1 = LAY["bodyX"]
marks = [(1, 247, 330), (2, rx - 72, ry - 52), (3, (g[0] + g[2]) / 2, g[1] - 16), (4, tgx - 50, tgy),
         (5, sm[0][0] - 50, sm[0][1] + 46), (6, sm[1][0] - 50, sm[1][1] + 46), (7, sm[2][0] + 50, sm[2][1] + 46),
         (8, pl[0] + 14, pl[1] - 14), (9, fx - 62, fy), (10, lx + 26, ly - 22), (11, bx1 - 24, jy - 52), (12, bx0 + 24, jy - 52)]
ann = src.copy(); dr = ImageDraw.Draw(ann)
fnt = ImageFont.truetype(os.path.join(FONTS, "Poppins-Bold.ttf"), 20)
for n, x, y in marks:
    cx, cy, r = x * k, y * k, 15
    dr.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(255, 255, 255), outline=(217, 130, 28), width=3)
    dr.text((cx, cy + 1), str(n), font=fnt, fill=(27, 24, 20), anchor="mm")
annotated = os.path.join(TMP, "crycat_annotated.png"); ann.save(annotated)

def crop_u(im, box): return im.crop(tuple(int(v * k) for v in box))
# plateau talon / pointe
pbox = (0, 0, 470, UH)
ht = Image.new("RGB", (int(470 * k) * 2 + 18, int(UH * k)), (255, 255, 255))
ht.paste(crop_u(shot("crycat_100pc_talon.png"), pbox), (0, 0)); ht.paste(crop_u(shot("crycat_100pc_pointe.png"), pbox), (int(470 * k) + 18, 0))
heeltoe = os.path.join(TMP, "crycat_heeltoe.png"); ht.save(heeltoe)
# écran
screen = os.path.join(TMP, "crycat_screen.png"); crop_u(shot("crycat_100pc_milieu.png"), (g[0] - 12, g[1] - 12, g[2] + 12, g[3] + 12)).save(screen)
# pastille : barre de presets au repos, ligne d'état pendant un réglage
bb = (pl[0] - 8, pl[1] - 8, pl[2] + 8, pl[3] + 8)
_a = crop_u(src, bb); _b = crop_u(shot("crycat_100pc_talon.png"), bb)
bar_img = os.path.join(TMP, "crycat_bar.png")
_s = Image.new("RGB", (_a.width, _a.height * 2 + 12), (255, 255, 255)); _s.paste(_a, (0, 0)); _s.paste(_b, (0, _a.height + 12)); _s.save(bar_img)
# footswitch + LED : bypass / actif
fb = (fx - 70, fy - 70, lx + 50, fy + 70)
on = Image.new("RGB", (int((lx + 50 - fx + 70) * k) * 2 + 16, int(140 * k)), (255, 255, 255))
on.paste(crop_u(shot("crycat_100pc_bypass.png"), fb), (0, 0)); on.paste(crop_u(src, fb), (int((lx + 50 - fx + 70) * k) + 16, 0))
on_img = os.path.join(TMP, "crycat_onoff.png"); on.save(on_img)

# ---------- couverture : pédale détourée (boîtier + jacks, plateau à plat), reflet au sol, halo ambre très doux ----------
c2 = shot("crycat_cover_2x.png")
msk = Image.open(os.path.join(ROOT, "background.png")).getchannel("A").resize(c2.size, Image.LANCZOS)
cut = Image.new("RGBA", c2.size, (0, 0, 0, 0)); cut.paste(c2, (0, 0), msk)
cut = cut.crop(cut.getbbox())
cw, ch = cut.size
pad = int(cw * 0.16)
canvas = Image.new("RGBA", (cw + 2 * pad, int(ch * 1.30) + pad), (0, 0, 0, 255))
yy, xx = np.mgrid[0:canvas.height, 0:canvas.width].astype(np.float64)
gcx, gcy = canvas.width / 2, pad + ch * 0.45
glow = np.exp(-(((xx - gcx) / (cw * 0.62)) ** 2 + ((yy - gcy) / (ch * 0.48)) ** 2)) * 30
edge = np.clip(np.minimum.reduce([xx, canvas.width - 1 - xx, yy, canvas.height - 1 - yy]) / (pad * 0.9), 0, 1)
glow *= edge ** 2
halo = np.dstack([glow * 0.95, glow * 0.55, glow * 0.15, np.full_like(glow, 255)]).astype(np.uint8)
canvas = Image.alpha_composite(canvas, Image.fromarray(halo, "RGBA"))
refl = cut.transpose(Image.FLIP_TOP_BOTTOM)
ra = np.array(refl).astype(np.float64)
fade = np.clip(1 - np.arange(refl.height) / (refl.height * 0.22), 0, 1) ** 1.6 * 0.22
ra[..., 3] *= fade[:, None]
canvas.alpha_composite(Image.fromarray(ra.astype(np.uint8), "RGBA"), (pad, pad + ch + 6))
canvas.alpha_composite(cut, (pad, pad))
canvas = canvas.crop((0, 0, canvas.width, pad + int(ch * 1.20)))
cover = os.path.join(TMP, "crycat_cover_cutout.png"); canvas.convert("RGB").save(cover)

def img(path, width):
    im = Image.open(path); h = width * im.height / im.width
    return RLImage(path, width=width, height=h)

# ---------- styles ----------
st = {
    "h1": ParagraphStyle("h1", fontName="PopB", fontSize=20, leading=24, textColor=ACC, spaceAfter=8, spaceBefore=4, keepWithNext=1),
    "h2": ParagraphStyle("h2", fontName="PopM", fontSize=13, leading=17, textColor=DARK, spaceAfter=4, spaceBefore=10, keepWithNext=1),
    "p": ParagraphStyle("p", fontName="Pop", fontSize=9.6, leading=14, textColor=DARK, spaceAfter=5),
    "tip": ParagraphStyle("tip", fontName="Pop", fontSize=9.0, leading=12.4, textColor=DARK, spaceAfter=3),
    "small": ParagraphStyle("small", fontName="Pop", fontSize=8.2, leading=11.5, textColor=GREY),
    "cell": ParagraphStyle("cell", fontName="Pop", fontSize=8.4, leading=11, textColor=DARK),
    "cellb": ParagraphStyle("cellb", fontName="PopM", fontSize=8.4, leading=11, textColor=DARK),
    "cells": ParagraphStyle("cells", fontName="Pop", fontSize=7.8, leading=10, textColor=DARK),
    "cellbs": ParagraphStyle("cellbs", fontName="PopM", fontSize=7.8, leading=10, textColor=DARK),
}
def P(t, s="p"): return Paragraph(t, st[s])
def bullets(items, s="p"): return [P("&bull;&nbsp;&nbsp;" + i, s) for i in items]
def table(rows, widths, header=True, small=False):
    data = [[P(c, ("cellbs" if small else "cellb") if (header and r == 0) else ("cells" if small else "cell")) for c in row] for r, row in enumerate(rows)]
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    style = [("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#E6DAC9")),
             ("TOPPADDING", (0, 0), (-1, -1), 2 if small else 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 2 if small else 3)]
    if header: style += [("BACKGROUND", (0, 0), (-1, 0), LIGHT), ("LINEBELOW", (0, 0), (-1, 0), 0.8, ACC)]
    t.setStyle(TableStyle(style)); return t

# ---------- données (identiques au code livré : CrycatDSP.h et PluginProcessor.cpp) ----------
RANGES = [("1", "Low / 7-string", 220, 900), ("2", "Dark", 320, 1250), ("3", "GCB95 Classic", 450, 1600),
          ("4", "Vintage (V847)", 480, 2100), ("5", "Bright", 600, 2600), ("6", "Shriek", 750, 3200)]
RANGE_DESC = ["Balayage le plus grave : basse, baryton et 7 cordes accordée en G ou plus bas.", "Balayage plus sombre et rond, jazz et rythmiques douces.",
              "Le balayage d'origine de la Cry Baby GCB95 (par défaut).", "Balayage plus large et ouvert, dans l'esprit de la Vox V847 des débuts.",
              "Pointe plus brillante pour le funk et les sons clairs.", "Balayage le plus aigu : solos hurlants, passe à travers un mix chargé."]
FACTORY = [  # nom, plage, Q, purr, boost, auto, pédale
    ("GCB95 Classic", 3, 40, 20, 0, False, None), ("Voodoo Fuzz Wah (V847)", 4, 50, 30, 20, False, None),
    ("Funk Quack", 5, 65, 10, 15, False, None), ("Shriek Lead", 6, 78, 35, 35, False, None),
    ("Cocked Wah - Mid Honk", 3, 55, 25, 20, False, 55), ("Seven-String Growl", 1, 45, 55, 20, False, None),
    ("Bass Wah", 1, 30, 20, 10, False, None), ("Talking Cat (vocal)", 4, 92, 15, 10, False, None),
    ("Smooth Dark Sweep", 2, 20, 0, 5, False, None), ("Auto-Engage Lead", 3, 50, 25, 25, True, None)]
FACT_DESC = ["La référence : la voix de la Cry Baby d'origine.", "Balayage vintage ouvert, un peu de grain et de boost : fait pour une fuzz placée devant.",
             "« Quack » brillant et serré pour la rythmique funk.", "Balayage aigu, très résonant, avec boost pour les solos.",
             "Wah « bloquée » à mi-course (plateau à 55 %) : médium nasal.", "Plage grave et beaucoup de Purr : grognement épais pour guitares accordées bas.",
             "Plage grave, Q modéré : wah adaptée à la basse.", "Q très élevé pour un effet vocal, qui « parle ».", "Balayage doux et sombre, presque comme un filtre.",
             "Voix classique avec AUTO-ENGAGE : il suffit de bouger la pédale pour activer la wah."]

t = dict(
 lang="FRANÇAIS", sub="Wah vocale",
 intro_t="1. Présentation",
 intro=["<b>Crycat</b> est un plugin NINE HANDS | DSP inspiré de la wah la plus célèbre, la <b>Dunlop Cry Baby GCB95</b>. Comme l'originale, c'est un filtre passe-bande résonant construit autour d'un inducteur de 500 mH : la pointe balaye d'environ <b>450 Hz talon enfoncé à 1,6 kHz pointe enfoncée</b>, avec jusqu'à environ +18 dB de résonance, tandis qu'une partie des graves passe toujours pour garder le corps de la guitare.",
        "Crycat garde cette voix et ajoute les modifications les plus recherchées des Cry Baby plus récentes et des mods DIY : six <b>plages</b> de balayage (RANGE), un <b>Q</b> réglable, une saturation de l'inducteur (<b>PURR</b>), un <b>BOOST</b> propre jusqu'à +15 dB et un mode <b>AUTO-ENGAGE</b> qui active la wah dès que vous bougez la pédale, idéal avec une pédale d'expression branchée sur une M-Vave Chocolate Plus.",
        "Son : vocal, guttural et chantant ; du médium nasal de la « wah bloquée » au « quack » funk et au solo hurlant.",
        "Le visuel est un design original NINE HANDS | DSP : boîtier noir à grain, plateau chromé à caoutchouc rainuré, potards en aluminium tourné, écran ambre encastré. Crycat n'est pas affilié à Dunlop ; « Cry Baby » et « GCB95 » ne servent qu'à décrire le circuit reproduit."],
 inst_t="2. Installation",
 inst=[("Windows", "Cliquez sur le bouton <b>Télécharger Windows</b> de la page GitHub Nine-Hands-Dsp/Crycat (il donne toujours la dernière version), décompressez <b>Crycat-VST3-Windows.zip</b> et copiez le dossier <b>Crycat.vst3</b> dans <b>C:\\Program Files\\Common Files\\VST3</b>."),
       ("macOS", "Cliquez sur <b>Télécharger macOS</b>, décompressez <b>Crycat-VST3-macOS.zip</b> et copiez <b>Crycat.vst3</b> dans <b>~/Bibliothèque/Audio/Plug-Ins/VST3</b>. Si macOS le bloque, tapez <b>xattr -cr ~/Library/Audio/Plug-Ins/VST3/Crycat.vst3</b> dans le Terminal. Le binaire est universel (Apple Silicon et Intel)."),
       ("Reaper", "Options &gt; Préférences &gt; Plug-ins &gt; VST &gt; <b>Re-scan</b>. Le plugin apparaît sous le nom <b>Crycat (NINE HANDS | DSP)</b> ; vos projets faits avec une version précédente gardent leurs réglages. Pour le piloter avec votre pédale MIDI, la piste doit recevoir le MIDI du contrôleur (armement ou monitoring d'entrée, entrée MIDI réglée sur votre appareil, par exemple la M-Vave Chocolate Plus en Bluetooth ou USB).")],
 ov_t="3. Vue d'ensemble de l'interface",
 ov_rows=[["#", "Commande", "Rôle"],
   ["1", "Plateau", "La pédale wah : talon = 0 % (grave), pointe = 100 % (aigu). Souris (tirer vers le bas = appuyer sur la pointe, Maj = réglage fin), molette, double-clic = talon / pointe, pédale MIDI, automation."],
   ["2", "RANGE", "6 plages de balayage. Glisser, molette ou clic direct sur un numéro ; le numéro choisi s'allume en ambre."],
   ["3", "Écran", "Plage, état, courbe de réponse en direct, fréquence centrale, Q, boost et course du plateau. Un clic ouvre le menu des presets."],
   ["4", "MAN · AUTO", "MAN : seul le footswitch active la wah. AUTO : elle s'enclenche quand le plateau quitte le talon."],
   ["5", "Q", "Résonance, de large (Q 2) à très vocale (Q 14)."],
   ["6", "PURR", "Saturation de l'inducteur et grain."],
   ["7", "BOOST", "Gain de sortie, 0 à +15 dB."],
   ["8", "Presets / état", "Barre de presets (flèches, clic = menu) ; ligne d'état à la place tant qu'un réglage bouge."],
   ["9", "Footswitch", "Effet ON / OFF, sans clic."],
   ["10", "LED", "Ambre : wah active ; faible lueur en AUTO en attente."],
   ["11", "IN", "Jack d'entrée (côté droit)."],
   ["12", "OUT", "Jack de sortie (côté gauche)."]],
 on_cap="Bypass, puis wah active : la LED ambre s'allume et éclaire la façade et l'écrou du footswitch.",
 ctl_t="4. Les commandes en détail",
 ctl=[("Plateau", "La fréquence de la pointe suit le plateau sur une échelle logarithmique : le balayage paraît régulier sur toute la course, comme avec le potentiomètre logarithmique d'une vraie wah. Le talon garde davantage de graves, la pointe les amincit, pour le contraste « wah » classique ; la résonance se resserre un peu vers la pointe, comme sur l'originale. À l'écran, le plateau bascule vraiment autour de sa charnière : en se levant, la pointe s'élargit en perspective, ses tranches apparaissent, un reflet glisse sur le chrome et son ombre portée s'étend vers le bas à droite."),
      ("RANGE", "Fixe le début et la fin du balayage (tableau des plages au chapitre 8). La plage 3 est celle de la GCB95 (450 Hz à 1,6 kHz). Les plages graves conviennent à la basse et aux guitares accordées bas ; les plages aiguës percent et hurlent."),
      ("Q", "Sur une vraie Cry Baby, le Q dépend d'une seule résistance ; l'augmenter donne le son plus vocal que beaucoup de guitaristes obtiennent par modification. Q faible : doux, façon filtre. Q élevé : parlant, nasal, très expressif. 40 % par défaut (Q d'environ 4,4, la Cry Baby d'origine)."),
      ("PURR", "Reproduit la saturation de l'inducteur et de l'étage d'entrée : à 0 % le filtre est parfaitement propre, au-delà il ajoute un grain légèrement asymétrique, comprime la résonance sur les attaques fortes et donne une voix plus gutturale, qui « miaule ». 20 % par défaut."),
      ("BOOST", "Comme le booster de la Cry Baby 535Q : compense la perte de volume de la wah ou pousse l'ampli pour les solos. Il ne s'applique que lorsque la wah est active."),
      ("MAN / AUTO", "<b>AUTO-ENGAGE</b> : la wah s'active dès que le plateau quitte le talon (au-delà de 3,5 %) et se coupe après un court repos au talon (400 ms par défaut, réglable au clic droit). Le footswitch reste l'interrupteur principal : s'il est sur OFF, la wah reste coupée. L'inverseur passe brièvement par sa position centrale pendant la bascule.")],
 scr="<b>L'écran</b> affiche la plage et l'état (ON, BYPASS, AUTO = en attente, AUTO ON = enclenchée par la pédale), la courbe de réponse de 80 Hz à 5 kHz (la bande ombrée correspond au balayage de la plage choisie, le point à la pointe actuelle), la fréquence centrale, le Q effectif, le boost et les barres de position du plateau.",
 heeltoe_cap="Plateau talon enfoncé (pointe levée, à gauche) et pointe enfoncée (à droite) : le dessin suit la pédale MIDI et les automations en temps réel.",
 fs_t="5. Footswitch, LED, mode AUTO et pédale d'expression",
 fs=["<b>Footswitch</b> : active / coupe l'effet avec un fondu sans clic. Il bascule dès l'appui et son bouton s'assombrit tant qu'on appuie.",
     "<b>LED</b> : la LED ambre s'allume en fondu quand la wah est active ; la façade autour d'elle et le flanc de l'écrou du footswitch reçoivent sa lumière (intensité du halo : clic droit &gt; <b>Glow</b>). En AUTO, elle luit faiblement tant que Crycat attend que la pédale bouge.",
     "<b>MAN / AUTO</b> : en AUTO, la wah se coupe après un repos au talon : clic droit &gt; <b>Switch off after resting on the heel</b> (150, 300, 400, 800 ou 1500 ms).",
     "<b>Pédale d'expression</b> : aucun CC n'est assigné par défaut : clic droit sur le plateau &gt; <b>MIDI Learn: Wah pedal</b>, puis bougez votre pédale. <b>Le sens de la pédale est inversé par défaut</b> (clic droit &gt; <b>Invert pedal direction</b> coché) : décochez-le si le plateau part dans le mauvais sens. Autres choix : <b>Calibrate</b> (balayez la pédale entièrement pendant 6 secondes), <b>Reset pedal calibration</b> et <b>Pedal glide</b> (0, 8, 15, 30, 60 ou 120 ms ; 15 ms par défaut).",
     "<b>Mouvement sans saccade</b> : Crycat mesure le temps entre deux messages de votre pédale et glisse vers chaque nouvelle position pendant ce temps, puis lisse le résultat ; fréquence, Q, Purr et Boost sont aussi lissés. Les pédales 14 bits (CC n + CC n+32) sont prises en charge.",
     "<b>Course de la pédale</b> : beaucoup de pédales n'envoient jamais exactement 0 et 127 (une M-Audio EX-P sur une M-Vave Chocolate Plus envoie souvent 2 à 116). Crycat apprend tout seul la course réelle : talon = exactement 0 %, pointe = exactement 100 %. Le menu clic droit affiche la course utilisée (par ex. <i>auto 2 - 116</i>) ; une calibration manuelle reste prioritaire."],
 midi_t="6. MIDI",
 midi=["<b>MIDI Learn sur toutes les commandes</b> : clic droit sur une commande (plateau, RANGE ou l'un de ses numéros, Q, PURR, BOOST, MAN / AUTO, footswitch). Le menu affiche <b>MIDI Learn: &lt;Nom&gt; (CC n / none)</b>, <b>Clear MIDI: &lt;Nom&gt;</b> et, tant qu'un apprentissage est en attente, <b>Cancel MIDI learn</b>. Bougez ensuite une commande de votre contrôleur : la ligne d'état affiche <b>MIDI LEARN: move a control for &lt;Nom&gt;</b>, puis <b>&lt;Nom&gt; = CC n</b> pendant 2 secondes.",
       "Un clic droit hors des commandes ouvre le menu général avec un sous-menu <b>MIDI</b> : <b>Learn</b> pour chacune des 7 commandes, <b>Cancel MIDI learn</b> et <b>Clear all MIDI assignments</b>. Un numéro de CC ne pilote qu'une seule commande ; MAN / AUTO et le footswitch peuvent aussi apprendre une <b>note</b>. Crycat écoute tous les canaux MIDI ; les assignations sont sauvegardées avec le projet."],
 midi_hdr=["Commande", "Type"],
 midi_rows=[["Wah pedal (plateau)", "Continu 0-127 (talon à pointe), calibration, course automatique, inversion (active par défaut), glissé, CC 14 bits"],
            ["Range selector", "6 positions : la course 0-127 est découpée en 6 zones égales"],
            ["Q / Purr", "Continu 0-127 = 0-100 %"], ["Boost", "Continu 0-127 = 0 à +15 dB"],
            ["MAN / AUTO switch", "CC ou note : momentané (chaque appui bascule) ou à accrochage (127 = AUTO, 0 = MAN)"],
            ["ON / OFF footswitch", "CC ou note : momentané ou à accrochage (127 = ON, 0 = OFF)"]],
 midi2=["<b>Messages des commutateurs</b> : clic droit sur le footswitch ou l'inverseur : <b>Momentary (each press toggles)</b> ou <b>Latching (127 = ON, 0 = OFF)</b>.",
        "<b>Program Change</b> : PC 1 à 10 chargent les 10 presets usine (clic droit &gt; <b>Respond to MIDI Program Change (PC 1-10)</b>, actif par défaut).",
        "<b>M-Vave Chocolate Plus</b> : branchez votre pédale d'expression sur son entrée EXP, faites un MIDI Learn du plateau, puis apprenez un footswitch de la Chocolate sur le footswitch de Crycat et éventuellement un autre sur MAN / AUTO ; son mode Program Change charge directement les presets.",
        "Chaque commande est aussi un paramètre du DAW, automatisable dans Reaper."],
 win_t="7. Fenêtre",
 win=["Crycat utilise le format pédale double de NINE HANDS | DSP : la fenêtre montre la pédale plein cadre (visuel de 1870 × 1800 px), textes, graduations et logo Crycat dessinés en vectoriel, nets à toutes les tailles. Elle s'ouvre à <b>60 %</b> et ne peut jamais être réduite en dessous. Clic droit &gt; <b>Plugin size</b> : <b>60 %</b>, <b>75 %</b> ou <b>100 %</b>, « (default) » indiquant la taille par défaut ; <b>Default size (new windows)</b> choisit la taille d'ouverture de toutes les nouvelles fenêtres de Crycat (réglage commun à toutes les instances). La taille choisie pour une instance est enregistrée avec le projet. Vous pouvez aussi tirer le coin en bas à droite (proportions conservées).",
      "La <b>barre de presets</b> et la <b>ligne d'état</b> partagent la même pastille. Au repos, elle affiche le preset avec ses flèches (précédent / suivant ; clic sur le nom = menu des presets ; molette). Dès qu'un réglage bouge (souris, molette, pédale, automation, MIDI), la ligne d'état prend sa place en fondu et affiche les valeurs en direct (PEDAL, Q, PURR, BOOST en %) ou les messages du MIDI Learn et de la calibration ; 2,5 s après le dernier mouvement, la barre de presets revient. Un clic sur la pastille la fait revenir tout de suite.",
      "Les menus clic droit s'ouvrent à l'endroit du clic. Clic droit &gt; <b>Glow</b> règle l'intensité du halo de la LED (25, 50, 75 ou 100 %, réglage commun à toutes les fenêtres)."],
 bar_cap="Barre de presets au repos, ligne d'état pendant un réglage.",
 pre_t="8. Presets et plages",
 pre=["Utilisez les flèches de la barre de presets, cliquez sur son nom ou sur l'écran, ou passez par le menu de presets de votre DAW. Le même menu permet de choisir directement une plage (<b>Sweep range</b>)."],
 rng_hdr=["#", "Plage", "Talon", "Pointe", "Usage"],
 fac_hdr=["PC", "Preset", "Plage", "Q / Purr / Boost (%)", "Description"],
 tips_t="9. Conseils d'utilisation",
 tips=["Dans Reaper, placez Crycat <b>avant</b> votre simulateur d'ampli (par exemple avant Ampire, suivi d'Impulse pour le baffle), comme une vraie wah devant l'ampli. Avec une fuzz, essayez les deux ordres : wah avant la fuzz = plus doux, fuzz avant la wah = plus hurlant.",
       "7 cordes accordée en G ou plus bas : plage 1 (220 Hz à 900 Hz) et un peu de PURR pour des graves épais et grognants ; plage 2 pour les rythmiques.",
       "Pour une « wah bloquée », laissez le plateau vers 40-60 % (ou chargez <i>Cocked Wah</i>) et montez le Q.",
       "Si la pédale vous semble nerveuse, montez Pedal glide à 30 ms ; pour le funk rapide, gardez 8-15 ms.",
       "Apprenez le Q ou le BOOST sur une deuxième pédale d'expression pour jouer avec la résonance en direct."],
 tech_t="10. Caractéristiques techniques",
 tech=[["Format", "VST3 (Windows 64 bits, macOS universel), AU également sur macOS"],
       ["Canaux", "Entrée et sortie mono ou stéréo (chaque canal est filtré)"],
       ["Latence", "0 échantillon"], ["Balayage", "de 220 Hz à 3,2 kHz selon la plage (GCB95 : 450 Hz à 1,6 kHz)"],
       ["Q / Boost", "Q de 2 à 14 ; boost de 0 à +15 dB"],
       ["MIDI", "MIDI Learn sur les 7 commandes (sauvegardé avec le projet), aucun CC assigné par défaut, pédale inversée par défaut, CC 14 bits, notes pour les commutateurs, Program Change 1-10, tous canaux"],
       ["Fenêtre", "60 % / 75 % / 100 %, taille par défaut des nouvelles fenêtres au choix, jamais sous 60 %, Glow 25 à 100 % ; anti-gel v2 sous Windows"],
       ["Processeur", "moins de 1 % d'un cœur à 48 kHz pour le son"]])

W = A4[0] - 36 * mm
LOGO_PNG = os.path.join(TMP, "nine_hands_logo_blanc.png")

def story():
    f = [NextPageTemplate("p"), Spacer(1, 1), PageBreak()]
    f.append(P(t["intro_t"], "h1")); f += [P(x) for x in t["intro"]]
    f.append(P(t["inst_t"], "h1"))
    for h, x in t["inst"]: f.append(P(h, "h2")); f.append(P(x))
    f.append(PageBreak())
    f.append(P(t["ov_t"], "h1"))
    f.append(img(annotated, 130 * mm))
    f.append(Spacer(1, 3 * mm))
    f.append(table(t["ov_rows"], [9 * mm, 30 * mm, W - 39 * mm], small=True))
    f.append(Spacer(1, 3 * mm))
    f.append(KeepTogether([img(on_img, 80 * mm), P(t["on_cap"], "small")]))
    f.append(PageBreak())
    f.append(P(t["ctl_t"], "h1"))
    for h, x in t["ctl"]: f.append(P(h, "h2")); f.append(P(x))
    sc = Table([[[P(t["scr"])], [img(screen, 52 * mm)]]], colWidths=[W - 56 * mm, 56 * mm])
    sc.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (0, 0), 0)]))
    f.append(Spacer(1, 2 * mm)); f.append(sc)
    f.append(KeepTogether([img(heeltoe, 110 * mm), P(t["heeltoe_cap"], "small")]))
    f.append(P(t["fs_t"], "h1")); f += bullets(t["fs"])
    f.append(P(t["midi_t"], "h1")); f += [P(x) for x in t["midi"]]
    f.append(KeepTogether([table([t["midi_hdr"]] + t["midi_rows"], [40 * mm, W - 40 * mm])]))
    f.append(Spacer(1, 2 * mm)); f += bullets(t["midi2"])
    f.append(P(t["win_t"], "h1")); f.append(P(t["win"][0]))
    wt = Table([[[P(t["win"][1]), P(t["win"][2])], [img(bar_img, 66 * mm), P(t["bar_cap"], "small")]]], colWidths=[W - 70 * mm, 70 * mm])
    wt.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (0, 0), 0)]))
    f.append(wt)
    f.append(P(t["pre_t"], "h1")); f += [P(x) for x in t["pre"]]
    rows = [t["rng_hdr"]] + [[n, "<b>" + nm + "</b>", f"{lo} Hz", f"{hi / 1000:.2f} kHz".replace(".", ","), RANGE_DESC[i]] for i, (n, nm, lo, hi) in enumerate(RANGES)]
    f.append(table(rows, [7 * mm, 30 * mm, 16 * mm, 18 * mm, W - 71 * mm], small=True))
    f.append(Spacer(1, 3 * mm))
    rows = [t["fac_hdr"]]
    for i, (n, rg, q, pu, bo, au, pd) in enumerate(FACTORY):
        extra = (" ; AUTO" if au else "") + (f" ; plateau {pd} %" if pd is not None else "")
        rows.append([str(i + 1), "<b>" + n + "</b>", str(rg), f"{q} / {pu} / {bo}{extra}", FACT_DESC[i]])
    f.append(table(rows, [8 * mm, 36 * mm, 11 * mm, 30 * mm, W - 85 * mm], small=True))
    f.append(KeepTogether([P(t["tips_t"], "h1")] + bullets(t["tips"], "tip") +
                          [P(t["tech_t"], "h1"), table(t["tech"], [28 * mm, W - 28 * mm], header=False, small=True)]))
    return f

def deco(c, doc):
    c.saveState()
    c.setFillColor(DARK); c.rect(0, A4[1] - 6 * mm, A4[0], 6 * mm, stroke=0, fill=1)
    c.setFillColor(ACC); c.rect(0, A4[1] - 6.8 * mm, A4[0], 0.8 * mm, stroke=0, fill=1)
    c.setFont("Pop", 7.5); c.setFillColor(GREY)
    c.drawString(18 * mm, 10 * mm, "Crycat (NINE HANDS | DSP) · v" + VERSION)
    c.drawRightString(A4[0] - 18 * mm, 10 * mm, str(doc.page))
    c.restoreState()

doc = BaseDocTemplate(OUT, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=18 * mm,
                      title="Crycat - Notice v" + VERSION, author="NINE HANDS | DSP")
# ---- Couverture « minimale » (modèle 6, validé nov. 2026) : gabarit fixe commun à toutes les notices ----
COVER_NAME = "CRYCAT"
PEDAL_H, PEDAL_MAXW, PEDAL_TOP = 82 * mm, 115 * mm, 84 * mm
LANG_TOP = 18 * mm
NAME_TOP, NAME_PT = 194 * mm, 30
SUB_TOP, SUB_PT = 208 * mm, 10
LOGO_W, LOGO_BOTTOM = 38 * mm, 22 * mm
BAND_H = 3 * mm
def cover_bg(c, doc):
    c.saveState(); c.setFillColor(colors.black); c.rect(0, 0, A4[0], A4[1], stroke=0, fill=1)
    c.setFillColor(ACC); c.rect(0, 0, A4[0], BAND_H, stroke=0, fill=1)
    def line(text, top, font, size, cs, col):
        w = pdfmetrics.stringWidth(text, font, size) + cs * (len(text) - 1)
        tt = c.beginText((A4[0] - w) / 2, A4[1] - top - size * 0.8); tt.setFont(font, size); tt.setCharSpace(cs)
        tt.setFillColor(col); tt.textOut(text); c.drawText(tt)
    line(t["lang"], LANG_TOP, "PopM", 8.5, 0, ACC_L)
    ci = Image.open(cover); iw, ih = ci.size
    cw_ = iw / 1.32; ch_ = (ih - int(cw_ * 0.16)) / 1.2; pad_ = int(cw_ * 0.16)     # géométrie de crycat_cover_cutout.png
    kk = min(PEDAL_H / ch_, PEDAL_MAXW / cw_)
    dw, dh = iw * kk, ih * kk
    y0 = A4[1] - (PEDAL_TOP + (PEDAL_H - ch_ * kk) / 2) + pad_ * kk
    c.drawImage(cover, (A4[0] - dw) / 2, y0 - dh, dw, dh)
    line(COVER_NAME, NAME_TOP - NAME_PT * 0.02, "Title", NAME_PT, NAME_PT * 0.5, colors.white)
    line(t["sub"], SUB_TOP, "Pop", SUB_PT, 1.5, colors.HexColor("#BDC4B8"))
    lw, lh = Image.open(LOGO_PNG).size
    c.drawImage(LOGO_PNG, (A4[0] - LOGO_W) / 2, LOGO_BOTTOM, LOGO_W, LOGO_W * lh / lw, mask="auto")
    c.restoreState()
doc.addPageTemplates([PageTemplate(id="cover", frames=[Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="fc")], onPage=cover_bg),
                      PageTemplate(id="p", frames=[Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="f")], onPage=deco)])
doc.build(story())
print(OUT)
