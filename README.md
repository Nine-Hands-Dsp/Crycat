# Crycat (NINE HANDS | DSP)

Plugin VST3 (Windows / macOS, + AU sur Mac) reproduisant la wah **Dunlop Cry Baby GCB95**, avec modifications, au format **pédale double**.

<p align="center">
  <a href="https://github.com/Nine-Hands-Dsp/Crycat/releases/latest/download/Crycat-VST3-Windows.zip"><img alt="Télécharger pour Windows" src="https://img.shields.io/badge/%E2%AC%87%20T%C3%A9l%C3%A9charger-Windows-0078D6?style=for-the-badge"></a>
  <a href="https://github.com/Nine-Hands-Dsp/Crycat/releases/latest/download/Crycat-VST3-macOS.zip"><img alt="Télécharger pour macOS" src="https://img.shields.io/badge/%E2%AC%87%20T%C3%A9l%C3%A9charger-macOS-111111?style=for-the-badge&logo=apple&logoColor=white"></a>
  <br>
  <a href="https://github.com/Nine-Hands-Dsp/Crycat/releases/latest/download/Crycat-Notice.pdf"><img alt="Télécharger la notice (PDF)" src="https://img.shields.io/badge/%F0%9F%93%96%20Notice-PDF-919496?style=for-the-badge"></a>
  <br>
  <a href="https://github.com/Nine-Hands-Dsp/Crycat/releases/latest"><img alt="Dernière version" src="https://img.shields.io/github/v/release/Nine-Hands-Dsp/Crycat?label=derni%C3%A8re%20version&color=919496"></a>
</p>

- Filtre passe-bande résonant façon inducteur 500 mH : 450 Hz (talon) -> 1,6 kHz (pointe) sur la plage 3 « GCB95 »
- **RANGE** : 6 plages (1 Low / 7 cordes, 2 Dark, 3 GCB95, 4 Vintage V847, 5 Bright, 6 Shriek)
- **Q** (résonance, de large à vocal), **PURR** (saturation de l'inducteur / grain), **BOOST** (0 à +15 dB)
- Inverseur **MAN / AUTO** : en AUTO, la wah s'enclenche dès que la pédale quitte le talon et se coupe après un repos au talon (délai réglable)
- Footswitch ON / OFF avec LED, bypass sans clic
- Pédale d'expression MIDI : aucun CC assigné par défaut (clic droit > MIDI Learn), calibration automatique, sens inversé par défaut,
  aucune saccade (rampe sur l'intervalle mesuré entre deux CC, glissé à 2 pôles, CC 14 bits accepté)
- Compatible **M-Vave Chocolate Plus** : MIDI Learn des footswitches (CC ou note), momentané ou à accrochage, Program Change 1-10 = presets usine
- Écran ambre encastré : plage, état, courbe de réponse en direct, fréquence centrale, Q, boost, course de la pédale
- Barre de presets (10 presets usine) remplacée par la ligne d'état en direct pendant les réglages
- Clic droit (menus au design d'Octopus, ouverts là où l'on clique) : MIDI Learn de chaque commande, réglages de la pédale,
  **Plugin size** (60 % par défaut, 75 %, 100 %, taille par défaut des nouvelles fenêtres), **Glow** (25 / 50 / 75 / 100 %)

## Visuel (v2.0.0)
Façade générée à partir des pièces fournies par l'utilisateur (façade, calques du potard, logo Crycat SVG) :
`tools/v2/make_art_v2.py` produit `background.png` (pédale plein cadre 1870 x 1800, coins refaits, écran encastré, occlusion et
ombres portées, jacks photo), `treadle_down.png` (plateau avec le logo NINE HANDS | DSP), l'index des potards, l'inverseur photo
3 positions, le reflet de la LED sur le footswitch, la LED et son halo, et `tools/layout_v2.json`. Les textes, graduations et le logo
Crycat sont dessinés en vectoriel par l'éditeur (Poppins + SVG). Le plateau est calculé en perspective (tranches, reflet sur le chrome,
ombre portée de Wharry agrandie x2, charnière). Captures réelles de la fenêtre : `tools/render` (outil Linux).

## Build
GitHub Actions (`.github/workflows/build.yml`) : artefacts `Crycat-VST3-Windows` et `Crycat-VST3-macOS`.
Tests du moteur audio : `g++ -O2 -std=c++17 tests/test_dsp.cpp -o test_dsp && ./test_dsp`

- v1.4.2 : menu de taille de fenêtre : « 60 % (default) », 75 %, 100 % (plus de taille en pixels)
- v1.5.0 : MIDI Learn au clic droit sur chaque commande (Clear MIDI, assignations sauvegardées avec le projet)
- v1.6.0 : clic droit > Plugin size > Default size (new windows) : taille par défaut des nouvelles fenêtres au choix, comme dans Octopus
- v1.6.1 : plus aucun CC MIDI assigné par défaut (tout passe par le MIDI Learn)
- v1.6.2 : NINE HANDS | DSP
- v2.0.0 : nouveau design (pédale plein cadre, potards alu à index, écran encastré, inverseur et jacks photo, logo Crycat),
  barre de presets / ligne d'état, menus au design d'Octopus ouverts là où l'on clique, réglage Glow
