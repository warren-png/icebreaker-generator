# Configuration de l'automatisation Icebreaker
import os
from dotenv import load_dotenv

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()

# ========================================
# 1. CLÉ API CLAUDE
# ========================================
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# ========================================
# 2. CLÉ API APIFY
# ========================================
APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN")

# ========================================
# 3. CLÉ API SERPER
# ========================================
SERPER_API_KEY = os.getenv("SERPER_API_KEY")

# ========================================
# 4. ACTEURS APIFY
# ========================================
APIFY_ACTORS = {
    "profile": "dev_fusion/Linkedin-Profile-Scraper", 
    "profile_posts": "supreme_coder/Linkedin-post",
    "company_posts": "supreme_coder/Linkedin-post",
    "company_profile": "dev_fusion/Linkedin-Company-Scraper"
}

# ========================================
# 5. GOOGLE SHEET
# ========================================
GOOGLE_SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME", "Prospects Icebreaker")
WORKSHEET_NAME = os.getenv("WORKSHEET_NAME", "Feuille 1")
GOOGLE_CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "google-credentials.json")

# ========================================
# 6. INFORMATIONS ENTREPRISE
# ========================================

COMPANY_INFO = {
    # Identité
    'name': 'Entourage Recrutement',
    
    # Positionnement (essence de votre différence)
    'positioning': 'Cabinet de chasse spécialisé en recrutements critiques de profils finance à fort impact business',
    
    # Notre rôle unique
    'mission': 'Sécuriser les décisions de recrutement sur des postes où une erreur est coûteuse en temps, organisation et crédibilité managériale',
    
    # Différenciateurs clés (3 points max)
    'differentiators': [
        'Approche 100% chasse ciblée et confidentielle (pas de diffusion d\'annonces)',
        'Évaluation orientée contexte : capacité à réussir CHEZ VOUS, pas juste "savoir faire le métier"',
        'Compréhension fine du besoin réel : priorités opérationnelles, irritants équipes, critères d\'échec'
    ],
    
    # Profils recrutés (synthèse)
    'profiles': 'DAF/CFO/RAF, Contrôle de gestion/FP&A, M&A/Corporate Dev, Transformation Finance, BI/Data Finance, MOA Finance',
    
    # Clients types
    'clients': 'Groupes, ETI, filiales. Secteurs : assurance, banque, services financiers. Contextes : transformation, structuration finance, croissance externe',
    
    # Ce que vous NE faites PAS
    'not_us': 'Pas de recrutement de masse, pas de start-ups early stage, pas de logiques de volume',
    
    # Valeur client (ce qu'ils gagnent)
    'client_value': 'Moins d\'entretiens non pertinents, profils réellement comparables, décision plus rapide et sécurisée, meilleure tenue dans le temps',
    
    # Philosophie icebreaker
    'icebreaker_philosophy': 'L\'icebreaker doit démontrer qu\'on comprend LEURS enjeux business/finance spécifiques. Notre expertise doit transparaître dans la qualité de l\'analyse, pas dans l\'auto-promotion.'
}


# ========================================
# 7. PAIN POINTS DÉTAILLÉS PAR MÉTIER
# VERSION V27.2.1 : Pain points SAFE sans présupposés
# ========================================

PAIN_POINTS_DETAILED = {
    'audit': {
        'multi_site_international': {
            'short': "audit en environnement multi-sites international",
            'context': "Difficulté à trouver des profils qui allient expertise audit financier et opérationnel avec compréhension des enjeux multi-sites et capacité à travailler en environnement international complexe."
        },
        'industrial_processes': {
            'short': "compréhension des processus industriels",
            'context': "Le défi réside dans la capacité à allier rigueur de l'audit avec une forte compréhension des enjeux opérationnels industriels (production, supply chain, clôture)."
        },
        'control_internal': {
            'short': "expertise contrôle interne en environnement complexe",
            'context': "Difficulté à trouver des profils qui combinent expertise technique de l'audit et capacité à évaluer la qualité du contrôle interne dans des organisations décentralisées."
        }
    },
    
    'controle_gestion': {
        'structuration': {
            'short': "structuration du pilotage financier multi-entités",
            'context': "Le défi réside dans la capacité à structurer from scratch les outils de pilotage financier tout en fiabilisant les données et en accélérant la production d'indicateurs de performance."
        },
        'multi_site': {
            'short': "pilotage de réseau multi-sites",
            'context': "Difficulté à trouver des profils capables de déployer un pilotage financier cohérent sur un réseau décentralisé tout en garantissant la fiabilité des reportings consolidés."
        },
        'business_partnering': {
            'short': "business partnering en environnement complexe",
            'context': "Le marché combine difficilement expertise technique du contrôle de gestion et capacités relationnelles pour accompagner les opérationnels dans le pilotage de la performance."
        }
    },
    
    'consolidation': {
        'ifrs_expertise': {
            'short': "expertise consolidation IFRS en environnement complexe",
            'context': "Difficulté à trouver des profils qui combinent expertise technique des normes IFRS et capacité à accompagner les filiales dans la montée en compétence."
        },
        'multi_entity': {
            'short': "consolidation multi-entités internationales",
            'context': "Le défi réside dans la capacité à gérer la consolidation d'entités internationales aux référentiels hétérogènes tout en garantissant la fiabilité et les délais de production."
        }
    },
    
    'data_ia': {
        'technical_business': {
            'short': "profils qui allient technique et acculturation métier",
            'context': "Le marché combine difficilement expertise technique (Data Science, IA) et capacités d'accompagnement des métiers dans l'adoption de ces technologies."
        },
        'use_case_deployment': {
            'short': "déploiement de cas d'usage IA opérationnels",
            'context': "Difficulté à trouver des profils capables de transformer des POCs IA en solutions opérationnelles avec adoption réelle par les métiers."
        }
    },
    
    'epm': {
        'tool_deployment': {
            'short': "déploiement outil EPM et adoption utilisateurs",
            'context': "Le marché combine difficilement expertise technique de l'outil EPM et capacités projet pour garantir l'adoption utilisateurs et la pérennité du déploiement."
        },
        'functional_technical': {
            'short': "profils fonctionnels ET techniques sur EPM",
            'context': "Difficulté à trouver des profils qui allient compréhension métier (consolidation, reporting, budget) et capacités techniques de paramétrage et d'intégration."
        }
    },
    
    'comptabilite': {
        'technical_agility': {
            'short': "expertise comptable et agilité opérationnelle",
            'context': "Le défi réside dans la capacité à allier rigueur comptable et agilité pour accompagner la croissance en environnement dynamique."
        },
        'regulatory_operational': {
            'short': "comptabilité réglementaire en environnement complexe",
            'context': "Difficulté à trouver des profils qui combinent expertise des normes comptables et capacité à gérer la production dans des délais contraints."
        }
    },
    
    'fpna': {
        'modeling_communication': {
            'short': "modélisation financière et business partnering",
            'context': "Le marché combine difficilement expertise en modélisation financière (forecast, business plans) et capacités de communication pour accompagner les décisions stratégiques."
        }
    },
    
    'bi_data': {
        'technical_functional': {
            'short': "profils techniques ET fonctionnels en BI",
            'context': "Difficulté à trouver des profils qui allient compétences techniques (BI, data) et compréhension des besoins métier pour créer des outils de pilotage réellement utilisés."
        }
    },
    
    'daf': {
        'visibility': {
            'short': "manque de visibilité fiable et rapide",
            'context': "Reporting lent. Indicateurs discutés plutôt qu'utilisés. Décisions prises avec retard."
        },
        'production_focus': {
            'short': "organisation finance trop orientée production",
            'context': "Équipes absorbées par la clôture. Peu de bande passante pour l'analyse et la stratégie."
        },
        'transformation': {
            'short': "transformation permanente (ERP, EPM, BI) qui épuise les équipes",
            'context': "Projets ERP, EPM, BI, CSP, digitalisation. Fatigue organisationnelle."
        }
    },
    
    'raf': {
        'polyvalence': {
            'short': "polyvalence extrême sans relais managérial",
            'context': "Comptabilité, contrôle, trésorerie, fiscalité avec peu de relais managérial."
        },
        'undersizing': {
            'short': "sous-dimensionnement chronique des équipes",
            'context': "Difficulté à absorber la charge. Priorisation constante entre urgence et structuration."
        }
    }
}


"""
═══════════════════════════════════════════════════════════════════
PAIN_POINTS_DETAILED - ANCIENNE VERSION (DÉSACTIVÉE)
Conservé en commentaire pour référence historique
═══════════════════════════════════════════════════════════════════

Cette version contenait des présupposés qui pouvaient générer des 
inventions de contenu (ex: "data_driven" pour audit même sans mention
de data/analytics dans la fiche de poste).

PAIN_POINTS_DETAILED_OLD = {
    'daf': {
        'visibility': {
            'short': "manque de visibilité fiable et rapide",
            'context': "Reporting lent. Indicateurs discutés plutôt qu'utilisés. Décisions prises avec retard."
        },
        'production_focus': {
            'short': "organisation finance trop orientée production",
            'context': "Équipes absorbées par la clôture. Peu de bande passante pour l'analyse et la stratégie."
        },
        'transformation': {
            'short': "transformation permanente (ERP, EPM, BI) qui épuise les équipes",
            'context': "Projets ERP, EPM, BI, CSP, digitalisation. Fatigue organisationnelle."
        },
        'key_man_risk': {
            'short': "dépendance forte à quelques profils clés",
            'context': "Key-man risk élevé. Difficulté à sécuriser les compétences critiques."
        },
        'attractiveness': {
            'short': "attractivité limitée de la fonction finance",
            'context': "Concurrence forte pour les bons profils. Difficulté à attirer des talents haut potentiel."
        }
    },
    
    'audit': {
        'data_driven': {  # ← PROBLÉMATIQUE : présuppose data/analytics
            'short': "transformation vers l'audit data-driven difficile",
            'context': "Outillage insuffisant. Analyses très manuelles. Faible exploitation de la data."
        }
    }
}
"""


# ========================================
# 8. OUTCOMES DÉTAILLÉS PAR MÉTIER
# ========================================

OUTCOMES_DETAILED = {
    'general': [
        "sécurisation rapide de profils opérationnels alignés avec vos enjeux",
        "réduction du temps de recrutement et du risque d'erreur de casting",
        "accès à des profils passifs non visibles sur les jobboards",
        "évaluation orientée contexte : capacité à réussir chez vous, pas juste savoir faire le métier"
    ],
    
    'daf': [
        "pilotage plus rapide et plus fiable de la performance",
        "finance repositionnée comme partenaire business auprès des opérationnels",
        "capacité à mener la transformation sans rupture organisationnelle",
        "stabilisation et montée en compétence des équipes finance",
        "réduction du key-man risk sur les fonctions critiques"
    ],
    
    'raf': [
        "sécurisation du socle financier (compta, contrôle, tréso, fiscal)",
        "structuration progressive de la fonction sans tout bloquer",
        "gain de bande passante pour le pilotage stratégique",
        "capacité à accompagner la croissance sans tension structurelle"
    ],
    
    'controle_gestion': [
        "accélération du pilotage de la performance avec des données fiables",
        "transformation du rôle des équipes vers le business partnering",
        "réussite des projets EPM/BI par des profils sachant les porter",
        "réduction de la dépendance aux tableurs critiques"
    ],
    
    'fpna': [
        "amélioration de la qualité décisionnelle par des analyses plus rapides",
        "réduction de la dépendance aux tableurs critiques et aux retraitements manuels",
        "rééquilibrage production / analyse avec plus de temps pour la stratégie",
        "crédibilité renforcée auprès du CODIR et de la DG"
    ],
    
    'comptabilite': [
        "absorption des pics d'activité sans tension structurelle sur les équipes",
        "sécurisation de la production comptable avec moins d'erreurs",
        "réduction de la dépendance à quelques personnes clés",
        "capacité à mener les projets de transformation en parallèle du run"
    ],
    
    'consolidation': [
        "accélération des cycles de clôture groupe avec meilleure fiabilité",
        "montée en compétence collective des équipes consolidation",
        "autonomie renforcée vis-à-vis des filiales et meilleure gouvernance",
        "réduction du key-man risk sur la fonction critique"
    ],
    
    'audit': [
        "couverture de risques alignée avec la stratégie et les priorités du comité",
        "renforcement rapide du niveau senior pour dialoguer avec la DG",
        "crédibilité renforcée auprès des comités d'audit et de direction",
        "accélération de la digitalisation de l'audit (data analytics, audit continu)"
    ],
    
    'epm': [
        "accélération des cycles budget / forecast / clôture avec meilleure qualité",
        "adoption réelle des outils par les utilisateurs avec moins de contournements Excel",
        "autonomie vis-à-vis des intégrateurs et montée en compétence interne",
        "sécurisation de la continuité opérationnelle et réduction du key-man risk"
    ],
    
    'bi_data': [
        "time-to-insight fortement réduit pour les décisions stratégiques",
        "crédibilité renforcée du pilotage financier auprès du CODIR",
        "self-service gouverné avec référentiels clairs et stables",
        "réduction des risques opérationnels liés aux erreurs de pilotage"
    ],
    
    'data_ia': [
        "adoption réelle de l'IA dans les métiers avec des cas d'usage en production",
        "ROI mesurable sur les cas d'usage déployés (pas juste des POCs)",
        "acculturation IA accélérée par des formations, ateliers, centre d'excellence",
        "réduction de la dépendance aux consultants externes et montée en compétence interne"
    ]
}


# ========================================
# 9. PARAMÈTRES
# ========================================
DELAY_BETWEEN_PROSPECTS = 5  # Délai entre chaque prospect (secondes)
CLAUDE_MODEL = "claude-sonnet-4-20250514"

# Paramètres de recherche web
WEB_SEARCH_ENABLED = True  # Activer/désactiver facilement
MAX_SEARCH_RESULTS = 5  # Limiter le nombre de résultats

# ========================================
# 10. COLONNES GOOGLE SHEET
# ========================================
COL_LINKEDIN_URL = 4      # Colonne D
COL_HOOKS = 7             # Colonne G
COL_ICEBREAKER = 11       # Colonne K

# ========================================
# 11. VÉRIFICATION DES CLÉS API
# ========================================
def check_api_keys():
    """Vérifie que toutes les clés API sont configurées"""
    
    import streamlit as st
    
    required_keys = {
        'ANTHROPIC_API_KEY': 'Clé API Anthropic',
        'APIFY_API_KEY': 'Clé API Apify',
        'SERPER_API_KEY': 'Clé API Serper'
    }
    
    missing_keys = []
    
    for key, description in required_keys.items():
        # Essayer d'abord st.secrets, puis os.getenv
        try:
            value = st.secrets.get(key, os.getenv(key))
        except:
            value = os.getenv(key)
        
        if not value:
            missing_keys.append(f"{description} ({key})")
    
    if missing_keys:
        raise ValueError(
            f"❌ Clés API manquantes : {', '.join(missing_keys)}\n"
            "Veuillez les configurer dans .env ou Streamlit Cloud Secrets"
        )
    
    print("✅ Toutes les clés API sont configurées")
