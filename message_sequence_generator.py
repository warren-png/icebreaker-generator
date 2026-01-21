"""
═══════════════════════════════════════════════════════════════════
MESSAGE SEQUENCE GENERATOR - Messages 2, 3 + OBJETS
═══════════════════════════════════════════════════════════════════

Ce module génère :
1. Les Objets de mail (Variantes Copywriting)
2. Le Message 2 (Méthode "Dilemme Expert")
3. Le Message 3 (Méthode "Break-up FOMO" - Fin de séquence)

"""

import anthropic
import os
import json
from config import COMPANY_INFO 

# Clé API Anthropic
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

if not ANTHROPIC_API_KEY:
    raise ValueError("❌ ANTHROPIC_API_KEY non trouvée dans les variables d'environnement")


# ========================================
# 1. GÉNÉRATEUR D'OBJETS
# ========================================

def generate_subject_lines(prospect_data, job_posting_data):
    """
    Génère 3 variantes d'objets copywrités pour maximiser l'ouverture.
    """
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    contexte_poste = "votre équipe Finance"
    if job_posting_data and job_posting_data.get('title'):
        contexte_poste = f"le poste de {job_posting_data['title']}"

    prompt = f"""Tu es un copywriter B2B expert.
Ta mission : Rédiger 3 objets de mail pour un prospect Finance/RH.
Le but est uniquement de provoquer l'ouverture (curiosité ou précision).

PROSPECT : {prospect_data['first_name']} ({prospect_data['company']})
SUJET : Recrutement pour {contexte_poste}

RÈGLES :
1. Courts (2 à 6 mots max).
2. Pas de majuscules agressives, pas de points d'exclamation.
3. Ton : "Peer-to-peer" (d'égal à égal).

Génère 3 variantes selon ces angles :
- Variante 1 (Ultra-Directe) : Ex: "Question sur [Poste]"
- Variante 2 (Le Dilemme) : Ex: "Arbitrage [Compétence A] vs [Compétence B]"
- Variante 3 (Intriguante) : Ex: "[Prénom], votre avis ?" ou "Profil [Poste]"

Réponds UNIQUEMENT avec les 3 objets séparés par une barre verticale "|".
Exemple : Question AMOA | Arbitrage Technique vs Projet | Profil hybride pour Mutualia
"""

    try:
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=100,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text.strip()
    except:
        return f"Question {contexte_poste} | Votre recrutement | Profil Entourage"


# ========================================
# 2. MESSAGE 2 : LE DILEMME (J+5)
# ========================================

def generate_message_2(prospect_data, hooks_data, job_posting_data, message_1_content):
    """
    Génère le message 2 basé sur la structure "Dilemme" (Profil A vs Profil B -> Hybride)
    """
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    # Contexte du poste
    job_context = "votre recherche actuelle"
    if job_posting_data and job_posting_data.get('title'):
        job_context = f"le poste de {job_posting_data['title']}"
    
    prompt = f"""Tu es consultant chez {COMPANY_INFO['name']}.
Ton style est expert, précis et analytique.

CONTEXTE :
Tu relances {prospect_data['first_name']} ({prospect_data['company']}) concernant {job_context}.

TA MISSION :
Rédiger un email de relance qui expose un DILEMME DE RECRUTEMENT (A vs B) et propose un profil HYBRIDE.

EXEMPLES À IMITER PARFAITEMENT (Structure & Ton) :

Exemple 1 (AMOA) :
"Bonjour Domitille,
Je fais suite à mon courriel concernant votre arbitrage sur le profil AMOA.
En observant les projets SI actuels, une tendance se confirme : recruter un expert purement "Métier" crée souvent un goulot d'étranglement face à la DSI, tandis qu'un profil purement "Projet" peine à anticiper les impacts DSN.
Mon objectif est de sécuriser votre roadmap en vous présentant des profils "hybrides", capables de traduire instantanément les contraintes légales en specs techniques.
Avez-vous un créneau ce jeudi pour définir ensemble si cette double compétence est la clé pour débloquer vos projets ?"

Exemple 2 (Trésorerie) :
"Bonjour Sileymane,
Je fais suite à mon courriel concernant votre recherche de profil Trésorerie.
En observant le secteur retail, une réalité s'impose : un expert trésorerie trop traditionnel peine souvent à suivre la cadence des flux magasins, tandis qu'un profil trop généraliste manque de la rigueur nécessaire pour sécuriser vos liquidités.
Mon objectif est de fiabiliser votre gestion du cash en vous présentant des profils "agiles", qui possèdent la technicité mais ont prouvé leur adaptation.
Avez-vous un créneau ce jeudi pour définir ensemble si cette capacité d'adaptation est le critère décisif ?"

CONSIGNES DE RÉDACTION :
1. Reprends EXACTEMENT la structure : 
   - Intro ("Je fais suite concernant votre arbitrage...")
   - Le Constat/Dilemme ("En observant..., une tendance se confirme : Profil A [défaut], tandis que Profil B [défaut].")
   - La Solution ("Mon objectif est de sécuriser [Enjeu] en vous présentant des profils [Hybrides/Mixtes]...")
   - Le CTA ("Avez-vous un créneau ce jeudi pour définir si...")
2. Adapte le contenu au poste de : {job_context}.
3. Invente un dilemme PLAUSIBLE et PERTINENT pour ce métier (Tech vs Métier, Cabinet vs Entreprise, Expert vs Business Partner).

Génère maintenant le message 2. Réponds UNIQUEMENT avec le message final.
"""

    message = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text


# ========================================
# 3. MESSAGE 3 : BREAK-UP EXPERT (J+12)
# ========================================

def generate_message_3(prospect_data, message_1_content):
    """
    Génère le message 3 : Break-up avec Insight Marché/FOMO
    """
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    prompt = f"""Tu es consultant chez {COMPANY_INFO['name']}. C'est ton DERNIER message.
Ton but : Créer un FOMO (Fear Of Missing Out) en partageant une observation marché alarmante (délai, échec, pénurie).

PROSPECT : {prospect_data['first_name']} ({prospect_data['company']})

EXEMPLES À IMITER PARFAITEMENT :

Exemple 1 (Délai qui s'allonge) :
"Bonjour Domitille,
Sans retour de votre part, je vais arrêter mes relances sur ce poste de Responsable AMOA.
Avant de clore le dossier, je voulais juste partager un dernier chiffre : sur les recrutements similaires ce trimestre, le délai moyen de prise de poste s'allonge (environ 4 mois) en raison de la pénurie de profils hybrides Paie/SI.
Si jamais vous rencontrez des difficultés de sourcing dans les semaines à venir, n'hésitez pas à revenir vers moi.
Bonne continuation dans vos recherches,
Bien à vous,"

Exemple 2 (Risque d'échec) :
"Bonjour Matthias,
Sans retour de votre part, je vais arrêter mes relances sur ce poste de PMO.
Avant de clore le dossier, je voulais partager une dernière observation critique : nous constatons que près de 40% des recrutements échouent dans les 6 premiers mois, non par manque de compétence technique, mais par manque de leadership d'influence.
Si jamais vous faites face à cette difficulté d'adhésion terrain, n'hésitez pas à revenir vers moi.
Bonne continuation pour la structuration de Cap Vert Group.
Bien à vous,"

CONSIGNES DE RÉDACTION :
1. Structure stricte :
   - Intro ("Sans retour, je vais arrêter mes relances...")
   - L'Insight FOMO ("Avant de clore, je voulais partager une dernière observation/chiffre : [Insight alarmant lié au poste].")
   - La Porte ouverte ("Si jamais vous faites face à [Problème], n'hésitez pas...")
   - Fin ("Bonne continuation...")
2. Sois crédible : invente une stat ou une tendance réaliste pour le poste du prospect.

Génère maintenant le message 3. Réponds UNIQUEMENT avec le message final.
"""

    message = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text


# ========================================
# FONCTION HELPER : Séquence Complète (3 Messages)
# ========================================

def generate_full_sequence(prospect_data, hooks_data, job_posting_data, message_1_content):
    """
    Orchestre la génération des objets et des messages 2 & 3.
    """
    
    print(f"🔄 Génération séquence (3 msgs) pour {prospect_data['first_name']}...")
    
    # 1. Objets
    print("   💡 Génération des objets...")
    subject_lines = generate_subject_lines(prospect_data, job_posting_data)
    
    # 2. Message 2
    print("   📝 Génération message 2 (Dilemme)...")
    message_2 = generate_message_2(prospect_data, hooks_data, job_posting_data, message_1_content)
    
    # 3. Message 3
    print("   📝 Génération message 3 (Break-up)...")
    message_3 = generate_message_3(prospect_data, message_1_content)
    
    print("   ✅ Séquence générée avec succès\n")
    
    return {
        'subject_lines': subject_lines,
        'message_1': message_1_content,
        'message_2': message_2,
        'message_3': message_3
    }


# ========================================
# TEST UNITAIRE
# ========================================

if __name__ == "__main__":
    
    print("🧪 Test des nouveaux messages (Séquence 3 messages)\n")
    
    test_prospect = {
        'first_name': 'Thomas',
        'last_name': 'Durand',
        'company': 'Green Energy'
    }
    
    test_job = {
        'title': 'Responsable Administratif et Financier'
    }
    
    test_msg_1 = "Contenu msg 1..."
    
    # Test Objets
    print("1️⃣ Idées Objets :")
    print(generate_subject_lines(test_prospect, test_job))
    print("\n----------------\n")
    
    # Test M2
    print("2️⃣ Message 2 (Dilemme) :")
    print(generate_message_2(test_prospect, None, test_job, test_msg_1))
    print("\n----------------\n")
    
    # Test M3
    print("3️⃣ Message 3 (Break-up) :")
    print(generate_message_3(test_prospect, test_msg_1))
    
    print("\n✅ Tests terminés !")