"""
═══════════════════════════════════════════════════════════════════
TESTIMONIAL GENERATOR - Génération de témoignages clients PDF
Format A4 - Design Entourage Recrutement (Noir/Or)
═══════════════════════════════════════════════════════════════════
"""

import io
import os
import json
import anthropic
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Palette
BLACK      = HexColor('#000000')
GOLD       = HexColor('#FFD700')
GRAY_DARK  = HexColor('#555555')
GRAY_LIGHT = HexColor('#F8F9FA')
WHITE      = HexColor('#FFFFFF')
BORDER     = HexColor('#DDDDDD')


# ─────────────────────────────────────────────────────────────────
# ANALYSE IA
# ─────────────────────────────────────────────────────────────────

def analyze_testimonial(q1, q2, q3, poste_recrute, secteur, contexte):
    """
    Utilise Claude pour extraire :
    - titre_principal, titre_surligne
    - citation_choc
    - points_cles (liste de 3)
    """
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    prompt = f"""Tu es expert en communication commerciale pour un cabinet de recrutement.

Voici un témoignage client en 3 questions/réponses :

QUESTION 1 — Contexte et difficultés avant l'intervention :
{q1}

QUESTION 2 — Relation avec le cabinet et qualité des intervenants :
{q2}

QUESTION 3 — Recommandation :
{q3}

Mandat : {poste_recrute} | {secteur} | {contexte}

Génère UNIQUEMENT un JSON valide (sans markdown, sans ```json) :
{{
  "titre_principal": "Titre accrocheur de 5 à 8 mots qui capte l'essence du témoignage",
  "titre_surligne": "2 à 3 mots de la fin du titre à mettre en avant",
  "citation_choc": "Phrase courte et impactante tirée mot pour mot des réponses (20 mots max)",
  "points_cles": [
    "Bénéfice concret 1 en 5-7 mots",
    "Bénéfice concret 2 en 5-7 mots",
    "Bénéfice concret 3 en 5-7 mots"
  ]
}}

RÈGLES :
- La citation doit être authentique, extraite telle quelle du témoignage
- Les points clés sont des bénéfices concrets mesurables ou qualitatifs forts
- Le titre doit donner envie de lire le document"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}]
    )

    text = response.content[0].text.strip()
    # Supprimer d'éventuels blocs markdown
    if "```" in text:
        parts = text.split("```")
        for part in parts:
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            try:
                return json.loads(part)
            except Exception:
                continue
    return json.loads(text)


# ─────────────────────────────────────────────────────────────────
# HELPERS DESSIN
# ─────────────────────────────────────────────────────────────────

def _draw_image_fit(c, img_bytes, x, y, max_w, max_h):
    """Dessine une image depuis bytes, centrée dans la boite max_w x max_h."""
    if not img_bytes:
        return
    try:
        from PIL import Image as PILImage
        pil = PILImage.open(io.BytesIO(img_bytes))
        w_px, h_px = pil.size
        scale = min(max_w / w_px, max_h / h_px)
        w = w_px * scale
        h = h_px * scale
        ir = ImageReader(io.BytesIO(img_bytes))
        c.drawImage(ir,
                    x + (max_w - w) / 2,
                    y + (max_h - h) / 2,
                    width=w, height=h, mask='auto')
    except Exception:
        pass


def _wrap_lines(c, text, font_name, font_size, max_w):
    """Découpe un texte en lignes tenant dans max_w."""
    words = str(text).split()
    lines, current = [], ""
    for word in words:
        test = (current + " " + word).strip()
        if c.stringWidth(test, font_name, font_size) <= max_w:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [""]


def _draw_wrapped(c, text, font_name, font_size, color, x, y, max_w, leading):
    """Dessine un texte avec retour à la ligne. Retourne le y après la dernière ligne."""
    c.setFillColor(color)
    c.setFont(font_name, font_size)
    for line in _wrap_lines(c, text, font_name, font_size, max_w):
        c.drawString(x, y, line)
        y -= leading
    return y


def _draw_sidebar_title(c, title, x, y):
    """Titre de section sidebar avec soulignement or."""
    c.setFillColor(BLACK)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(x, y, title)
    tw = c.stringWidth(title, "Helvetica-Bold", 10)
    c.setStrokeColor(GOLD)
    c.setLineWidth(1.5)
    c.line(x, y - 1.5*mm, x + tw, y - 1.5*mm)
    return y - 7*mm


def _draw_qa_block(c, question, answer, x, y, w):
    """Dessine un bloc Q&A avec préfixe or et barre latérale grise."""
    # Préfixe "Q." en or
    c.setFillColor(GOLD)
    c.setFont("Helvetica-Bold", 9.5)
    c.drawString(x, y, "Q.")
    q_x = x + 7*mm

    # Intitulé de la question
    y = _draw_wrapped(c, question, "Helvetica-Bold", 9.5, BLACK, q_x, y, w - 7*mm, 4.5*mm)
    y -= 2*mm

    # Réponse avec barre latérale
    ans_x = x + 6*mm
    start_y = y
    y = _draw_wrapped(c, answer, "Helvetica", 8.5, GRAY_DARK, ans_x, y, w - 6*mm, 4*mm)

    c.setStrokeColor(BORDER)
    c.setLineWidth(0.8)
    c.line(x + 2.5*mm, y, x + 2.5*mm, start_y + 4*mm)

    return y


def _draw_highlight_box(c, citation, x, y, w):
    """Dessine le bloc citation noir/or."""
    c.setFont("Helvetica-BoldOblique", 10)
    lines = _wrap_lines(c, citation, "Helvetica-BoldOblique", 10, w - 14*mm)
    box_h = len(lines) * 5.5*mm + 10*mm
    box_y = y - box_h

    # Fond noir
    c.setFillColor(BLACK)
    c.roundRect(x, box_y, w, box_h, 4, fill=1, stroke=0)

    # Barre gauche or
    c.setFillColor(GOLD)
    c.rect(x, box_y, 3.5*mm, box_h, fill=1, stroke=0)

    # Texte blanc centré
    ty = y - 5*mm
    for line in lines:
        c.setFillColor(WHITE)
        c.setFont("Helvetica-BoldOblique", 10)
        c.drawCentredString(x + w / 2, ty, line)
        ty -= 5.5*mm

    return box_y


# ─────────────────────────────────────────────────────────────────
# GÉNÉRATION PDF
# ─────────────────────────────────────────────────────────────────

def create_testimonial_pdf(data, logo_entourage_bytes=None, logo_client_bytes=None):
    """
    Génère le PDF témoignage client.

    data = {
        'prenom_nom'    : str,
        'poste_contact' : str,   # titre du contact
        'entreprise'    : str,
        'poste_recrute' : str,
        'secteur'       : str,
        'contexte'      : str,
        'q1_label'      : str,   # intitulé question 1
        'q1'            : str,   # réponse client
        'q2_label'      : str,
        'q2'            : str,
        'q3_label'      : str,
        'q3'            : str,
        'titre_principal': str,
        'titre_surligne' : str,
        'citation_choc'  : str,
        'points_cles'    : list[str],  # 3 items
    }

    Returns: bytes du PDF
    """
    buf = io.BytesIO()
    PAGE_W, PAGE_H = A4

    HEADER_H   = 40 * mm
    GOLD_STRIP = 3  * mm
    FOOTER_H   = 15 * mm
    SIDEBAR_W  = 55 * mm
    ML         = 8  * mm   # marge gauche sidebar
    TW         = SIDEBAR_W - ML - 4*mm  # largeur texte sidebar

    c = canvas.Canvas(buf, pagesize=A4)

    # ── HEADER ────────────────────────────────────────────────────
    c.setFillColor(BLACK)
    c.rect(0, PAGE_H - HEADER_H, PAGE_W, HEADER_H, fill=1, stroke=0)

    c.setFillColor(GOLD)
    c.rect(0, PAGE_H - HEADER_H - GOLD_STRIP, PAGE_W, GOLD_STRIP, fill=1, stroke=0)

    if logo_entourage_bytes:
        _draw_image_fit(c, logo_entourage_bytes,
                        x=15*mm,
                        y=PAGE_H - HEADER_H + (HEADER_H - 18*mm) / 2,
                        max_w=80*mm, max_h=18*mm)

    # Badge "TÉMOIGNAGE CLIENT"
    bw, bh = 44*mm, 10*mm
    bx = PAGE_W - 15*mm - bw
    b_y = PAGE_H - HEADER_H + (HEADER_H - bh) / 2
    c.setStrokeColor(GOLD)
    c.setLineWidth(0.6)
    c.rect(bx, b_y, bw, bh, fill=0, stroke=1)
    c.setFillColor(GOLD)
    c.setFont("Helvetica-Bold", 6.5)
    c.drawCentredString(bx + bw / 2, b_y + 3.5*mm, "TEMOIGNAGE CLIENT")

    # ── FOOTER ────────────────────────────────────────────────────
    c.setFillColor(GRAY_LIGHT)
    c.rect(0, 0, PAGE_W, FOOTER_H, fill=1, stroke=0)
    c.setStrokeColor(BORDER)
    c.setLineWidth(0.5)
    c.line(0, FOOTER_H, PAGE_W, FOOTER_H)
    c.setFillColor(GRAY_DARK)
    c.setFont("Helvetica", 7.5)
    c.drawCentredString(PAGE_W / 2, 5*mm, "Contact : Warren Elbaz  |  entouragerecrutement.com")

    # ── SIDEBAR ───────────────────────────────────────────────────
    CONTENT_TOP = PAGE_H - HEADER_H - GOLD_STRIP
    CONTENT_BOT = FOOTER_H

    c.setFillColor(GRAY_LIGHT)
    c.rect(0, CONTENT_BOT, SIDEBAR_W, CONTENT_TOP - CONTENT_BOT, fill=1, stroke=0)
    c.setStrokeColor(BORDER)
    c.setLineWidth(0.5)
    c.line(SIDEBAR_W, CONTENT_BOT, SIDEBAR_W, CONTENT_TOP)

    sy  = CONTENT_TOP - 10*mm
    CX  = SIDEBAR_W / 2
    R   = 17 * mm

    # Cercle logo client
    cy_c = sy - R
    c.setFillColor(WHITE)
    c.setStrokeColor(GOLD)
    c.setLineWidth(1.5)
    c.circle(CX, cy_c, R, fill=1, stroke=1)

    if logo_client_bytes:
        sz = (R - 2*mm) * 2
        _draw_image_fit(c, logo_client_bytes,
                        x=CX - sz / 2, y=cy_c - sz / 2,
                        max_w=sz, max_h=sz)

    sy = cy_c - R - 5*mm

    # Nom, poste, entreprise
    c.setFillColor(BLACK)
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(CX, sy, data['prenom_nom'])
    sy -= 4*mm

    c.setFillColor(GRAY_DARK)
    c.setFont("Helvetica-Oblique", 7.5)
    c.drawCentredString(CX, sy, data['poste_contact'])
    sy -= 4*mm
    c.drawCentredString(CX, sy, f"chez {data['entreprise']}")
    sy -= 10*mm

    # Bloc "Le Mandat"
    sy = _draw_sidebar_title(c, "Le Mandat", ML, sy)
    for label, val in [
        ("Poste :", data['poste_recrute']),
        ("Secteur :", data['secteur']),
        ("Contexte :", data['contexte']),
    ]:
        c.setFillColor(BLACK)
        c.setFont("Helvetica-Bold", 7.5)
        c.drawString(ML, sy, label)
        sy -= 3.5*mm
        sy = _draw_wrapped(c, val, "Helvetica", 7.5, GRAY_DARK, ML + 2*mm, sy, TW, 3.8*mm)
        sy -= 3*mm

    sy -= 5*mm

    # Bloc "Points Clés"
    sy = _draw_sidebar_title(c, "Points Cles", ML, sy)
    for pt in data['points_cles'][:3]:
        c.setFillColor(GOLD)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(ML, sy, ">")
        sy = _draw_wrapped(c, pt, "Helvetica", 7.5, GRAY_DARK, ML + 5*mm, sy, TW - 5*mm, 3.8*mm)
        sy -= 3.5*mm

    # ── CONTENT BODY ──────────────────────────────────────────────
    BX = SIDEBAR_W + 10*mm
    BW = PAGE_W - SIDEBAR_W - 10*mm - 8*mm
    by = CONTENT_TOP - 10*mm

    # Titre principal
    by = _draw_wrapped(c, data['titre_principal'], "Helvetica-Bold", 20, BLACK, BX, by, BW, 7.5*mm)
    by -= 8*mm

    # Q1
    by = _draw_qa_block(c, data['q1_label'], data['q1'], BX, by, BW)
    by -= 5*mm

    # Q2
    by = _draw_qa_block(c, data['q2_label'], data['q2'], BX, by, BW)
    by -= 5*mm

    # Citation
    by = _draw_highlight_box(c, data['citation_choc'], BX, by, BW)
    by -= 5*mm

    # Q3
    _draw_qa_block(c, data['q3_label'], data['q3'], BX, by, BW)

    c.save()
    buf.seek(0)
    return buf.read()
