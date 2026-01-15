"""
Application Web Streamlit pour Icebreaker Generator
"""

import streamlit as st
import pandas as pd
from icebreaker_v2 import *
import time

# Configuration de la page
st.set_page_config(
    page_title="Icebreaker Generator",
    page_icon="🎯",
    layout="wide"
)

# Initialisation de la session state
if 'results' not in st.session_state:
    st.session_state.results = []
if 'processing' not in st.session_state:
    st.session_state.processing = False

# ========================================
# HEADER
# ========================================

st.title("🎯 Icebreaker Generator")
st.markdown("*Générez des messages LinkedIn ultra-personnalisés en quelques clics*")

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
    st.info("💰 Coût estimé : ~0.05€ par prospect")
    st.info("⏱️ Temps moyen : ~50s par prospect")

# ========================================
# MAIN CONTENT
# ========================================

# Onglets
tab1, tab2, tab3 = st.tabs(["📝 Génération", "📊 Résultats", "📈 Historique"])

# ========================================
# TAB 1 : GÉNÉRATION
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
            placeholder="https://www.linkedin.com/in/jean-dupont/\nhttps://www.linkedin.com/in/marie-martin/"
        )
        
    else:
        # Import Google Sheet
        st.info("🔗 L'outil va se connecter à votre Google Sheet configuré dans config.py")
        use_google_sheet = True
    
    st.divider()
    
    # Bouton de génération
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        if st.button("🚀 Générer les icebreakers", type="primary", use_container_width=True):
            
            # Préparer les prospects
            if mode == "URLs LinkedIn manuelles":
                first_names_list = [x.strip() for x in first_names.split('\n') if x.strip()]
                last_names_list = [x.strip() for x in last_names.split('\n') if x.strip()]
                companies_list = [x.strip() for x in companies.split('\n') if x.strip()]
                urls_list = [x.strip() for x in linkedin_urls.split('\n') if x.strip()] if linkedin_urls else []
                
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
                        'linkedin_url': urls_list[i] if i < len(urls_list) else ''
                    })
            
            else:
                # Import depuis Google Sheet
                try:
                    sheet = connect_to_google_sheet()
                    prospects = get_prospects(sheet)
                    
                    if not prospects:
                        st.warning("⚠️ Aucun prospect à traiter dans le Google Sheet")
                        st.stop()
                except Exception as e:
                    st.error(f"❌ Erreur de connexion à Google Sheet : {e}")
                    st.stop()
            
            # Traitement
            st.session_state.processing = True
            st.session_state.results = []
            
            # Progress bar
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Initialiser Apify
            apify_client = init_apify_client()
            
            # Traiter chaque prospect
            for i, prospect in enumerate(prospects):
                status_text.text(f"🔄 Traitement de {prospect['first_name']} {prospect['last_name']} ({i+1}/{len(prospects)})")
                
                start_time = time.time()
                
                try:
                    # URL LinkedIn
                    if not prospect.get('linkedin_url'):
                        linkedin_url = search_linkedin_profile(
                            prospect['first_name'],
                            prospect['last_name'],
                            prospect['company']
                        )
                    else:
                        linkedin_url = prospect['linkedin_url']
                    
                    # Scraping
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
                    
                    # Recherche web
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
                    
                    # Extraction hooks
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
                    
                    # Génération icebreaker
                    icebreaker = generate_advanced_icebreaker(prospect, hooks_json)
                    
                    # Calculer le temps
                    elapsed_time = time.time() - start_time
                    
                    # Stocker le résultat
                    st.session_state.results.append({
                        'first_name': prospect['first_name'],
                        'last_name': prospect['last_name'],
                        'company': prospect['company'],
                        'linkedin_url': linkedin_url,
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
                        'hooks': '',
                        'icebreaker': f"Erreur : {str(e)}",
                        'time': 0,
                        'status': 'error'
                    })
                
                # Mise à jour progress bar
                progress_bar.progress((i + 1) / len(prospects))
            
            status_text.text("✅ Génération terminée !")
            st.session_state.processing = False
            st.balloons()

# ========================================
# TAB 2 : RÉSULTATS
# ========================================

with tab2:
    st.header("📊 Résultats de la génération")
    
    if not st.session_state.results:
        st.info("👆 Lancez une génération dans l'onglet 'Génération' pour voir les résultats ici")
    else:
        # Statistiques globales
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
        
        # Afficher chaque résultat
        for i, result in enumerate(st.session_state.results):
            with st.expander(f"{'✅' if result['status'] == 'success' else '❌'} {result['first_name']} {result['last_name']} - {result['company']}"):
                
                if result['status'] == 'success':
                    st.markdown("**🎯 Icebreaker généré :**")
                    st.info(result['icebreaker'])
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button(f"📋 Copier", key=f"copy_{i}"):
                            st.toast("✅ Copié dans le presse-papier !")
                    
                    with col2:
                        st.markdown(f"🔗 [Voir le profil LinkedIn]({result['linkedin_url']})")
                    
                    # Hooks
                    if result['hooks'] and result['hooks'] != 'NOT_FOUND':
                        with st.expander("🎣 Voir les hooks identifiés"):
                            st.json(result['hooks'])
                    
                    st.caption(f"⏱️ Généré en {result['time']:.1f}s")
                
                else:
                    st.error(result['icebreaker'])
        
        st.divider()
        
        # Export
        st.subheader("💾 Export des résultats")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Export CSV
            df = pd.DataFrame([
                {
                    'Prénom': r['first_name'],
                    'Nom': r['last_name'],
                    'Entreprise': r['company'],
                    'LinkedIn': r['linkedin_url'],
                    'Icebreaker': r['icebreaker'],
                    'Statut': r['status']
                }
                for r in st.session_state.results
            ])
            
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Télécharger en CSV",
                data=csv,
                file_name="icebreakers.csv",
                mime="text/csv",
            )
        
        with col2:
            # Sauvegarder dans Google Sheet
            if st.button("💾 Sauvegarder dans Google Sheet"):
                try:
                    sheet = connect_to_google_sheet()
                    
                    for result in st.session_state.results:
                        if result['status'] == 'success' and 'row_number' in result:
                            update_sheet(
                                sheet,
                                result['row_number'],
                                result['linkedin_url'],
                                result['hooks'],
                                result['icebreaker']
                            )
                    
                    st.success("✅ Sauvegardé dans Google Sheet !")
                except Exception as e:
                    st.error(f"❌ Erreur : {e}")

# ========================================
# TAB 3 : HISTORIQUE
# ========================================

with tab3:
    st.header("📈 Historique des générations")
    st.info("🚧 Fonctionnalité à venir : historique des générations précédentes")

# ========================================
# FOOTER
# ========================================

st.divider()
st.caption("🎯 Icebreaker Generator v1.0 - Propulsé par Claude Sonnet 4")