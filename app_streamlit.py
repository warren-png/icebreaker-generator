"""
Application Web Streamlit pour Icebreaker Generator
VERSION AMÉLIORÉE - Avec support Leonar automatisé
"""

import streamlit as st
import pandas as pd
from icebreaker_v2 import *
from scraper_job_posting import scrape_job_posting, format_job_data_for_prompt
from message_sequence_generator import generate_message_2, generate_message_4
import time
import json
import requests
import os
from dotenv import load_dotenv

load_dotenv()

# Configuration de la page
st.set_page_config(
    page_title="Icebreaker Generator + Leonar",
    page_icon="🎯",
    layout="wide"
)

# Initialisation de la session state
if 'results' not in st.session_state:
    st.session_state.results = []
if 'processing' not in st.session_state:
    st.session_state.processing = False
if 'leonar_prospects' not in st.session_state:
    st.session_state.leonar_prospects = []

# Configuration Leonar
try:
    # Sur Streamlit Cloud, utiliser st.secrets (AVEC CROCHETS !)
    LEONAR_EMAIL = st.secrets["LEONAR_EMAIL"]
    LEONAR_PASSWORD = st.secrets["LEONAR_PASSWORD"]
    LEONAR_CAMPAIGN_ID = st.secrets["LEONAR_CAMPAIGN_ID"]
except (KeyError, AttributeError):
    # Fallback sur .env en local
    LEONAR_EMAIL = os.getenv("LEONAR_EMAIL")
    LEONAR_PASSWORD = os.getenv("LEONAR_PASSWORD")
    LEONAR_CAMPAIGN_ID = os.getenv("LEONAR_CAMPAIGN_ID")


# Fichier de tracking (AJOUTEZ ICI)
PROCESSED_FILE = "processed_prospects.txt"


# ========================================
# FONCTIONS LEONAR
# ========================================

def get_leonar_token():
    """Obtient le token Leonar"""
    try:
        response = requests.post(
            'https://dashboard.leonar.app/api/1.1/wf/auth',
            headers={'Content-Type': 'application/json'},
            json={"email": LEONAR_EMAIL, "password": LEONAR_PASSWORD},
            timeout=10
        )
        
        if response.status_code == 200:
            return response.json()['response']['token']
        return None
    except:
        return None

def load_processed():
    """Charge la liste des prospects déjà traités"""
    if os.path.exists(PROCESSED_FILE):
        with open(PROCESSED_FILE, 'r') as f:
            return set(f.read().splitlines())
    return set()

def save_processed(prospect_id):
    """Sauvegarde un prospect comme traité"""
    with open(PROCESSED_FILE, 'a') as f:
        f.write(f"{prospect_id}\n")

def get_new_prospects_leonar(token):
    """Récupère les prospects Leonar sans messages"""
    try:
        response = requests.get(
            f'https://dashboard.leonar.app/api/1.1/obj/matching?constraints=[{{"key":"campaign","constraint_type":"equals","value":"{LEONAR_CAMPAIGN_ID}"}}]&cursor=0',
            headers={'Authorization': f'Bearer {token}'},
            timeout=10
        )
        
        if response.status_code != 200:
            return []
        
        all_prospects = response.json()['response']['results']
        processed = load_processed()
        
        # Filtrer : nouveaux prospects SANS messages
        new_prospects = [
            p for p in all_prospects 
            if p['_id'] not in processed and (
                not p.get('notes') or 
                len(p.get('notes', '')) < 100 or 
                'MESSAGE 1' not in p.get('notes', '')
            )
        ]
        
        return new_prospects
    except:
        return []

def update_prospect_leonar(token, prospect_id, messages):
    """Met à jour un prospect avec les 3 messages"""
    try:
        formatted_notes = f"""═══════════════════════════════════════════════════════════════
MESSAGE 1 (J+0) - ICEBREAKER
═══════════════════════════════════════════════════════════════

{messages['message_1']}

═══════════════════════════════════════════════════════════════
MESSAGE 2 (J+5) - APPORT VALEUR
═══════════════════════════════════════════════════════════════

{messages['message_2']}

═══════════════════════════════════════════════════════════════
MESSAGE 3 (J+12) - BREAK-UP
═══════════════════════════════════════════════════════════════

{messages['message_3']}"""
        
        response = requests.patch(
            f'https://dashboard.leonar.app/api/1.1/obj/matching/{prospect_id}',
            headers={
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            },
            json={"notes": formatted_notes},
            timeout=10
        )
        
        return response.status_code == 204
    except:
        return False

# ========================================
# HEADER
# ========================================

st.title("🎯 Icebreaker Generator + Leonar")
st.markdown("*Générez des messages LinkedIn ultra-personnalisés et exportez vers Leonar*")

st.divider()

# ========================================
# SIDEBAR - CONFIGURATION
# ========================================

with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Options de scraping
    st.subheader("Options de scraping")
    enable_web_search = st.checkbox("Recherche Web", value=True)
    enable_company_scraping = st.checkbox("Scraper l'entreprise", value=True)
    enable_job_scraping = st.checkbox("🆕 Scraper l'annonce", value=True)
    
    st.divider()
    
    # Leonar Status
    st.subheader("📤 Statut Leonar")
    
    if all([LEONAR_EMAIL, LEONAR_PASSWORD, LEONAR_CAMPAIGN_ID]):
        token_test = get_leonar_token()
        if token_test:
            st.success("✅ Connecté")
            st.caption(f"📧 {LEONAR_EMAIL}")
        else:
            st.error("❌ Erreur connexion")
    else:
        st.warning("⚠️ Non configuré")
        st.caption("Ajoutez les variables dans .env")
    
    st.divider()
    
    # Statistiques
    st.subheader("📊 Statistiques")
    st.metric("Prospects traités", len(st.session_state.results))
    
    if st.session_state.results:
        avg_time = sum(r['time'] for r in st.session_state.results) / len(st.session_state.results)
        st.metric("Temps moyen", f"{avg_time:.1f}s")
    
    st.divider()
    
    # Informations
    st.subheader("ℹ️ Informations")
    st.info("💰 Coût : ~0.065€ / prospect (3 messages)")
    st.info("⏱️ Temps moyen : ~50s / prospect")

# ========================================
# MAIN CONTENT
# ========================================

# Onglets (AJOUT DU 4ÈME ONGLET)
tab1, tab2, tab3, tab4 = st.tabs(["📝 Génération", "📊 Résultats", "📈 Historique", "📤 Export Leonar"])

# ========================================
# TAB 1 : GÉNÉRATION (INCHANGÉ)
# ========================================

with tab1:
    st.header("Génération d'icebreakers")
    
    # Choix du mode
    mode = st.radio(
        "Mode de saisie",
        ["URLs LinkedIn manuelles", "Import Google Sheet"],
        horizontal=True
    )
    
    if mode == "URLs LinkedIn manuelles":
        # Input manuel
        col1, col2 = st.columns(2)
        
        with col1:
            first_names = st.text_area(
                "Prénoms (un par ligne)",
                height=200,
                placeholder="Jean\nMarie\nPierre"
            )
        
        with col2:
            last_names = st.text_area(
                "Noms (un par ligne)",
                height=200,
                placeholder="Dupont\nMartin\nDurand"
            )
        
        companies = st.text_area(
            "Entreprises (une par ligne)",
            height=100,
            placeholder="CCE France\nTotal Energies\nAirbus"
        )
        
        linkedin_urls = st.text_area(
            "URLs LinkedIn (une par ligne) - Optionnel",
            height=150,
            placeholder="https://www.linkedin.com/in/jean-dupont/"
        )
        
        job_posting_urls = st.text_area(
            "🆕 URLs Annonces de poste (une par ligne) - Optionnel",
            height=150,
            placeholder="https://www.hellowork.com/...",
            help="Ajoutez les URLs des annonces pour enrichir l'icebreaker"
        )
        
    else:
        # Import Google Sheet
        st.info("🔗 L'outil va se connecter à votre Google Sheet configuré")
        use_google_sheet = True
    
    st.divider()
    
    # Bouton de génération
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        if st.button("🚀 Générer les icebreakers", type="primary", use_container_width=True):
            
            # [LE RESTE DU CODE DE GÉNÉRATION RESTE IDENTIQUE]
            # Je ne le copie pas ici pour la lisibilité, mais il reste exactement pareil
            
            # Préparer les prospects
            if mode == "URLs LinkedIn manuelles":
                first_names_list = [x.strip() for x in first_names.split('\n') if x.strip()]
                last_names_list = [x.strip() for x in last_names.split('\n') if x.strip()]
                companies_list = [x.strip() for x in companies.split('\n') if x.strip()]
                urls_list = [x.strip() for x in linkedin_urls.split('\n') if x.strip()] if linkedin_urls else []
                job_urls_list = [x.strip() for x in job_posting_urls.split('\n') if x.strip()] if job_posting_urls else []
                
                # Validation
                if not first_names_list or not last_names_list or not companies_list:
                    st.error("❌ Veuillez remplir au moins les prénoms, noms et entreprises")
                    st.stop()
                
                if len(first_names_list) != len(last_names_list) or len(first_names_list) != len(companies_list):
                    st.error("❌ Le nombre de prénoms, noms et entreprises doit être identique")
                    st.stop()
                
                # Créer la liste de prospects
                prospects = []
                for i in range(len(first_names_list)):
                    prospects.append({
                        'first_name': first_names_list[i],
                        'last_name': last_names_list[i],
                        'company': companies_list[i],
                        'linkedin_url': urls_list[i] if i < len(urls_list) else '',
                        'job_posting_url': job_urls_list[i] if i < len(job_urls_list) else ''
                    })
            
            else:
                # Import depuis Google Sheet
                try:
                    sheet = connect_to_google_sheet()
                    prospects = get_prospects(sheet)
                    
                    if not prospects:
                        st.warning("⚠️ Aucun prospect à traiter")
                        st.stop()
                except Exception as e:
                    st.error(f"❌ Erreur : {e}")
                    st.stop()
            
            # Traitement (code identique à l'original)
            st.session_state.processing = True
            st.session_state.results = []
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            apify_client = init_apify_client()
            
            for i, prospect in enumerate(prospects):
                status_text.text(f"🔄 {prospect['first_name']} {prospect['last_name']} ({i+1}/{len(prospects)})")
                
                start_time = time.time()
                
                try:
                    # Scraping et génération (code identique)
                    if not prospect.get('linkedin_url'):
                        linkedin_url = search_linkedin_profile(
                            prospect['first_name'],
                            prospect['last_name'],
                            prospect['company']
                        )
                    else:
                        linkedin_url = prospect['linkedin_url']
                    
                    job_posting_data = None
                    if enable_job_scraping and prospect.get('job_posting_url'):
                        job_posting_data = scrape_job_posting(prospect['job_posting_url'])
                        time.sleep(2)
                    
                    profile_data = scrape_linkedin_profile(apify_client, linkedin_url)
                    time.sleep(2)
                    
                    posts_data = scrape_linkedin_posts(apify_client, linkedin_url)
                    time.sleep(2)
                    
                    if enable_company_scraping:
                        company_posts = scrape_company_posts(apify_client, prospect['company'])
                        time.sleep(2)
                        company_profile = scrape_company_profile(apify_client, prospect['company'])
                        time.sleep(2)
                    else:
                        company_posts = []
                        company_profile = None
                    
                    if enable_web_search:
                        title = ""
                        if profile_data and profile_data.get('experiences'):
                            title = profile_data['experiences'][0].get('title', '')
                        
                        web_results = web_search_prospect(
                            prospect['first_name'],
                            prospect['last_name'],
                            prospect['company'],
                            title
                        )
                        time.sleep(2)
                    else:
                        web_results = []
                    
                    hooks_json = extract_hooks_with_claude(
                        profile_data,
                        posts_data,
                        company_posts,
                        company_profile,
                        web_results,
                        f"{prospect['first_name']} {prospect['last_name']}",
                        prospect['company']
                    )
                    time.sleep(2)
                    
                    icebreaker = generate_advanced_icebreaker(prospect, hooks_json, job_posting_data)
                    
                    elapsed_time = time.time() - start_time
                    
                    st.session_state.results.append({
                        'first_name': prospect['first_name'],
                        'last_name': prospect['last_name'],
                        'company': prospect['company'],
                        'linkedin_url': linkedin_url,
                        'job_posting_url': prospect.get('job_posting_url', ''),
                        'job_posting_data': job_posting_data,
                        'hooks': hooks_json,
                        'icebreaker': icebreaker,
                        'time': elapsed_time,
                        'status': 'success'
                    })
                    
                except Exception as e:
                    st.session_state.results.append({
                        'first_name': prospect['first_name'],
                        'last_name': prospect['last_name'],
                        'company': prospect['company'],
                        'linkedin_url': prospect.get('linkedin_url', ''),
                        'job_posting_url': prospect.get('job_posting_url', ''),
                        'job_posting_data': None,
                        'hooks': '',
                        'icebreaker': f"Erreur : {str(e)}",
                        'time': 0,
                        'status': 'error'
                    })
                
                progress_bar.progress((i + 1) / len(prospects))
            
            status_text.text("✅ Génération terminée !")
            st.session_state.processing = False
            st.balloons()

# ========================================
# TAB 2 : RÉSULTATS (INCHANGÉ - je garde tel quel)
# ========================================

with tab2:
    st.header("📊 Résultats de la génération")
    
    if not st.session_state.results:
        st.info("👆 Lancez une génération pour voir les résultats")
    else:
        # [CODE IDENTIQUE - je ne le recopie pas pour la lisibilité]
        col1, col2, col3 = st.columns(3)
        
        with col1:
            success_count = sum(1 for r in st.session_state.results if r['status'] == 'success')
            st.metric("✅ Réussis", success_count)
        
        with col2:
            error_count = sum(1 for r in st.session_state.results if r['status'] == 'error')
            st.metric("❌ Erreurs", error_count)
        
        with col3:
            total_time = sum(r['time'] for r in st.session_state.results)
            st.metric("⏱️ Temps total", f"{total_time:.0f}s")
        
        st.divider()
        
        for i, result in enumerate(st.session_state.results):
            with st.expander(f"{'✅' if result['status'] == 'success' else '❌'} {result['first_name']} {result['last_name']} - {result['company']}"):
                
                if result['status'] == 'success':
                    st.markdown("**🎯 Icebreaker généré :**")
                    st.info(result['icebreaker'])
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        if st.button(f"📋 Copier", key=f"copy_{i}"):
                            st.toast("✅ Copié !")
                    
                    with col2:
                        st.markdown(f"🔗 [LinkedIn]({result['linkedin_url']})")
                    
                    with col3:
                        if result.get('job_posting_url'):
                            st.markdown(f"📄 [Annonce]({result['job_posting_url']})")
                    
                    if result.get('job_posting_data'):
                        with st.expander("📋 Données annonce"):
                            st.json(result['job_posting_data'])
                    
                    if result['hooks'] and result['hooks'] != 'NOT_FOUND':
                        with st.expander("🎣 Hooks"):
                            st.json(result['hooks'])
                    
                    st.caption(f"⏱️ {result['time']:.1f}s")
                
                else:
                    st.error(result['icebreaker'])
        
        st.divider()
        
        st.subheader("💾 Export")
        
        col1, col2 = st.columns(2)
        
        with col1:
            df = pd.DataFrame([
                {
                    'Prénom': r['first_name'],
                    'Nom': r['last_name'],
                    'Entreprise': r['company'],
                    'LinkedIn': r['linkedin_url'],
                    'Icebreaker': r['icebreaker']
                }
                for r in st.session_state.results
            ])
            
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                "📥 CSV",
                data=csv,
                file_name="icebreakers.csv",
                mime="text/csv",
            )

# ========================================
# TAB 3 : HISTORIQUE (INCHANGÉ)
# ========================================

with tab3:
    st.header("📈 Historique")
    
    try:
        sheet = connect_to_google_sheet()
        all_data = sheet.get_all_records()
        history = [row for row in all_data if row.get('icebreaker')]
        
        if not history:
            st.info("📭 Aucun historique")
        else:
            st.success(f"✅ {len(history)} icebreaker(s)")
            
            for i, row in enumerate(reversed(history[-20:])):
                with st.expander(f"{row.get('first_name', '')} {row.get('last_name', '')} - {row.get('company', '')}"):
                    st.info(row.get('icebreaker', ''))
                    
                    if st.button(f"📋 Copier", key=f"hist_{i}"):
                        st.toast("✅ Copié !")
    
    except Exception as e:
        st.error(f"❌ Erreur : {e}")

# ========================================
# TAB 4 : EXPORT LEONAR (NOUVEAU !)
# ========================================

with tab4:
    st.header("📤 Export vers Leonar")
    
    # Vérification config
    if not all([LEONAR_EMAIL, LEONAR_PASSWORD, LEONAR_CAMPAIGN_ID]):
        st.error("❌ Configuration Leonar manquante !")
        st.info("""
        **Ajoutez dans Streamlit Cloud → Settings → Secrets :**
        ```
        LEONAR_EMAIL = "votre_email@leonar.app"
        LEONAR_PASSWORD = "votre_mot_de_passe"
        LEONAR_CAMPAIGN_ID = "votre_campaign_id"
        ```
        """)
        st.stop()
    
    # Test connexion
    with st.spinner("🔐 Connexion à Leonar..."):
        token = get_leonar_token()
    
    if not token:
        st.error("❌ Impossible de se connecter à Leonar")
        st.stop()
    
    st.success("✅ Connecté à Leonar")
    st.caption(f"📧 {LEONAR_EMAIL}")
    st.caption(f"📋 Campaign ID : {LEONAR_CAMPAIGN_ID[:20]}...")
    
    st.divider()
    
    # OPTIONS DE SCRAPING (comme dans l'onglet Génération)
    st.subheader("⚙️ Options de scraping")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        leonar_web_search = st.checkbox("🔍 Recherche Web", value=True, key="leonar_web")
    with col2:
        leonar_company_scraping = st.checkbox("🏢 Scraper entreprise", value=True, key="leonar_company")
    with col3:
        leonar_job_scraping = st.checkbox("📄 Scraper annonce", value=True, key="leonar_job")
    
    st.divider()
    
    # Rafraîchir la liste
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        if st.button("🔄 RAFRAÎCHIR LA LISTE", type="secondary", use_container_width=True):
            with st.spinner("📊 Récupération des prospects..."):
                st.session_state.leonar_prospects = get_new_prospects_leonar(token)
            st.rerun()
    
    # Afficher les prospects
    if 'leonar_prospects' not in st.session_state or not st.session_state.leonar_prospects:
        with st.spinner("📊 Récupération des prospects..."):
            st.session_state.leonar_prospects = get_new_prospects_leonar(token)
    
    if not st.session_state.leonar_prospects:
        st.success("✅ Aucun nouveau prospect à traiter !")
        st.info("""
        **💡 Comment l'utiliser :**
        
        1. Ajoutez des prospects manuellement dans Leonar avec :
           - Prénom, Nom, Entreprise (obligatoire)
           - URL LinkedIn (fortement recommandé pour qualité)
           - URL annonce de poste (optionnel, dans un champ personnalisé)
        
        2. Cliquez sur "Rafraîchir la liste"
        3. Cliquez sur "Générer les messages"
        4. Les 3 messages ultra-personnalisés seront ajoutés dans "Commentaires"
        5. Copiez-collez dans votre séquence
        
        **⏱️ Temps de traitement :**
        - Avec scraping complet : ~2-3 min par prospect
        - Sans URL LinkedIn : ~40 sec (qualité basique)
        
        **💰 Coût : ~$0.065 par prospect**
        """)
    else:
        st.warning(f"📊 **{len(st.session_state.leonar_prospects)} prospect(s)** en attente")
        
        # Liste
        with st.expander("👥 Voir la liste", expanded=True):
            for i, p in enumerate(st.session_state.leonar_prospects, 1):
                linkedin = "✅ LinkedIn" if p.get('linkedin_url') else "⚠️ Pas de LinkedIn"
                st.markdown(f"**{i}.** {p.get('user_full name', 'N/A')} - *{p.get('linkedin_company', 'N/A')}* - {linkedin}")
        
        st.divider()
        
        # BOUTON PRINCIPAL
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            if st.button("🚀 GÉNÉRER LES MESSAGES (SCRAPING COMPLET)", type="primary", use_container_width=True):
                
                st.markdown("---")
                st.subheader("⚙️ Génération en cours...")
                
                results = []
                overall_progress = st.progress(0)
                status_container = st.empty()
                
                # Initialiser Apify une seule fois
                apify_client = init_apify_client()
                
                for i, prospect in enumerate(st.session_state.leonar_prospects):
                    overall_progress.progress(i / len(st.session_state.leonar_prospects))
                    
                    name = prospect.get('user_full name', 'N/A')
                    status_container.markdown(f"**Prospect {i+1}/{len(st.session_state.leonar_prospects)} : {name}**")
                    
                    start_time = time.time()
                    
                    try:
                        # ========================================
                        # ÉTAPE 1 : PRÉPARATION DES DONNÉES
                        # ========================================
                        
                        prospect_data = {
                            'first_name': prospect.get('first_name', ''),
                            'last_name': prospect.get('last_name', ''),
                            'company': prospect.get('linkedin_company', ''),
                            'linkedin_url': prospect.get('linkedin_url', ''),
                            'job_posting_url': prospect.get('job_posting_url', '')  # Si vous avez ce champ
                        }
                        
                        # ========================================
                        # ÉTAPE 2 : SCRAPING COMPLET (comme onglet Génération)
                        # ========================================
                        
                        linkedin_url = prospect.get('linkedin_url', '')
                        
                        if not linkedin_url:
                            st.warning(f"⚠️ {name} - Pas d'URL LinkedIn, génération basique")
                            profile_data = None
                            posts_data = []
                            company_posts = []
                            company_profile = None
                            web_results = []
                            hooks_json = {'type': 'manual'}
                        
                        else:
                            st.write(f"🔗 {name} - URL LinkedIn trouvée : {linkedin_url}")
                            
                            # Scraping profil LinkedIn
                            with st.spinner(f"📊 {name} - Scraping profil LinkedIn..."):
                                profile_data = scrape_linkedin_profile(apify_client, linkedin_url)
                                time.sleep(2)
                            st.success(f"✅ {name} - Profil LinkedIn récupéré")
                            
                            # Scraping posts LinkedIn
                            with st.spinner(f"📝 {name} - Scraping posts LinkedIn..."):
                                posts_data = scrape_linkedin_posts(apify_client, linkedin_url)
                                time.sleep(2)
                            st.success(f"✅ {name} - Posts LinkedIn récupérés")
                            
                            # Scraping entreprise (optionnel)
                            if leonar_company_scraping and prospect_data['company']:
                                with st.spinner(f"🏢 {name} - Scraping entreprise..."):
                                    company_posts = scrape_company_posts(apify_client, prospect_data['company'])
                                    time.sleep(2)
                                    company_profile = scrape_company_profile(apify_client, prospect_data['company'])
                                    time.sleep(2)
                                st.success(f"✅ {name} - Entreprise scrapée")
                            else:
                                company_posts = []
                                company_profile = None
                            
                            # Recherche web (optionnel)
                            if leonar_web_search:
                                with st.spinner(f"🔍 {name} - Recherche web..."):
                                    title = ""
                                    if profile_data and profile_data.get('experiences'):
                                        title = profile_data['experiences'][0].get('title', '')
                                    
                                    web_results = web_search_prospect(
                                        prospect_data['first_name'],
                                        prospect_data['last_name'],
                                        prospect_data['company'],
                                        title
                                    )
                                    time.sleep(2)
                                st.success(f"✅ {name} - Recherche web effectuée")
                            else:
                                web_results = []
                            
                            # Extraction des hooks avec Claude
                            with st.spinner(f"🎣 {name} - Extraction des hooks..."):
                                hooks_json = extract_hooks_with_claude(
                                    profile_data,
                                    posts_data,
                                    company_posts,
                                    company_profile,
                                    web_results,
                                    f"{prospect_data['first_name']} {prospect_data['last_name']}",
                                    prospect_data['company']
                                )
                                time.sleep(2)
                            st.success(f"✅ {name} - Hooks extraits")
                        
                        # ========================================
                        # ÉTAPE 3 : SCRAPING ANNONCE (optionnel)
                        # ========================================
                        
                        job_posting_data = None
                        if leonar_job_scraping and prospect_data.get('job_posting_url'):
                            with st.spinner(f"📄 {name} - Scraping annonce..."):
                                job_posting_data = scrape_job_posting(prospect_data['job_posting_url'])
                                time.sleep(2)
                            st.success(f"✅ {name} - Annonce scrapée")
                        
                        # ========================================
                        # ÉTAPE 4 : GÉNÉRATION DES 3 MESSAGES
                        # ========================================
                        
                        # Message 1 (Icebreaker)
                        with st.spinner(f"📝 {name} - Génération message 1 (icebreaker)..."):
                            message_1 = generate_advanced_icebreaker(prospect_data, hooks_json, job_posting_data)
                            time.sleep(15)
                        st.success(f"✅ {name} - Message 1 généré ({len(message_1.split())} mots)")
                        
                        # Message 2 (Apport valeur)
                        with st.spinner(f"📝 {name} - Génération message 2 (apport valeur)..."):
                            message_2 = generate_message_2(prospect_data, hooks_json, job_posting_data, message_1)
                            time.sleep(15)
                        st.success(f"✅ {name} - Message 2 généré ({len(message_2.split())} mots)")
                        
                        # Message 3 (Break-up)
                        with st.spinner(f"📝 {name} - Génération message 3 (break-up)..."):
                            message_3 = generate_message_4(prospect_data, message_1)
                            time.sleep(5)
                        st.success(f"✅ {name} - Message 3 généré ({len(message_3.split())} mots)")
                        
                        # ========================================
                        # ÉTAPE 5 : ENVOI VERS LEONAR
                        # ========================================
                        
                        with st.spinner(f"📤 {name} - Envoi vers Leonar..."):
                            messages = {
                                'message_1': message_1,
                                'message_2': message_2,
                                'message_3': message_3
                            }
                            
                            success = update_prospect_leonar(token, prospect['_id'], messages)
                        
                        elapsed_time = time.time() - start_time
                        
                        if success:
                            save_processed(prospect['_id'])
                            results.append({
                                'name': name,
                                'success': True,
                                'len1': len(message_1.split()),
                                'len2': len(message_2.split()),
                                'len3': len(message_3.split()),
                                'time': elapsed_time,
                                'had_linkedin': bool(linkedin_url)
                            })
                            st.success(f"🎉 {name} - Terminé en {elapsed_time:.0f}s !")
                        else:
                            results.append({
                                'name': name,
                                'success': False,
                                'time': elapsed_time,
                                'had_linkedin': bool(linkedin_url)
                            })
                            st.error(f"❌ {name} - Erreur mise à jour Leonar")
                        
                    except Exception as e:
                        elapsed_time = time.time() - start_time
                        results.append({
                            'name': name,
                            'success': False,
                            'time': elapsed_time,
                            'had_linkedin': False
                        })
                        st.error(f"❌ {name} - Erreur : {str(e)}")
                    
                    # Pause entre prospects
                    if i < len(st.session_state.leonar_prospects) - 1:
                        time.sleep(2)
                
                overall_progress.progress(1.0)
                
                # ========================================
                # RÉSULTATS FINAUX
                # ========================================
                
                st.markdown("---")
                st.subheader("📊 Résultats")
                
                success_count = sum(1 for r in results if r.get('success'))
                linkedin_count = sum(1 for r in results if r.get('had_linkedin'))
                total_time = sum(r.get('time', 0) for r in results)
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("✅ Succès", success_count)
                with col2:
                    st.metric("❌ Erreurs", len(results) - success_count)
                with col3:
                    st.metric("🔗 Avec LinkedIn", linkedin_count)
                with col4:
                    st.metric("⏱️ Temps total", f"{total_time/60:.1f} min")
                
                # Détails par prospect
                with st.expander("📋 Détails par prospect", expanded=True):
                    for r in results:
                        if r.get('success'):
                            linkedin_icon = "🔗" if r.get('had_linkedin') else "⚠️"
                            st.success(
                                f"{linkedin_icon} ✅ {r['name']} - "
                                f"M1: {r.get('len1', 0)}w, M2: {r.get('len2', 0)}w, M3: {r.get('len3', 0)}w - "
                                f"{r.get('time', 0):.0f}s"
                            )
                        else:
                            st.error(f"❌ {r['name']} - Échec")
                
                # Coûts
                cost = success_count * 0.065
                st.metric("💰 Coût total", f"${cost:.2f}")
                
                st.markdown("---")
                st.success("🎉 **Génération terminée !**")
                
                st.info("""
                **📋 Prochaines étapes :**
                
                1. Ouvrez Leonar
                2. Allez sur la fiche de chaque prospect
                3. Onglet "Commentaires" ou "Notes"
                4. Copiez les 3 messages séparément :
                   
                   **MESSAGE 1 (J+0) - ICEBREAKER**
                   → Collez dans Étape 1 de votre séquence
                   
                   **MESSAGE 2 (J+5) - APPORT VALEUR**
                   → Collez dans Étape 2 de votre séquence
                   
                   **MESSAGE 3 (J+12) - BREAK-UP**
                   → Collez dans Étape 3 de votre séquence
                
                5. Lancez la séquence ! 🚀
                
                **💡 Astuce :** Les messages s'enchaînent logiquement et 
                font référence aux précédents pour créer une vraie conversation.
                """)
                
                st.balloons()

# ========================================
# FOOTER
# ========================================

st.divider()
st.caption("🎯 Icebreaker Generator v2.1 + Leonar | Powered by Claude Sonnet 4")
