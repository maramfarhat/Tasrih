# Tasrih — What the platform does

**Tasrih** (تصريح) is a guided web platform that helps Tunisian businesses prepare their
**monthly tax declaration** (Déclaration mensuelle des impôts — DGI) end to end: it reads
the company's official documents, asks only the questions that matter, computes the taxes,
and produces the **pre-filled official form**.

> In one sentence: *from your tax documents and a month of invoices to a ready-to-file
> monthly declaration — no accounting software required.*

---

## 1. The problem it solves

Preparing a monthly declaration in Tunisia means juggling several sources:

- the **carte d'identification fiscale** (matricule, code TVA, code catégorie…),
- the **extrait RNE** (legal form, capital, activity),
- **Fatoora / TEIF** electronic invoices (output VAT, stamp duty…),
- **TEJ** withholding-tax declarations (certificates, retenue à la source),
- **payslips** (gross payroll → TFP, FOPROLOS),
- and the 12-page official **mensuelle2026.pdf** form.

Tasrih reads those files, calculates the amounts, decides which tax lines apply to the
company's activity, and fills the form — flagging anything uncertain before submission.

---

## 2. Who it's for

- SMEs, self-employed professionals and liberal professions.
- Accountants / experts-comptables preparing dossiers for several clients.
- Anyone who wants to double-check a monthly declaration before filing.

---

## 3. The journey (5 steps)

| # | Step | What happens |
|---|------|--------------|
| 1 | **Documents fiscaux** | Upload the **carte d'identification fiscale** + **extrait RNE**. Text is extracted by OCR + AI. |
| 2 | **Questions** | A few framing questions (previous IS, do you have staff?, filing channel, accountant?). |
| 3 | **Factures Fatoora** | Import **TEIF/TTN XML** invoices → VAT, turnover, stamp duty are computed. |
| 4 | **Retenue à la source (TEJ)** | Import the **TEJ XML** declaration → generates the official withholding schedule PDF. |
| 5 | **Formulaire** | Review/edit the amounts → export the **pre-filled monthly declaration**. |

*(Personnel, when the company has employees, adds contract + payslip uploads; the company
profile can be corrected at any time.)*

---

## 4. Documents it reads

| Document | Extracted data |
|---|---|
| **Carte d'identification fiscale** | Matricule fiscal, **code TVA**, **code catégorie**, secondary establishment, name, activity, address, **VAT status**. |
| **Extrait RNE** | RNE identifier, old commercial register, company name, **legal form** (SA/SARL/SUARL/SNC/SCS/SCA), capital, registered address, activity, status. |
| **Factures Fatoora (TEIF XML)** | Invoice no., date, vendor/client, HT, VAT rate, VAT amount, TTC, stamp duty, line items. |
| **Certificats / déclaration TEJ (XML)** | Beneficiary + tax ID, certificates, operations, base HT, rate, **retenue amount**, totals. |
| **Fiches de paie** | Gross salary, contributions, net — per employee. |

Uploads can be **PDF, image (JPG/PNG), or XML**. The platform also **detects when a document
is uploaded in the wrong slot** (e.g. an RNE in the CIF box) and says so, instead of silently
returning empty fields.

---

## 5. What it computes

| Line | Base | Rule |
|---|---|---|
| **TVA collectée** | Turnover HT by rate (19 / 13 / 7 %) | from sales invoices |
| **TVA déductible** | Purchases | from received invoices |
| **TVA nette / crédit** | collected − deductible | credit carried to next month |
| **Retenue à la source** | TEJ certificates | base × certificate rate |
| **TFP** | gross payroll | **1 %** manufacturing · **2 %** others |
| **FOPROLOS** | gross payroll | **1 %** (waived for fully exporting companies) |
| **Droit de timbre** | number of invoices collected | **1 DT per invoice** |
| **Taxe hôtelière** | establishment turnover | **2 %** |
| **Taxe sur les établissements** | turnover | per commune |
| **Droit de consommation** | — | alcohol / tobacco / cement products |

Every calculated value is **editable**, then recomputed.

---

## 6. Smart applicability (the “only what concerns you” logic)

The most error-prone part of the form is filling lines that don't apply. Tasrih deduces the
**domaine d'activité** (from the CIF/RNE activity + answers) and marks every tax line either
**applicable** or **“sans objet” (X)**.

**Example — consulting / IT services:** the platform automatically rules out
**taxe hôtelière**, **droit de consommation (alcool, tabac, ciment)**, **fonds de promotion
touristique**, **fonds de compensation agricole** and **droit de licence**; only VAT, TFP,
FOPROLOS, withholding and stamp duty remain.

In the PDF, applicable taxes are ticked (**X**) and non-applicable rubriques are marked **X
(sans objet)** instead of being left ambiguous. If the activity can't be deduced, a single
“domaine d'activité” question replaces dozens of irrelevant ones.

---

## 7. What it produces

1. **Déclaration mensuelle (official PDF)** — the 12-page `mensuelle2026` form, pre-filled
   and ready to review/deposit.
2. **Retenue à la source PDF** — the official withholding schedule
   **جدول الخصم من المورد**, one row per operation (beneficiary, tax ID, nature, base, rate,
   amount) with totals.

Both open in the browser and can be saved/printed (Ctrl+S).

---

## 8. Assistant “Karim”

A built-in French voice assistant guides the user screen by screen:

- contextual **guidance** at every step and proactive tips;
- **3D half-body avatar** with lip-sync driven by the voice;
- **natural French voice** (Edge neural TTS, local Piper fallback, then browser voice);
- answers questions in chat, with a **RAG knowledge base** built from the official guide.

---

## 9. Knowledge base & reference data

A SQLite knowledge base is built from the **official monthly-declaration guide**:

- RAG search over the guide's sections;
- **VAT rates**, **31 withholding-tax lines**, taxes/funds and required documents;
- a **field registry** (type, required, enum, regex, aliases) used to normalise and validate
  every value extracted from a document.

---

## 10. Tech at a glance

- **Frontend:** React + TypeScript + Vite.
- **Backend:** FastAPI (Python), SQLite.
- **AI:** vision/LLM extraction (Groq), Arabic/French OCR (Tesseract).
- **PDF:** ReportLab + pypdf (official form overlay + withholding schedule, with Arabic shaping).
- **Voice:** Edge TTS (neural) with Piper offline fallback.

---

## 11. Important notes

- Tasrih is a **preparation and verification aid**. It does **not** file on your behalf: the
  generated PDF must be reviewed and deposited (tele-declaration or paper).
- Extracted values are **proposals**; always check the matricule, the legal form, the VAT
  amounts and the checked tax boxes before submission.
- Keep the source documents (invoices, certificates, payslips) as supporting evidence.
