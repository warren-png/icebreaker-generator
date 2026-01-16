"""
Scraper universel pour annonces de poste
Supporte : HelloWork, LinkedIn Jobs, Apec
"""

import requests
from bs4 import BeautifulSoup
import re
import time


def scrape_job_posting(url):
    """
    Scrappe une annonce de poste depuis différents job boards
    
    Args:
        url (str): URL de l'annonce
        
    Returns:
        dict: Données de l'annonce ou None si échec/URL vide
    """
    
    # Vérifier si l'URL est vide
    if not url or url.strip() == "":
        print("   ⏭️  Aucune URL d'annonce fournie")
        return None
    
    url = url.strip()
    
    # Déterminer le job board
    if "hellowork.com" in url:
        return scrape_hellowork(url)
    elif "linkedin.com/jobs" in url:
        return scrape_linkedin_job(url)
    elif "apec.fr" in url:
        return scrape_apec(url)
    else:
        print(f"   ⚠️  Job board non supporté : {url}")
        return scrape_generic(url)


def scrape_hellowork(url):
    """Scrappe une annonce HelloWork"""
    print(f"   🔍 Scraping HelloWork...")
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            print(f"   ❌ Erreur HTTP {response.status_code}")
            return None
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extraction HelloWork
        job_data = {
            'source': 'HelloWork',
            'url': url,
            'title': '',
            'company': '',
            'location': '',
            'contract_type': '',
            'description': '',
            'missions': '',
            'profile': '',
            'benefits': ''
        }
        
        # Titre
        title_elem = soup.find('h1', class_='tw-text-3xl') or soup.find('h1')
        if title_elem:
            job_data['title'] = title_elem.get_text(strip=True)
        
        # Entreprise
        company_elem = soup.find('p', class_='tw-text-xl') or soup.find('a', class_='company-name')
        if company_elem:
            job_data['company'] = company_elem.get_text(strip=True)
        
        # Localisation
        location_elem = soup.find('span', string=re.compile('Localisation')) or soup.find('div', class_='location')
        if location_elem:
            parent = location_elem.find_parent()
            if parent:
                job_data['location'] = parent.get_text(strip=True).replace('Localisation', '').strip()
        
        # Type de contrat
        contract_elem = soup.find('span', string=re.compile('Type de contrat')) or soup.find('div', class_='contract-type')
        if contract_elem:
            parent = contract_elem.find_parent()
            if parent:
                job_data['contract_type'] = parent.get_text(strip=True).replace('Type de contrat', '').strip()
        
        # Description complète
        description_elem = soup.find('div', class_='job-description') or soup.find('div', id='description')
        if description_elem:
            job_data['description'] = description_elem.get_text(separator='\n', strip=True)[:3000]
        
        # Missions
        missions_elem = soup.find('h2', string=re.compile('Missions|Vos missions'))
        if missions_elem:
            missions_parent = missions_elem.find_next_sibling()
            if missions_parent:
                job_data['missions'] = missions_parent.get_text(separator='\n', strip=True)[:1500]
        
        # Profil recherché
        profile_elem = soup.find('h2', string=re.compile('Profil|Profil recherché'))
        if profile_elem:
            profile_parent = profile_elem.find_next_sibling()
            if profile_parent:
                job_data['profile'] = profile_parent.get_text(separator='\n', strip=True)[:1500]
        
        print(f"   ✅ Annonce HelloWork extraite : {job_data['title'][:50]}...")
        return job_data
        
    except Exception as e:
        print(f"   ❌ Erreur scraping HelloWork : {e}")
        return None


def scrape_linkedin_job(url):
    """Scrappe une annonce LinkedIn Jobs"""
    print(f"   🔍 Scraping LinkedIn Jobs...")
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            print(f"   ❌ Erreur HTTP {response.status_code}")
            return None
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        job_data = {
            'source': 'LinkedIn Jobs',
            'url': url,
            'title': '',
            'company': '',
            'location': '',
            'contract_type': '',
            'description': '',
            'missions': '',
            'profile': '',
            'benefits': ''
        }
        
        # Titre
        title_elem = soup.find('h1', class_='top-card-layout__title') or soup.find('h1')
        if title_elem:
            job_data['title'] = title_elem.get_text(strip=True)
        
        # Entreprise
        company_elem = soup.find('a', class_='topcard__org-name-link') or soup.find('span', class_='topcard__flavor')
        if company_elem:
            job_data['company'] = company_elem.get_text(strip=True)
        
        # Localisation
        location_elem = soup.find('span', class_='topcard__flavor topcard__flavor--bullet')
        if location_elem:
            job_data['location'] = location_elem.get_text(strip=True)
        
        # Description
        description_elem = soup.find('div', class_='show-more-less-html__markup') or soup.find('div', class_='description__text')
        if description_elem:
            job_data['description'] = description_elem.get_text(separator='\n', strip=True)[:3000]
        
        print(f"   ✅ Annonce LinkedIn extraite : {job_data['title'][:50]}...")
        return job_data
        
    except Exception as e:
        print(f"   ❌ Erreur scraping LinkedIn : {e}")
        return None


def scrape_apec(url):
    """Scrappe une annonce Apec"""
    print(f"   🔍 Scraping Apec...")
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            print(f"   ❌ Erreur HTTP {response.status_code}")
            return None
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        job_data = {
            'source': 'Apec',
            'url': url,
            'title': '',
            'company': '',
            'location': '',
            'contract_type': '',
            'description': '',
            'missions': '',
            'profile': '',
            'benefits': ''
        }
        
        # Titre
        title_elem = soup.find('h1', class_='title') or soup.find('h1')
        if title_elem:
            job_data['title'] = title_elem.get_text(strip=True)
        
        # Entreprise
        company_elem = soup.find('span', class_='company-name') or soup.find('h2', class_='company')
        if company_elem:
            job_data['company'] = company_elem.get_text(strip=True)
        
        # Localisation
        location_elem = soup.find('li', class_='location') or soup.find('span', class_='location')
        if location_elem:
            job_data['location'] = location_elem.get_text(strip=True)
        
        # Type de contrat
        contract_elem = soup.find('li', string=re.compile('CDI|CDD|Intérim'))
        if contract_elem:
            job_data['contract_type'] = contract_elem.get_text(strip=True)
        
        # Description
        description_elem = soup.find('div', class_='offre-description') or soup.find('div', class_='description')
        if description_elem:
            job_data['description'] = description_elem.get_text(separator='\n', strip=True)[:3000]
        
        # Missions
        missions_section = soup.find('h3', string=re.compile('Mission|Missions'))
        if missions_section:
            missions_content = missions_section.find_next_sibling()
            if missions_content:
                job_data['missions'] = missions_content.get_text(separator='\n', strip=True)[:1500]
        
        # Profil
        profile_section = soup.find('h3', string=re.compile('Profil'))
        if profile_section:
            profile_content = profile_section.find_next_sibling()
            if profile_content:
                job_data['profile'] = profile_content.get_text(separator='\n', strip=True)[:1500]
        
        print(f"   ✅ Annonce Apec extraite : {job_data['title'][:50]}...")
        return job_data
        
    except Exception as e:
        print(f"   ❌ Erreur scraping Apec : {e}")
        return None


def scrape_generic(url):
    """
    Scraping générique pour job boards non supportés
    Tente d'extraire les informations de base
    """
    print(f"   🔍 Scraping générique...")
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            print(f"   ❌ Erreur HTTP {response.status_code}")
            return None
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        job_data = {
            'source': 'Generic',
            'url': url,
            'title': '',
            'company': '',
            'location': '',
            'contract_type': '',
            'description': '',
            'missions': '',
            'profile': '',
            'benefits': ''
        }
        
        # Titre (chercher le premier h1)
        title_elem = soup.find('h1')
        if title_elem:
            job_data['title'] = title_elem.get_text(strip=True)
        
        # Description (chercher les paragraphes)
        paragraphs = soup.find_all('p')
        if paragraphs:
            description_text = '\n'.join([p.get_text(strip=True) for p in paragraphs[:10]])
            job_data['description'] = description_text[:3000]
        
        print(f"   ⚠️  Extraction générique (limitée)")
        return job_data
        
    except Exception as e:
        print(f"   ❌ Erreur scraping générique : {e}")
        return None


def format_job_data_for_prompt(job_data):
    """
    Formate les données de l'annonce pour le prompt Claude
    """
    if not job_data:
        return ""
    
    formatted = f"""
📋 ANNONCE DE POSTE ({job_data.get('source', 'N/A')})

Titre : {job_data.get('title', 'N/A')}
Entreprise : {job_data.get('company', 'N/A')}
Localisation : {job_data.get('location', 'N/A')}
Type de contrat : {job_data.get('contract_type', 'N/A')}

MISSIONS / DESCRIPTION :
{job_data.get('missions', job_data.get('description', 'N/A'))[:1500]}

PROFIL RECHERCHÉ :
{job_data.get('profile', 'N/A')[:1000]}
"""
    
    return formatted.strip()


# Test unitaire
if __name__ == "__main__":
    print("Test du scraper d'annonces\n")
    
    # Test avec URL vide
    print("Test 1 : URL vide")
    result = scrape_job_posting("")
    print(f"Résultat : {result}\n")
    
    # Test HelloWork
    print("Test 2 : HelloWork (exemple)")
    test_url = "https://www.hellowork.com/fr-fr/emplois/exemple.html"
    result = scrape_job_posting(test_url)
    print(f"Résultat : {result is not None}\n")