"""
Application Web Streamlit pour Icebreaker Generator
VERSION FINALE v3.2 - CODE COMPLET RESTAURÉ
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
import re  # Import essentiel

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

# Configuration Leonar (Avec fallback Secrets/Env)
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
# FONCTIONS UTILITAIRES CORRIGÉES
# ========================================

def clean_message_format(message, first_name):
    """
    Nettoie le format des messages générés :
    - Assure une ligne vide après "Bonjour {prénom},"
    - Force la MAJUSCULE au début du message
    - Supprime les signatures
    """
    import re
    
    # 1. Assurer ligne vide après salutation
    pattern = r'(Bonjour ' + re.escape(first_name) + r',)\s*'
    message = re.sub(pattern, r'\1\n\n', message, count=1, flags=re.IGNORECASE)
    
    # 2. Nettoyer les doubles lignes vides en trop
    message = re.sub(r'(Bonjour ' + re.escape(first_name) + r',)\n\n\n+', r'\1\n\n', message, count=1, flags=re.IGNORECASE)
    
    # 3. Force la majuscule après "Bonjour Prénom,\n\n"
    # C'est ICI que la magie opère pour transformer "j'ai" en "J'ai"
    pattern_lowercase = r'(Bonjour ' + re.escape(first_name) + r',\n\n)([a-zà-ÿ])'
    message = re.sub(pattern_lowercase, lambda m: m.group(1) + m.group(2).upper(), message, count=1, flags=re.IGNORECASE)
    
    # 4. Supprimer toutes les variations de signature
    patterns_to_remove = [
        r'\n\nBien cordialement,?\s*\n+\[Prénom\]',
        r'\nBien cordialement,\s*\[Prénom\]',
        r'\n\[Prénom\]\s*$',
        r'Cordialement,\s*\[Prénom\]'
    ]
    
    for pattern in patterns_to_remove:
        message = re.sub(pattern, '\n\nBien cordialement', message)
    
    # 5. Nettoyer signature orpheline
    message = re.sub(r'\n+\[Prénom\]\s*$', '', message)
    
    return message.strip()

def generate_subject_line(message_1, first_name, hooks_data):
    """
    Génère un objet de mail/LinkedIn basé sur le PAIN POINT du message 1
    VERSION OPTIMISÉE v2.1 - Gestion robuste de la Clé API
    """
    import anthropic 
    
    # --- Récupération sécurisée de la clé API ---
    api_key = None
    try:
        api_key = st.secrets["ANTHROPIC_API_KEY"]
    except:
        pass
        
    if not api_key:
        api_key = os.getenv("ANTHROPIC_API_KEY")
    
    if not api_key:
        print("⚠️ ERREUR : Clé API Anthropic introuvable")
        return "Défis recrutement et opportunité"
    
    client = anthropic.Anthropic(api_key=api_key)

    prompt = f"""Tu es un expert en copywriting pour LinkedIn et email B2B.

Ta mission : extraire le PAIN POINT central du message et créer un objet percutant.

MESSAGE :
{message_1}

RÈGLES :
1. FORMAT : "[Élément 1] vs [Élément 2]" (ex: "Rigueur comptable vs réalité terrain")
2. LONGUEUR : 35-48 caractères MAX
3. INTERDIT : Ne JAMAIS commencer par "Votre recherche" ou "Bonjour".
4. CONTENU : Doit refléter la tension ou le défi décrit dans le message.

Réponds UNIQUEMENT avec l'objet final."""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=150,
            temperature=0.2,
            messages=[{"role": "user", "content": prompt}]
        )
    
        subject = response.content[0].text.strip()
        subject = subject.replace('"', '').replace("'", '').replace('`', '').strip()
        
        # Fallback de sécurité
        if len(subject) > 60 or "votre recherche" in subject.lower():
            return "Profils rares sur le marché"
        
        return subject
    
    except Exception as e:
        print(f"❌ ERREUR API: {str(e)}")
        if "vs" in message_1.lower():
            return "Arbitrage recrutement : le défi"
        return "Défis recrutement spécifiques"

def update_prospect_leonar(token, prospect_id, messages):
    """Met à jour un prospect - Version Formatage Explicite (Anti-Bug)"""
    try:
        subject_content = messages.get('subject', 'Défis recrutement spécifiques').strip()
        msg1_content = messages['message_1'].strip()
        msg2_content = messages['message_2'].strip()
        msg3_content = messages['message_3'].strip()

        # Construction explicite ligne par ligne pour garantir l'affichage
        formatted_notes = (
            "═══════════════════════════════════════════════════════════════\n"
            "OBJET (Mail/LinkedIn)\n"
            "═══════════════════════════════════════════════════════════════\n"
            "\n"
            f"{subject_content}\n"
            "\n"
            "═══════════════════════════════════════════════════════════════\n"
            "MESSAGE 1 (J+0) - ICEBREAKER\n"
            "═══════════════════════════════════════════════════════════════\n"
            "\n"
            f"{msg1_content}\n"
            "\n"
            "═══════════════════════════════════════════════════════════════\n"
            "MESSAGE 2 (J+5) - APPORT VALEUR\n"
            "═══════════════════════════════════════════════════════════════\n"
            "\n"
            f"{msg2_content}\n"
            "\n"
            "═══════════════════════════════════════════════════════════════\n"
            "MESSAGE 3 (J+12) - BREAK-UP\n"
            "═══════════════════════════════════════════════════════════════\n"
            "\n"
            f"{msg3_content}"
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
        print(f"ERROR: {str(e)}")
        return False

# ========================================
# FONCTIONS LEONAR (API)
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
# HEADER & SIDEBAR
# ========================================

st.title("🎯 Icebreaker Generator + Leonar")
st.markdown("*Générez des messages LinkedIn ultra-personnalisés et exportez vers Leonar*")
st.divider()

with st.sidebar:
    st.header("⚙️ Configuration")
    enable_web_search = st.checkbox("Recherche Web", value=True)
    enable_company_scraping = st.checkbox("Scraper l'entreprise", value=True)
    enable_job_scraping = st.checkbox("🆕 Scraper l'annonce", value=True)
    st.divider()
    
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
    st.divider()
    
    st.subheader("📊 Statistiques")
    st.metric("Prospects traités", len(st.session_state.results))
    if st.session_state.results:
        avg_time = sum(r['time'] for r in st.session_state.results) / len(st.session_state.results)
        st.metric("Temps moyen", f"{avg_time:.1f}s")

# ========================================
# MAIN CONTENT (LES 4 ONGLETS COMPLETS)
# ========================================

tab1, tab2, tab3, tab4 = st.tabs(["📝 Génération", "📊 Résultats", "📈 Historique", "📤 Export Leonar"])

# --- TAB 1 : GÉNÉRATION STANDARD ---
with tab1:
    st.header("Génération d'icebreakers")
    mode = st.radio("Mode de saisie", ["URLs LinkedIn manuelles", "Import Google Sheet"], horizontal=True)
    
    if mode == "URLs LinkedIn manuelles":
        col1, col2 = st.columns(2)
        with col1:
            first_names = st.text_area("Prénoms (un par ligne)", height=200, placeholder="Jean\nMarie")
        with col2:
            last_names = st.text_area("Noms (un par ligne)", height=200, placeholder="Dupont\nMartin")
        companies = st.text_area("Entreprises (une par ligne)", height=100, placeholder="Total\nAirbus")
        linkedin_urls = st.text_area("URLs LinkedIn (Optionnel)", height=150)
        job_posting_urls = st.text_area("🆕 URLs Annonces (Optionnel)", height=150)
        
    else:
        st.info("🔗 L'outil va se connecter à votre Google Sheet configuré")

    st.divider()
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🚀 Générer les icebreakers", type="primary", use_container_width=True):
            # Préparation des prospects
            prospects = []
            if mode == "URLs LinkedIn manuelles":
                f_list = [x.strip() for x in first_names.split('\n') if x.strip()]
                l_list = [x.strip() for x in last_names.split('\n') if x.strip()]
                c_list = [x.strip() for x in companies.split('\n') if x.strip()]
                u_list = [x.strip() for x in linkedin_urls.split('\n') if x.strip()] if linkedin_urls else []
                j_list = [x.strip() for x in job_posting_urls.split('\n') if x.strip()] if job_posting_urls else []
                
                if not (f_list and l_list and c_list):
                    st.error("❌ Remplissez Prénoms, Noms et Entreprises")
                    st.stop()
                
                for i in range(len(f_list)):
                    prospects.append({
                        'first_name': f_list[i],
                        'last_name': l_list[i],
                        'company': c_list[i],
                        'linkedin_url': u_list[i] if i < len(u_list) else '',
                        'job_posting_url': j_list[i] if i < len(j_list) else ''
                    })
            else:
                try:
                    sheet = connect_to_google_sheet()
                    prospects = get_prospects(sheet)
                except Exception as e:
                    st.error(f"❌ Erreur Sheet : {e}")
                    st.stop()
            
            # Traitement
            st.session_state.processing = True
            st.session_state.results = []
            progress_bar = st.progress(0)
            status_text = st.empty()
            apify_client = init_apify_client()
            
            for i, prospect in enumerate(prospects):
                status_text.text(f"🔄 {prospect['first_name']} {prospect['last_name']} ({i+1}/{len(prospects)})")
                start_time = time.time()
                
                try:
                    if not prospect.get('linkedin_url'):
                        linkedin_url = search_linkedin_profile(prospect['first_name'], prospect['last_name'], prospect['company'])
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
                    
                    web_results = []
                    if enable_web_search:
                        title = profile_data['experiences'][0].get('title', '') if profile_data and profile_data.get('experiences') else ""
                        web_results = web_search_prospect(prospect['first_name'], prospect['last_name'], prospect['company'], title)
                        time.sleep(2)
                    
                    hooks_json = extract_hooks_with_claude(profile_data, posts_data, company_posts, company_profile, web_results, f"{prospect['first_name']} {prospect['last_name']}", prospect['company'])
                    time.sleep(2)
                    
                    icebreaker = generate_advanced_icebreaker(prospect, hooks_json, job_posting_data)
                    # Utilisation de la nouvelle fonction clean
                    icebreaker = clean_message_format(icebreaker, prospect['first_name'])
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
                        'hooks': '',
                        'icebreaker': f"Erreur : {str(e)}",
                        'time': 0,
                        'status': 'error'
                    })
                progress_bar.progress((i + 1) / len(prospects))
            
            status_text.text("✅ Terminé !")
            st.session_state.processing = False
            st.balloons()

# --- TAB 2 : RÉSULTATS ---
with tab2:
    st.header("📊 Résultats")
    if not st.session_state.results:
        st.info("👆 Lancez une génération pour voir les résultats")
    else:
        col1, col2, col3 = st.columns(3)
        with col1: st.metric("✅ Réussis", sum(1 for r in st.session_state.results if r['status'] == 'success'))
        with col2: st.metric("❌ Erreurs", sum(1 for r in st.session_state.results if r['status'] == 'error'))
        with col3: st.metric("⏱️ Temps total", f"{sum(r['time'] for r in st.session_state.results):.0f}s")
        st.divider()
        
        for i, result in enumerate(st.session_state.results):
            with st.expander(f"{'✅' if result['status'] == 'success' else '❌'} {result['first_name']} {result['last_name']} - {result['company']}"):
                if result['status'] == 'success':
                    st.info(result['icebreaker'])
                    st.markdown(f"[LinkedIn]({result['linkedin_url']})")
                    if result.get('hooks'): st.json(result['hooks'])
                else:
                    st.error(result['icebreaker'])
        
        st.divider()
        df = pd.DataFrame([{
            'Prénom': r['first_name'], 'Nom': r['last_name'], 'Entreprise': r['company'],
            'LinkedIn': r['linkedin_url'], 'Icebreaker': r['icebreaker']
        } for r in st.session_state.results])
        st.download_button("📥 Télécharger CSV", data=df.to_csv(index=False).encode('utf-8'), file_name="icebreakers.csv", mime="text/csv")

# --- TAB 3 : HISTORIQUE ---
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
                with st.expander(f"{row.get('first_name', '')} {row.get('last_name', '')}"):
                    st.info(row.get('icebreaker', ''))
    except Exception as e:
        st.error(f"❌ Erreur : {e}")

# --- TAB 4 : EXPORT LEONAR (CORRIGÉ & COMPLET) ---
with tab4:
    st.header("📤 Export vers Leonar")
    if not all([LEONAR_EMAIL, LEONAR_PASSWORD, LEONAR_CAMPAIGN_ID]):
        st.error("❌ Configuration Leonar manquante !")
        st.stop()
    
    with st.spinner("🔐 Connexion à Leonar..."):
        token = get_leonar_token()
    
    if not token:
        st.error("❌ Impossible de se connecter à Leonar")
        st.stop()
    
    st.success("✅ Connecté à Leonar")
    
    col1, col2, col3 = st.columns(3)
    with col1: leonar_web_search = st.checkbox("🔍 Recherche Web", value=True, key="leonar_web")
    with col2: leonar_company_scraping = st.checkbox("🏢 Scraper entreprise", value=True, key="leonar_company")
    with col3: leonar_job_scraping = st.checkbox("📄 Scraper annonce", value=True, key="leonar_job")
    
    job_urls_list = []
    if leonar_job_scraping:
        st.subheader("📄 URLs des fiches de poste")
        job_urls_input = st.text_area("Collez les URLs (une par ligne, dans l'ordre)", height=150, key="leonar_job_urls")
        if job_urls_input: job_urls_list = [url.strip() for url in job_urls_input.split('\n')]
    
    st.divider()
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🔄 RAFRAÎCHIR LA LISTE", type="secondary", use_container_width=True):
            with st.spinner("📊 Récupération des prospects..."):
                st.session_state.leonar_prospects = get_new_prospects_leonar(token)
            st.rerun()
            
    if not st.session_state.leonar_prospects:
        st.success("✅ Aucun nouveau prospect à traiter !")
    else:
        st.warning(f"📊 {len(st.session_state.leonar_prospects)} prospect(s) en attente")
        
        # Liste des prospects
        with st.expander("👥 Voir la liste des prospects", expanded=True):
            for i, p in enumerate(st.session_state.leonar_prospects, 1):
                linkedin_icon = "✅" if p.get('linkedin_url') else "⚠️"
                job_icon = " 📄" if (job_urls_list and i <= len(job_urls_list) and 'http' in job_urls_list[i-1]) else ""
                st.markdown(f"**{i}.** {p.get('user_full name', 'N/A')} - {linkedin_icon} LinkedIn{job_icon}")
        
        st.divider()
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🚀 GÉNÉRER LES MESSAGES (SCRAPING COMPLET)", type="primary", use_container_width=True):
                st.subheader("⚙️ Génération en cours...")
                results = []
                progress = st.progress(0)
                status = st.empty()
                apify_client = init_apify_client()
                
                for i, prospect in enumerate(st.session_state.leonar_prospects):
                    progress.progress(i / len(st.session_state.leonar_prospects))
                    name = prospect.get('user_full name', 'N/A')
                    status.markdown(f"**Traitement de {name}...**")
                    start_time = time.time()
                    
                    try:
                        # 1. Préparation données
                        job_url = job_urls_list[i] if (job_urls_list and i < len(job_urls_list) and 'http' in job_urls_list[i]) else None
                        prospect_data = {
                            'first_name': prospect.get('first_name', ''),
                            'last_name': prospect.get('last_name', ''),
                            'company': prospect.get('linkedin_company', ''),
                            'linkedin_url': prospect.get('linkedin_url', ''),
                            'job_posting_url': job_url or ''
                        }
                        
                        # 2. Scraping
                        linkedin_url = prospect.get('linkedin_url', '')
                        if linkedin_url:
                            profile_data = scrape_linkedin_profile(apify_client, linkedin_url)
                            posts_data = scrape_linkedin_posts(apify_client, linkedin_url)
                            time.sleep(2)
                            
                            company_posts = []
                            company_profile = None
                            if leonar_company_scraping:
                                company_posts = scrape_company_posts(apify_client, prospect_data['company'])
                                company_profile = scrape_company_profile(apify_client, prospect_data['company'])
                                time.sleep(2)
                                
                            web_results = []
                            if leonar_web_search:
                                title = profile_data.get('experiences', [{}])[0].get('title', '') if profile_data else ""
                                web_results = web_search_prospect(prospect_data['first_name'], prospect_data['last_name'], prospect_data['company'], title)
                                time.sleep(2)
                            
                            hooks_json = extract_hooks_with_claude(profile_data, posts_data, company_posts, company_profile, web_results, name, prospect_data['company'])
                        else:
                            hooks_json = 'NOT_FOUND'
                            
                        job_posting_data = scrape_job_posting(job_url) if job_url else None
                        
                        # 3. Génération & Nettoyage (AVEC LES CORRECTIFS)
                        st.write(f"📝 {name} - Rédaction...")
                        
                        message_1 = generate_advanced_icebreaker(prospect_data, hooks_json, job_posting_data)
                        message_1 = clean_message_format(message_1, prospect_data['first_name'])
                        
                        subject_line = generate_subject_line(message_1, prospect_data['first_name'], hooks_json)
                        
                        message_2 = generate_message_2(prospect_data, hooks_json, job_posting_data, message_1)
                        message_2 = clean_message_format(message_2, prospect_data['first_name'])
                        
                        message_3 = generate_message_4(prospect_data, message_1)
                        message_3 = clean_message_format(message_3, prospect_data['first_name'])
                        
                        # 4. Envoi Leonar
                        msgs = {
                            'subject': subject_line,
                            'message_1': message_1,
                            'message_2': message_2,
                            'message_3': message_3
                        }
                        
                        success = update_prospect_leonar(token, prospect['_id'], msgs)
                        
                        elapsed = time.time() - start_time
                        if success:
                            save_processed(prospect['_id'])
                            st.success(f"✅ {name} traité ({elapsed:.0f}s)")
                            results.append({'name': name, 'status': 'success'})
                        else:
                            st.error(f"❌ Erreur envoi Leonar pour {name}")
                            results.append({'name': name, 'status': 'error'})
                            
                    except Exception as e:
                        st.error(f"❌ Crash sur {name}: {e}")
                        results.append({'name': name, 'status': 'error'})
                
                progress.progress(1.0)
                st.success(f"🎉 Campagne terminée ! ({len([r for r in results if r['status']=='success'])} succès)")
                st.balloons()

# ========================================
# FOOTER
# ========================================
st.divider()
st.caption("🎯 Icebreaker Generator v3.2 + Leonar | Powered by Claude Sonnet 4")