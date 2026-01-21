"""
Application Web Streamlit pour Icebreaker Generator
VERSION CORRIGÉE v5.1 - Avec statistiques de génération
"""

import streamlit as st
import pandas as pd
from icebreaker_v2 import *
from scraper_job_posting import scrape_job_posting
from message_sequence_generator import generate_full_sequence
from prospection_utils.cost_tracker import tracker
import time
import json
import requests
import os
from dotenv import load_dotenv
import re

load_dotenv()

st.set_page_config(page_title="Icebreaker Generator + Leonar", page_icon="🎯", layout="wide")

if 'results' not in st.session_state: 
    st.session_state.results = []
if 'processing' not in st.session_state: 
    st.session_state.processing = False
if 'leonar_prospects' not in st.session_state: 
    st.session_state.leonar_prospects = []

try:
    LEONAR_EMAIL = st.secrets["LEONAR_EMAIL"]
    LEONAR_PASSWORD = st.secrets["LEONAR_PASSWORD"]
    LEONAR_CAMPAIGN_ID = st.secrets["LEONAR_CAMPAIGN_ID"]
except:
    LEONAR_EMAIL = os.getenv("LEONAR_EMAIL")
    LEONAR_PASSWORD = os.getenv("LEONAR_PASSWORD")
    LEONAR_CAMPAIGN_ID = os.getenv("LEONAR_CAMPAIGN_ID")

PROCESSED_FILE = "processed_prospects.txt"

def clean_message_format(message, first_name):
    if not message: 
        return ""
    pattern = r'(Bonjour ' + re.escape(first_name) + r',)\s*'
    message = re.sub(pattern, r'\1\n\n', message, count=1, flags=re.IGNORECASE)
    message = re.sub(r'\n{3,}', '\n\n', message)
    pattern_lowercase = r'(Bonjour ' + re.escape(first_name) + r',\n\n)([a-zà-ÿ])'
    message = re.sub(pattern_lowercase, lambda m: m.group(1) + m.group(2).upper(), message, count=1, flags=re.IGNORECASE)
    patterns_to_remove = [
        r'\n\nBien cordialement,?\s*\n+\[Prénom\]', 
        r'\nBien cordialement,\s*\[Prénom\]', 
        r'\n\[Prénom\]\s*$', 
        r'Cordialement,\s*\[Prénom\]'
    ]
    for p in patterns_to_remove: 
        message = re.sub(p, '\n\nBien cordialement', message)
    return message.strip()

def update_prospect_leonar(token, prospect_id, sequence_data):
    try:
        subject_lines = sequence_data.get('subject_lines', '').strip()
        msg1 = sequence_data.get('message_1', '').strip()
        msg2 = sequence_data.get('message_2', '').strip()
        msg3 = sequence_data.get('message_3', '').strip()
        formatted_notes = f"""═══════════════════════════════════════════════════════════════
OBJETS SUGGÉRÉS (Choisir 1)
═══════════════════════════════════════════════════════════════

{subject_lines}

═══════════════════════════════════════════════════════════════
MESSAGE 1 (ICEBREAKER - J+0)
═══════════════════════════════════════════════════════════════

{msg1}

═══════════════════════════════════════════════════════════════
MESSAGE 2 (LE DILEMME - J+5)
═══════════════════════════════════════════════════════════════

{msg2}

═══════════════════════════════════════════════════════════════
MESSAGE 3 (BREAK-UP EXPERT - J+12)
═══════════════════════════════════════════════════════════════

{msg3}

═══════════════════════════════════════════════════════════════
FIN DE SÉQUENCE
═══════════════════════════════════════════════════════════════"""
        requests.patch(
            f'https://dashboard.leonar.app/api/1.1/obj/matching/{prospect_id}', 
            headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}, 
            json={"notes": formatted_notes}, 
            timeout=10
        )
        return True
    except: 
        return False

def get_leonar_token():
    try:
        r = requests.post(
            'https://dashboard.leonar.app/api/1.1/wf/auth', 
            json={"email": LEONAR_EMAIL, "password": LEONAR_PASSWORD}, 
            timeout=10
        )
        return r.json()['response']['token'] if r.status_code == 200 else None
    except: 
        return None

def load_processed():
    if os.path.exists(PROCESSED_FILE):
        with open(PROCESSED_FILE, 'r') as f: 
            return set(f.read().splitlines())
    return set()

def save_processed(pid):
    with open(PROCESSED_FILE, 'a') as f: 
        f.write(f"{pid}\n")

def get_new_prospects_leonar(token):
    try:
        r = requests.get(
            f'https://dashboard.leonar.app/api/1.1/obj/matching?constraints=[{{"key":"campaign","constraint_type":"equals","value":"{LEONAR_CAMPAIGN_ID}"}}]&cursor=0', 
            headers={'Authorization': f'Bearer {token}'}, 
            timeout=10
        )
        if r.status_code != 200: 
            return []
        processed = load_processed()
        return [
            p for p in r.json()['response']['results'] 
            if p['_id'] not in processed and (
                not p.get('notes') or 
                len(p.get('notes', '')) < 100 or 
                'MESSAGE 1' not in p.get('notes', '')
            )
        ]
    except: 
        return []

# ========================================
# INTERFACE PRINCIPALE
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
    if all([LEONAR_EMAIL, LEONAR_PASSWORD, LEONAR_CAMPAIGN_ID]):
        if get_leonar_token(): 
            st.success("✅ Connecté à Leonar")
        else: 
            st.error("❌ Erreur connexion")

tab1, tab2, tab3, tab4 = st.tabs(["📝 Test Manuel", "📊 Résultats Test", "📈 Historique", "📤 Export Leonar"])

# ========================================
# TAB 1 : TEST MANUEL
# ========================================
with tab1:
    st.header("Test Manuel")
    c1, c2 = st.columns(2)
    with c1: 
        t_first = st.text_input("Prénom", "Thomas")
        t_comp = st.text_input("Entreprise", "Green Energy")
    with c2: 
        t_last = st.text_input("Nom", "Durand")
        t_lnk = st.text_input("URL LinkedIn")
    
    t_job = st.text_input("URL Annonce")
    
    if st.button("🚀 Lancer le test"):
        with st.spinner("Génération en cours..."):
            # Préparation des données
            prospect = {
                'first_name': t_first, 
                'last_name': t_last, 
                'company': t_comp, 
                'linkedin_url': t_lnk, 
                'job_posting_url': t_job
            }
            
            # Scraping annonce
            job_data = scrape_job_posting(t_job) if t_job else None
            
            # Extraction hooks
            hooks = "NOT_FOUND"
            if t_lnk:
                ac = init_apify_client()
                prof = scrape_linkedin_profile(ac, t_lnk)
                posts = scrape_linkedin_posts(ac, t_lnk)
                hooks = extract_hooks_with_claude(
                    prof, posts, [], None, [], 
                    f"{t_first} {t_last}", t_comp
                )
            
            # Génération message 1
            m1 = generate_advanced_icebreaker(prospect, hooks, job_data)
            
            # Génération séquence complète
            seq = generate_full_sequence(prospect, hooks, job_data, m1)
            
            # Affichage des résultats
            st.subheader("📧 Objets d'email")
            st.code(seq['subject_lines'])
            
            st.subheader("✉️ Message 1 (Icebreaker)")
            st.info(clean_message_format(seq['message_1'], t_first))
            
            st.subheader("✉️ Message 2 (Le Dilemme)")
            st.info(clean_message_format(seq['message_2'], t_first))
            
            st.subheader("✉️ Message 3 (Break-up)")
            st.info(clean_message_format(seq['message_3'], t_first))
            
            # ========================================
            # STATISTIQUES DE GÉNÉRATION
            # ========================================
            st.divider()
            st.subheader("📊 Statistiques de génération")
            
            summary = tracker.get_summary()
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Appels API", summary['total_calls'])
            
            with col2:
                st.metric("Tokens total", f"{summary['total_tokens']:,}")
            
            with col3:
                st.metric("Coût total", f"${summary['total_cost_usd']}")
            
            with col4:
                st.metric("Durée", f"{summary['session_duration_seconds']}s")
            
            # Détail des appels
            with st.expander("📋 Détail des appels"):
                for call in tracker.calls:
                    st.write(f"**{call['function']}**")
                    st.write(f"   - Tokens: {call['input_tokens']} → {call['output_tokens']}")
                    st.write(f"   - Coût: ${call['cost_usd']}")
                    st.write("---")

# ========================================
# TAB 2 : RÉSULTATS TEST
# ========================================
with tab2:
    st.header("📊 Résultats des tests")
    st.info("Fonctionnalité à venir")

# ========================================
# TAB 3 : HISTORIQUE
# ========================================
with tab3:
    st.header("📈 Historique")
    st.info("Fonctionnalité à venir")

# ========================================
# TAB 4 : EXPORT LEONAR
# ========================================
with tab4:
    st.header("📤 Export Leonar")
    
    if not all([LEONAR_EMAIL, LEONAR_PASSWORD, LEONAR_CAMPAIGN_ID]): 
        st.error("Configuration Leonar manquante")
        st.stop()
    
    token = get_leonar_token()
    if not token: 
        st.error("Impossible de se connecter à Leonar")
        st.stop()
    
    # Zone URL Jobs
    job_urls_list = []
    if enable_job_scraping:
        st.subheader("📄 URLs des fiches de poste")
        urls_input = st.text_area("URLs (une par ligne, ordre Leonar)", height=100)
        if urls_input: 
            job_urls_list = [u.strip() for u in urls_input.split('\n') if u.strip()]

    if st.button("🔄 Rafraîchir Liste"):
        st.session_state.leonar_prospects = get_new_prospects_leonar(token)
    
    # Liste des prospects
    if st.session_state.leonar_prospects:
        st.success(f"📊 {len(st.session_state.leonar_prospects)} prospects détectés")
        
        with st.expander("👥 Voir la liste des prospects (Cliquer pour dérouler)", expanded=True):
            for i, p in enumerate(st.session_state.leonar_prospects):
                lnk = "✅" if p.get('linkedin_url') else "⚠️"
                job_stat = "📄 Annonce dispo" if (job_urls_list and i < len(job_urls_list)) else "❌ Pas d'annonce"
                st.write(f"**{i+1}. {p.get('user_full name', 'Inconnu')}** | {p.get('linkedin_company', '')} | {lnk} | {job_stat}")

        if st.button("🚀 LANCER LA GÉNÉRATION COMPLÈTE", type="primary"):
            bar = st.progress(0)
            st_txt = st.empty()
            ac = init_apify_client()
            
            for i, p in enumerate(st.session_state.leonar_prospects):
                bar.progress(i / len(st.session_state.leonar_prospects))
                name = p.get('user_full name', 'Inconnu')
                st_txt.write(f"⚙️ Traitement de **{name}**...")
                
                try:
                    j_url = job_urls_list[i] if (job_urls_list and i < len(job_urls_list)) else None
                    p_data = {
                        'first_name': p.get('first_name', ''), 
                        'last_name': p.get('last_name', ''), 
                        'company': p.get('linkedin_company', ''), 
                        'linkedin_url': p.get('linkedin_url', ''), 
                        'job_posting_url': j_url
                    }
                    
                    j_data = scrape_job_posting(j_url) if j_url else None
                    hooks = "NOT_FOUND"
                    
                    if p_data['linkedin_url']:
                        prof = scrape_linkedin_profile(ac, p_data['linkedin_url'])
                        posts = scrape_linkedin_posts(ac, p_data['linkedin_url'])
                        hooks = extract_hooks_with_claude(prof, posts, [], None, [], name, p_data['company'])
                    
                    m1 = generate_advanced_icebreaker(p_data, hooks, j_data)
                    m1 = clean_message_format(m1, p_data['first_name'])
                    
                    full = generate_full_sequence(p_data, hooks, j_data, m1)
                    
                    full['message_2'] = clean_message_format(full['message_2'], p_data['first_name'])
                    full['message_3'] = clean_message_format(full['message_3'], p_data['first_name'])
                    
                    if update_prospect_leonar(token, p['_id'], full):
                        save_processed(p['_id'])
                        st.toast(f"✅ {name} OK")
                    else: 
                        st.error(f"Erreur API Leonar pour {name}")
                        
                except Exception as e: 
                    st.error(f"Erreur pour {name}: {e}")
            
            bar.progress(1.0)
            st.success("✅ Traitement terminé !")
            st.balloons()
    else:
        st.info("Aucun nouveau prospect à traiter.")