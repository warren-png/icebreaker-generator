"""
Script d'automatisation pour générer des icebreakers personnalisés
Version simplifiée pour débutants
"""

import gspread
from oauth2client.service_account import ServiceAccountCredentials
import anthropic
from config import *
import time
import json

# ========================================
# PARTIE 1 : CONNEXION À GOOGLE SHEETS
# ========================================

def connect_to_google_sheet():
    """
    Se connecte à Google Sheets et retourne la feuille de calcul
    """
    print("📊 Connexion à Google Sheets...")
    
    # Définir les permissions nécessaires
    scope = [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/drive'
    ]
    
    # Se connecter avec les identifiants
    credentials = ServiceAccountCredentials.from_json_keyfile_name(
        GOOGLE_CREDENTIALS_FILE, 
        scope
    )
    client = gspread.authorize(credentials)
    
    # Ouvrir la feuille
    sheet = client.open(GOOGLE_SHEET_NAME).worksheet(WORKSHEET_NAME)
    
    print("✅ Connecté avec succès !\n")
    return sheet


# ========================================
# PARTIE 2 : RÉCUPÉRER LES PROSPECTS
# ========================================

def get_prospects(sheet):
    """
    Récupère tous les prospects qui n'ont pas encore d'icebreaker
    """
    print("🔍 Recherche des prospects à traiter...")
    
    # Récupérer toutes les données
    all_data = sheet.get_all_records()
    
    # Filtrer les prospects sans icebreaker
    prospects_to_process = []
    for index, row in enumerate(all_data, start=2):  # start=2 car ligne 1 = headers
        if not row.get('icebreaker'):  # Si pas d'icebreaker
            prospects_to_process.append({
                'row_number': index,
                'first_name': row.get('first_name', ''),
                'last_name': row.get('last_name', ''),
                'company': row.get('company', ''),
                'data': row
            })
    
    print(f"📋 {len(prospects_to_process)} prospect(s) à traiter\n")
    return prospects_to_process


# ========================================
# PARTIE 3 : RECHERCHE D'INFORMATIONS
# ========================================

def search_linkedin_profile(first_name, last_name, company):
    """
    Simule une recherche LinkedIn (version simplifiée sans API payante)
    Dans la vraie version, on utiliserait une API de scraping
    """
    print(f"🔎 Recherche du profil LinkedIn de {first_name} {last_name}...")
    
    # Pour l'instant, on construit juste l'URL probable
    # Dans une version complète, on utiliserait l'API Serper ou similaire
    linkedin_url = f"https://www.linkedin.com/in/{first_name.lower()}-{last_name.lower()}"
    
    print(f"   URL estimé : {linkedin_url}\n")
    return linkedin_url


def get_company_info(company_name):
    """
    Récupère des informations sur l'entreprise
    Version simplifiée - utilise Claude pour faire une recherche
    """
    print(f"🏢 Recherche d'informations sur {company_name}...")
    
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    prompt = f"""Tu es un assistant de recherche. Donne-moi des informations basiques sur l'entreprise "{company_name}".

Format ta réponse en JSON avec ces champs :
- sector: le secteur d'activité
- notable_facts: 2-3 faits notables récents (événements, produits, succès)
- recent_events: événements récents (webinaires, conférences, masterclass)

Si tu ne trouves pas d'information, mets "Non trouvé" pour chaque champ.
Réponds UNIQUEMENT avec le JSON, sans texte avant ou après."""

    try:
        message = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        response_text = message.content[0].text
        print(f"   Informations trouvées ✓\n")
        
        return response_text
    except Exception as e:
        print(f"   ⚠️ Erreur lors de la recherche : {e}\n")
        return json.dumps({
            "sector": "Non trouvé",
            "notable_facts": "Non trouvé",
            "recent_events": "Non trouvé"
        })


# ========================================
# PARTIE 4 : GÉNÉRATION DE L'ICEBREAKER
# ========================================

def generate_icebreaker(prospect_data, company_info):
    """
    Génère un icebreaker personnalisé avec Claude
    """
    print(f"✍️  Génération de l'icebreaker pour {prospect_data['first_name']}...")
    
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    prompt = f"""Tu es un expert en copywriting et prospection commerciale.

INFORMATIONS SUR LE PROSPECT :
- Nom : {prospect_data['first_name']} {prospect_data['last_name']}
- Entreprise : {prospect_data['company']}
- Informations collectées : {company_info}

INFORMATIONS SUR NOTRE ENTREPRISE :
- Nom : {COMPANY_INFO['name']}
- Description : {COMPANY_INFO['description']}
- Proposition de valeur : {COMPANY_INFO['value_proposition']}

MISSION :
Rédige un message d'approche (icebreaker) personnalisé pour contacter ce prospect sur LinkedIn.

INSTRUCTIONS :
1. Commence par une accroche personnalisée basée sur les informations du prospect
2. Fais un lien naturel avec notre proposition de valeur
3. Termine par une question ouverte pour démarrer la conversation
4. Ton : professionnel mais chaleureux, pas trop commercial
5. Longueur : 50-80 mots maximum

RÈGLES :
- N'invente RIEN, base-toi uniquement sur les informations fournies
- Si tu manques d'infos, fais une approche plus générique mais personnalisée
- Utilise le prénom du prospect
- Pas de formule de politesse finale (pas de "cordialement", etc.)

Réponds UNIQUEMENT avec le message, sans introduction."""

    try:
        message = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )
        
        icebreaker = message.content[0].text.strip()
        print(f"   ✅ Icebreaker généré !\n")
        
        return icebreaker
    except Exception as e:
        print(f"   ❌ Erreur lors de la génération : {e}\n")
        return f"Erreur : Impossible de générer l'icebreaker"


# ========================================
# PARTIE 5 : MISE À JOUR DU GOOGLE SHEET
# ========================================

def update_sheet(sheet, row_number, linkedin_url, company_info, icebreaker):
    """
    Met à jour la ligne du prospect dans Google Sheets
    """
    print(f"💾 Mise à jour de la ligne {row_number}...")
    
    # Les colonnes correspondent à : D, E, F, G, H, I, J, K
    # D = linkedin_url, K = icebreaker, etc.
    
    try:
        # Extraire les infos de company_info si c'est du JSON
        try:
            info = json.loads(company_info)
            sector = info.get('sector', 'Non trouvé')
            notable_facts = info.get('notable_facts', 'Non trouvé')
            events = info.get('recent_events', 'Non trouvé')
        except:
            sector = 'Non trouvé'
            notable_facts = str(company_info)[:200] if company_info else 'Non trouvé'
            events = 'Non trouvé'
        
        # Mettre à jour chaque colonne
        sheet.update_cell(row_number, 4, linkedin_url)  # Colonne D
        sheet.update_cell(row_number, 5, sector)  # Colonne E
        sheet.update_cell(row_number, 7, str(notable_facts)[:500])  # Colonne G
        sheet.update_cell(row_number, 10, str(events)[:500])  # Colonne J
        sheet.update_cell(row_number, 11, icebreaker)  # Colonne K
        
        print(f"   ✅ Ligne {row_number} mise à jour avec succès !\n")
        
    except Exception as e:
        print(f"   ❌ Erreur lors de la mise à jour : {e}\n")


# ========================================
# PARTIE 6 : FONCTION PRINCIPALE
# ========================================

def main():
    """
    Fonction principale qui orchestre tout le processus
    """
    print("\n" + "="*60)
    print("🚀 DÉMARRAGE DE L'AUTOMATISATION ICEBREAKER")
    print("="*60 + "\n")
    
    try:
        # 1. Connexion à Google Sheets
        sheet = connect_to_google_sheet()
        
        # 2. Récupérer les prospects à traiter
        prospects = get_prospects(sheet)
        
        if not prospects:
            print("✨ Aucun prospect à traiter. Tout est à jour !")
            return
        
        # 3. Traiter chaque prospect
        for i, prospect in enumerate(prospects, 1):
            print(f"\n{'─'*60}")
            print(f"TRAITEMENT DU PROSPECT {i}/{len(prospects)}")
            print(f"{'─'*60}\n")
            
            # 3.1 Rechercher le profil LinkedIn
            linkedin_url = search_linkedin_profile(
                prospect['first_name'],
                prospect['last_name'],
                prospect['company']
            )
            
            # 3.2 Récupérer les infos de l'entreprise
            company_info = get_company_info(prospect['company'])
            
            # Petit délai pour éviter de surcharger les APIs
            time.sleep(2)
            
            # 3.3 Générer l'icebreaker
            icebreaker = generate_icebreaker(prospect, company_info)
            
            # 3.4 Mettre à jour le Google Sheet
            update_sheet(
                sheet,
                prospect['row_number'],
                linkedin_url,
                company_info,
                icebreaker
            )
            
            # Délai entre chaque prospect
            if i < len(prospects):
                print(f"⏳ Pause de {DELAY_BETWEEN_PROSPECTS} secondes avant le prochain prospect...\n")
                time.sleep(DELAY_BETWEEN_PROSPECTS)
        
        print("\n" + "="*60)
        print("✅ AUTOMATISATION TERMINÉE AVEC SUCCÈS !")
        print("="*60 + "\n")
        print(f"📊 {len(prospects)} prospect(s) traité(s)")
        print("💡 Consultez votre Google Sheet pour voir les résultats\n")
        
    except Exception as e:
        print(f"\n❌ ERREUR : {e}")
        print("💡 Vérifiez votre configuration et réessayez\n")


# ========================================
# POINT D'ENTRÉE DU SCRIPT
# ========================================

if __name__ == "__main__":
    main()