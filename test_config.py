"""Test de la configuration"""
from config import check_api_keys, ANTHROPIC_API_KEY, APIFY_API_TOKEN, SERPER_API_KEY

print("🧪 Test de la configuration...\n")

try:
    check_api_keys()
    print("\n✅ Configuration OK ! Toutes les clés sont présentes.")
    print(f"\n   Clé Anthropic : {ANTHROPIC_API_KEY[:20]}...")
    print(f"   Token Apify : {APIFY_API_TOKEN[:20]}...")
    print(f"   Clé Serper : {SERPER_API_KEY[:20]}...")
except ValueError as e:
    print(f"\n❌ {e}")
except Exception as e:
    print(f"\n❌ Erreur : {e}")
    import traceback
    traceback.print_exc()