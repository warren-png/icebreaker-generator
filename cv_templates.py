"""
═══════════════════════════════════════════════════════════════════
CV TEMPLATES - 3 designs différents pour éviter la répétition
═══════════════════════════════════════════════════════════════════
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.lib.enums import TA_LEFT, TA_JUSTIFY
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Frame, PageTemplate
from reportlab.lib.colors import HexColor, white
import random
import io


# ========================================
# TEMPLATE 1 : CLASSIQUE 1 COLONNE
# ========================================

def create_cv_template_classic(cv_data, output_path=None):
    """
    Template classique 1 colonne - Sobre et professionnel
    """
    
    # Si output_path est None, créer en mémoire
    if output_path is None:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4,
                               topMargin=2*cm, bottomMargin=2*cm,
                               leftMargin=2*cm, rightMargin=2*cm)
    else:
        doc = SimpleDocTemplate(output_path, pagesize=A4,
                               topMargin=2*cm, bottomMargin=2*cm,
                               leftMargin=2*cm, rightMargin=2*cm)
    
    # Couleurs
    PRIMARY = HexColor('#2c3e50')
    ACCENT = HexColor('#3498db')
    GRAY = HexColor('#7f8c8d')
    
    # Styles
    styles = getSampleStyleSheet()
    
    nom_style = ParagraphStyle('Nom', parent=styles['Heading1'], fontSize=18, 
                               textColor=PRIMARY, spaceAfter=2*mm)
    titre_style = ParagraphStyle('Titre', parent=styles['Normal'], fontSize=12, 
                                 textColor=ACCENT, fontName='Helvetica-Bold', spaceAfter=5*mm)
    section_style = ParagraphStyle('Section', parent=styles['Heading2'], fontSize=11, 
                                   textColor=PRIMARY, fontName='Helvetica-Bold', spaceAfter=3*mm, spaceBefore=5*mm)
    poste_style = ParagraphStyle('Poste', parent=styles['Normal'], fontSize=10, 
                                 fontName='Helvetica-Bold', spaceAfter=1*mm)
    entreprise_style = ParagraphStyle('Entreprise', parent=styles['Normal'], fontSize=9, 
                                      textColor=GRAY, spaceAfter=2*mm)
    bullet_style = ParagraphStyle('Bullet', parent=styles['Normal'], fontSize=9, 
                                  leading=12, leftIndent=5*mm, spaceAfter=2*mm)
    body_style = ParagraphStyle('Body', parent=styles['Normal'], fontSize=9, 
                                leading=12, spaceAfter=2*mm)
    
    # Contenu
    story = []
    
    # Header
    story.append(Paragraph('PROFIL ANONYME', nom_style))
    story.append(Paragraph(cv_data['metadata']['job_title'].upper(), titre_style))
    
    profil_info = cv_data['profil']
    story.append(Paragraph(
        f"{profil_info['age']} ans • {profil_info['localisation']} • {profil_info['mobilite']}", 
        body_style
    ))
    story.append(Spacer(1, 3*mm))
    
    # Profil
    story.append(Paragraph('PROFIL', section_style))
    story.append(Paragraph(cv_data['profil_text'], body_style))
    story.append(Spacer(1, 3*mm))
    
    # Expériences
    story.append(Paragraph('EXPÉRIENCES PROFESSIONNELLES', section_style))
    
    for exp in cv_data['experiences']:
        story.append(Paragraph(
            f"{exp['titre']} <font color='#7f8c8d'>• {exp['dates']}</font>", 
            poste_style
        ))
        story.append(Paragraph(f"{exp['entreprise']} • {exp['lieu']}", entreprise_style))
        
        for mission in exp['missions']:
            story.append(Paragraph(f"• {mission}", bullet_style))
        
        story.append(Spacer(1, 3*mm))
    
    # Formation
    story.append(Paragraph('FORMATION', section_style))
    for form in cv_data['formation']:
        story.append(Paragraph(
            f"{form['diplome']} • {form['ecole']} • {form['annees']}", 
            body_style
        ))
    story.append(Spacer(1, 3*mm))
    
    # Compétences
    story.append(Paragraph('COMPÉTENCES TECHNIQUES', section_style))
    story.append(Paragraph(cv_data['competences']['techniques'], body_style))
    story.append(Spacer(1, 2*mm))
    
    # Langues
    story.append(Paragraph('LANGUES', section_style))
    story.append(Paragraph(cv_data['competences']['langues'], body_style))
    
    # Build
    doc.build(story)
    
    if output_path is None:
        return buffer.getvalue()
    else:
        return output_path


# ========================================
# TEMPLATE 2 : 2 COLONNES
# ========================================

def create_cv_template_two_columns(cv_data, output_path=None):
    """
    Template 2 colonnes - Moderne avec colonne gauche foncée
    """
    
    if output_path is None:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0, bottomMargin=0, 
                               leftMargin=0, rightMargin=0)
    else:
        doc = SimpleDocTemplate(output_path, pagesize=A4, topMargin=0, bottomMargin=0, 
                               leftMargin=0, rightMargin=0)
    
    # Couleurs
    DARK_TEAL = HexColor('#1a4d4d')
    LIGHT_BLUE = HexColor('#5eb8c5')
    TEXT_WHITE = white
    TEXT_DARK = HexColor('#333333')
    
    # Styles colonnes (code similaire au CV qu'on a créé avant)
    # [...]
    # Simplifié pour l'exemple - utiliser le code complet du CV 2 colonnes précédent
    
    # Pour l'instant, fallback sur template 1
    return create_cv_template_classic(cv_data, output_path)


# ========================================
# TEMPLATE 3 : TIMELINE
# ========================================

def create_cv_template_timeline(cv_data, output_path=None):
    """
    Template timeline - Design moderne avec années en gros
    """
    
    # Pour l'instant, fallback sur template 1
    return create_cv_template_classic(cv_data, output_path)


# ========================================
# SÉLECTEUR DE TEMPLATE
# ========================================

AVAILABLE_TEMPLATES = {
    'classic': create_cv_template_classic,
    'two_columns': create_cv_template_two_columns,
    'timeline': create_cv_template_timeline
}


def create_cv_pdf(cv_data, template_name=None, output_path=None):
    """
    Crée un PDF avec le template choisi (ou aléatoire)
    
    Args:
        cv_data: Dict avec le contenu du CV
        template_name: 'classic', 'two_columns', 'timeline' ou None (aléatoire)
        output_path: Chemin de sortie ou None pour retourner bytes
    
    Returns:
        bytes si output_path=None, sinon chemin du fichier
    """
    
    # Choisir template
    if template_name is None or template_name not in AVAILABLE_TEMPLATES:
        template_name = random.choice(list(AVAILABLE_TEMPLATES.keys()))
    
    template_func = AVAILABLE_TEMPLATES[template_name]
    
    # Générer
    return template_func(cv_data, output_path)
