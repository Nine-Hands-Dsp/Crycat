#pragma once
#include "PluginProcessor.h"
#include "NineHandsWindow.h"

class PedalView;

class CrycatEditor : public juce::AudioProcessorEditor
{
public:
    explicit CrycatEditor (CrycatProcessor&);
    ~CrycatEditor() override;
    void paint (juce::Graphics&) override;
    void resized() override;
    void parentHierarchyChanged() override;
    void visibilityChanged() override;
    int  getScaleIndex() const;          // 0, 1, 2 = 60 % (défaut d'origine, aussi la taille minimale), 75 %, 100 %  (-1 = taille libre)
    void setScaleIndex (int idx);        // change la taille et l'enregistre pour cette instance
    void applyScaleIndex (int idx);      // change la taille sans l'enregistrer (ouverture à la taille par défaut choisie)
    juce::PopupMenu buildContextMenu (int learnIdx = -1);   // menu clic droit (aussi pour l'outil de contrôle des menus)
    NineHandsWindow::HostLock hostLock;  // fenêtre du DAW : jamais sous 60 %, jamais au-delà de 150 %

private:
    friend class PedalView;              // son timer surveille le moteur de rendu (anti-gel v2)
    void useSoftwareRenderer();          // applique le moteur logiciel (Windows) ; repaint si la fenêtre hôte a changé
    void checkRenderer();                // depuis le timer : seulement si la fenêtre a changé ou au plus 1 fois / s
    void resetRenderer();                // chien de garde : oublie la fenêtre mémorisée et réapplique tout
    void* lastPeer = nullptr;
    double lastRendererCheckMs = 0.0;
    CrycatProcessor& proc;
    std::unique_ptr<PedalView> view;
    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (CrycatEditor)
};
