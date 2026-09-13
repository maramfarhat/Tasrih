# Tasrih — Déclaration mensuelle Tunisie

## Flux

1. **Scan** carte d’identification fiscale + extrait RNE  
2. **Profil entreprise** (vérifiable / éditable)  
3. **Factures** (Fatoora démo ou import) → calcul TVA + champs  
4. **Formulaire** officiel `mensuelle2026.pdf` (12 pages) prérempli  

## Lancer

Linux / macOS :

- Tout : `./start.sh`
- Backend seul : `./start-backend.sh` → http://127.0.0.1:8010
- Frontend seul : `./start-frontend.sh` → http://localhost:5180

Windows : `start-backend.bat` et `start-frontend.bat`.

`.env` à la racine : `GROQ_API_KEY=...` (voir `backend/app/config.py`).

## Assistant (Karim)

Un assistant conversationnel en français guide l'utilisateur écran par écran.

- **Avatar 3D** (three.js) : `frontend/public/avatars/avatarsdk.glb`, corps animé +
  synchronisation labiale pilotée par l'amplitude de la voix (`visemes` Oculus + ARKit).
- **Voix** : Edge TTS (voix neuronale française, en ligne) avec prosodie adaptée au ton du
  message — chaleureux, neutre, succès, avertissement, erreur. Repli automatique sur
  Piper (local, hors ligne) puis sur la voix du navigateur.
- Config : `TTS_ENGINE=edge|piper`, `TTS_VOICE=fr-FR-RemyMultilingualNeural` (`.env`).
- **Cerveau** : Groq (`.env`). Routes : `POST /agent/chat`, `POST /agent/guidance`,
  `POST /agent/tts`.
- Le widget est proactif : il prend la parole à chaque changement d'étape et met en
  évidence le champ concerné.

Astuce dev : `http://localhost:5180/?agent=open` ouvre le panneau de l'assistant directement.
