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
# 7. PAIN POINTS DÉTAILLÉS PAR MÉTIER (VERSION ENRICHIE)
# ========================================

PAIN_POINTS_DETAILED = {
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
    
    'raf': {
        'polyvalence': {
            'short': "polyvalence extrême sans relais managérial",
            'context': "Comptabilité, contrôle, trésorerie, fiscalité avec peu de relais managérial."
        },
        'undersizing': {
            'short': "sous-dimensionnement chronique des équipes",
            'context': "Difficulté à absorber la charge. Priorisation constante entre urgence et structuration."
        },
        'tools': {
            'short': "outillage finance insuffisant",
            'context': "ERP partiellement exploité. Reporting artisanal."
        },
        'structuration': {
            'short': "projets de structuration à mener en parallèle de la production",
            'context': "Process, contrôle interne, reporting groupe. Peu de temps pour conduire le changement."
        }
    },
    
    'controle_gestion': {
        'data_quality': {
            'short': "données peu fiables et disponibles trop tard",
            'context': "Dépendance à Excel. Retraitements multiples. Indicateurs disponibles trop tard pour décider."
        },
        'hybrid_profiles': {
            'short': "manque de profils hybrides finance + data",
            'context': "Profils très finance mais peu outillés. Profils data ne comprenant pas les logiques business."
        },
        'business_partnering': {
            'short': "difficulté à passer du reporting au business partnering",
            'context': "Équipes cantonnées au reporting. Faible influence dans les décisions opérationnelles."
        },
        'demand_overflow': {
            'short': "multiplication des demandes métiers sans priorisation",
            'context': "Sollicitations constantes. Arbitrages difficiles. Frustration des opérationnels."
        }
    },
    
    'fpna': {
        'excel_dependency': {
            'short': "trop de dépendance à Excel, retraitements manuels multiples",
            'context': "Tableurs critiques. Fichiers partagés instables. Erreurs de version."
        },
        'reporting_trap': {
            'short': "équipes cantonnées au reporting, faible influence stratégique",
            'context': "Production de slides. Peu d'écoute en CODIR. Rôle de « faiseur de chiffres »."
        },
        'demand_overflow': {
            'short': "multiplication des demandes métiers sans priorisation claire",
            'context': "Sollicitations constantes. Arbitrages difficiles."
        },
        'volatility': {
            'short': "difficulté à modéliser rapidement dans un contexte volatil",
            'context': "Volatilité des coûts, prix, volumes. Scénarios difficiles à modéliser."
        }
    },
    
    'comptabilite': {
        'closing_pressure': {
            'short': "charge de clôture excessive et récurrente",
            'context': "Deadlines serrées. Heures sup structurelles. Peu de marge pour traiter les anomalies."
        },
        'talent_shortage': {
            'short': "pénurie de profils comptables opérationnels fiables",
            'context': "Difficulté à recruter des comptables autonomes. Courbe d'apprentissage longue."
        },
        'key_person_dependency': {
            'short': "dépendance à des personnes clés",
            'context': "Connaissance concentrée sur 1-2 seniors. Risque élevé en cas d'absence ou départ."
        },
        'transformation_projects': {
            'short': "projets de transformation en parallèle de la production",
            'context': "ERP, CSP, dématérialisation, e-invoicing. Double charge run + projet."
        }
    },
    
    'consolidation': {
        'manual_processes': {
            'short': "process lourds et peu automatisés",
            'context': "Retraitements manuels. Fichiers critiques multiples. Forte dépendance à Excel."
        },
        'deadline_pressure': {
            'short': "pression extrême sur les délais de clôture groupe",
            'context': "Deadlines groupe non négociables. Arbitrages permanents qualité / rapidité."
        },
        'data_quality': {
            'short': "qualité hétérogène des données filiales",
            'context': "Niveau comptable variable selon pays/BU. Retards de remontée. Reprises fréquentes."
        },
        'key_man_risk': {
            'short': "key-man risk élevé",
            'context': "Connaissance concentrée sur 1-2 personnes. Risque majeur en cas de départ."
        }
    },
    
    'audit': {
        'coverage': {
            'short': "couverture de risques insuffisante face à la croissance",
            'context': "Périmètres en croissance. Nouveaux risques (cyber, data, fournisseurs). Ressources stables."
        },
        'senior_profiles': {
            'short': "manque de profils seniors autonomes",
            'context': "Difficulté à recruter des auditeurs capables de dialoguer avec la DG."
        },
        'recommendations_backlog': {
            'short': "backlog de recommandations non suivies",
            'context': "Faible taux de mise en œuvre. Crédibilité de la fonction en jeu."
        },
        'data_driven': {
            'short': "transformation vers l'audit data-driven difficile",
            'context': "Outillage insuffisant. Analyses très manuelles. Faible exploitation de la data."
        }
    },
    
    'epm': {
        'project_delays': {
            'short': "projets EPM qui s'éternisent",
            'context': "Roadmaps surchargées. Dépendance aux intégrateurs. Faible capacité interne d'évolution."
        },
        'adoption': {
            'short': "faible adoption des outils par les utilisateurs",
            'context': "Contournements Excel. Process parallèles non maîtrisés."
        },
        'hybrid_profiles': {
            'short': "difficulté à trouver des profils Tech + Finance",
            'context': "Profils techniques sans culture finance. Profils finance sans compétences outils."
        },
        'support_load': {
            'short': "charge élevée de support utilisateurs",
            'context': "Peu de bande passante pour les projets stratégiques. Mode pompier permanent."
        }
    },
    
    'bi_data': {
        'data_access': {
            'short': "accès aux données lent et instable",
            'context': "Pipelines fragiles. Dépendance à la DSI ou aux prestataires."
        },
        'kpi_credibility': {
            'short': "KPI contestés en comité de direction",
            'context': "Définitions variables selon BU. Référentiels absents. Multiples versions de la vérité."
        },
        'hybrid_profiles': {
            'short': "manque de profils hybrides data + finance",
            'context': "Data engineers sans culture finance. Contrôleurs sans compétences data avancées."
        },
        'analytical_debt': {
            'short': "dette analytique importante",
            'context': "Tableurs critiques. Retraitements manuels avant CODIR."
        }
    },
    
    'data_ia': {
        'hybrid_profiles': {
            'short': "difficulté à trouver des profils technique + business",
            'context': "Maîtrise Python, SQL, ML mais compréhension limitée des enjeux métiers."
        },
        'acculturation': {
            'short': "acculturation IA lente dans les métiers",
            'context': "Résistance au changement. Manque de formation. Faible appropriation."
        },
        'use_cases': {
            'short': "cas d'usage IA qui n'aboutissent pas",
            'context': "Faute de sponsor métier engagé. POCs qui ne passent pas en production."
        },
        'leadership': {
            'short': "manque de profils capables d'animer un centre d'excellence IA",
            'context': "Leadership transverse. Capacité à former, évangéliser, structurer la gouvernance."
        }
    }
}

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
