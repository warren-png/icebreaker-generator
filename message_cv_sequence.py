"""
═══════════════════════════════════════════════════════════════════
MESSAGE CV SEQUENCE - Messages 1 & 2 pour séquence avec CV
═══════════════════════════════════════════════════════════════════
"""

import anthropic
import os
from datetime import datetime, timedelta

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")


def extract_main_challenge(job_posting_data):
    """
    Détecte le contexte/enjeu prioritaire du poste
    Ex: "transformation digitale", "forte croissance", "restructuration"
    """
    
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    job_desc = job_posting_data.get('description', '')
    
    prompt = f"""Analyse cette fiche de poste et identifie le CONTEXTE/ENJEU PRIORITAIRE en 3-5 mots maximum.

FICHE DE POSTE :
{job_desc[:2000]}

Exemples de contextes :
- "transformation digitale"
- "forte croissance"
- "restructuration des équipes"
- "fusion de sites"
- "ouverture d'un nouveau site"
- "mise en conformité réglementaire"
- "modernisation des infrastructures"

Réponds UNIQUEMENT avec le contexte (3-5 mots, pas de phrase complète).
"""
    
    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=50,
            messages=[{"role": "user", "content": prompt}]
        )
        
        return message.content[0].text.strip()
        
    except:
        return "contexte de transformation"


def extract_key_skills(job_posting_data):
    """
    Extrait les 2 compétences clés les plus critiques
    """
    
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    job_desc = job_posting_data.get('description', '')
    
    prompt = f"""Analyse cette fiche de poste et identifie les 2 COMPÉTENCES CLÉS les plus critiques.

FICHE DE POSTE :
{job_desc[:2000]}

Critères de sélection :
- Compétences mentionnées plusieurs fois
- Compétences marquées comme "obligatoires" ou "indispensables"
- Compétences rares/difficiles à trouver

Format de réponse (JSON uniquement) :
{{
  "skill_1": "expertise technique précise",
  "skill_2": "compétence managériale ou métier"
}}

Exemples :
- "maîtrise SAP CO-PC" + "pilotage budgétaire multi-sites"
- "consolidation IFRS" + "anglais courant"
- "DevOps/CI-CD" + "management d'équipes 100+ personnes"

Réponds UNIQUEMENT en JSON.
"""
    
    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=150,
            messages=[{"role": "user", "content": prompt}]
        )
        
        import json
        result = json.loads(message.content[0].text.strip())
        return result['skill_1'], result['skill_2']
        
    except:
        return "expertise technique", "compétences managériales"


def generate_sequence_with_cv(prospect_data, job_posting_data, cv_url, cv_gaps):
    """
    Génère les 2 messages de la séquence CV
    
    Args:
        prospect_data: Dict avec first_name, company, etc.
        job_posting_data: Dict avec title, description
        cv_url: URL du CV sur Google Drive
        cv_gaps: Liste des écarts du CV vs fiche (ex: ["Pas d'expérience JDE"])
    
    Returns:
        Dict avec message_1, message_2, send_dates
    """
    
    first_name = prospect_data.get('first_name', '[Prénom]')
    job_title = job_posting_data.get('title', '[Poste]')
    
    # Nettoyer le titre (enlever H/F)
    import re
    job_title_clean = re.sub(r'\s*\(?[HhFf]\s*[/\-]\s*[HhFfMm]\)?', '', job_title).strip()
    
    # Extraire contexte et compétences
    main_challenge = extract_main_challenge(job_posting_data)
    skill_1, skill_2 = extract_key_skills(job_posting_data)
    
    # Formater les gaps pour le message
    gaps_text = " et ".join(cv_gaps[:2]) if cv_gaps else "certains écarts avec votre descriptif"
    
    # ========================================
    # MESSAGE 1
    # ========================================
    
    message_1 = f"""Bonjour {first_name},

J'ai vu que vous recrutiez actuellement un(e) {job_title_clean}, dans un contexte de {main_challenge}. Ce type de recrutement est souvent exigeant, car il combine {skill_1} et {skill_2} avec des enjeux opérationnels immédiats.

Sur ce type de poste, l'écart entre la cible idéale et les profils réellement disponibles sur le marché est fréquent.

Je vous partage ci-dessous un CV anonymisé qui me semble répondre aux enjeux majeurs de votre recherche.

📄 CV Anonyme - {job_title_clean}
{cv_url}

Si le profil vous paraît pertinent, je suis disponible pour en discuter. Dans le cas contraire, votre retour m'aidera à affiner le ciblage.

Bien à vous,
Warren"""
    
    # ========================================
    # MESSAGE 2
    # ========================================
    
    message_2 = f"""Bonjour {first_name},

Je me permets de revenir vers vous concernant le CV anonymisé partagé pour le poste de {job_title_clean}.

Il est possible que le profil ne corresponde pas pleinement à votre besoin actuel, ou que le timing ne soit pas idéal. Dans les deux cas, aucun souci.

Si le besoin évolue ou si vous souhaitez, à l'avenir, confronter votre recherche à d'autres profils proches de votre cible, je serai ravi de rester en contact. Je reste attentif aux évolutions du marché sur ce type de profils sous tension.

Bien à vous,
Warren"""
    
    # Dates d'envoi
    now = datetime.now()
    
    return {
        'message_1': message_1,
        'message_2': message_2,
        'send_dates': {
            'message_1': now.strftime('%Y-%m-%d'),
            'message_2': (now + timedelta(days=7)).strftime('%Y-%m-%d')
        }
    }


def generate_subject_lines_cv(job_title):
    """
    Génère les objets d'email pour la séquence CV
    """
    
    import re
    job_title_clean = re.sub(r'\s*\(?[HhFf]\s*[/\-]\s*[HhFfMm]\)?', '', job_title).strip()
    
    return f"""1. {job_title_clean} - profil qui pourrait vous intéresser
2. Re: {job_title_clean}"""
