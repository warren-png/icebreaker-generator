"""
═══════════════════════════════════════════════════════════════════
APP STREAMLIT V28 - VERSION TEST
═══════════════════════════════════════════════════════════════════
Pour tester : streamlit run app_streamlit_v28.py
═══════════════════════════════════════════════════════════════════
"""

import streamlit as st
import os
import json
from dotenv import load_dotenv

load_dotenv()

# Import V28
from sequence_generator_v28 import (
    generate_sequence_v28,
    init_apify_client,
    scrape_linkedin_profile,
    scrape_linkedin_posts,
    tracker
)

# ========================================
# CONFIGURATION PAGE
# ========================================

st.set_page_config(
    page_title="Icebreaker Generator V28",
    page_icon="🎯",
    layout="wide"
)

st.title("🎯 Icebreaker Generator V28")
st.caption("Architecture simplifiée - 1 appel Claude pour M1+M2")

# ========================================
# SIDEBAR - CONFIGURATION
# ========================================

with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Vérification API Keys
    api_key = os.getenv("ANTHROPIC_API_KEY")
    apify_key = os.getenv("APIFY_API_TOKEN")
    
    if api_key:
        st.success("✅ Anthropic API Key configurée")
    else:
        st.error("❌ ANTHROPIC_API_KEY manquante")
    
    if apify_key:
        st.success("✅ Apify API Key configurée")
    else:
        st.warning("⚠️ APIFY_API_TOKEN manquante (scraping désactivé)")
    
    st.divider()
    
    # Stats
    st.header("📊 Stats Session")
    if tracker.calls:
        st.metric("Appels API", len(tracker.calls))
        st.metric("Tokens totaux", f"{tracker.total_input_tokens + tracker.total_output_tokens:,}")
        st.metric("Coût total", f"${tracker.total_cost:.4f}")
    else:
        st.info("Aucun appel API encore")

# ========================================
# TABS
# ========================================

tab1, tab2, tab3 = st.tabs(["🎯 Génération", "📋 Tests Rapides", "📖 Documentation"])

# ========================================
# TAB 1 : GÉNÉRATION MANUELLE
# ========================================

with tab1:
    st.header("Génération de séquence")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("👤 Prospect")
        
        prenom = st.text_input("Prénom", value="Alexandre")
        nom = st.text_input("Nom", value="Dupont")
        headline = st.text_input("Titre LinkedIn", value="Responsable Comptabilité Technique")
        company = st.text_input("Entreprise", value="CAMCA")
        linkedin_url = st.text_input("URL LinkedIn (optionnel)", value="")
    
    with col2:
        st.subheader("📄 Fiche de poste")
        
        job_title = st.text_input("Titre du poste", value="Comptable Technique F/H")
        job_description = st.text_area(
            "Description du poste",
            height=300,
            value="""Rattaché(e) au Responsable Comptabilité Technique, le comptable technique aura pour missions principales :
• Enregistrer la comptabilité des opérations techniques d'assurance, de réassurance et de coassurance
• Participer à la mise en œuvre des outils, processus et méthodes liés aux opérations d'assurance
• Contribuer au respect des obligations déclaratives aux niveaux comptable, fiscal, réglementaire

Profil :
• De formation supérieure Bac +3 (type DCG), 5 ans d'expérience minimum
• Maîtrise des opérations comptables courantes et d'inventaire d'une société d'assurance non-vie"""
        )
    
    st.subheader("💬 Posts LinkedIn (optionnel)")
    posts_text = st.text_area(
        "Collez ici les posts LinkedIn récents du prospect (un par ligne)",
        height=100,
        placeholder="Post 1: J'ai eu le plaisir de participer à...\nPost 2: Retour sur notre événement..."
    )
    
    # Bouton génération
    if st.button("🚀 Générer la séquence", type="primary", use_container_width=True):
        
        if not api_key:
            st.error("❌ Configurez ANTHROPIC_API_KEY dans .env")
        else:
            # Préparer les données
            prospect_data = {
                'full_name': f"{prenom} {nom}",
                'first_name': prenom,
                'headline': headline,
                'company': company,
                'linkedin_url': linkedin_url
            }
            
            job_posting_data = {
                'title': job_title,
                'description': job_description
            }
            
            # Parser les posts
            posts_data = []
            if posts_text.strip():
                for line in posts_text.strip().split('\n'):
                    if line.strip():
                        posts_data.append({'text': line.strip(), 'date': 'récent'})
            
            # Générer
            with st.spinner("🔄 Génération en cours..."):
                try:
                    result = generate_sequence_v28(
                        prospect_data=prospect_data,
                        posts_data=posts_data,
                        job_posting_data=job_posting_data,
                        profile_data=prospect_data
                    )
                    
                    st.success("✅ Séquence générée !")
                    
                    # Afficher les messages
                    st.divider()
                    
                    col_m1, col_m2 = st.columns(2)
                    
                    with col_m1:
                        st.subheader("📨 Message 1 (J+0)")
                        st.text_area("M1", value=result['message_1'], height=300, key="m1")
                        if st.button("📋 Copier M1"):
                            st.write("Copiez depuis le champ ci-dessus")
                    
                    with col_m2:
                        st.subheader("📨 Message 2 (J+5)")
                        st.text_area("M2", value=result['message_2'], height=300, key="m2")
                        if st.button("📋 Copier M2"):
                            st.write("Copiez depuis le champ ci-dessus")
                    
                    with st.expander("📨 Message 3 (Break-up)", expanded=False):
                        st.text_area("M3", value=result['message_3'], height=200, key="m3")
                    
                    # Stats
                    with st.expander("📊 Détails API", expanded=False):
                        st.json(tracker.get_summary())
                    
                except Exception as e:
                    st.error(f"❌ Erreur : {e}")
                    import traceback
                    st.code(traceback.format_exc())

# ========================================
# TAB 2 : TESTS RAPIDES
# ========================================

with tab2:
    st.header("Tests rapides - Cas pré-configurés")
    
    # Cas de test
    TEST_CASES = {
        "CAMCA - Comptable Technique": {
            "prospect": {
                "full_name": "Alexandre Dupont",
                "first_name": "Alexandre",
                "headline": "Responsable Comptabilité Technique",
                "company": "Groupe CAMCA"
            },
            "posts": [],
            "job": {
                "title": "Comptable Technique F/H",
                "description": """La Caisse d'Assurances Mutuelles du Crédit Agricole (CAMCA) est la compagnie d'assurances du Groupe Crédit Agricole.

Rattaché(e) au Responsable Comptabilité Technique, le comptable technique aura pour missions principales :
• Enregistrer la comptabilité des opérations techniques d'assurance, de réassurance et de coassurance ainsi que de la gestion des flux financiers liés (encaissements/décaissements)
• Participer à la mise en œuvre des outils, processus et méthodes liés aux opérations d'assurance, de réassurance et de coassurance
• Contribuer au respect des obligations déclaratives aux niveaux comptable, fiscal, réglementaire et Groupe Crédit Agricole

Missions courantes :
• Enregistrer les activités de comptabilité technique d'assurance (cotisations, taxes, commissions, sinistres…), de coassurance et de réassurance (acceptée et cédée)
• Réaliser des rapprochements bancaires des opérations techniques et suivi des suspens
• Contribuer aux arrêtés trimestriels de CAMCA Mutuelle (calcul des estimations de primes à émettre, centralisation des provisions techniques, réconciliation des comptes intragroupe)

Profil :
• De formation supérieure Bac +3 (type DCG), 5 ans d'expérience minimum avec connaissance du domaine de l'assurance
• Maîtrise des opérations comptables courantes et d'inventaire d'une société d'assurance non-vie"""
            }
        },
        "CNP - Comptable Technique Assurances": {
            "prospect": {
                "full_name": "Honorine Amouzoun",
                "first_name": "Honorine",
                "headline": "RH - Talent Acquisition",
                "company": "CNP Assurances"
            },
            "posts": [],
            "job": {
                "title": "Comptable Technique Assurances H/F",
                "description": """Au sein de CNP Assurances IARD, filiale du Groupe CNP Assurances.

Vos Missions :
• Gérer les flux techniques : primes, sinistres en gestion propre/déléguée, opérations de réassurance (traitement des quote-parts, Excess loss, stop loss) / Co-assurance
• Constituer en lien avec les directions Techniques des filiales les écritures d'inventaire
• Produire les états règlementaires (QRT –S2- et ENS) en lien avec la Direction Risques et Actuariat
• Produire les déclarations fiscales, les comptes sociaux et IFRS
• Gérer les comptes de réassurance (analyse des traités, schéma comptable…)
• Mettre en œuvre les contrôles de niveau 2 sur les comptes produits par les délégataires

Profil :
Fort(e) d'une expérience de 2 à 3 ans acquise en comptabilité ou en audit.
Une bonne maîtrise des outils informatiques et une connaissance de SAP sont nécessaires."""
            }
        },
        "Kereis - Gestionnaire Comptable": {
            "prospect": {
                "full_name": "Celine Martin",
                "first_name": "Celine",
                "headline": "Responsable Comptabilité",
                "company": "Kereis France"
            },
            "posts": [],
            "job": {
                "title": "Comptable Technique Assurances H/F",
                "description": """Chez Kereis, vous évoluez au sein de l'équipe comptable et consolidation et contribuez activement à la structuration de la comptabilité du pôle courtage direct, en pleine expansion.

Vos Principales Activités :
• Exploiter et vérifier l'adéquation des flux techniques et comptables des primes
• Garantir la cohérence des informations de gestion et la traduction comptable (centralisation mensuelle)
• Calculer les primes d'assurance et reversement aux compagnies
• Calculer et suivre le règlement des commissions de gestion et de distribution
• Préparer les états financiers des primes et commissions destinés aux partenaires
• Règlement et suivi des prestations sinistres auprès des assurés
• Suivi et contrôle des rejets et impayés

Profil :
De formation bac +3 en finance, vous bénéficiez d'au moins 5 ans d'expérience en comptabilité."""
            }
        }
    }
    
    # Sélection du test
    selected_test = st.selectbox("Choisir un cas de test", list(TEST_CASES.keys()))
    
    test_data = TEST_CASES[selected_test]
    
    # Afficher les données
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("👤 Prospect")
        st.json(test_data["prospect"])
    
    with col2:
        st.subheader("📄 Fiche de poste")
        st.write(f"**{test_data['job']['title']}**")
        st.text(test_data["job"]["description"][:500] + "...")
    
    # Lancer le test
    if st.button(f"🧪 Lancer le test : {selected_test}", type="primary", use_container_width=True):
        
        if not api_key:
            st.error("❌ Configurez ANTHROPIC_API_KEY")
        else:
            with st.spinner("🔄 Génération en cours..."):
                try:
                    result = generate_sequence_v28(
                        prospect_data=test_data["prospect"],
                        posts_data=test_data["posts"],
                        job_posting_data=test_data["job"],
                        profile_data=test_data["prospect"]
                    )
                    
                    st.success("✅ Test réussi !")
                    
                    st.divider()
                    
                    st.subheader("📨 Message 1")
                    st.info(result['message_1'])
                    
                    st.subheader("📨 Message 2")
                    st.info(result['message_2'])
                    
                    # Analyse qualité
                    st.divider()
                    st.subheader("🔍 Analyse qualité")
                    
                    m1 = result['message_1'].lower()
                    m2 = result['message_2'].lower()
                    
                    checks = [
                        ("M1 ne dit pas 'Je travaille'", "je travaille" not in m1),
                        ("M1 contient la question finale", "écarts que vous observez" in m1),
                        ("M2 contient 'synthèses anonymisées'", "synthèses anonymisées" in m2),
                        ("Pas de 'rigueur' générique", "rigueur" not in m1 and "rigueur" not in m2),
                        ("Pas de 'agilité' générique", "agilité" not in m1 and "agilité" not in m2),
                        ("Pas de 'dynamique' générique", "dynamique" not in m1 and "dynamique" not in m2),
                    ]
                    
                    for label, passed in checks:
                        if passed:
                            st.write(f"✅ {label}")
                        else:
                            st.write(f"❌ {label}")
                    
                    # Coût
                    st.metric("Coût de ce test", f"${tracker.calls[-1]['cost']:.4f}" if tracker.calls else "$0")
                    
                except Exception as e:
                    st.error(f"❌ Erreur : {e}")
                    import traceback
                    st.code(traceback.format_exc())

# ========================================
# TAB 3 : DOCUMENTATION
# ========================================

with tab3:
    st.header("Documentation V28")
    
    st.markdown("""
    ## 🎯 Philosophie V28
    
    **Avant (V27.x)** : 15+ fonctions de détection (métier, secteur, pain points, scoring hooks...)
    → Bugs fréquents, maintenance complexe
    
    **Maintenant (V28)** : 1 seul appel Claude qui analyse TOUT
    → Simple, cohérent, moins de bugs
    
    ---
    
    ## 📊 Comparaison
    
    | Métrique | V27.5 | V28 |
    |----------|-------|-----|
    | Appels Claude/prospect | 5-8 | **1** |
    | Lignes de code | ~2200 | **~350** |
    | Fonctions de détection | ~15 | **0** |
    | Coût/prospect | ~$0.05 | **~$0.02** |
    
    ---
    
    ## 🔧 Structure des messages
    
    ### Message 1 (Icebreaker)
    ```
    Bonjour {Prénom},
    
    [Hook LinkedIn OU "Je vous contacte concernant..."]
    
    [Pain point #1 - vocabulaire EXACT de la fiche]
    
    Quels sont les principaux écarts que vous observez 
    entre vos attentes et les profils rencontrés ?
    
    Bien à vous,
    ```
    
    ### Message 2 (Relance)
    ```
    Bonjour {Prénom},
    
    Je me permets de vous relancer concernant votre recherche de {Poste}.
    
    [Pain point #2 - DIFFÉRENT de M1]
    
    J'ai identifié 2 profils qui pourraient retenir votre attention :
    - L'un [profil 1 cohérent avec la fiche]
    - L'autre [profil 2 parcours différent]
    
    Seriez-vous d'accord pour recevoir leurs synthèses anonymisées ?
    
    Bien à vous,
    ```
    
    ### Message 3 (Break-up)
    Template fixe, pas d'appel Claude.
    
    ---
    
    ## 🚫 Interdictions
    
    - "Je travaille sur..."
    - "rigueur", "agilité", "dynamisme"
    - Inventer des compétences non mentionnées
    - Répéter le même pain point M1/M2
    - Profils incohérents avec la fiche
    """)
