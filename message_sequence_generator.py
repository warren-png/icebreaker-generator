"""
═══════════════════════════════════════════════════════════════════
MESSAGE SEQUENCE GENERATOR - Messages 2, 3 + OBJETS
CORRECTIF v5 - Traduction FR forcée + Contexte Job Message 3
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
# 1. GÉNÉRATEUR D'OBJETS (CORRIGÉ)
# ========================================

def generate_subject_lines(prospect_data, job_posting_data):
    """
    Génère 3 variantes d'objets copywrités.
    """
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    contexte_poste = "votre équipe Finance"
    if job_posting_data and job_posting_data.get('title'):
        contexte_poste = f"le poste de {job_posting_data['title']}"

    prompt = f"""Tu es un copywriter B2B expert.
Ta mission : Rédiger 3 objets de mail pour un prospect Finance/RH.

PROSPECT : {prospect_data['first_name']} ({prospect_data['company']})
SUJET : Recrutement pour {contexte_poste}

RÈGLES STRICTES :
1. Langue : FRANÇAIS uniquement.
2. Pas de "Votre retour", pas de prénoms seuls, pas de familiarités.
3. Doit faire référence au sujet technique ou au recrutement.

Génère 3 variantes selon ces angles :
- Variante 1 (Question précise) : Ex: "Question recrutement EPM"
- Variante 2 (Le Dilemme) : Ex: "Arbitrage Technique vs Métier"
- Variante 3 (Candidature/Profil) : Ex: "Profil {job_posting_data.get('title', 'Finance')}"

Réponds UNIQUEMENT avec les 3 objets séparés par une barre verticale "|".
"""

    try:
        message = client.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=100,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text.strip()
    except:
        return f"Question {contexte_poste} | Recrutement en cours | Profil Entourage"


# ========================================
# 2. MESSAGE 2 : LE DILEMME (CORRIGÉ TRADUCTION)
# ========================================

def generate_message_2(prospect_data, hooks_data, job_posting_data, message_1_content):
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    job_title = "ce poste"
    if job_posting_data and job_posting_data.get('title'):
        job_title = job_posting_data['title']
    
    prompt = f"""Tu es consultant chez {COMPANY_INFO['name']}.
Ton style est expert, précis et analytique.

CONTEXTE :
Tu relances {prospect_data['first_name']} ({prospect_data['company']}) concernant le poste : {job_title}.

RÈGLE D'OR (TRADUCTION) :
Si le titre du poste ou le descriptif est en ANGLAIS, tu dois TRADUIRE les concepts en FRANÇAIS.
Ne dis pas "Functional", dis "Fonctionnel".
Ne dis pas "Technical", dis "Technique".
Ne dis pas "Business Partner", dis "Partenaire Business".

TA MISSION :
Rédiger un email de relance (Structure DILEMME).

STRUCTURE :
1. Intro : "Bonjour [Prénom], Je fais suite à mon courriel concernant votre arbitrage sur le profil [Nom du Poste]."
2. Le Constat (Dilemme) : "En observant..., une tendance se confirme : recruter un profil purement [Qualité A] crée [Défaut A], tandis qu'un profil purement [Qualité B] manque de [Défaut B]."
3. La Solution : "Mon objectif est de sécuriser [Enjeu] en vous présentant des profils [Hybrides], qui allient..."
4. CTA : "Avez-vous un créneau ce jeudi pour définir ensemble si..."

Génère maintenant le message 2. Réponds UNIQUEMENT avec le message final.
"""

    message = client.messages.create(
        model="claude-3-5-sonnet-20240620",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text


# ========================================
# 3. MESSAGE 3 : BREAK-UP (CORRIGÉ CONTEXTE)
# ========================================

# MODIFICATION IMPORTANTE : Ajout de job_posting_data dans les arguments
def generate_message_3(prospect_data, message_1_content, job_posting_data):
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    # On force le contexte du poste pour éviter l'hallucination "Marketing Digital"
    job_title = "ce poste"
    if job_posting_data and job_posting_data.get('title'):
        job_title = job_posting_data['title']
    
    prompt = f"""Tu es consultant chez {COMPANY_INFO['name']}. C'est ton DERNIER message.
Ton but : Créer un FOMO (Fear Of Missing Out) réaliste.

PROSPECT : {prospect_data['first_name']} ({prospect_data['company']})
POSTE CONCERNÉ : {job_title}
⚠️ INTERDICTION D'INVENTER UN AUTRE POSTE. Parle uniquement de : {job_title}.

STRUCTURE OBLIGATOIRE :
"Bonjour [Prénom],
Sans retour de votre part, je vais arrêter mes relances sur ce poste de {job_title}.
Avant de clore le dossier, je voulais partager une dernière observation : [Invente une stat/tendance plausible sur la pénurie de profils POUR CE POSTE SPÉCIFIQUE].
Si jamais vous rencontrez des difficultés de sourcing dans les semaines à venir, n'hésitez pas à revenir vers moi.
Bonne continuation dans vos recherches,
Bien à vous,"

Génère maintenant le message 3. Réponds UNIQUEMENT avec le message final.
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
    
    print(f"🔄 Génération séquence pour {prospect_data['first_name']}...")
    
    # 1. Objets
    subject_lines = generate_subject_lines(prospect_data, job_posting_data)
    
    # 2. Message 2
    message_2 = generate_message_2(prospect_data, hooks_data, job_posting_data, message_1_content)
    
    # 3. Message 3 (On passe bien job_posting_data maintenant !)
    message_3 = generate_message_3(prospect_data, message_1_content, job_posting_data)
    
    return {
        'subject_lines': subject_lines,
        'message_1': message_1_content,
        'message_2': message_2,
        'message_3': message_3
    }