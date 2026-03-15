"""Generate invoice PDFs using fpdf2."""
import io
from typing import Optional
from fpdf import FPDF


# Seller details
SELLER_NAME = "Aardvark Hosting"
SELLER_ADDRESS_1 = ""  # Fill in your address
SELLER_CITY = ""
SELLER_POSTAL = ""
SELLER_COUNTRY = "Netherlands"
SELLER_VAT = "NL001778406B98"
SELLER_EMAIL = "support@opaloptics.com"
SELLER_KVK = ""  # Chamber of Commerce number, fill in if needed


class InvoicePDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 20)
        self.set_text_color(8, 11, 22)
        self.cell(0, 10, "INVOICE", ln=True, align="R")
        self.ln(2)

    def footer(self):
        self.set_y(-25)
        self.set_font("Helvetica", "", 7)
        self.set_text_color(120, 120, 120)
        self.cell(0, 4, f"{SELLER_NAME}  |  VAT: {SELLER_VAT}", ln=True, align="C")
        self.cell(0, 4, SELLER_EMAIL, ln=True, align="C")


def generate_invoice_pdf(invoice: dict) -> bytes:
    """Generate a PDF invoice and return as bytes."""
    pdf = InvoicePDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=30)

    # ── Seller block (left) + Invoice details (right) ──
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(8, 11, 22)
    y_start = pdf.get_y()

    # Seller (left column)
    pdf.cell(95, 5, SELLER_NAME, ln=True)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(80, 80, 80)
    if SELLER_ADDRESS_1:
        pdf.cell(95, 4, SELLER_ADDRESS_1, ln=True)
    if SELLER_CITY:
        pdf.cell(95, 4, f"{SELLER_POSTAL} {SELLER_CITY}", ln=True)
    pdf.cell(95, 4, SELLER_COUNTRY, ln=True)
    pdf.cell(95, 4, f"VAT: {SELLER_VAT}", ln=True)
    y_after_seller = pdf.get_y()

    # Invoice details (right column)
    pdf.set_y(y_start)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(80, 80, 80)

    details = [
        ("Invoice #:", invoice["invoice_number"]),
        ("Date:", _format_date(invoice.get("issued_at", ""))),
        ("Currency:", invoice.get("currency", "EUR")),
    ]
    for label, value in details:
        pdf.set_x(120)
        pdf.set_font("Helvetica", "", 8)
        pdf.cell(25, 4, label)
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(45, 4, str(value), ln=True)

    pdf.set_y(max(y_after_seller, pdf.get_y()) + 8)

    # ── Bill To ──
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(8, 11, 22)
    pdf.cell(0, 5, "Bill To:", ln=True)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(60, 60, 60)

    if invoice.get("buyer_company"):
        pdf.cell(0, 4, invoice["buyer_company"], ln=True)
    if invoice.get("buyer_name"):
        pdf.cell(0, 4, invoice["buyer_name"], ln=True)
    if invoice.get("buyer_address_line1"):
        pdf.cell(0, 4, invoice["buyer_address_line1"], ln=True)
    if invoice.get("buyer_address_line2"):
        pdf.cell(0, 4, invoice["buyer_address_line2"], ln=True)
    postal_city = " ".join(filter(None, [invoice.get("buyer_postal_code"), invoice.get("buyer_city")]))
    if postal_city:
        pdf.cell(0, 4, postal_city, ln=True)
    if invoice.get("buyer_country"):
        pdf.cell(0, 4, _country_name(invoice["buyer_country"]), ln=True)
    if invoice.get("buyer_vat_number"):
        pdf.cell(0, 4, f"VAT: {invoice['buyer_vat_number']}", ln=True)
    if invoice.get("buyer_email"):
        pdf.cell(0, 4, invoice["buyer_email"], ln=True)

    pdf.ln(10)

    # ── Line items table ──
    pdf.set_fill_color(245, 245, 250)
    pdf.set_text_color(60, 60, 60)
    pdf.set_font("Helvetica", "B", 8)

    col_w = [95, 30, 30, 35]
    headers = ["Description", "Qty", "Unit Price", "Amount"]
    for i, h in enumerate(headers):
        align = "L" if i == 0 else "R"
        pdf.cell(col_w[i], 7, h, border=0, align=align, fill=True)
    pdf.ln()

    # Divider
    pdf.set_draw_color(200, 200, 210)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(2)

    # Line item
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(30, 30, 30)
    description = invoice.get("description", "Opal tokens")
    net = invoice.get("amount_net_cents", 0)

    pdf.cell(col_w[0], 6, description, align="L")
    pdf.cell(col_w[1], 6, "1", align="R")
    pdf.cell(col_w[2], 6, _fmt_money(net, invoice.get("currency", "EUR")), align="R")
    pdf.cell(col_w[3], 6, _fmt_money(net, invoice.get("currency", "EUR")), align="R")
    pdf.ln()

    pdf.ln(3)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(4)

    # ── Totals ──
    x_label = 130
    x_value = 165

    def _total_row(label: str, amount: int, bold: bool = False):
        pdf.set_font("Helvetica", "B" if bold else "", 9)
        pdf.set_x(x_label)
        pdf.cell(35, 6, label, align="R")
        pdf.cell(35, 6, _fmt_money(amount, invoice.get("currency", "EUR")), align="R")
        pdf.ln()

    _total_row("Subtotal:", net)

    vat_rate = invoice.get("vat_rate", 0)
    vat_cents = invoice.get("vat_amount_cents", 0)
    if vat_rate and vat_cents:
        _total_row(f"VAT ({vat_rate:.0f}%):", vat_cents)
    elif invoice.get("vat_reverse_charged"):
        pdf.set_font("Helvetica", "", 8)
        pdf.set_x(x_label)
        pdf.cell(35, 6, "VAT (0%):", align="R")
        pdf.cell(35, 6, _fmt_money(0, invoice.get("currency", "EUR")), align="R")
        pdf.ln()
    elif invoice.get("vat_exempt_reason"):
        pdf.set_font("Helvetica", "", 8)
        pdf.set_x(x_label)
        pdf.cell(35, 6, "VAT (0%):", align="R")
        pdf.cell(35, 6, _fmt_money(0, invoice.get("currency", "EUR")), align="R")
        pdf.ln()

    pdf.ln(1)
    pdf.line(x_label, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(2)
    _total_row("Total:", invoice.get("amount_total_cents", net + vat_cents), bold=True)

    # ── VAT note ──
    if invoice.get("vat_reverse_charged"):
        pdf.ln(8)
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(100, 100, 100)
        pdf.multi_cell(0, 4, "VAT reverse-charged per Article 196 EU VAT Directive. "
                       "The recipient is liable for the payment of VAT.")
    elif invoice.get("vat_exempt_reason") and not vat_cents:
        pdf.ln(8)
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(100, 100, 100)
        pdf.multi_cell(0, 4, invoice["vat_exempt_reason"])

    # Return bytes
    buf = io.BytesIO()
    pdf.output(buf)
    return buf.getvalue()


def _fmt_money(cents: int, currency: str = "EUR") -> str:
    symbol = {"EUR": "\u20ac", "USD": "$", "GBP": "\u00a3"}.get(currency, currency + " ")
    return f"{symbol}{cents / 100:.2f}"


def _format_date(iso: str) -> str:
    if not iso:
        return ""
    return iso[:10] if "T" in iso else iso[:10]


_COUNTRY_NAMES = {
    "NL": "Netherlands", "DE": "Germany", "FR": "France", "BE": "Belgium",
    "AT": "Austria", "IT": "Italy", "ES": "Spain", "PT": "Portugal",
    "IE": "Ireland", "GB": "United Kingdom", "CH": "Switzerland",
    "SE": "Sweden", "DK": "Denmark", "NO": "Norway", "FI": "Finland",
    "PL": "Poland", "CZ": "Czechia", "US": "United States", "CA": "Canada",
    "TR": "Turkey",
}


def _country_name(code: Optional[str]) -> str:
    if not code:
        return ""
    return _COUNTRY_NAMES.get(code.upper(), code.upper())
