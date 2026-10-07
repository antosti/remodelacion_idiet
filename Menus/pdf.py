from io import BytesIO

from django.template.loader import render_to_string
from xhtml2pdf import pisa


def render_diet_pdf(client, menu, weeks):
    """PDF (bytes) de la dieta: una pagina A4 apaisada por semana, con las
    tomas en filas y los dias en columnas. `weeks` es la estructura de
    Menus.views._build_diet_weeks."""
    html = render_to_string('pdf/diet.html', {'client': client, 'menu': menu, 'weeks': weeks})
    output = BytesIO()
    result = pisa.CreatePDF(html, dest=output, encoding='utf-8')
    if result.err:
        raise RuntimeError('No se pudo generar el PDF de la dieta.')
    return output.getvalue()


def diet_pdf_filename(client, menu):
    last_name = ''.join(ch for ch in (client.last_name or 'cliente') if ch.isalnum()) or 'cliente'
    return f'dieta_{last_name}_{menu.date_ini:%Y%m%d}.pdf'
