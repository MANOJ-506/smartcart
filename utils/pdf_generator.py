from xhtml2pdf import pisa
from io import BytesIO


def generate_pdf(html):

    result = BytesIO()

    pdf = pisa.CreatePDF(
        html,
        dest=result
    )

    if pdf.err:
        return None

    return result.getvalue()