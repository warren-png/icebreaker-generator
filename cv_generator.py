"""
═══════════════════════════════════════════════════════════════════
CV GENERATOR - Génération de CVs anonymes réalistes
Version 1.0 - Utilise Claude Opus 4.6 pour qualité maximale
═══════════════════════════════════════════════════════════════════
"""

import anthropic
import os
from datetime import datetime
import json

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

def generate_cv_content(job_posting_data, prospect_data=None):
    """
    Génère le contenu d'un CV anonyme qui matche à 85% la fiche de poste
    
    Args:
        job_posting_data: Dict avec 'title' et 'description'
        prospect_data: Dict optionnel avec infos prospect (pour contexte)
    
    Returns:
        Dict avec le contenu du CV structuré
    """
    
    if not job_posting_data:
        raise ValueError("job_posting_data requis")
    
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    job_title = job_posting_data.get('title', 'Poste')
    job_desc = job_posting_data.get('description', '')
    
    # Nettoyer le titre (enlever H/F)
    import re
    job_title_clean = re.sub(r'\s*\(?[HhFf]\s*[/\-]\s*[HhFfMm]\)?', '', job_title).strip()
    
    prompt = f"""Tu dois générer un CV anonyme ultra-réaliste pour un poste de {job_title_clean}.

═══════════════════════════════════════════════════════════════════
FICHE DE POSTE
═══════════════════════════════════════════════════════════════════
{job_desc[:3000]}

═══════════════════════════════════════════════════════════════════
RÈGLES ABSOLUES POUR UN CV À 8-9/10 EN AUTHENTICITÉ
═══════════════════════════════════════════════════════════════════

1. MATCH À 85% (PAS 100%)
   - Identifier 1-2 compétences/outils demandés que le profil N'A PAS
   - Exemple : Fiche demande JDE → CV a SAP (ERP concurrent)
   - Exemple : Fiche demande cosmétique → CV vient d'agroalimentaire

2. CHIFFRES IMPARFAITS (JAMAIS RONDS)
   - ❌ 2M€, 10%, 1h, 12 mois
   - ✅ 1,87M€, 9,3%, 1h20, 16 mois
   - Toujours contextualiser : "objectif 3M€, réalisé 1,87M€"

3. ÉCHECS/LIMITES (1 PAR EXPÉRIENCE)
   - Projet retardé : "16 mois au lieu de 12 (complexité technique)"
   - Objectif partiel : "45% workloads migrés (objectif 60%)"
   - Problème non résolu : "on bute encore sur les fromages frais (pertes 9,3% vs objectif 6%)"

4. PROBLÈMES RÉSOLUS MAIS COÛTEUX
   - "Anomalie valorisation stocks : impact comptable 380K€"
   - "Incident sécurité 2019 : forensic + correctifs 180K€"
   - "Coûts réseau cloud plus élevés que prévu"

5. DÉTAILS ULTRA-PRÉCIS
   - Noms d'outils complets : "SAP CO-PC" pas "SAP"
   - Contexte chiffré : "380 serveurs physiques", "8 datacenters → 2 sites"
   - Méthodes techniques : "FG au prorata heures machines", "PPA sur 3 acquisitions"

6. LANGAGE TERRAIN (PAS CONSULTING)
   - ✅ "on bute encore sur", "résistance opérationnelle", "dépendances sous-estimées"
   - ❌ "optimisation des processus", "construction du business case", "pilotage des KPI"

7. PARCOURS COHÉRENT
   - 3-4 expériences progressives
   - Durées réalistes (pas de missions 2 mois)
   - Secteur adjacent si pas match parfait

═══════════════════════════════════════════════════════════════════
FORMAT JSON À RETOURNER
═══════════════════════════════════════════════════════════════════

{{
  "profil": {{
    "age": 32,
    "localisation": "Région parisienne",
    "disponibilite": "Préavis 3 mois",
    "mobilite": "Mobilité nationale"
  }},
  
  "profil_text": "3-4 lignes décrivant le parcours et la recherche. Ton naturel, pas corporate.",
  
  "experiences": [
    {{
      "titre": "Contrôleur de Gestion Industriel",
      "dates": "Mars 2021 - Aujourd'hui",
      "entreprise": "Groupe agroalimentaire (CA 850M€)",
      "lieu": "Site Chartres, 450 collaborateurs",
      "missions": [
        "Mission 1 avec chiffres imparfaits et contexte détaillé",
        "Mission 2 avec un problème/limite assumé",
        "Mission 3 avec jargon technique précis"
      ]
    }},
    {{
      "titre": "...",
      "dates": "...",
      "entreprise": "...",
      "lieu": "...",
      "missions": ["..."]
    }}
  ],
  
  "formation": [
    {{
      "diplome": "Master Finance & Contrôle de Gestion",
      "ecole": "IAE Paris-Sorbonne",
      "annees": "2016-2018"
    }}
  ],
  
  "competences": {{
    "techniques": "ERP: SAP (CO-PC, FI-CO), Excel avancé (VBA), Power BI • Gestion industrielle: Prix de revient standards, GPAO • Finance: Budget, forecast, P&L",
    "langues": "Français (langue maternelle) • Anglais courant (TOEIC 915/990)",
    "certifications": []
  }},
  
  "gaps_vs_fiche": [
    "Pas d'expérience JDE (a SAP à la place)",
    "Secteur agroalimentaire au lieu de cosmétique"
  ]
}}

═══════════════════════════════════════════════════════════════════
GÉNÈRE LE CV MAINTENANT (JSON UNIQUEMENT)
═══════════════════════════════════════════════════════════════════
"""
    
    try:
        message = client.messages.create(
            model="claude-opus-4-20250514",  # Opus 4.6
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        result = message.content[0].text.strip()
        
        # Parser le JSON (gérer les backticks markdown)
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', result, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Chercher juste le JSON
            json_match = re.search(r'(\{.*\})', result, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = result
        
        cv_data = json.loads(json_str)
        
        # Ajouter métadonnées
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
    """
    Estime si le CV tiendra sur 1 page A4
    Retourne True si OK, False si trop long
    """
    
    total_chars = 0
    
    # Profil
    total_chars += len(cv_data.get('profil_text', ''))
    
    # Expériences
    for exp in cv_data.get('experiences', []):
        total_chars += len(exp.get('titre', ''))
        total_chars += len(exp.get('entreprise', ''))
        for mission in exp.get('missions', []):
            total_chars += len(mission)
    
    # Estimation grossière : 1 page A4 = ~3000 caractères max
    return total_chars < 3000


def condense_cv_content(cv_data):
    """
    Condense le CV s'il est trop long
    Garde les 3 premières missions par expérience max
    """
    
    for exp in cv_data.get('experiences', []):
        if len(exp.get('missions', [])) > 3:
            exp['missions'] = exp['missions'][:3]
    
    return cv_data
