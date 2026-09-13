# Tasrih — Déclaration mensuelle Tunisie

## Flux

1. **Documents fiscaux** — carte d’identification fiscale (CIF) + extrait RNE  
2. **Questions** — IS, personnel, canal de dépôt  
3. **Documents du personnel** (si personnel) — contrat, fiche CNSS, fiche de paie  
4. **Profil entreprise** (vérifiable / éditable)  
5. **Factures** (Fatoora démo ou import) → calcul TVA + champs  
6. **Retenue à la source (TEJ)** — import du XML TEJ et PDF « Retenue à la source »  
7. **Formulaire** officiel `mensuelle2026.pdf` (12 pages) prérempli  

### Étape Retenue à la source (TEJ)

Le portail officiel est <https://tej.finances.gov.tn/> : on y déclare la retenue à la
source puis on télécharge le **XML** (`DeclarationsRS`). L’étape Tasrih :

- ouvre le portail TEJ ;
- importe un ou plusieurs XML (`POST /extract/retenue`) — d’où les bénéficiaires,
  bases HT, taux et montants de retenue (totaux par certificat) ;
- génère le tableau officiel **جدول الخصم من المورد** (`POST /export/retenue`).

Le générateur (`app/declaration/retenue_pdf.py`) reproduit l’imprimé de référence
`backend/data/templates/mens_mnt_retenue_ar.pdf`. Exemple d’import :
`backend/data/samples/retenue-tej-2026-09.xml`.  

## Applicabilité des taxes selon le domaine d'activité

`backend/app/declaration/applicability.py` déduit le **domaine d'activité** (CIF/RNE + réponses)
et décide, pour chacune des 10 lignes du formulaire, si la taxe est **applicable** ou
**sans objet (X)** — au lieu de demander à l'utilisateur de remplir des rubriques qui ne le
concernent pas.

Exemple : pour des **services de conseil**, la taxe hôtelière, le droit de consommation
(alcool / tabac / ciment), les autres taxes sur CA (fonds tourisme, fonds compensation
agricole) et le droit de licence sont marqués **sans objet (X)** ; seules TVA, TFP, FOPROLOS,
retenue à la source et timbre restent applicables.

- La réponse est exposée par `POST /pipeline/build` : `domain`, `tax_applicability`,
  `tax_lines`, `sans_objet`.
- Le PDF (`fill_official.py`) coche (X) les taxes applicables et marque **X** les rubriques
  sans objet (page 3 TFP/FOPROLOS, page 5 TVA, page 8 taxes locales).
- Si le domaine est indéterminé (`autre`), une **seule** question « domaine d'activité » est
  posée : elle élimine d'un coup toutes les rubriques non concernées.

## Calculs de la déclaration mensuelle

Le formulaire reprend chaque rubrique, calculée automatiquement puis **modifiable** :

| Rubrique | Base | Taux / règle |
|---|---|---|
| Retenue à la source | certificats **TEJ (XML)** importés | assiette + taux du certificat |
| TFP | masse salariale brute (fiches de paie scannées) | 1 % industrie manufacturière · 2 % autres |
| FOPROLOS | masse salariale brute | 1 % (exonération totale exportatrice) |
| TVA collectée | CA HT par taux (7 / 13 / 19 %) | factures de vente TEIF |
| TVA déductible | achats des factures reçues | — |
| Crédit de TVA | collectée − déductible < 0 | reporté au mois suivant |
| Droit de timbre | nombre de factures encaissées | 1 DT / facture |
| Taxe hôtelière | CA brut de l'établissement | 2 % (hôtellerie) |

Routes ajoutées :

- `POST /extract/payslip` — masse salariale brute d'une fiche de paie
- `POST /extract/retenue` — déclaration/certificat(s) de retenue TEJ (XML) + `declaration` détaillée
- `POST /export/retenue` — PDF « Retenue à la source » (جدول الخصم من المورد) depuis un XML TEJ
- `GET  /employees/payroll` — cumul des fiches de paie scannées du mois
- `POST /pipeline/build` accepte `retenues` et `payslips` (+ `amounts_override` manuel)

## Recherche — formulaire officiel

`docs/declaration-mensuelle/RECHERCHE.md` documente **ce qu'il faut pour remplir** la
« Déclaration mensuelle des impôts » (DGI) : en-tête, 12 pages détaillées, taux/bases,
pièces justificatives, délais, et les écarts à combler pour remplir tout le formulaire.
Imprimés de référence : `imprime-officiel-2023.pdf`, `imprime-officiel-2025.pdf`,
`imprime-fr-2010.pdf`.

## Administration DGI (`/admin`) — suivi & détection

Vue **totalement séparée** du contribuable (accessible via `/admin`, protégée par
`X-Admin-Key` = `ADMIN_PASSWORD`). Aucune donnée DGI n'est exposée au contribuable.

- **Modèle** : `businesses`, `declarations`, `invoices_summary`, `field_edits`,
  `risk_flags` (`app/admin_db.py`).
- **Règles pures & testables** (`app/services/anomaly_detection.py`) — aucun ML, seuils
  transparents, chaque drapeau porte ses **chiffres exacts + une explication en clair** :
  - `check_manual_override` — correction manuelle d'une valeur matérielle (> 5 %), motif obligatoire.
  - `check_revenue_invoice_mismatch` — CA déclaré < facturation électronique (> 20 %).
  - `check_sudden_drop` — chute vs moyenne des 6 derniers mois (hors saisonnalité).
- **Endpoints** : `GET /admin/dashboard`, `/admin/businesses`, `/admin/businesses/{id}`,
  `/admin/flags`, `POST /admin/flags/{id}/review`, `POST /admin/run-detection`,
  `POST /declarations/save` et `POST /declarations/{id}/field-edit` (motif obligatoire
  côté contribuable si écart > tolérance).
- **Front** : `frontend/src/admin/` (tableau de bord, entreprises, détail, file de drapeaux).
- **Tests** : `cd backend && PYTHONPATH=. .venv/bin/python tests/test_anomaly_detection.py`.

## Base de connaissances (`knowledge.db`)
Référentiel construit à partir du **guide officiel** de la déclaration mensuelle
(`backend/data/knowledge/guide-declaration-mensuelle-tunisie.pdf`), dans une base SQLite
séparée de la base utilisateurs.

- **RAG** : le guide est découpé en sections/chunks indexés en FTS5. L’assistant
  (`/agent/chat`) récupère les passages pertinents et les injecte dans le prompt.
- **Référentiel fiscal** : taux de TVA, 31 lignes de retenue à la source, taxes/fonds,
  documents à fournir chaque mois.
- **Registre des champs** : pour chaque type de document (`cif`, `rne`, `invoice`,
  `payslip`, `profile`, `amounts`, `form`) la liste des champs **connus** (type, requis,
  enum, regex) + alias. Tout champ extrait d’une photo est mappé/normalisé/validé contre
  ce registre ; les valeurs inconnues ou invalides sont signalées.

Routes :

- `GET  /knowledge/stats` — état de la base
- `GET  /knowledge/search?q=…` — passages du guide (RAG)
- `GET  /knowledge/fields?doc_type=cif` — champs connus d’un type de document
- `GET  /knowledge/reference` — TVA, retenues, taxes, documents
- `POST /knowledge/validate` `{doc_type, values}` — normalise/valide une extraction
- `POST /knowledge/ingest` — ré-ingère le guide (idempotent)

Ré-ingérer en CLI :

```bash
cd backend && PYTHONPATH="$PWD" .venv/bin/python -m app.knowledge.ingest \
  data/knowledge/guide-declaration-mensuelle-tunisie.pdf
```

La base s’auto-ingère au démarrage du backend si elle est vide.

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
