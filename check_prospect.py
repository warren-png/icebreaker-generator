"""
Script pour vérifier les données d'un prospect dans Leonar
"""

import requests
import os
from dotenv import load_dotenv

load_dotenv()

LEONAR_EMAIL = os.getenv("LEONAR_EMAIL")
LEONAR_PASSWORD = os.getenv("LEONAR_PASSWORD")
LEONAR_CAMPAIGN_ID = os.getenv("LEONAR_CAMPAIGN_ID")

# 1. Authentification
response = requests.post(
    'https://dashboard.leonar.app/api/1.1/wf/auth',
    headers={'Content-Type': 'application/json'},
    json={
        "email": LEONAR_EMAIL,
        "password": LEONAR_PASSWORD
    }
)

token = response.json()['response']['token']
print("✅ Token obtenu\n")

# 2. Récupérer les prospects de la campagne
print("🔍 Récupération des prospects de la campagne...\n")

response = requests.get(
    f'https://dashboard.leonar.app/api/1.1/obj/matching?constraints=[{{"key":"campaign","constraint_type":"equals","value":"{LEONAR_CAMPAIGN_ID}"}}]&cursor=0',
    headers={'Authorization': f'Bearer {token}'}
)

if response.status_code != 200:
    print(f"❌ Erreur : {response.text}")
    exit(1)

prospects = response.json()['response']['results']

print(f"📊 Nombre de prospects trouvés : {len(prospects)}\n")
print("=" * 70)

for prospect in prospects:
    print(f"\n👤 {prospect.get('user_full name', 'N/A')}")
    print(f"   LinkedIn : {prospect.get('linkedin_url', 'N/A')}")
    print(f"   Status : {prospect.get('status', 'N/A')}")
    print(f"   ID : {prospect.get('_id', 'N/A')}")
    
    # Afficher TOUS les champs disponibles
    print(f"\n   📋 TOUS LES CHAMPS DISPONIBLES :")
    for key, value in prospect.items():
        if key not in ['_id', 'user_full name', 'linkedin_url', 'status']:
            # Afficher seulement les 100 premiers caractères pour les champs longs
            if isinstance(value, str) and len(value) > 100:
                print(f"   - {key}: {value[:100]}...")
            else:
                print(f"   - {key}: {value}")
    
    print("=" * 70)