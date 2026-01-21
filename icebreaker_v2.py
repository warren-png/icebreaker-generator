"""
═══════════════════════════════════════════════════════════════════
ICEBREAKER GENERATOR V2 (MODULE)
Version : V16 (Ton Adouci + Formatage Corrigé)
Utilisé par : app_streamlit.py
═══════════════════════════════════════════════════════════════════
"""

import anthropic
import json
import os
from config import COMPANY_INFO 
from scraper_job_posting import format_job_data_for_prompt

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

if not ANTHROPIC_API_KEY:
    raise ValueError("❌ ANTHROPIC_API_KEY non trouvée")

# ========================================
# 1. EXTRACTION DES HOOKS
# ========================================

def extract_hooks_with_claude(profile_data, posts_data, company_posts, company_profile, web_results, prospect_name, company_name):
    """Extrait 1-2 hooks pertinents pour l'icebreaker (Limité à 3 mois)"""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    data_summary = {
        "profile": {
            "fullName": profile_data.get("fullName", "") if profile_data else "",
            "headline": profile_data.get("headline", "") if profile_data else "",
            "summary": profile_data.get("summary", "") if profile_data else "",
            "current_position": profile_data.get("experiences", [{}])[0].get("title", "") if profile_data and profile_data.get("experiences") else "",
        },
        "recent_posts": posts_data[:5] if posts_data else [],
        "company_posts": company_posts[:3] if company_posts else [],
        "web_mentions": web_results
    }
    
    prompt = f"""Tu es un analyste en intelligence économique.
OBJECTIF : Trouver un prétexte (Hook) de moins de 3 mois pour engager une conversation B2B.

DONNÉES :
{json.dumps(data_summary, indent=2, ensure_ascii=False)}

RÈGLES :
1. Cherche en priorité un contenu CRÉÉ par le prospect (Post, Article).
2. Sinon, une interaction (Like/Commentaire).
3. Sinon, une actu entreprise majeure.
4. DATE LIMITE : Tout ce qui a > 3 mois est IGNORÉ.

SORTIE JSON UNIQUEMENT :
{{
  "hook_principal": {{
    "description": "Description concise",
    "type_action": "CREATOR" | "INTERACTOR" | "COMPANY",
    "date": "Date approx",
    "pertinence": 5
   }}
}}
Si rien trouvé : Réponds "NOT_FOUND".
"""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            temperature=0.2,
            messages=[{"role": "user", "content": prompt}]
        )
        response_text = message.content[0].text.strip()
        # Nettoyage basique si Claude met du markdown
        response_text = response_text.replace('```json', '').replace('```', '').strip()
        return response_text
        
    except Exception as e:
        return "NOT_FOUND"


# ========================================
# 2. GÉNÉRATION ICEBREAKER (Message 1)
# ========================================

def generate_advanced_icebreaker(prospect_data, hooks_json, job_posting_data=None):
    """Génère un icebreaker (Message 1) avec le ton adouci et le bon formatage."""
    
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    # Gestion des hooks
    try:
        if hooks_json and hooks_json != "NOT_FOUND":
            hooks_data = json.loads(hooks_json)
        else:
            hooks_data = {"status": "NOT_FOUND"}
    except:
        hooks_data = {"status": "NOT_FOUND"}
    
    # Contexte Annonce
    job_context = ""
    if job_posting_data:
        job_context = format_job_data_for_prompt(job_posting_data)
    
    prompt = f"""Tu es un expert en copywriting B2B pour le recrutement.
Ta mission : Rédiger le MESSAGE 1 (Icebreaker) d'une séquence d'approche directe.

CONTEXTE :
Prospect : {prospect_data['first_name']} ({prospect_data['company']})
Poste Visé (Annonce) : {job_posting_data.get('title', 'N/A') if job_posting_data else 'N/A'}
Hooks : {json.dumps(hooks_data, ensure_ascii=False)}

RÈGLES DE FORMATAGE (IMPÉRATIVES) :
1. Commence par "Bonjour {prospect_data['first_name']},"
2. SAUTE DEUX LIGNES (Laisse une ligne vide après le bonjour).
3. Commence la phrase suivante par une MAJUSCULE.
4. PAS de signature (gérée par le CRM).

TON & STYLE (MODIFIÉ - IMPORTANT) :
- Ne sois JAMAIS négatif ou critique ("lacunes", "rigide" = INTERDIT).
- Utilise la rhétorique de la "POLARISATION" pour décrire le marché.
  -> Au lieu de dire "les candidats sont mauvais", dis : "On observe souvent une polarisation : d'un côté des experts pointus, de l'autre des profils opérationnels. L'équilibre est rare."
- Sois valorisant pour le prospect.

STRUCTURE DU MESSAGE :
1. Salutation + [Hook Perso OU Mention de l'annonce].
   *Ex avec Hook : "J'ai lu votre post sur..."*
   *Ex sans Hook : "J'ai consulté votre recherche de [Poste]..."*

2. L'Insight Marché (La Polarisation) :
   "Trouver un profil alliant [Compétence A] et [Compétence B] est un vrai défi. On observe souvent une polarisation sur le marché : d'un côté des experts très pointus sur [A], de l'autre des profils focalisés sur [B]. L'équilibre parfait est rare."

3. La Question d'Arbitrage :
   "Comment arbitrez-vous aujourd'hui entre privilégier [A] ou favoriser [B] ?"

EXEMPLES DE PHRASES D'INSIGHT (À Utiliser) :
- "On observe souvent une polarisation sur le marché : d'un côté des experts techniques, de l'autre des business partners. L'équilibre parfait est rare."
- "Le marché est souvent scindé en deux : les purs techniciens et les profils terrain. Trouver le pont entre les deux est complexe."

Génère le Message 1.
"""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=600,
            temperature=0.4,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text.strip()
        
    except Exception as e:
        return f"Bonjour {prospect_data['first_name']},\n\nErreur de génération."