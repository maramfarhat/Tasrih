# Recherche — « Déclaration mensuelle des impôts » (Tunisie)

Objectif : documenter **exactement ce qu'il faut pour remplir** l'imprimé officiel
« Déclaration mensuelle des impôts » (DGI), afin de le reconstruire/remplir dans Tasrih.

## 1. Sources

| Source | Nature | Fichier / lien |
|---|---|---|
| Ministère des Finances — Direction Générale des Impôts | Imprimé officiel 2023 (12 p., AR) | `imprime-officiel-2023.pdf` · [finances.gov.tn](https://www.finances.gov.tn/fr/document/imprime-de-la-declaration-mensuelle-des-impots-2023) |
| DGI / partenaires | Imprimé officiel 2025 (12 p., AR) | `imprime-officiel-2025.pdf` · jibaya.tn |
| Imprimé français (version antérieure, layout clair, 12 p.) | Référence de structure | `imprime-fr-2010.pdf` / `.txt` |
| Guide technique (repo) | Bases, taux, pièces, textes | `backend/data/knowledge/guide-declaration-mensuelle-tunisie.pdf` |
| Codes | Code TVA, CDPF, Code IRPP/IS, Lois de Finances jusqu'à **LF 2026** | — |
| Télédéclaration | Portail | https://tl.finances.gov.tn/pls/webdeclar/identification |

> Le portail DGI (`impots.finances.gov.tn`) a un **certificat TLS invalide** et renvoie 400
> depuis l'extérieur ; l'imprimé se récupère via `finances.gov.tn` / `jibaya.tn` / `idaraty.tn`.

## 2. En-tête du formulaire (identique à toutes les pages, page 1)

| Champ | Obligatoire | Source dans Tasrih |
|---|---|---|
| Code acte : 0 spontané · 1 régularisation · 2 rectification · 3 taxation d'office · 4 cessation | oui | `MonthContext.declaration_code` |
| Mois / Année | oui | `MonthContext.month/year` |
| Identifiant fiscal (matricule) | oui | CIF `tax_id` |
| Code T.V.A. | oui | CIF `vat_code` |
| Code catégorie | oui | CIF `category_code` |
| Nombre de filiales | si > 0 | **non collecté** |
| N° registre de commerce / RNE | oui | RNE `rne_identifier` |
| Nom et prénom ou raison sociale | oui | CIF/RNE `name` |
| Adresse ou siège social + code postal | oui | CIF/RNE `address` |
| Activité | oui | CIF/RNE `main_activity` |
| Date de cessation d'activité (si code acte 4) | conditionnel | **non collecté** |
| Cases « nature de l'impôt/taxe » (X) | oui (≥ 1) | déduit du profil (`rules.active_sections_for`) |

Cases à cocher (page 1) :
`Retenue à la source · TFP · FOPROLOS · DC · TVA · Autres taxes sur le CA · Taxes sur les
assurances · Droit de timbre · TCL · Taxe hôtelière · Droit de licence`

## 3. Contenu du formulaire, page par page (12 pages)

| Page | Section | Ce qu'il faut saisir |
|---|---|---|
| 1 | En-tête + **Retenue à la source** (début) | Identité (ci-dessus) ; lignes retenue : *libellé, assiette (D), taux, montant (D)* |
| 2 | Retenue à la source (suite) | idem, lignes 9 à 17+ (capital mobilier, jetons, marchés publics, retenue TVA 50 %…) |
| 3 | **TFP** + **FOPROLOS** + **Droit de consommation** | TFP : assiette, 1 %/2 %, taxe due I, taxe déductible II, avances/ristournes, restant dû/report, date décision d'approbation, nb bénéficiaires. FOPROLOS : assiette, 1 %, due, nb bénéficiaires. DC : CA net, achats locaux/importés, taux, due I, déductible II, restant |
| 4 | **TVA collectée / déductible** | CA imposable par taux (6/7,5/12/15/18/22,5 % — mis à jour LF : 7/13/19 %), TVA due ; achats immobilisations/équipements/autres (locaux/importés) → TVA déductible ; autres déductions (retenue 50 % ≥1000 D, 100 % non-établis, forfaitaire transport) ; régularisations |
| 5 | TVA (suite) | Restant dû/report, report mois précédent, montant restitué, **crédit avec droit à déduction suspendu** (colonnes III–VII), n° factures émises (de … à …), % de déduction (activité partiellement imposable), achats en suspension/exonérés, exportations, ventes en suspension, CA exonéré |
| 6 | **Autres taxes sur le chiffre d'affaires** | Fonds de développement (industrie 1 %, agric./pêche 2 %, tourisme 0,5 %), télécom 5 %, FNE (café/thé 0,150 D/kg, ciment 2 D/T + 1 D/T), tomate (0,005 / 0,028 D/kg), environnement 5 %, maîtrise d'énergie (10 D/1000 UT, 40 %), jeux télécom, création littéraire 1 %, repos biologique… |
| 7 | **Taxe unique sur les assurances** + autres taxes assurances | Primes émises/coassurance/annulées par catégorie (nav. maritime 5 %, autres 10 %) ; contributions fonds (circulation, protection civile, garantie assurés, prévention) |
| 8 | Assurances — exonérations + **Droit de timbre fiscal** | Primes exonérées par nature ; timbre : autorisation n°, n° société, nature de la pièce, nombre de pièces, taxe due ; taxe sur recharge téléphonique |
| 9 | **Taxe hôtelière** + **TCL** + **Droit de licence** | Taxe hôtelière : CA brut, 2 %. TCL : CA local brut 0,2 %, IR/IS 25 %, mois précédents, taxe annuelle, minimum. Licence boissons : nb établissements classes 1/2/3 (300/150/25 D) par collectivité locale |
| 10 | **Récapitulation** + signature | Taxe due (I), déduction (II), total (III=I−II), pénalités de retard, total par impôt ; recette des finances, code paiement, date ; certification |
| 11 | **Filiales** | Achats ouvrant droit à déduction (locaux/importés, équipements/autres) ; CA par taux ; n°, adresse, activité des filiales |
| 12 | **Répartition TCL & taxe hôtelière** | Superficies bâtie/non bâtie, nb carrières, par collectivité locale ; part de la collectivité par immeuble/filiale |

## 4. Taux & bases de référence

Tout est dans la base de connaissances (`GET /knowledge/reference`) :

- **TVA** : 0 / 6 / 7 / 12 / 13 / 18 / 19 % (le guide LF retient 7/13/19 comme taux courants).
- **TFP** : 1 % industrie manufacturière · 2 % autres. **FOPROLOS** : 1 %.
- **Retenue à la source** : **31 lignes** (barème IRPP sur salaires, 20/25 % non-résidents,
  10/15/17,64 % honoraires & loyers, 5 % hôtels, 20/25 % capitaux mobiliers, 10 % dividendes,
  15 % occasionnels, 2,5 % cession immobilière, 1/0,5/1,5 % acquisitions ≥1000 D, 25 % État,
  100 % non-établis, 5/10/15 % non-résidents établis, 25/33,33 % pays à fiscalité privilégiée…).
- **Droit de timbre** : 0,300 D facture LCE, 2 D ticket transport international,
  3,5/7 D visite technique, etc.
- **Taxe hôtelière** 2 % · **TCL** 0,2 % CA local + 0,1 % export / 25 % IR-IS / 0,1 % prix
  réglementés · **Licence boissons** 300/150/25 D.

## 5. Pièces justificatives à préparer chaque mois

Comptabilité (balance, grand livre, journaux ventes/achats) · Paie (livre de paie, bulletins,
contrats salariés étrangers) · Factures ventes par taux de TVA + achats par nature + factures
≥ 1000 D isolées · Contrats (baux, prestations, marchés, prêts, conventions fiscales) · DAU
douane · Justificatifs bancaires (intérêts, RIB) · Actes juridiques (PV, cessions) ·
Attestations (régime, exonération, remboursement crédit TVA) · Répartition géographique des
locaux/succursales (TCL, taxe hôtelière).

## 6. Délais & codes

- Dépôt **dans les 28 premiers jours** du mois suivant (personnes physiques) ; **15 ou 28**
  selon la catégorie / forme juridique (personnes morales à l'IS souvent décalées).
- Retard : pénalités CDPF art. 81 à 87 (progressives, majorées en taxation d'office).
- Code acte : 0 spontané · 1 régularisation (taswiya) · 2 rectification · 3 taxation d'office ·
  4 cessation.
- TVA : retenue 50 % (ou 25 % selon millésime) sur montants ≥ 1000 D TTC ; 100 % non-établis ;
  remboursement du crédit (art. 28 CDPF, 90/120 jours).

## 7. Ce que Tasrih collecte déjà vs ce qui manque

**Déjà collecté / calculé** : identité (CIF), RNE, profil, montants TVA collectée/déductible/
nette, CA par taux, timbre, retenues, TFP, FOPROLOS, TCL & taxe hôtelière (bases), licence.

**À compléter pour remplir tout le formulaire** :

1. Nombre de filiales + page 11 (achats par filiale, CA par taux, adresses).
2. Répartition TCL/taxe hôtelière par **collectivité locale** (superficies, immeubles).
3. **Droit de consommation** (produits soumis, achats locaux/importés).
4. **Autres taxes sur le CA** (fonds sectoriels) — sélection selon activité.
5. **Taxes sur les assurances** (si assureur).
6. **Droit de timbre fiscal** détaillé (nature & nombre de pièces).
7. **Crédit de TVA** (report, restitution, suspension du droit à déduction).
8. **Déclaration code acte** et **date de cessation**.
9. **Recette des finances + code paiement**.

## 8. Gabarit PDF

- L'app attend `backend/data/templates/mensuelle2026.pdf` (absent → `/health` =
  `official_template: false`). **Aucun imprimé 2026 n'est publié** à ce jour ; le plus récent
  disponible est **2025** (`docs/declaration-mensuelle/imprime-officiel-2025.pdf`, 12 p., AR).
- L'overlay d'écriture est dans `backend/app/declaration/fill_official.py`
  (positions à recalibrer sur le PDF cible).

## 9. Prochaines étapes proposées

1. Choisir le gabarit cible (2025 AR, ou reproduire le formulaire en HTML/React) et l'ajouter
   comme `mensuelle2026.pdf` — puis recalibrer les coordonnées d'overlay.
2. Étendre le modèle de données pour les sections manquantes (§7) et la zone « récapitulation ».
3. Ajouter les taux « Autres taxes sur le CA » et assurances dans le référentiel.
4. Générer le PDF prérempli et le tester page par page contre l'imprimé officiel.
