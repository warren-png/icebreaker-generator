"""Test avec un seul prospect"""
from icebreaker_v2 import *

print("\n" + "="*80)
print("🧪 TEST - UN SEUL PROSPECT")
print("="*80 + "\n")

try:
    sheet = connect_to_google_sheet()
    apify_client = init_apify_client()
    
    prospects = get_prospects(sheet)
    
    if not prospects:
        print("✨ Aucun prospect à traiter (tous ont déjà un icebreaker)")
        print("💡 Effacez le contenu de la colonne K pour un prospect pour le tester à nouveau")
    else:
        # Prendre UNIQUEMENT le premier prospect
        prospect = prospects[0]
        
        print(f"\n{'='*80}")
        print(f"TEST PROSPECT : {prospect['first_name']} {prospect['last_name']}")
        print(f"Entreprise : {prospect['company']}")
        print(f"LinkedIn : {prospect['linkedin_url']}")
        print(f"{'='*80}\n")
        
        # Demander confirmation
        response = input("⚠️  Voulez-vous continuer ? (o/n) : ")
        if response.lower() != 'o':
            print("❌ Test annulé")
            exit()
        
        print("\n🚀 Lancement du processus...\n")
        
        # 1. URL LinkedIn
        if not prospect['linkedin_url']:
            print("⚠️  Aucune URL LinkedIn fournie, estimation...")
            linkedin_url = search_linkedin_profile(
                prospect['first_name'],
                prospect['last_name'],
                prospect['company']
            )
        else:
            linkedin_url = prospect['linkedin_url']
            print(f"🔗 URL LinkedIn : {linkedin_url}\n")
        
        # 2. Scraping LinkedIn
        profile_data = scrape_linkedin_profile(apify_client, linkedin_url)
        time.sleep(3)
        
        posts_data = scrape_linkedin_posts(apify_client, linkedin_url)
        time.sleep(3)
        
        company_posts = scrape_company_posts(apify_client, prospect['company'])
        time.sleep(3)
        
        company_profile = scrape_company_profile(apify_client, prospect['company'])
        time.sleep(3)
        
        # 3. Recherche Web
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
        
        # 4. Extraction des hooks
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
        
        print("\n" + "="*80)
        print("📊 HOOKS EXTRAITS")
        print("="*80)
        print(hooks_json)
        print("="*80 + "\n")
        
        # 5. Génération icebreaker
        icebreaker = generate_advanced_icebreaker(prospect, hooks_json)
        
        print("\n" + "="*80)
        print("💬 ICEBREAKER GÉNÉRÉ")
        print("="*80)
        print(icebreaker)
        print("="*80 + "\n")
        
        # 6. Mise à jour Google Sheet
        response = input("💾 Sauvegarder dans Google Sheets ? (o/n) : ")
        if response.lower() == 'o':
            update_sheet(sheet, prospect['row_number'], linkedin_url, hooks_json, icebreaker)
            print("\n✅ Sauvegardé !")
        else:
            print("\n⏭️  Non sauvegardé")
        
        print("\n" + "="*80)
        print("✅ TEST TERMINÉ AVEC SUCCÈS !")
        print("="*80 + "\n")
        
except Exception as e:
    print(f"\n❌ ERREUR : {e}")
    import traceback
    traceback.print_exc()