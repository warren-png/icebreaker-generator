"""
Application Web Streamlit pour Icebreaker Generator
VERSION V27 - Avec mapping prénom corrigé et statistiques de génération
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
    """
    Nettoie le format du message
    VERSION V27 : Nettoyage amélioré
    """
    if not message: 
        return ""
    
    # S'assurer d'une ligne vide après "Bonjour {prénom},"
    pattern = r'(Bonjour ' + re.escape(first_name) + r',)\s*'
    message = re.sub(pattern, r'\1\n\n', message, count=1, flags=re.IGNORECASE)
    
    # Supprimer les lignes vides excessives
    message = re.sub(r'\n{3,}', '\n\n', message)
    
    # Capitaliser la première lettre après le bonjour
    pattern_lowercase = r'(Bonjour ' + re.escape(first_name) + r',\n\n)([a-zà-ÿ])'
    message = re.sub(pattern_lowercase, lambda m: m.group(1) + m.group(2).upper(), message, count=1, flags=re.IGNORECASE)
    
    # Supprimer les signatures parasites
    patterns_to_remove = [
        r'\n\nBien cordialement,?\s*\n+\[Prénom\]', 
        r'\nBien cordialement,\s*\[Prénom\]', 
        r'\n\[Prénom\]\s*$', 
        r'Cordialement,\s*\[Prénom\]',
        r'\[Votre signature\]'
    ]
    for p in patterns_to_remove: 
        message = re.sub(p, '', message)
    
    # S'assurer qu'on finit bien par "Bien à vous," ou "Bonne continuation,"
    message = message.strip()
    if not message.endswith('Bien à vous,') and not message.endswith('Bonne continuation,'):
        if 'Bien à vous' in message:
            message = message.rsplit('Bien à vous', 1)[0].strip() + '\n\nBien à vous,'
        elif 'Bonne continuation' in message:
            message = message.rsplit('Bonne continuation', 1)[0].strip() + '\n\nBonne continuation,'
    
    return message.strip()


def update_prospect_leonar(token, prospect_id, sequence_data):
    """
    Met à jour le prospect dans Leonar avec la séquence générée
    VERSION V27 : Format amélioré
    """
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
MESSAGE 2 (LA PROPOSITION - J+5)
═══════════════════════════════════════════════════════════════

{msg2}

═══════════════════════════════════════════════════════════════
MESSAGE 3 (BREAK-UP - J+12)
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
    except Exception as e:
        print(f"❌ Erreur update Leonar: {e}")
        return False


def get_leonar_token():
    """Obtient un token d'authentification Leonar"""
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
    """Charge la liste des prospects déjà traités"""
    if os.path.exists(PROCESSED_FILE):
        with open(PROCESSED_FILE, 'r') as f: 
            return set(f.read().splitlines())
    return set()


def save_processed(pid):
    """Sauvegarde un prospect comme traité"""
    with open(PROCESSED_FILE, 'a') as f: 
        f.write(f"{pid}\n")


def get_new_prospects_leonar(token):
    """
    Récupère les nouveaux prospects depuis Leonar
    VERSION V27 : Meilleure extraction des données
    """
    try:
        r = requests.get(
            f'https://dashboard.leonar.app/api/1.1/obj/matching?constraints=[{{"key":"campaign","constraint_type":"equals","value":"{LEONAR_CAMPAIGN_ID}"}}]&cursor=0', 
            headers={'Authorization': f'Bearer {token}'}, 
            timeout=10
        )
        if r.status_code != 200: 
            return []
        
        processed = load_processed()
        
        # Filtrer les prospects non traités
        return [
            p for p in r.json()['response']['results'] 
            if p['_id'] not in processed and (
                not p.get('notes') or 
                len(p.get('notes', '')) < 100 or 
                'MESSAGE 1' not in p.get('notes', '')
            )
        ]
    except Exception as e:
        print(f"❌ Erreur get prospects: {e}")
        return []


def extract_prospect_data(leonar_prospect):
    """
    Extrait les données du prospect depuis Leonar
    VERSION V27 : Mapping correct des champs
    """
    # Extraire le prénom et nom depuis user_full name
    full_name = leonar_prospect.get('user_full name', '')
    first_name = ''
    last_name = ''
    
    if full_name and ' ' in str(full_name):
        parts = str(full_name).split()
        first_name = parts[0] if len(parts) > 0 else ''
        last_name = ' '.join(parts[1:]) if len(parts) > 1 else ''
    
    # Construire le dictionnaire de données
    prospect_data = {
        '_id': leonar_prospect.get('_id', ''),
        'full_name': full_name,
        'user_full name': full_name,  # Conserver le champ original
        'first_name': first_name,
        'last_name': last_name,
        'company': leonar_prospect.get('linkedin_company', ''),
        'linkedin_company': leonar_prospect.get('linkedin_company', ''),
        'linkedin_url': leonar_prospect.get('linkedin_url', ''),
        'headline': leonar_prospect.get('linkedin_headline', ''),
        'title': leonar_prospect.get('linkedin_headline', ''),
        'job_posting_url': ''  # Sera rempli plus tard
    }
    
    return prospect_data


# ========================================
# INTERFACE PRINCIPALE
# ========================================

st.title("🎯 Icebreaker Generator + Leonar")
st.markdown("*Génération automatique Séquence 3 Messages optimisée V27*")
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
        t_first = st.text_input("Prénom", "Guillaume")
        t_comp = st.text_input("Entreprise", "LCL")
    with c2: 
        t_last = st.text_input("Nom", "Mullier")
        t_lnk = st.text_input("URL LinkedIn")
    
    t_job = st.text_input("URL Annonce")
    
    if st.button("🚀 Lancer le test"):
        with st.spinner("Génération en cours..."):
            # Préparation des données
            prospect = {
                'first_name': t_first, 
                'last_name': t_last,
                'full_name': f"{t_first} {t_last}",
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
            
            st.subheader("✉️ Message 2 (La Proposition)")
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
        st.caption("⚠️ IMPORTANT : Les URLs doivent être dans le MÊME ORDRE que les prospects dans Leonar")
        urls_input = st.text_area("URLs (une par ligne, ordre Leonar)", height=150)
        if urls_input: 
            job_urls_list = [u.strip() for u in urls_input.split('\n') if u.strip()]
            st.success(f"✅ {len(job_urls_list)} URLs détectées")

    if st.button("🔄 Rafraîchir Liste des Prospects"):
        st.session_state.leonar_prospects = get_new_prospects_leonar(token)
    
    # Liste des prospects
    if st.session_state.leonar_prospects:
        st.success(f"📊 {len(st.session_state.leonar_prospects)} prospects détectés")
        
        with st.expander("👥 Voir la liste des prospects (Cliquer pour dérouler)", expanded=True):
            for i, p in enumerate(st.session_state.leonar_prospects):
                full_name = p.get('user_full name', 'Inconnu')
                company = p.get('linkedin_company', 'N/A')
                lnk = "✅ LinkedIn" if p.get('linkedin_url') else "⚠️ Pas de LinkedIn"
                job_stat = f"📄 URL {i+1}" if (job_urls_list and i < len(job_urls_list)) else "❌ Pas d'URL annonce"
                
                st.write(f"**{i+1}. {full_name}** | {company} | {lnk} | {job_stat}")

        if st.button("🚀 LANCER LA GÉNÉRATION COMPLÈTE", type="primary"):
            bar = st.progress(0)
            st_txt = st.empty()
            ac = init_apify_client()
            
            for i, p in enumerate(st.session_state.leonar_prospects):
                bar.progress(i / len(st.session_state.leonar_prospects))
                
                full_name = p.get('user_full name', 'Inconnu')
                st_txt.write(f"⚙️ Traitement de **{full_name}**...")
                
                try:
                    # Extraire les données du prospect
                    p_data = extract_prospect_data(p)
                    
                    # Ajouter l'URL de l'annonce si disponible
                    j_url = job_urls_list[i] if (job_urls_list and i < len(job_urls_list)) else None
                    p_data['job_posting_url'] = j_url
                    
                    # Scraping de l'annonce
                    j_data = scrape_job_posting(j_url) if j_url else None
                    
                    # Extraction des hooks
                    hooks = "NOT_FOUND"
                    if p_data['linkedin_url']:
                        prof = scrape_linkedin_profile(ac, p_data['linkedin_url'])
                        posts = scrape_linkedin_posts(ac, p_data['linkedin_url'])
                        hooks = extract_hooks_with_claude(
                            prof, posts, [], None, [], 
                            full_name, p_data['company']
                        )
                    
                    # Génération du message 1
                    m1 = generate_advanced_icebreaker(p_data, hooks, j_data)
                    m1 = clean_message_format(m1, p_data['first_name'])
                    
                    # Génération de la séquence complète
                    full = generate_full_sequence(p_data, hooks, j_data, m1)
                    
                    # Nettoyage des messages
                    full['message_2'] = clean_message_format(full['message_2'], p_data['first_name'])
                    full['message_3'] = clean_message_format(full['message_3'], p_data['first_name'])
                    
                    # Update dans Leonar
                    if update_prospect_leonar(token, p['_id'], full):
                        save_processed(p['_id'])
                        st.toast(f"✅ {full_name} OK")
                    else: 
                        st.error(f"❌ Erreur API Leonar pour {full_name}")
                        
                except Exception as e: 
                    st.error(f"❌ Erreur pour {full_name}: {e}")
                    print(f"Détail erreur: {e}")
            
            bar.progress(1.0)
            st.success("✅ Traitement terminé !")
            st.balloons()
            
            # Afficher les statistiques finales
            st.divider()
            st.subheader("📊 Statistiques de la session")
            summary = tracker.get_summary()
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Appels API totaux", summary['total_calls'])
            with col2:
                st.metric("Tokens totaux", f"{summary['total_tokens']:,}")
            with col3:
                st.metric("Coût total", f"${summary['total_cost_usd']}")
    
    else:
        st.info("Aucun nouveau prospect à traiter. Cliquez sur 'Rafraîchir Liste' pour vérifier.")
