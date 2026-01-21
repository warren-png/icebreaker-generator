"""
═══════════════════════════════════════════════════════════════════
MESSAGE SEQUENCE GENERATOR - V8 (Copywriting Expert & Varié)
Corrections : Formatage, "Message", Pertinence EPM, Variantes CTA
═══════════════════════════════════════════════════════════════════
"""

import anthropic
import os
from config import COMPANY_INFO 

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

if not ANTHROPIC_API_KEY:
    raise ValueError("❌ ANTHROPIC_API_KEY non trouvée")


# ========================================
# 1. GÉNÉRATEUR D'OBJETS
# ========================================

def generate_subject_lines(prospect_data, job_posting_data):
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    job_title = job_posting_data.get('title', 'Finance') if job_posting_data else 'Finance'
    job_desc = job_posting_data.get('description', '')[:500] if job_posting_data else ''
    
    prompt = f"""Tu es un copywriter B2B d'élite.
Ton but : 3 objets de mail pour un recrutement, courts et percutants.

CONTEXTE :
Recrutement pour : {job_title}
Chez : {prospect_data['company']}
Extrait annonce : {job_desc}

RÈGLES D'OR :
1. Langue : FRANÇAIS.
2. INTERDIT : "Votre avis", "Votre retour", "[Prénom] seul".
3. INTERDIT : Inventer des outils (ne cite SAP ou Tagetik que si présents dans l'extrait).
4. Ton : Professionnel, pair-à-pair.

Génère 3 variantes séparées par " | " :
- V1 : Question technique précise (ex: "Expertise Consolidation ?")
- V2 : Le Dilemme (ex: "Tech vs Métier")
- V3 : Poste + Entreprise (ex: "Profil {job_title}")
"""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=150,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text.strip()
    except:
        return f"Candidature {job_title} | Profil {job_title} | Recrutement {prospect_data['company']}"


# ========================================
# 2. MESSAGE 2 : LE DILEMME (VARIÉ & PERTINENT)
# ========================================

def generate_message_2(prospect_data, hooks_data, job_posting_data, message_1_content):
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    job_title = job_posting_data.get('title', 'ce poste') if job_posting_data else 'ce poste'
    
    prompt = f"""Tu es chasseur de têtes expert. Tu écris un message de relance.

CONTEXTE :
Prospect : {prospect_data['first_name']}
Poste : {job_title}

CONSIGNE FORMATAGE (CRITIQUE) :
1. Écris "Bonjour {prospect_data['first_name']},"
2. SAUTE DEUX LIGNES OBLIGATOIREMENT.
3. Commence la phrase suivante par une MAJUSCULE.
4. PAS DE SIGNATURE à la fin (mon CRM l'ajoute).
5. Utilise le mot "message" (jamais "courriel").

CONSIGNE FOND (LE DILEMME) :
Trouve le vrai point de tension du poste (Dilemme) :
- Si EPM/SI Finance : Le dilemme est "Expertise Outil (Tech)" vs "Vision Business (Métier)". (Ne parle pas de réglementaire international sauf si précisé).
- Si Audit : "Rigueur Normative" vs "Agilité Opérationnelle".
- Si Comptable : "Expertise Cabinet" vs "Polyvalence PME".

CHOISIS UNE FIN (CTA) PARMI CES OPTIONS (Ne prends pas toujours la même) :
Option A : "Plutôt que de multiplier les entretiens, prenons 15 min pour valider si cette double compétence est la clé de votre roadmap."
Option B : "Si cet équilibre est critique pour votre équipe, je vous propose d'échanger 15 min pour en discuter."
Option C : "Avez-vous 15 min cette semaine pour définir si cette approche hybride correspond à votre besoin ?"

STRUCTURE DU MESSAGE :
"Bonjour {prospect_data['first_name']},

Je fais suite à mon message concernant votre arbitrage sur le profil {job_title}.

En observant [Secteur/Marché], une tendance se confirme : recruter un profil purement [Qualité A] crée [Risque A], tandis qu'un profil purement [Qualité B] manque de [Risque B].

[Insère ici ta phrase de transition sur le profil hybride].

[Insère ici une des Options de Fin (A, B ou C)]."
"""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text


# ========================================
# 3. MESSAGE 3 : BREAK-UP (VARIÉ & ANTI-HALLUCINATION)
# ========================================

def generate_message_3(prospect_data, message_1_content, job_posting_data):
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    job_title = job_posting_data.get('title', 'ce poste') if job_posting_data else 'ce poste'
    raw_desc = job_posting_data.get('description', '') if job_posting_data else ''
    
    prompt = f"""Tu es chasseur de têtes. C'est ton DERNIER message (Rupture).

CONTEXTE :
Poste : {job_title}
Extrait : {raw_desc[:300]}

CONSIGNE FORMATAGE :
1. "Bonjour {prospect_data['first_name']}," + 2 sauts de ligne + Majuscule.
2. PAS DE SIGNATURE.

CONSIGNE ANTI-HALLUCINATION :
- Regarde le titre du poste.
- Si Comptable/Finance : PARLE DE PROFILS FINANCIERS (Jamais de "Tech" ou "Dev").
- Si EPM : Parle d'experts EPM.

CHOISIS UNE FIN (PORTE OUVERTE) PARMI CES OPTIONS :
Option A : "Si jamais la pénurie de candidats sur ce créneau spécifique persiste, ma ligne reste ouverte."
Option B : "Si vous faites face à cette difficulté de sourcing dans les semaines à venir, n'hésitez pas à revenir vers moi."
Option C : "Je clos le dossier pour le moment. Si la situation évolue de votre côté, je reste à l'écoute."

STRUCTURE :
"Bonjour {prospect_data['first_name']},

Sans retour de votre part, je vais arrêter mes relances sur ce poste.

Avant de clore le dossier, je voulais partager une dernière observation : sur des profils [Citer le métier exact], nous constatons que [Inventer une stat/tendance pénurie crédible liée au métier].

[Insère ici une des Options de Fin (A, B ou C)]."
"""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text


# ========================================
# FONCTION HELPER
# ========================================

def generate_full_sequence(prospect_data, hooks_data, job_posting_data, message_1_content):
    
    # 1. Objets
    subject_lines = generate_subject_lines(prospect_data, job_posting_data)
    
    # 2. Message 2
    message_2 = generate_message_2(prospect_data, hooks_data, job_posting_data, message_1_content)
    
    # 3. Message 3
    message_3 = generate_message_3(prospect_data, message_1_content, job_posting_data)
    
    return {
        'subject_lines': subject_lines,
        'message_1': message_1_content,
        'message_2': message_2,
        'message_3': message_3
    }