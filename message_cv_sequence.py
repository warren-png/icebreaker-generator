"""
═══════════════════════════════════════════════════════════════════
MESSAGE CV SEQUENCE V2.1 - Messages courts et directs
Séquence 2 messages : M1 (CV joint) + M2 (relance stratégique J+7)
═══════════════════════════════════════════════════════════════════
"""

import anthropic
import os
import re
import json
import time
from datetime import datetime, timedelta

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")


def generate_sequence_with_cv(prospect_data, job_posting_data, cv_url, cv_gaps=None):
    """
    Génère les 2 messages via Claude à partir de la fiche de poste
    """
    
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    first_name = prospect_data.get('first_name', '[Prénom]')
    job_title = job_posting_data.get('title', '[Poste]')
    job_desc = job_posting_data.get('description', '')
    
    # Nettoyer le titre (enlever H/F)
    job_title_clean = re.sub(r'\s*\(?[HhFf]\s*[/\-]\s*[HhFfMm]\)?', '', job_title).strip()
    
    prompt = f"""Tu es chasseur de têtes Finance. Génère 2 messages COURTS pour accompagner un CV anonymisé.

═══════════════════════════════════════════════════════════════════
FICHE DE POSTE
═══════════════════════════════════════════════════════════════════
Titre : {job_title_clean}
Description :
{job_desc[:3000]}

═══════════════════════════════════════════════════════════════════
MESSAGE 1 — STRUCTURE EXACTE (4 blocs, pas un de plus)
═══════════════════════════════════════════════════════════════════

Bonjour {first_name},

[BLOC 1 — 2 phrases COURTES collées, pas de saut de ligne entre elles]
Phrase 1 : "Vous recrutez actuellement un profil [domaine reformulé] dans [environnement], avec [contraintes clés entre parenthèses]."
Phrase 2 : "Ce type de recrutement est exigeant, [raison en 10-15 mots]."

[BLOC 2 — 1 phrase]
"Je vous partage ci-dessous un CV anonymisé qui me semble répondre aux enjeux majeurs de votre recherche, notamment sur [2 compétences courtes]."

[BLOC 3 — lien]
📄 CV anonymisé – [Domaine court 3-5 mots] {cv_url}

[BLOC 4 — closing EXACT, ne pas modifier]
Si le profil vous paraît pertinent, je suis disponible pour en discuter. Dans le cas contraire, votre retour m'aidera à affiner le ciblage.

Bien à vous,

═══════════════════════════════════════════════════════════════════
MESSAGE 2 — STRUCTURE EXACTE (3 blocs, pas de saut de ligne entre phrases)
═══════════════════════════════════════════════════════════════════

Bonjour {first_name},

[BLOC 1 — 1 phrase]
"Je me permets de revenir vers vous concernant le CV anonymisé partagé pour votre recrutement en [domaine court / sous-domaine] dans [environnement court]."

[BLOC 2 — 2 phrases collées]
"Il est possible que le profil ne corresponde pas pleinement à vos attentes, ou que le timing ne soit pas le bon. Avant de clore le sujet de mon côté, pouvez-vous m'indiquer si cette recherche est aujourd'hui pilotée en direct ou avec l'appui d'un cabinet de recrutement ?"

[BLOC 3 — 1 phrase]
"Selon le cas, je saurai s'il est pertinent de vous recontacter ultérieurement."

Bien à vous,

═══════════════════════════════════════════════════════════════════
RÈGLES ABSOLUES
═══════════════════════════════════════════════════════════════════
❌ JAMAIS "Je comprends que vous recherchez" → TOUJOURS "Vous recrutez actuellement"
❌ JAMAIS "Un recrutement particulièrement exigeant par..." → TOUJOURS "Ce type de recrutement est exigeant,"
❌ JAMAIS "attendus actuels" → "attentes"
❌ JAMAIS "me dire" → "m'indiquer"
❌ JAMAIS "ce recrutement est piloté" → "cette recherche est pilotée"
❌ JAMAIS "un ou plusieurs cabinets" → "un cabinet de recrutement"
❌ JAMAIS de paragraphes longs (max 2 phrases par bloc)
❌ JAMAIS de signature
❌ JAMAIS inventer des compétences absentes de la fiche
❌ JAMAIS plus de 3 mots-clés entre parenthèses
❌ M1 = maximum 8 lignes (hors "Bonjour" et "Bien à vous")
❌ M2 = maximum 6 lignes (hors "Bonjour" et "Bien à vous")

═══════════════════════════════════════════════════════════════════
FORMAT JSON UNIQUEMENT
═══════════════════════════════════════════════════════════════════
{{
  "message_1": "contenu complet M1 avec lien CV",
  "message_2": "contenu complet M2",
  "cv_link_label": "📄 CV anonymisé – [Domaine court]"
}}
"""

    try:
        max_retries = 3
        base_delay = 30
        
        for attempt in range(max_retries):
            try:
                message = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=1500,
                    messages=[{"role": "user", "content": prompt}]
                )
                break
            except anthropic.RateLimitError as e:
                if attempt < max_retries - 1:
                    wait_time = base_delay * (2 ** attempt)
                    print(f"⏳ Rate limit. Attente {wait_time}s ({attempt + 1}/{max_retries})...")
                    time.sleep(wait_time)
                else:
                    raise e
        
        result = message.content[0].text.strip()
        
        # Parser le JSON
        json_match = re.search(r'\{.*\}', result, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
        else:
            raise ValueError(f"Pas de JSON trouvé dans la réponse: {result[:200]}")
        
        # Dates d'envoi
        now = datetime.now()
        
        return {
            'message_1': data['message_1'],
            'message_2': data['message_2'],
            'cv_link_label': data.get('cv_link_label', f'📄 CV anonymisé – {job_title_clean}'),
            'send_dates': {
                'message_1': now.strftime('%Y-%m-%d'),
                'message_2': (now + timedelta(days=7)).strftime('%Y-%m-%d')
            }
        }
        
    except json.JSONDecodeError as e:
        print(f"❌ Erreur parsing JSON: {e}")
        print(f"Résultat brut: {result[:500]}")
        raise
    
    except Exception as e:
        print(f"❌ Erreur génération messages CV: {e}")
        raise


def generate_subject_lines_cv(job_title):
    """
    Génère les objets d'email pour la séquence CV
    """
    job_title_clean = re.sub(r'\s*\(?[HhFf]\s*[/\-]\s*[HhFfMm]\)?', '', job_title).strip()
    
    return f"""1. {job_title_clean} – profil qui pourrait vous intéresser
2. Re: {job_title_clean}"""
