"""
Script pour lister vos campagnes Leonar et trouver le CAMPAIGN_ID
"""

import requests
import os
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

LEONAR_EMAIL = os.getenv("LEONAR_EMAIL")
LEONAR_PASSWORD = os.getenv("LEONAR_PASSWORD")

if not LEONAR_EMAIL or not LEONAR_PASSWORD:
    print("❌ LEONAR_EMAIL et LEONAR_PASSWORD requis dans .env")
    exit(1)

print("🔐 Authentification Leonar...\n")

# 1. Authentification
response = requests.post(
    'https://dashboard.leonar.app/api/1.1/wf/auth',
    headers={'Content-Type': 'application/json'},
    json={
        "email": LEONAR_EMAIL,
        "password": LEONAR_PASSWORD
    }
)

if response.status_code != 200:
    print(f"❌ Erreur authentification : {response.text}")
    exit(1)

token = response.json()['response']['token']
print(f"✅ Token obtenu\n")

# 2. Liste des campagnes
print("📋 RÉCUPÉRATION DE VOS CAMPAGNES...\n")

response = requests.get(
    'https://dashboard.leonar.app/api/1.1/obj/campaign?cursor=0',
    headers={'Authorization': f'Bearer {token}'}
)

if response.status_code != 200:
    print(f"❌ Erreur : {response.text}")
    exit(1)

campaigns = response.json()['response']['results']

print("=" * 70)
print("VOS CAMPAGNES LEONAR")
print("=" * 70 + "\n")

for i, campaign in enumerate(campaigns, 1):
    campaign_name = campaign.get('campaign_name', 'Sans nom')
    campaign_id = campaign['_id']
    status = campaign.get('status', 'N/A')
    
    print(f"{i}. {campaign_name}")
    print(f"   ID     : {campaign_id}")
    print(f"   Statut : {status}")
    print("-" * 70)

print("\n💡 COPIEZ l'ID de votre campagne active et ajoutez-le dans .env :")
print("   LEONAR_CAMPAIGN_ID=votre_id_ici\n")