"""
═══════════════════════════════════════════════════════════════════
MESSAGE SEQUENCE GENERATOR - Messages 2, 3 + OBJETS
CORRECTIF v6 - Anti-Hallucination & Contextualisation Stricte
═══════════════════════════════════════════════════════════════════
"""

import anthropic
import os
import json
from config import COMPANY_INFO 

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

if not ANTHROPIC_API_KEY:
    raise ValueError("❌ ANTHROPIC_API_KEY non trouvée")


# ========================================
# 1. GÉNÉRATEUR D'OBJETS (CORRIGÉ & STRICT)
# ========================================

def generate_subject_lines(prospect_data, job_posting_data):
    """
    Génère 3 variantes d'objets copywrités sans hallucination.
    """
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    # Extraction sécurisée des infos
    job_title = job_posting_data.get('title', 'Finance') if job_posting_data else 'Finance'
    job_desc = job_posting_data.get('description', '')[:500] if job_posting_data else '' # On prend le début pour le contexte
    
    prompt = f"""Tu es un copywriter B2B.
Ton but : 3 objets de mail pour un recrutement.

PROSPECT : {prospect_data['first_name']} ({prospect_data['company']})
POSTE : {job_title}
EXTRAIT ANNONCE : {job_desc}

RÈGLES D'OR (A RESPECTER SINON ÉCHEC) :
1. INTERDIT : "Votre avis", "Votre retour", "[Prénom] seul".
2. INTERDIT : Inventer des logiciels (Ne cite pas SAP si ce n'est pas dans l'extrait).
3. OBLIGATOIRE : Utilise des mots-clés présents dans l'extrait (ex: logiciel spécifique, secteur, compétence).

Génère 3 variantes séparées par " | " :
- V1 : Question précise sur une compétence réelle du poste.
- V2 : Dilemme (Option A vs Option B).
- V3 : Nom du poste + Entreprise.

Exemple si poste Comptable Cinéma : "Expertise Louma ? | Rigueur vs Agilité Production | Comptable pour {prospect_data['company']}"
"""

    try:
        message = client.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=150,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text.strip()
    except:
        return f"Candidature {job_title} | Profil {job_title} | Recrutement {prospect_data['company']}"


# ========================================
# 2. MESSAGE 2 : LE DILEMME
# ========================================

def generate_message_2(prospect_data, hooks_data, job_posting_data, message_1_content):
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    job_title = job_posting_data.get('title', 'ce poste') if job_posting_data else 'ce poste'
    
    prompt = f"""Tu es consultant chez {COMPANY_INFO['name']}.
Ta mission : Email de relance "Dilemme Expert".

CONTEXTE :
Prospect : {prospect_data['first_name']} ({prospect_data['company']})
Poste : {job_title}

RÈGLES DE RÉDACTION :
1. Ne parle PAS anglais (Traduis "Functional" -> "Fonctionnel").
2. Le dilemme doit être lié au métier de : {job_title}.
   - Si Comptable : Rigueur cabinet vs Agilité PME.
   - Si Finance : Contrôle vs Business Partner.
   - Si RH : Admin vs Stratégie.

STRUCTURE :
"Bonjour {prospect_data['first_name']},
Je fais suite à mon courriel concernant votre arbitrage sur le profil {job_title}.
En observant le marché, une tendance se confirme : recruter un expert purement [Qualité A] crée [Risque A], tandis qu'un profil purement [Qualité B] manque de [Risque B].
Mon objectif est de sécuriser votre département en vous présentant des profils hybrides.
Avez-vous un créneau ce jeudi pour en discuter ?"

Génère le message 2.
"""

    message = client.messages.create(
        model="claude-3-5-sonnet-20240620",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text


# ========================================
# 3. MESSAGE 3 : BREAK-UP (CORRIGÉ "TECH")
# ========================================

def generate_message_3(prospect_data, message_1_content, job_posting_data):
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    job_title = job_posting_data.get('title', 'ce poste') if job_posting_data else 'ce poste'
    # On récupère le secteur ou une info clé pour guider l'IA
    raw_desc = job_posting_data.get('description', '') if job_posting_data else ''
    
    prompt = f"""Tu es consultant chez {COMPANY_INFO['name']}. DERNIER message (Rupture).

PROSPECT : {prospect_data['first_name']} ({prospect_data['company']})
POSTE CIBLÉ : {job_title}
DESCRIPTION SOMMAIRE : {raw_desc[:300]}

🚨 PROTOCOLE ANTI-HALLUCINATION :
1. Regarde le TITRE DU POSTE.
2. Si le poste est "Comptable", NE PARLE PAS de "Tech", "Développeurs" ou "Code". Parle de "Profils financiers", "Comptables", "Rigueur".
3. Si le poste est "RH", parle de "Recruteurs" ou "DRH".
4. Adapte la statistique inventée au MÉTIER RÉEL.

STRUCTURE :
"Bonjour {prospect_data['first_name']},
Sans retour de votre part, je vais arrêter mes relances sur ce poste de {job_title}.
Avant de clore le dossier, je voulais partager une dernière observation : sur ce type de profil, nous constatons [INVENTER UNE STAT PÉNURIE LIÉE AU MÉTIER SPÉCIFIQUE DU POSTE].
Si jamais vous rencontrez des difficultés de sourcing, n'hésitez pas à revenir vers moi.
Bonne continuation pour le développement de {prospect_data['company']}.
Bien à vous,"

Génère le message 3.
"""

    message = client.messages.create(
        model="claude-3-5-sonnet-20240620",
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