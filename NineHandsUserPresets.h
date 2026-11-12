#pragma once
#include <juce_audio_processors/juce_audio_processors.h>
#include "NineHandsFolder.h"

// NINE HANDS | DSP (fichier commun, nov. 2026) : presets utilisateur a 9 emplacements, comme Doorn.
// Fichier : Nine Hands DSP/<Plugin>/UserPresets.xml (commun a toutes les instances du plugin).
// Chaque preset garde la valeur de tous les parametres du plugin, sauf ceux de la liste « skip »
// (reglages de fonctionnement : bypass, sens de la pedale, reponse MIDI...).
namespace NineHandsUserPresets
{
    constexpr int numSlots = 9;

    inline juce::File file (const juce::String& plugin)
    {
        return juce::File::getSpecialLocation (juce::File::userApplicationDataDirectory)
                 .getChildFile (nhd::folderName()).getChildFile (plugin).getChildFile ("UserPresets.xml");
    }

    inline bool skipped (const juce::String& id, const juce::StringArray& skip) { return skip.contains (id); }

    inline bool save (juce::AudioProcessor& p, const juce::String& plugin, int slot, const juce::StringArray& skip = {})
    {
        if (slot < 1 || slot > numSlots) return false;
        auto f = file (plugin);
        f.getParentDirectory().createDirectory();
        std::unique_ptr<juce::XmlElement> root;
        if (f.existsAsFile()) root = juce::XmlDocument::parse (f);
        if (root == nullptr || ! root->hasTagName ("UserPresets")) root = std::make_unique<juce::XmlElement> ("UserPresets");
        for (auto* e = root->getFirstChildElement(); e != nullptr; e = e->getNextElement())
            if (e->getIntAttribute ("slot") == slot) { root->removeChildElement (e, true); break; }
        auto* e = root->createNewChildElement ("Preset");
        e->setAttribute ("slot", slot);
        for (auto* prm : p.getParameters())
            if (auto* rp = dynamic_cast<juce::RangedAudioParameter*> (prm))
                if (! skipped (rp->getParameterID(), skip))
                    e->setAttribute (rp->getParameterID(), (double) rp->convertFrom0to1 (rp->getValue()));
        return root->writeTo (f);
    }

    // a appeler depuis le thread de messages (setValueNotifyingHost)
    inline bool load (juce::AudioProcessor& p, const juce::String& plugin, int slot)
    {
        const auto f = file (plugin);
        if (! f.existsAsFile()) return false;
        auto root = juce::XmlDocument::parse (f);
        if (root == nullptr) return false;
        for (auto* e = root->getFirstChildElement(); e != nullptr; e = e->getNextElement())
            if (e->getIntAttribute ("slot") == slot)
            {
                for (auto* prm : p.getParameters())
                    if (auto* rp = dynamic_cast<juce::RangedAudioParameter*> (prm))
                        if (e->hasAttribute (rp->getParameterID()))
                        {
                            rp->beginChangeGesture();
                            rp->setValueNotifyingHost (rp->convertTo0to1 ((float) e->getDoubleAttribute (rp->getParameterID())));
                            rp->endChangeGesture();
                        }
                return true;
            }
        return false;
    }

    inline bool exists (const juce::String& plugin, int slot)
    {
        const auto f = file (plugin);
        if (! f.existsAsFile()) return false;
        if (auto root = juce::XmlDocument::parse (f))
            for (auto* e = root->getFirstChildElement(); e != nullptr; e = e->getNextElement())
                if (e->getIntAttribute ("slot") == slot) return true;
        return false;
    }

    // sous-menus « Load user preset » (idLoad + n) et « Save user preset » (idSave + n), n = 1..9
    inline void addMenus (juce::PopupMenu& menu, const juce::String& plugin, int idLoad, int idSave, int currentUserSlot)
    {
        juce::PopupMenu load, save;
        for (int s = 1; s <= numSlots; ++s)
        {
            const bool ex = exists (plugin, s);
            load.addItem (idLoad + s, "User " + juce::String (s) + (ex ? "" : "  (empty)"), ex, currentUserSlot == s);
            save.addItem (idSave + s, "User " + juce::String (s) + (ex ? "  (overwrite)" : ""));
        }
        menu.addSubMenu ("Load user preset", load);
        menu.addSubMenu ("Save user preset", save);
    }
}
