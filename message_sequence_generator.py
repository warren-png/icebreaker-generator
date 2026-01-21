"""
═══════════════════════════════════════════════════════════════════
MESSAGE SEQUENCE GENERATOR - V15 (FINAL & CLEAN)
Corrections : Nettoyage Titres, Prénoms, CTA Utilisateur, Logique Audit
═══════════════════════════════════════════════════════════════════
"""

import anthropic
import os
import re 
from config import COMPANY_INFO 

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

if not ANTHROPIC_API_KEY:
    raise ValueError("❌ ANTHROPIC_API_KEY non trouvée")


# ========================================
# FONCTIONS UTILITAIRES (NETTOYAGE)
# ========================================

def clean_job_title_string(title):
    """
    Nettoie le titre du poste pour l'insérer dans une phrase.
    Ex: "COMPTABLE SENIOR H/F" -> "Comptable Senior"
    """
    if not title: return "ce poste"
    
    # 1. Enlever H/F, M/F, (h/f), etc. avec regex insensible à la casse
    title = re.sub(r'\s*\(?[HhFf]\s*[/\-]\s*[HhFfMm]\)?', '', title, flags=re.IGNORECASE)
    title = re.sub(r'\s*\(?[Mm]\s*[/\-]\s*[Ff]\)?', '', title, flags=re.IGNORECASE)
    
    # 2. Enlever les tirets ou barres en fin de chaîne
    title = re.sub(r'\s*[-|]\s*.*$', '', title) # Coupe tout après un tiret final type " - CDI"
    
    # 3. Formater en "Title Case" (Première lettre majuscule)
    return title.strip().title()


# ========================================
# 1. GÉNÉRATEUR D'OBJETS
# ========================================

def generate_subject_lines(prospect_data, job_posting_data):
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    raw_title = job_posting_data.get('title', 'Finance') if job_posting_data else 'Finance'
    job_title = clean_job_title_string(raw_title)
    job_desc = job_posting_data.get('description', '')[:500] if job_posting_data else ''
    
    prompt = f"""Tu es un copywriter B2B expert en recrutement.
CONTEXTE :
Recrutement pour : {job_title}
Chez : {prospect_data['company']}
Extrait annonce : {job_desc}

RÈGLES D'OR :
1. Langue : FRANÇAIS.
2. INTERDIT : "Votre avis", "Votre retour", "[Prénom] seul".
3. INTERDIT : Inventer des outils (ne cite SAP, Tagetik, etc. que si présents dans l'extrait).
4. INTERDIT : Copier la description de l'entreprise dans l'objet (trop long).

Génère 3 variantes séparées par " | " :
- V1 : Question technique précise (ex: "Expertise Consolidation ?")
- V2 : Le Dilemme (ex: "Conformité vs Business")
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
# 2. MESSAGE 2 : LE DILEMME (CORRIGÉ & VARIÉ)
# ========================================

def generate_message_2(prospect_data, hooks_data, job_posting_data, message_1_content):
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    raw_title = job_posting_data.get('title', 'ce poste') if job_posting_data else 'ce poste'
    job_title = clean_job_title_string(raw_title)
    
    hooks_str = str(hooks_data) if hooks_data and hooks_data != "NOT_FOUND" else "Aucune actualité récente"
    
    # Instruction spécifique Audit
    audit_instruction = ""
    if "audit" in job_title.lower():
        audit_instruction = "ATTENTION AUDIT : Le dilemme n'est PAS Technique vs Métier. C'est 'Expertise Méthodologique/Conformité' (Théorie) vs 'Pragmatisme Opérationnel/Business' (Pratique)."

    prompt = f"""Tu es chasseur de têtes expert.

CONTEXTE :
Prospect : {prospect_data['first_name']}
Poste : {job_title}
Actu Prospect : {hooks_str}

{audit_instruction}

RÈGLE D'OR (MATCHMAKING) :
- Analyse l'actualité du prospect (Hook).
- SI elle a un lien professionnel pertinent avec le poste, utilise-la en phrase d'accroche.
- SINON (ou si vide), commence directement par le rappel du poste.

CONSIGNE FORMATAGE STRICTE :
1. Écris EXACTEMENT "Bonjour {prospect_data['first_name']}," (Insère le prénom).
2. SAUTE DEUX LIGNES (Laisse une ligne vide).
3. Utilise "message" (pas "courriel").

STRUCTURE DU MESSAGE :
1. "Bonjour {prospect_data['first_name']},"
2. [Saut de ligne]
3. [Accroche personnalisée ou Rappel du poste]
4. [Le Dilemme : "En observant le marché, recruter un profil purement X crée le risque Y, tandis que Z..."]
5. [La Solution Hybride : "Les meilleurs profils savent jongler entre..."]
6. [CONCLUSION OBLIGATOIRE : Choisis UNE option ci-dessous. RECOPIE-LA AU MOT PRÈS.]

OPTIONS DE CONCLUSION (Strictement interdits de modifier) :
- Option 1 : "Si cet arbitrage entre technique et métier est aujourd'hui le point bloquant pour avancer sur votre roadmap, une approche ciblée sur ces profils 'passerelles' est souvent la clé. Avez-vous 15 min pour définir si cette stratégie correspond à votre besoin ?"
- Option 2 : "C'est précisément sur l'identification de ces profils que j'accompagne mes clients. Auriez-vous un rapide créneau de 15 min prochainement ou seriez-vous ouvert à recevoir des candidatures qui correspondent à votre besoin ?"
- Option 3 : "Pour éviter l'écueil d'un recrutement qui ne répondrait qu'à moitié aux enjeux opérationnels, je vous propose de valider ensemble la pertinence de ce profil hybride. Avez-vous 15 min cette semaine pour en échanger ?"

Génère le message 2 complet.
"""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text


# ========================================
# 3. MESSAGE 3 : BREAK-UP (CORRIGÉ & NETTOYÉ)
# ========================================

def generate_message_3(prospect_data, message_1_content, job_posting_data):
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    raw_title = job_posting_data.get('title', 'ce poste') if job_posting_data else 'ce poste'
    job_title = clean_job_title_string(raw_title)
    raw_desc = job_posting_data.get('description', '') if job_posting_data else ''
    
    prompt = f"""Tu es chasseur de têtes. DERNIER message (Rupture).

CONTEXTE :
Poste : {job_title}
Extrait Annonce : {raw_desc[:300]}

CONSIGNE FORMATAGE STRICTE :
1. Écris EXACTEMENT "Bonjour {prospect_data['first_name']}," (Insère le prénom).
2. SAUTE DEUX LIGNES (Laisse une ligne vide).

CONSIGNE ANTI-HALLUCINATION :
- Si poste Comptable/Finance -> Parle Finance/Expertise (Pas de Tech).
- Si poste EPM -> Parle EPM.
- Adapte la statistique de pénurie au métier réel.

STRUCTURE DU MESSAGE :
1. "Bonjour {prospect_data['first_name']},"
2. [Saut de ligne]
3. Intro : "Sans retour de votre part, je vais arrêter mes relances sur ce poste."
4. Observation Marché : "Avant de clore le dossier, je voulais partager une dernière observation : sur des profils [Métier], nous constatons que [Statistique pénurie crédible et pertinente]."
5. [CONCLUSION OBLIGATOIRE : Choisis UNE option ci-dessous. RECOPIE-LA AU MOT PRÈS.]

OPTIONS DE CONCLUSION (Strictement interdits de modifier) :
- Option A : "Je clos ce dossier. Si toutefois la tension sur ces compétences spécifiques venait à freiner vos recrutements dans les semaines à venir, je reste à votre disposition pour réévaluer le marché. Bonne continuation pour votre recherche."
- Option B : "Je cesse mes relances ici. Si vous constatez que le sourcing traditionnel atteint ses limites sur ce type d'expertise pointue, n'hésitez pas à me solliciter pour activer une approche par chasse directe. Bonne continuation pour votre recherche."
- Option C : "Je ne vous sollicite plus sur ce sujet. Si jamais vous faites face à cette inertie ou à une pénurie de CVs pertinents dans les semaines à venir, n'hésitez pas à revenir vers moi. Bonne continuation pour votre recherche."

Génère le message 3 complet.
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
    
    subject_lines = generate_subject_lines(prospect_data, job_posting_data)
    message_2 = generate_message_2(prospect_data, hooks_data, job_posting_data, message_1_content)
    message_3 = generate_message_3(prospect_data, message_1_content, job_posting_data)
    
    return {
        'subject_lines': subject_lines,
        'message_1': message_1_content,
        'message_2': message_2,
        'message_3': message_3
    }