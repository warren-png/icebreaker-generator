"""
═══════════════════════════════════════════════════════════════════
MESSAGE SEQUENCE GENERATOR - Messages 2, 3, 4
═══════════════════════════════════════════════════════════════════

Ce module génère les messages de relance personnalisés :
- Message 2 (J+5) : Apport de valeur + insight marché
- Message 3 (J+12) : Relance légère et empathique
- Message 4 (J+21) : Break-up message

"""

import anthropic
import os
import json

# Clé API Anthropic
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

if not ANTHROPIC_API_KEY:
    raise ValueError("❌ ANTHROPIC_API_KEY non trouvée dans les variables d'environnement")


# ========================================
# MESSAGE 2 : APPORT DE VALEUR (J+5)
# ========================================

def generate_message_2(prospect_data, hooks_data, job_posting_data, message_1_content):
    """
    Génère le message 2 : apport de valeur + insights marché
    
    Args:
        prospect_data: Dict avec first_name, last_name, company
        hooks_data: Dict avec les hooks LinkedIn/web
        job_posting_data: Dict avec annonce (ou None)
        message_1_content: Contenu du message 1 (pour contexte)
    
    Returns:
        str: Message 2 généré (60-80 mots)
    """
    
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    prompt = f"""Tu es un expert en prospection B2B recrutement finance.

CONTEXTE :
Il y a 5 jours, tu as envoyé ce message 1 au prospect :
---
{message_1_content}
---

Le prospect n'a PAS répondu.

PROSPECT :
- Prénom : {prospect_data['first_name']}
- Nom : {prospect_data['last_name']}
- Entreprise : {prospect_data['company']}

HOOKS INITIAUX :
{json.dumps(hooks_data, indent=2, ensure_ascii=False)}

ANNONCE (si disponible) :
{json.dumps(job_posting_data, indent=2, ensure_ascii=False) if job_posting_data else "Aucune annonce"}

TA MISSION : Rédiger un MESSAGE 2 de relance qui apporte de la VALEUR.

STRUCTURE OBLIGATOIRE (60-80 mots) :

1. Rappel discret du message 1 (10-15 mots)
   Exemple : "Suite à mon message sur votre recherche d'auditeur..."

2. Apport de valeur concret (35-50 mots)
   CHOISIR PARMI :
   
   OPTION A - Insight marché :
   "J'ai croisé une donnée intéressante : [stat/observation marché pertinente]."
   
   OPTION B - Observation terrain :
   "En échangeant avec d'autres [fonction similaire] cette semaine, j'ai noté que [pattern observé]."
   
   OPTION C - Tendance sectorielle :
   "Le marché [secteur] montre actuellement [tendance concrète liée à leur besoin]."

3. Question ouverte simple (10-15 mots)
   Exemples :
   - "Cela confirme-t-il la tendance que vous observez ?"
   - "Est-ce un critère que vous avez également identifié ?"
   - "Voyez-vous la même dynamique de votre côté ?"

RÈGLES STRICTES :
✅ Ton courtois et professionnel (vouvoiement)
✅ Apporter de la VALEUR réelle (pas juste relancer)
✅ Pas de pression commerciale
✅ Insight doit être PLAUSIBLE et lié au contexte
✅ 60-80 mots MAX
✅ Signature : "Bien cordialement, [Prénom]"

INTERDICTIONS :
❌ "Avez-vous vu mon message ?"
❌ "Je me permets de relancer..."
❌ Ton insistant ou commercial
❌ Inventer des stats non plausibles

Génère maintenant le message 2.

Réponds UNIQUEMENT avec le message final (pas de préambule)."""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )
    
    return message.content[0].text


# ========================================
# MESSAGE 3 : RELANCE LÉGÈRE (J+12)
# ========================================

def generate_message_3(prospect_data, message_1_content):
    """
    Génère le message 3 : relance légère et empathique
    
    Args:
        prospect_data: Dict avec first_name, company
        message_1_content: Contenu du message 1 (pour contexte)
    
    Returns:
        str: Message 3 généré (40-60 mots)
    """
    
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    prompt = f"""Tu es un expert en prospection B2B recrutement finance.

CONTEXTE :
Il y a 12 jours, tu as envoyé le message 1 au prospect.
Il y a 7 jours, tu as envoyé le message 2.
Le prospect n'a TOUJOURS PAS répondu.

MESSAGE 1 INITIAL :
---
{message_1_content}
---

PROSPECT :
- Prénom : {prospect_data['first_name']}
- Entreprise : {prospect_data['company']}

TA MISSION : Rédiger un MESSAGE 3 ultra-court et empathique.

STRUCTURE OBLIGATOIRE (40-60 mots) :

1. Empathie (10-15 mots)
   Exemple : "Je sais que vos journées sont bien remplies."

2. Rappel du sujet (15-25 mots)
   Exemple : "Ma question sur [sujet du message 1] reste ouverte si jamais vous avez 2 minutes pour échanger."

3. Zéro pression (10-15 mots)
   Exemple : "Pas d'urgence de mon côté." ou "Sinon, aucun souci !"

RÈGLES STRICTES :
✅ Ultra-court (40-60 mots MAX)
✅ Ton empathique et léger
✅ ZÉRO pression commerciale
✅ Faciliter la réponse au maximum
✅ Signature : "Bien cordialement, [Prénom]"

INTERDICTIONS :
❌ Ton insistant
❌ "Dernier message" (trop tôt)
❌ Répéter l'insight du message 2

Génère maintenant le message 3.

Réponds UNIQUEMENT avec le message final (pas de préambule)."""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )
    
    return message.content[0].text


# ========================================
# MESSAGE 4 : BREAK-UP (J+21)
# ========================================

def generate_message_4(prospect_data, message_1_content):
    """
    Génère le message 4 : break-up message (permission-based)
    
    Args:
        prospect_data: Dict avec first_name
        message_1_content: Contenu du message 1 (pour contexte)
    
    Returns:
        str: Message 4 généré (50-70 mots)
    """
    
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    prompt = f"""Tu es un expert en prospection B2B recrutement finance.

CONTEXTE :
Il y a 21 jours, tu as envoyé le message 1 au prospect.
Tu as envoyé 2 relances (messages 2 et 3).
Le prospect n'a JAMAIS répondu.

C'est le DERNIER message de la séquence (break-up message).

MESSAGE 1 INITIAL :
---
{message_1_content}
---

PROSPECT :
- Prénom : {prospect_data['first_name']}

TA MISSION : Rédiger un MESSAGE 4 "break-up" qui crée un FOMO tout en restant courtois.

STRUCTURE OBLIGATOIRE (50-70 mots) :

1. Annonce de clôture (15-20 mots)
   Exemple : "Je suppose que ma question sur [sujet] n'est pas tombée au bon moment. Je vais clore le sujet de mon côté."

2. Porte ouverte (15-25 mots)
   Exemple : "Si jamais vous souhaitez échanger sur ces enjeux dans les mois à venir, ma porte reste évidemment ouverte."

3. Bonne continuation (10-20 mots)
   Exemple : "Bonne continuation pour votre recherche." ou "Je vous souhaite de trouver la perle rare !"

RÈGLES STRICTES :
✅ Ton courtois et professionnel
✅ Créer FOMO ("clore le sujet", "retirer de mon radar")
✅ Laisser la porte ouverte (pour le futur)
✅ 50-70 mots MAX
✅ Signature : "Bien cordialement, [Prénom]"

INTERDICTIONS :
❌ Ton négatif ou vexé
❌ "Si vous êtes intéressé, répondez vite"
❌ Pression commerciale

Génère maintenant le message 4.

Réponds UNIQUEMENT avec le message final (pas de préambule)."""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )
    
    return message.content[0].text


# ========================================
# FONCTION HELPER : Générer toute la séquence
# ========================================

def generate_full_sequence(prospect_data, hooks_data, job_posting_data, message_1_content):
    """
    Génère les 4 messages d'une séquence complète
    
    Args:
        prospect_data: Dict avec infos prospect
        hooks_data: Dict avec hooks
        job_posting_data: Dict avec annonce (ou None)
        message_1_content: Message 1 déjà généré
    
    Returns:
        dict: {
            'message_1': str,
            'message_2': str,
            'message_3': str,
            'message_4': str
        }
    """
    
    print(f"🔄 Génération séquence complète pour {prospect_data['first_name']} {prospect_data['last_name']}...")
    
    # Message 1 déjà fourni
    print("   ✅ Message 1 (fourni)")
    
    # Générer message 2
    print("   📝 Génération message 2...")
    message_2 = generate_message_2(prospect_data, hooks_data, job_posting_data, message_1_content)
    
    # Générer message 3
    print("   📝 Génération message 3...")
    message_3 = generate_message_3(prospect_data, message_1_content)
    
    # Générer message 4
    print("   📝 Génération message 4...")
    message_4 = generate_message_4(prospect_data, message_1_content)
    
    print("   ✅ Séquence complète générée\n")
    
    return {
        'message_1': message_1_content,
        'message_2': message_2,
        'message_3': message_3,
        'message_4': message_4
    }


# ========================================
# TEST UNITAIRE
# ========================================

if __name__ == "__main__":
    
    # Test rapide des fonctions
    print("🧪 Test des générateurs de messages\n")
    
    # Données de test
    test_prospect = {
        'first_name': 'Claire',
        'last_name': 'Martin',
        'company': 'Mutualia'
    }
    
    test_hooks = {
        'type': 'job_posting',
        'title': 'Auditeur Interne'
    }
    
    test_message_1 = """Bonjour Claire, en lisant votre recherche pour Mutualia, une question me vient : comment gérez-vous le grand écart culturel ? Le marché dispose de nombreux auditeurs excellents techniquement (Big 4, normes strictes), mais qui peinent souvent à s'adapter à la réalité du terrain agricole et aux élus mutualistes. Avez-vous tendance à privilégier le savoir-être (le fit agricole) quitte à former sur la technique, ou l'expertise reste-t-elle non négociable pour l'ACPR ?"""
    
    # Générer les 3 messages de relance
    print("1️⃣ Test Message 2...")
    message_2 = generate_message_2(test_prospect, test_hooks, None, test_message_1)
    print(f"✅ Message 2 ({len(message_2.split())} mots):\n{message_2}\n")
    
    print("2️⃣ Test Message 3...")
    message_3 = generate_message_3(test_prospect, test_message_1)
    print(f"✅ Message 3 ({len(message_3.split())} mots):\n{message_3}\n")
    
    print("3️⃣ Test Message 4...")
    message_4 = generate_message_4(test_prospect, test_message_1)
    print(f"✅ Message 4 ({len(message_4.split())} mots):\n{message_4}\n")
    
    print("✅ Tests terminés !")
