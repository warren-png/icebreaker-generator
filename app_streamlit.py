"""
Application Web Streamlit pour Icebreaker Generator
VERSION FINALE v4.0 - Séquence "Expert Dilemma & Break-up" + Objets Copywrités
"""

import streamlit as st
import pandas as pd
from icebreaker_v2 import *
from scraper_job_posting import scrape_job_posting
# On importe la fonction maîtresse qui gère toute la séquence
from message_sequence_generator import generate_full_sequence
import time
import json
import requests
import os
from dotenv import load_dotenv
import re

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
    LEONAR_EMAIL = st.secrets["LEONAR_EMAIL"]
    LEONAR_PASSWORD = st.secrets["LEONAR_PASSWORD"]
    LEONAR_CAMPAIGN_ID = st.secrets["LEONAR_CAMPAIGN_ID"]
except (KeyError, AttributeError):
    LEONAR_EMAIL = os.getenv("LEONAR_EMAIL")
    LEONAR_PASSWORD = os.getenv("LEONAR_PASSWORD")
    LEONAR_CAMPAIGN_ID = os.getenv("LEONAR_CAMPAIGN_ID")

# Fichier de tracking
PROCESSED_FILE = "processed_prospects.txt"


# ========================================
# FONCTIONS UTILITAIRES
# ========================================

def clean_message_format(message, first_name):
    """
    Nettoie le format des messages générés
    """
    if not message: return ""
    
    # 1. Assurer ligne vide après salutation
    pattern = r'(Bonjour ' + re.escape(first_name) + r',)\s*'
    message = re.sub(pattern, r'\1\n\n', message, count=1, flags=re.IGNORECASE)
    
    # 2. Nettoyer les doubles lignes vides
    message = re.sub(r'\n{3,}', '\n\n', message)
    
    # 3. Force la majuscule après "Bonjour Prénom,\n\n"
    pattern_lowercase = r'(Bonjour ' + re.escape(first_name) + r',\n\n)([a-zà-ÿ])'
    message = re.sub(pattern_lowercase, lambda m: m.group(1) + m.group(2).upper(), message, count=1, flags=re.IGNORECASE)
    
    # 4. Standardiser la signature
    patterns_to_remove = [
        r'\n\nBien cordialement,?\s*\n+\[Prénom\]',
        r'\nBien cordialement,\s*\[Prénom\]',
        r'\n\[Prénom\]\s*$',
        r'Cordialement,\s*\[Prénom\]'
    ]
    for pattern in patterns_to_remove:
        message = re.sub(pattern, '\n\nBien cordialement', message)
        
    return message.strip()


def update_prospect_leonar(token, prospect_id, sequence_data):
    """Met à jour un prospect dans Leonar avec la séquence complète"""
    try:
        subject_lines = sequence_data.get('subject_lines', 'Question recrutement').strip()
        msg1 = sequence_data.get('message_1', '').strip()
        msg2 = sequence_data.get('message_2', '').strip()
        msg3 = sequence_data.get('message_3', '').strip()

        # Formatage explicite pour la note Leonar
        formatted_notes = (
            "═══════════════════════════════════════════════════════════════\n"
            "OBJETS SUGGÉRÉS (Choisir 1)\n"
            "═══════════════════════════════════════════════════════════════\n"
            "\n"
            f"{subject_lines}\n"
            "\n"
            "═══════════════════════════════════════════════════════════════\n"
            "MESSAGE 1 (ICEBREAKER - J+0)\n"
            "═══════════════════════════════════════════════════════════════\n"
            "\n"
            f"{msg1}\n"
            "\n"
            "═══════════════════════════════════════════════════════════════\n"
            "MESSAGE 2 (LE DILEMME - J+5)\n"
            "═══════════════════════════════════════════════════════════════\n"
            "\n"
            f"{msg2}\n"
            "\n"
            "═══════════════════════════════════════════════════════════════\n"
            "MESSAGE 3 (BREAK-UP EXPERT - J+12)\n"
            "═══════════════════════════════════════════════════════════════\n"
            "\n"
            f"{msg3}\n"
            "\n"
            "═══════════════════════════════════════════════════════════════\n"
            "FIN DE SÉQUENCE\n"
            "═══════════════════════════════════════════════════════════════"
        )
        
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
        
    except Exception as e:
        print(f"ERROR LEONAR UPDATE: {str(e)}")
        return False


# ========================================
# FONCTIONS API LEONAR (Authent & Fetch)
# ========================================

def get_leonar_token():
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
    if os.path.exists(PROCESSED_FILE):
        with open(PROCESSED_FILE, 'r') as f:
            return set(f.read().splitlines())
    return set()

def save_processed(prospect_id):
    with open(PROCESSED_FILE, 'a') as f:
        f.write(f"{prospect_id}\n")

def get_new_prospects_leonar(token):
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
        
        # Filtre : ID non traité ET Note vide ou ne contenant pas "MESSAGE 1"
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


# ========================================
# INTERFACE STREAMLIT
# ========================================

st.title("🎯 Icebreaker Generator + Leonar")
st.markdown("*Génération automatique Séquence 3 Messages (Dilemme & Break-up)*")
st.divider()

with st.sidebar:
    st.header("⚙️ Configuration")
    enable_web_search = st.checkbox("Recherche Web (3 mois)", value=True)
    enable_company_scraping = st.checkbox("Scraper l'entreprise", value=True)
    enable_job_scraping = st.checkbox("Scraper l'annonce", value=True)
    
    st.divider()
    
    st.subheader("📤 Statut Leonar")
    if all([LEONAR_EMAIL, LEONAR_PASSWORD, LEONAR_CAMPAIGN_ID]):
        token_test = get_leonar_token()
        if token_test:
            st.success("✅ Connecté")
        else:
            st.error("❌ Erreur connexion")
    else:
        st.warning("⚠️ Non configuré")

# ONGLETS
tab1, tab2, tab3, tab4 = st.tabs(["📝 Test Manuel", "📊 Résultats Test", "📈 Historique", "📤 Export Leonar"])

# --- TAB 1 : TEST MANUEL ---
with tab1:
    st.header("Test Manuel (Hors Leonar)")
    st.info("Utilisez cet onglet pour tester la génération sur un prospect fictif ou réel sans envoyer à Leonar.")
    
    col1, col2 = st.columns(2)
    with col1:
        t_first = st.text_input("Prénom", "Thomas")
        t_company = st.text_input("Entreprise", "Green Energy")
    with col2:
        t_last = st.text_input("Nom", "Durand")
        t_linkedin = st.text_input("URL LinkedIn (Optionnel)")
        
    t_job_url = st.text_input("URL Annonce (Optionnel)")
    
    if st.button("🚀 Lancer le test"):
        with st.spinner("Génération de la séquence..."):
            # Simulation données prospect
            prospect = {
                'first_name': t_first, 'last_name': t_last, 'company': t_company,
                'linkedin_url': t_linkedin, 'job_posting_url': t_job_url
            }
            
            # 1. Scraping Annonce
            job_posting_data = None
            if t_job_url and enable_job_scraping:
                job_posting_data = scrape_job_posting(t_job_url)
            
            # 2. Icebreaker (Message 1) + Hooks
            # Pour le test manuel, on simplifie sans scraper LinkedIn si pas d'URL, 
            # mais si URL on pourrait le faire. Ici on reste simple pour le test.
            if t_linkedin:
                apify_client = init_apify_client()
                profile_data = scrape_linkedin_profile(apify_client, t_linkedin)
                posts_data = scrape_linkedin_posts(apify_client, t_linkedin)
                hooks_json = extract_hooks_with_claude(profile_data, posts_data, [], None, [], f"{t_first} {t_last}", t_company)
            else:
                hooks_json = "NOT_FOUND"

            # Génération Message 1
            msg1 = generate_advanced_icebreaker(prospect, hooks_json, job_posting_data)
            
            # 3. Séquence Complète (Objets, Msg 2, Msg 3)
            # On appelle notre nouvelle fonction magique
            full_sequence = generate_full_sequence(prospect, hooks_json, job_posting_data, msg1)
            
            # Affichage Résultats
            st.success("✅ Séquence générée !")
            
            st.subheader("Objets Suggérés")
            st.code(full_sequence['subject_lines'])
            
            st.subheader("Message 1 (Icebreaker)")
            st.text_area("M1", clean_message_format(full_sequence['message_1'], t_first), height=200)
            
            st.subheader("Message 2 (Dilemme)")
            st.text_area("M2", clean_message_format(full_sequence['message_2'], t_first), height=200)
            
            st.subheader("Message 3 (Break-up)")
            st.text_area("M3", clean_message_format(full_sequence['message_3'], t_first), height=200)


# --- TAB 2 & 3 : Laissés tels quels ou simplifiés ---
with tab2:
    st.write("Voir onglet Test Manuel pour les résultats immédiats.")
with tab3:
    st.write("Historique non disponible en mode test.")


# --- TAB 4 : EXPORT LEONAR (PRODUCTION) ---
with tab4:
    st.header("📤 Production : Export vers Leonar")
    
    if not all([LEONAR_EMAIL, LEONAR_PASSWORD, LEONAR_CAMPAIGN_ID]):
        st.error("❌ Configuration Leonar manquante")
        st.stop()
        
    with st.spinner("Connexion Leonar..."):
        token = get_leonar_token()
        
    if not token:
        st.error("❌ Echec connexion Leonar")
        st.stop()
        
    # Input URLs Annonces
    job_urls_list = []
    if enable_job_scraping:
        st.subheader("📄 URLs des fiches de poste")
        st.caption("Collez les URLs correspondant à l'ordre des prospects dans Leonar")
        job_urls_input = st.text_area("URLs (une par ligne)", height=150)
        if job_urls_input: 
            job_urls_list = [url.strip() for url in job_urls_input.split('\n') if url.strip()]

    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("🔄 Rafraîchir Liste"):
            st.session_state.leonar_prospects = get_new_prospects_leonar(token)
            
    if not st.session_state.leonar_prospects:
        st.info("Aucun nouveau prospect à traiter.")
    else:
        st.write(f"📊 **{len(st.session_state.leonar_prospects)} prospects détectés**")
        
        if st.button("🚀 LANCER LA GÉNÉRATION COMPLÈTE", type="primary"):
            progress = st.progress(0)
            status = st.empty()
            apify_client = init_apify_client()
            
            for i, prospect in enumerate(st.session_state.leonar_prospects):
                progress.progress(i / len(st.session_state.leonar_prospects))
                name = prospect.get('user_full name', 'Inconnu')
                status.write(f"⚙️ Traitement de **{name}**...")
                
                try:
                    # 1. Données de base
                    # Gestion de l'URL de job correspondante (si liste fournie)
                    current_job_url = None
                    if job_urls_list and i < len(job_urls_list):
                        current_job_url = job_urls_list[i]
                    
                    prospect_data = {
                        'first_name': prospect.get('first_name', ''),
                        'last_name': prospect.get('last_name', ''),
                        'company': prospect.get('linkedin_company', ''),
                        'linkedin_url': prospect.get('linkedin_url', ''),
                        'job_posting_url': current_job_url
                    }
                    
                    # 2. Scraping Annonce
                    job_posting_data = None
                    if current_job_url:
                        job_posting_data = scrape_job_posting(current_job_url)
                    
                    # 3. Scraping LinkedIn & Hooks
                    linkedin_url = prospect_data['linkedin_url']
                    hooks_json = "NOT_FOUND"
                    
                    if linkedin_url:
                        profile_data = scrape_linkedin_profile(apify_client, linkedin_url)
                        posts_data = scrape_linkedin_posts(apify_client, linkedin_url)
                        time.sleep(1) # Respect API
                        
                        company_posts = []
                        company_profile = None
                        if enable_company_scraping:
                            company_posts = scrape_company_posts(apify_client, prospect_data['company'])
                            company_profile = scrape_company_profile(apify_client, prospect_data['company'])
                        
                        web_results = []
                        if enable_web_search:
                            title = profile_data.get('experiences', [{}])[0].get('title', '') if profile_data else ""
                            web_results = web_search_prospect(prospect_data['first_name'], prospect_data['last_name'], prospect_data['company'], title)
                        
                        # Extraction Hooks (Filtre 3 mois auto)
                        hooks_json = extract_hooks_with_claude(
                            profile_data, posts_data, company_posts, company_profile, 
                            web_results, name, prospect_data['company']
                        )
                    
                    # 4. Génération Message 1 (Icebreaker)
                    msg1 = generate_advanced_icebreaker(prospect_data, hooks_json, job_posting_data)
                    msg1 = clean_message_format(msg1, prospect_data['first_name'])
                    
                    # 5. Génération Séquence (Objets + Msg 2 + Msg 3)
                    full_sequence = generate_full_sequence(prospect_data, hooks_json, job_posting_data, msg1)
                    
                    # Nettoyage final des messages 2 et 3
                    full_sequence['message_2'] = clean_message_format(full_sequence['message_2'], prospect_data['first_name'])
                    full_sequence['message_3'] = clean_message_format(full_sequence['message_3'], prospect_data['first_name'])
                    
                    # 6. Envoi Leonar
                    success = update_prospect_leonar(token, prospect['_id'], full_sequence)
                    
                    if success:
                        save_processed(prospect['_id'])
                        st.success(f"✅ {name} : Séquence envoyée")
                    else:
                        st.error(f"❌ {name} : Erreur API Leonar")
                        
                except Exception as e:
                    st.error(f"❌ Crash sur {name}: {e}")
            
            progress.progress(1.0)
            st.success("🎉 Campagne terminée !")
            st.balloons()