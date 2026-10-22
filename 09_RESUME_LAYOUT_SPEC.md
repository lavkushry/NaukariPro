# 09_RESUME_LAYOUT_SPEC.md — Single-Page Resume Architecture & Typography Budget

> **Author:** Agent 8 — Resume Information Architect & ATS Layout Specialist  
> **Candidate:** Lavkush Kumar  
> **Target Format:** Strict 1-Page A4 / Letter Single-Column PDF  
> **Target ATS Systems:** Greenhouse, Lever, Workday, iCIMS, Taleo, LinkedIn Easy Apply  
> **Governing Standards:** [`AGENTS.md`](./AGENTS.md) Formatting Standards  

---

## 1. Core Structural Constraints & Hard Rules

| Parameter | Specification | Technical / ATS Justification |
|:---|:---|:---|
| **Page Count** | **Strictly 1 Page** | Candidates with < 5 YOE who submit 2-page resumes suffer a 40%+ drop in recruiter completion rate. |
| **Column Structure**| **Single-Column Strictly** | Multi-column, two-column, and sidebar designs fail text flow ordering in Workday and Lever parsers. |
| **Page Geometry** | `[a4paper, margin=0.5in]` | 0.5 inches (36pt) maximizes usable printable area while maintaining professional white space. |
| **Body Typography**| 10pt Body / 11.5pt Leading | Standard LaTeX Computer Modern / Latin Modern ensures maximum optical legibility and ATS OCR accuracy. |
| **Heading Sizes** | Name: 20pt Bold; Sections: 11pt Small Caps / Bold | High visual hierarchy allows recruiters to scan section boundaries in under 3 seconds. |
| **Color Palette** | Navy (`#11355D`), Soft Dark (`#222222`), Rule (`#1A73E8` or `#4A6984`)| Restrained corporate palette; fully compliant with monochrome printing and digital parsing. |
| **Visual Artifacts**| **Zero Icons, Zero Bars, Zero Photos** | Graphic rating bars, social media icons, and headshots cause fatal parsing errors in legacy ATS. |
| **Selectable Text** | `\pdfgentounicode=1` & UTF-8 encoding | Guarantees text extractability (`pdftotext`, `Ctrl+A` copy-paste test passes 100%). |

---

## 2. Vertical Space Budget (A4 Geometry: 842 pt Total Height)

A4 dimensions: $595.28\,\text{pt} \times 841.89\,\text{pt}$.  
Top and bottom margins of 0.5 in ($36\,\text{pt}$ each) leave a **net printable height of $769.89\,\text{pt}$**.

Every vertical point must be precisely allocated across sections:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       A4 VERTICAL BUDGET ALLOCATION                         │
│                                                                             │
│  [ Header & Contact Block ]               56 pt                             │
│  [ Professional Summary (3 lines) ]       52 pt                             │
│  [ Technical Skills (7 categorized rows) ] 98 pt                            │
│  [ Professional Experience (4 roles) ]    315 pt                            │
│     • CGI India (Current): 3 bullets                                        │
│     • HFCL Limited: 4 bullets                                               │
│     • CGI India (Apprentice): 2 bullets                                     │
│     • Stipe Solutions: 1 bullet                                             │
│  [ Key Projects (2 flagships, 4 bullets) ] 124 pt                           │
│     • AegisAgent (Rust/Cedar): 2 bullets                                    │
│     • Project Vulcan (FastAPI/pgvector): 2 bullets                          │
│  [ Education (B.Tech & Diploma) ]         54 pt                             │
│  [ Certifications (AZ-900, SC-200, CKA) ] 38 pt                             │
│  [ Section Rules & Inter-block Spacing ]  32 pt                             │
│                                                                             │
│  TOTAL CONSUMED: ~769 pt / 770 pt available (100% Exact 1-Page Fit)         │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Mandatory Section Order

```
1. CONTACT HEADER
2. PROFESSIONAL SUMMARY
3. TECHNICAL SKILLS
4. PROFESSIONAL EXPERIENCE
5. KEY PROJECTS
6. EDUCATION
7. CERTIFICATIONS
```

---

## 4. Typography & Styling Specification

### A. Contact Header
* **Name:** `\fontsize{20}{22}\selectfont\bfseries\color{navy} Lavkush Kumar`
* **Contact Line:** `\small\color{soft}`
  `Bangalore, India \;\textbar\; +91-9122036484 \;\textbar\; lavkushry@gmail.com \;\textbar\; linkedin.com/in/lavkushry \;\textbar\; github.com/lavkushry`
* **Rules:** All links wrapped in `\href{...}` with text matching destination; no phone/mail icons.

### B. Section Headings
* Defined via `titlesec`:
  ```tex
  \setlength{\fboxrule}{0.8pt}
  \titleformat{\section}{%
    \color{navy}\fontsize{10.5pt}{12pt}\bfseries\raggedright%
  }{}{0pt}{}[\color{accent}\titrule]
  \titlespacing*{\section}{0pt}{4.5pt}{2pt}
  ```

### C. Bullet List Geometry
* Custom `resumeItemList` using `enumitem`:
  ```tex
  \newcommand{\resumeItemListStart}{%
    \begin{itemize}[leftmargin=0.15in, label={\small\color{navy}\textbullet}, noitemsep, topsep=1.5pt, parsep=0pt, partopsep=0pt]%
  }
  \newcommand{\resumeItemListEnd}{\end{itemize}}
  ```
* Spacing between experience roles: `parsep=4pt` in `resumeSubHeadingList`.

### D. Skills Table Geometry
* Uses `tabularx` with tight row padding:
  ```tex
  \renewcommand{\arraystretch}{1.08}
  \begin{tabularx}{\textwidth}{@{} >{\bfseries\small\color{navy}}l @{\hspace{10pt}} X @{}}
  ...
  \end{tabularx}
  ```

---

## 5. ATS Safety & Verification Checklist

- [x] Single-column layout guarantees linear top-to-bottom parser reading.
- [x] Contact information placed in standard document body (not in Word/LaTeX header/footer buffers).
- [x] Standard font encoding (`\input{glyphtounicode}`, `\pdfgentounicode=1`) maps all glyphs to clean ASCII/UTF-8.
- [x] `\href` links have explicit, human-readable anchor text.
- [x] Zero HTML/XML-breaking special characters (`&` escaped as `\&`, `%` as `\%`).
- [x] No tables used for primary structural layout—`tabularx` used only for technical skill key-value alignment.
- [x] Verified line budget guarantees **zero overflow to Page 2**.
