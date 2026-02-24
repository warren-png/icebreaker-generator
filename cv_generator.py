"""
═══════════════════════════════════════════════════════════════════
CV GENERATOR V3.4 - Entreprises anonymisées, vocab distant
- Entreprises = descriptions riches (pas de noms)
- Deals/transactions publiques = nommables
- Vocabulaire distant de la fiche
- Age = nombre entier (pas "XX ans")
- Header = "CV Entourage Recrutement"
═══════════════════════════════════════════════════════════════════
"""

import anthropic
import os
import re
import json
from datetime import datetime

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")


FEW_SHOT_STYLE_GUIDE = """
═══════════════════════════════════════════════════════════════════
EXEMPLES DE VRAIS CVs - APPRENDS LE STYLE, PAS LE CONTENU
═══════════════════════════════════════════════════════════════════

--- EXEMPLE 1 : Auditeur Risk & Compliance (8 ans XP, Big4 assurance) ---

Poste actuel : "Risk & Compliance FS – Secteur Assurance"
• Audit interne - Conduite d'audits internes et de revues de processus auprès de diverses directions (Métiers, Finance, Conformité, SI, Achats), Support aux cellules d'audit interne pour l'intégration des contrôles IT, Benchmark de l'organisation et du fonctionnement de l'audit interne d'un assureur non-vie
• PMO - Pilotage d'équipes d'auditeurs internes dans des audits transverses
• Contrôle interne - Conception et déploiement de campagnes de contrôle interne sur les processus métiers : refonte des dispositifs, mise en conformité réglementaire, exécution des contrôles, sensibilisation des équipes.

Poste précédent (PARAGRAPHE NARRATIF) :
"Audits thématiques groupe et locaux auprès des entités françaises (achats, assurances cyber risques, dispositifs de paiement, stratégie ALM, risque de liquidité et cash management), analyse des processus et contrôles généraux informatiques, suivi des recommandations, projets transverses. Restitution orale et écrite (en anglais) des conclusions aux directions auditées."

→ STYLE : Aucun chiffre. Descriptions factuelles. Format catégoriel.

--- EXEMPLE 2 : Manager Gen AI (10 ans XP, banque) ---

Missions par client :
• BPCE Vie - Portfolio management — Pilotage du portefeuille de projets IA, instruction et priorisation des cas d'usage métiers.
• CNP Assurances - Change management — Déploiement de cas d'usage IA sur Microsoft Copilot, acculturation (cafés Copilot, plénières), suivi et mesure de l'adoption.

Début de carrière :
"Refonte du dispositif d'EAD Retail : étude initiale, modélisation, calibrage, documentation, recette du moteur."
"Participation aux travaux de révision du dispositif LGD Retail en réponse à des recommandations BCE."

→ STYLE : "Participation aux travaux" (humble). Comités nommés.

--- EXEMPLE 3 : M&A Investment Banking (6 ans XP) ---

• Participated in two successful public takeover bids: Keyrus (2023) and Prodware (2022)
• Accompanied InfraVia Capital Partners in the acquisition of Univet, a veterinary network of over 150 clinics

Stage : "Supported analysts in all of their work (market research, trading peers, past transactions, dataroom management)"

→ STYLE : Verbes simples. Deals nommés (info publique). Stages = 2 bullets.

--- EXEMPLE 4 : Responsable Comptabilité (10 ans XP, luxe) ---

"Conduite et supervision :
- Des travaux de clôtures mensuelles (French GAAP et IFRS), des états financiers, liasses fiscales de 6 entités
- Du flux Order to Cash : accompagnement de 25 magasins (réconciliation ventes/encaissements, gestion des acomptes et de la détaxe)
- Du flux Record to Report : projets finance en lien avec la facturation électronique (PDP, Tax Compliance), feuille de route Paie (suivi IJSS)"

→ STYLE : Structure par FLUX MÉTIER. Acronymes internes.

--- EXEMPLE 5 : Strategy Consultant (6 ans XP, MBB) ---

"● Insurance-related
  o Developed a strategic plan for a mid-sized insurance company, working closely with Senior management on risk portfolio and distribution channels
  o Steered deployment of 4 GenAI use cases, building the roadmap, and designing virtual Center of Excellence
● Other strategy-related projects
  o Defined development opportunities and market-entry approach for a civil engineering firm's sustainable activities"

→ STYLE : Regroupement THÉMATIQUE. Détail des livrables.

--- EXEMPLE 6 : Assistant Manager Big4 (5 ans XP, audit + strategy) ---

"Gestion de projets - M&A :
  Accompagnement d'un acteur majeur de l'asset management dans le cadre de l'acquisition de l'activité d'un concurrent en Europe et en Malaisie (Design du TOM, Gap Analysis & Roadmap) sur 3 streams.
Audit interne :
  Audit du cycle d'investissement d'un bancassureur (20 Mds€ d'actifs sous gestion) du Front au Back Office.
Principaux clients: BNP Paribas Asset Management & Groupama Asset Management."

→ STYLE : Catégories métier. Début de carrière = 1 paragraphe.

--- EXEMPLE 7 : Operational Excellence Lead (4 ans XP, insurtech) ---

"Intégration des équipes Excellence Opérationnelle et Opérations (40+ ETP) au sein de la nouvelle organisation. Management d'équipe: 3 membres
Organisation cross-fonctionnelle de la migration du stock de 10k+ sinistres - Coordination de la migration de 200k+ contrats"

→ STYLE : Chiffres opérationnels BRUTS. Bullets très courts.

═══════════════════════════════════════════════════════════════════
SYNTHÈSE DES PATTERNS HUMAINS
═══════════════════════════════════════════════════════════════════

1. FORMATS VARIÉS entre expériences
2. CHIFFRES RARES : max 2-3, contexte uniquement
3. VERBES SIMPLES : "Participation", "Support", "Accompagnement"
4. LONGUEURS IRRÉGULIÈRES entre bullets
5. DÉBUT CARRIÈRE SIMPLE
6. ACRONYMES MÉTIER : PDP, IJSS, LOD1, TOM, RCSA, SCR
7. STRUCTURE PAR FLUX ou PAR THÈME
"""


def generate_cv_content(job_posting_data, prospect_data=None):
    """
    Génère un CV anonyme Entourage Recrutement v3.4
    Entreprises anonymisées — Match 8/10 — Vocab distant
    """
    
    if not job_posting_data:
        raise ValueError("job_posting_data requis")
    
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    job_title = job_posting_data.get('title', 'Poste')
    job_desc = job_posting_data.get('description', '')
    
    job_title_clean = re.sub(r'\s*\(?[HhFf]\s*[/\-]\s*[HhFfMm]\)?', '', job_title).strip()
    
    prompt = f"""Génère un CV anonyme ultra-réaliste pour un poste de {job_title_clean}.

Ce CV est envoyé par le cabinet Entourage Recrutement en prospection commerciale.
Le nom du candidat ET les noms des entreprises sont anonymisés.

═══════════════════════════════════════════════════════════════════
FICHE DE POSTE
═══════════════════════════════════════════════════════════════════
{job_desc[:3000]}

{FEW_SHOT_STYLE_GUIDE}

═══════════════════════════════════════════════════════════════════
RÈGLES DE GÉNÉRATION
═══════════════════════════════════════════════════════════════════

RÈGLE 0 — MATCH GLOBAL : 8/10 (PAS PLUS)

Le CV donne envie de rencontrer le candidat mais n'est PAS le candidat parfait.
• Le SECTEUR est proche mais pas identique
• Les COMPÉTENCES couvrent 75-80% de la fiche, avec 1-2 zones non couvertes
• Le PARCOURS montre une SPÉCIALISATION PROGRESSIVE
• 1-2 éléments de la fiche ne sont PAS dans le CV (ça crée la question d'entretien)

RÈGLE 1 — ANNÉES D'XP CALIBRÉES

Si la fiche demande "au moins X ans" → profil de X+2 à X+3 ans MAXIMUM.
• Fiche "5 ans min" → CV 7-8 ans (3 expériences)
• Fiche "8 ans min" → CV 10-11 ans (3-4 expériences)
• Fiche "3 ans min" → CV 5-6 ans (2-3 expériences)
• Pas de minimum mentionné → estimer le niveau et faire +2-3 ans

RÈGLE 2 — MATCH GRADUÉ PAR EXPÉRIENCE

EXP 1 (récente) : 75-80%.
EXP 2 : 60-70%.
EXP 3-4 (début) : 40-50% — fonctions GÉNÉRALISTES, AUTRE CONTEXTE.

La SPÉCIALISATION arrive en cours de parcours, pas dès le premier poste.

RÈGLE 3 — LOCALISATION = RÉGION UNIQUEMENT

❌ JAMAIS de ville. ✅ Toujours la région.
Dernière exp : région de la fiche. Si pas de lieu → rien.

RÈGLE 4 — ANONYMISATION DES ENTREPRISES

C'est un CV anonyme envoyé par un cabinet de recrutement.
Les noms d'entreprises sont MASQUÉS et remplacés par des descriptions RICHES et PRÉCISES.

❌ TROP VAGUE (signal IA) :
"Groupe bancaire européen"
"Cabinet de conseil"
"Compagnie d'assurance"

❌ NOMS RÉELS (pas anonyme) :
"Deloitte", "AXA", "BPCE", "Generali"

✅ DESCRIPTIONS RICHES ET PRÉCISES :
"Cabinet d'audit et de conseil Big4, practice Financial Advisory"
"Compagnie d'assurance mutualiste française (18Mds€ de primes, 12 000 collaborateurs, réseau de 3 500 agents)"
"Fintech spécialisée dans les paiements B2B, série C (450M€ de valorisation)"
"Boutique M&A indépendante spécialisée FIG, bureau de Paris (35 professionnels)"
"Bancassureur filiale d'un groupe coopératif, activités vie-épargne et prévoyance collective"
"Cabinet d'audit mid-cap à dominante services financiers"
"Groupe de protection sociale issu d'une fusion récente"

La description doit être ASSEZ PRÉCISE pour que le recruteur visualise le type d'entreprise, mais PAS assez pour l'identifier formellement.

EXCEPTION : Les DEALS et TRANSACTIONS publiques PEUVENT être nommés dans les missions (c'est de l'info publique qui ne révèle pas l'identité du candidat).
Exemple : "Participation à la DD buy-side dans le cadre de l'opération April / Howden"

RÈGLE 5 — CONTEXTE SPÉCIFIQUE

Chaque mission = QUOI + POURQUOI + DANS QUEL CONTEXTE.

RÈGLE 6 — OUTILS EN PROFONDEUR

Module, workflow, usage précis. Pas juste le nom.

RÈGLE 7 — FORMATION COHÉRENTE

Parcours statistiquement probable pour le métier.

RÈGLE 8 — TENSIONS DE CONTEXTE

2-3 mentions de contexte tendu, formulées positivement :
✅ "Contexte post-fusion, 3 SI hétérogènes"
✅ "Périmètre legacy non documenté"
❌ JAMAIS : "objectif non atteint", "retard", "échec"

RÈGLE 9 — STRUCTURE IRRÉGULIÈRE

❌ 4 exp × 4 bullets × 2 lignes = signal IA
✅ Exp1 (catégories détaillées) + Exp2 (1 paragraphe) + Exp3 (3 bullets courts)

RÈGLE 10 — VOCABULAIRE DU CANDIDAT ≠ VOCABULAIRE DE L'ANNONCE

CRUCIAL. Un candidat écrit son CV AVANT de lire l'annonce.

Pour CHAQUE compétence clé de la fiche, utilise un SYNONYME MÉTIER :
• "opérations de M&A" → "deals", "transactions", "opérations capitalistiques"
• "identification d'opportunités" → "sourcing", "origination"
• "due diligences" → "DD buy-side", "travaux pré-acquisition"
• "suivi des participations" → "monitoring du portefeuille", "suivi des filiales"
• "instances de gouvernance" → "boards", "CA", "comités"
• "dispositifs de reporting" → "tableaux de bord", "reporting aux administrateurs"
• "accompagner les administrateurs" → "coaching des mandataires", "préparation des CA"
• "structurer la gouvernance" → "mise en place du cadre", "définition des rôles"
• "piloter la conformité" → "coordination avec le DPO", "suivi des obligations"
• "animer le réseau" → "correspondants dans les BU", "relais métiers"
• "préparer les stratégies d'intégration" → "cadrage de l'intégration post-deal"
• "analyser et formaliser" → "instruction des dossiers", "notes d'analyse"
• "missions transverses" → "chantiers horizontaux", "projets cross-fonctionnels"

RÈGLE STRICTE : Max 3 expressions exactes de la fiche dans tout le CV.

RÈGLE 11 — PROFIL_TEXT

3 lignes max, FACTUEL PUR — décris le périmètre, pas les qualités.
Un comptable ne dit pas "habitué aux clôtures sous pression", il dit "clôtures mensuelles en environnement multi-conventions".

STRUCTURE : "[Titre] avec [X] ans d'expérience en [environnements], spécialisé dans [domaine 1] et [domaine 2]. [Périmètre factuel : type de clôtures/missions/opérations], coordination avec [interlocuteurs] dans des contextes de [enjeu]."

❌ INTERDIT dans profil_text :
- "Habitué à", "Rompu à", "Passionné par", "Fort de"
- "sous pression", "en environnement exigeant", "challengeant"
- Tout adjectif valorisant le candidat (rigoureux, autonome, proactif)
✅ TOUJOURS factuel : ce qu'il FAIT, pas ce qu'il EST

RÈGLE 12 — FORMAT DU CHAMP AGE

Le champ "age" doit être un NOMBRE ENTIER uniquement (ex: 34).
Ne PAS écrire "34 ans" — juste le nombre. Le template ajoute "ans" automatiquement.

═══════════════════════════════════════════════════════════════════
FORMAT JSON
═══════════════════════════════════════════════════════════════════

{{
  "header": "CV Entourage Recrutement",
  
  "profil": {{
    "age": 34,
    "localisation": "Région uniquement OU vide",
    "disponibilite": "Préavis 3 mois",
    "mobilite": "Région uniquement"
  }},
  
  "profil_text": "3 lignes max.",
  
  "experiences": [
    {{
      "titre": "Titre du poste",
      "dates": "Mois Année - Aujourd'hui",
      "entreprise": "Description ANONYMISÉE riche et précise (PAS de nom réel)",
      "lieu": "RÉGION uniquement",
      "format": "categories|bullets|narratif|flux|thematique",
      "chapeau": "Phrase de contexte optionnelle",
      "missions": [
        "Mission avec CONTEXTE SPÉCIFIQUE. Les deals publics PEUVENT être nommés."
      ]
    }}
  ],
  
  "formation": [
    {{
      "diplome": "Intitulé COHÉRENT",
      "ecole": "École CRÉDIBLE",
      "annees": "20XX-20XX"
    }}
  ],
  
  "competences": {{
    "techniques": "Outils avec modules. Cadres. Méthodologies.",
    "langues": "Français (langue maternelle) • Anglais professionnel (TOEIC XXX)",
    "certifications": []
  }},
  
  "gaps_vs_fiche": [
    "Ce qui manque pour faire 10/10"
  ]
}}

═══════════════════════════════════════════════════════════════════
ANTI-PATTERNS
═══════════════════════════════════════════════════════════════════

❌ Match 9-10/10 (trop parfait)
❌ Profil surqualifié
❌ Vocabulaire identique à l'annonce
❌ Noms d'entreprises réels (Deloitte, AXA, BPCE...)
❌ Descriptions d'entreprises trop vagues ("Groupe bancaire européen")
❌ "age": "34 ans" (doit être juste 34)
❌ Spécialisation dès le premier poste
❌ Structure régulière
❌ Formulations génériques
❌ Outils sans profondeur
❌ Zéro tension de contexte
❌ Chiffres de performance à chaque bullet
❌ Noms de villes
❌ "Habitué à", "Rompu à", "Fort de", "Passionné par" dans le profil
❌ Adjectifs valorisants (rigoureux, autonome, proactif, dynamique)

═══════════════════════════════════════════════════════════════════
GÉNÈRE LE CV (JSON UNIQUEMENT)
═══════════════════════════════════════════════════════════════════
"""
    
    try:
        message = client.messages.create(
            model="claude-opus-4-20250514",
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        result = message.content[0].text.strip()
        
        # Parser le JSON
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', result, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            json_match = re.search(r'(\{.*\})', result, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = result
        
        cv_data = json.loads(json_str)
        
        # Forcer le header
        cv_data['header'] = 'CV Entourage Recrutement'
        
        # S'assurer que age est un int
        if 'profil' in cv_data and 'age' in cv_data['profil']:
            age_val = cv_data['profil']['age']
            if isinstance(age_val, str):
                age_val = re.sub(r'[^\d]', '', age_val)
                cv_data['profil']['age'] = int(age_val) if age_val else 35
        
        cv_data['metadata'] = {
            'generated_at': datetime.now().isoformat(),
            'job_title': job_title_clean,
            'model': 'claude-opus-4-20250514',
            'tokens_used': message.usage.input_tokens + message.usage.output_tokens
        }
        
        return cv_data
        
    except json.JSONDecodeError as e:
        print(f"Erreur parsing JSON: {e}")
        print(f"Résultat brut: {result[:500]}")
        raise
    
    except Exception as e:
        print(f"Erreur génération CV: {e}")
        raise


def estimate_cv_length(cv_data):
    """Estime si le CV tiendra sur 1 page A4"""
    total_chars = 0
    total_chars += len(cv_data.get('profil_text', ''))
    for exp in cv_data.get('experiences', []):
        total_chars += len(exp.get('titre', ''))
        total_chars += len(exp.get('entreprise', ''))
        total_chars += len(exp.get('chapeau', ''))
        for mission in exp.get('missions', []):
            total_chars += len(mission)
    return total_chars < 3000


def condense_cv_content(cv_data):
    """Condense le CV s'il est trop long"""
    for exp in cv_data.get('experiences', []):
        if len(exp.get('missions', [])) > 5:
            exp['missions'] = exp['missions'][:5]
    return cv_data
