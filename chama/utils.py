from io import BytesIO
from django.http import HttpResponse
from django.template.loader import get_template

# We will use xhtml2pdf to render the PDF.
# If you don't have it, install with: pip install xhtml2pdf
# Then, make sure to add it to requirements.txt
from xhtml2pdf import pisa


def render_to_pdf(template_src, context_dict={}):
    template = get_template(template_src)
    html  = template.render(context_dict)
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("ISO-8859-1")), result)
    if not pdf.err:
        return HttpResponse(result.getvalue(), content_type='application/pdf')
    return None