from functools import wraps
from flask import session, redirect, url_for, flash
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from datetime import datetime
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import sqlite3
from io import BytesIO
from reportlab.lib.units import inch

def get_db_connection():
    conn = sqlite3.connect("finance.db")
    conn.row_factory = sqlite3.Row
    return conn



def build_transaction_pdf(transactions, filename, total_income=0, total_expenses=0, balance=0):
    """
    Build a professional-looking financial report PDF
    
    Args:
        transactions: List of transaction dictionaries
        filename: Path where PDF will be saved
        total_income: Total income amount
        total_expenses: Total expenses amount
        balance: Net balance
    """
    try:
        # Create PDF document
        pdf = SimpleDocTemplate(
            filename,
            pagesize=letter,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch,
            title="Financial Report"
        )
        
        elements = []
        styles = getSampleStyleSheet()
        
        # Define custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=28,
            textColor=colors.HexColor("#0d6efd"),
            spaceAfter=6,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        subtitle_style = ParagraphStyle(
            'Subtitle',
            parent=styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor("#64748b"),
            spaceAfter=20,
            alignment=TA_CENTER,
            fontName='Helvetica'
        )
        
        section_style = ParagraphStyle(
            'SectionHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor("#1e293b"),
            spaceAfter=12,
            spaceBefore=12,
            fontName='Helvetica-Bold'
        )
        
        # HEADER SECTION
        elements.append(Paragraph(
            f"Financial Report - {datetime.now().strftime('%B %d, %Y')}",
            subtitle_style
        ))
        elements.append(Spacer(1, 12))
        
        # FINANCIAL SUMMARY SECTION
        elements.append(Paragraph("Financial Summary", section_style))
        
        # Summary cards style
        summary_data = [
            ["Metric", "Amount"],
            ["Total Income", f"${total_income:,.2f}"],
            ["Total Expenses", f"${total_expenses:,.2f}"],
            ["Net Balance", f"${balance:,.2f}"]
        ]
        
        summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
        summary_table.setStyle(TableStyle([
            # Header row
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0d6efd")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('ALIGNMENT', (0, 0), (-1, 0), 'CENTER'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 0), (-1, 0), 12),
            
            # Data rows - alternating backgrounds
            ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor("#f8fafc")),
            ('BACKGROUND', (0, 2), (-1, 2), colors.white),
            ('BACKGROUND', (0, 3), (-1, 3), colors.HexColor("#f8fafc")),
            
            # All cells
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor("#1e293b")),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 11),
            ('ALIGNMENT', (0, 1), (0, -1), 'LEFT'),
            ('ALIGNMENT', (1, 1), (1, -1), 'RIGHT'),
            ('FONTNAME', (1, 1), (1, -1), 'Helvetica-Bold'),
            
            # Padding and borders
            ('TOPPADDING', (0, 1), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor("#e2e8f0")),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        elements.append(summary_table)
        elements.append(Spacer(1, 20))
        
        # ================================================================
        # EXPENSE BREAKDOWN SECTION (if there are expenses)
        # ================================================================
        category_summary = get_category_summary(transactions)
        
        if category_summary:
            elements.append(Paragraph("Expense Breakdown by Category", section_style))
            
            category_data = [["Category", "Amount", "Percentage"]]
            total_expenses_calc = sum(category_summary.values())
            
            for category, amount in category_summary.items():
                percentage = (amount / total_expenses_calc * 100) if total_expenses_calc > 0 else 0
                category_data.append([
                    category,
                    f"${amount:,.2f}",
                    f"{percentage:.1f}%"
                ])
            
            category_table = Table(category_data, colWidths=[2.5*inch, 1.5*inch, 1*inch])
            category_table.setStyle(TableStyle([
                # Header
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#41b8d5")),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('ALIGNMENT', (0, 0), (-1, 0), 'CENTER'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('TOPPADDING', (0, 0), (-1, 0), 12),
                
                # Data rows
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#f8fafc")),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor("#1e293b")),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                
                ('ALIGNMENT', (0, 1), (0, -1), 'LEFT'),
                ('ALIGNMENT', (1, 1), (1, -1), 'RIGHT'),
                ('ALIGNMENT', (2, 1), (2, -1), 'CENTER'),
                
                ('TOPPADDING', (0, 1), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor("#e2e8f0")),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            
            elements.append(category_table)
            elements.append(Spacer(1, 20))
        
        # ================================================================
        # TRANSACTIONS TABLE
        # ================================================================
        elements.append(Paragraph("Transaction Details", section_style))
        
        if transactions:
            table_data = [["Date", "Description", "Category", "Type", "Amount"]]
            
            for txn in transactions:
                # Color code by type
                amount_str = f"${txn.get('amount', 0):,.2f}"
                
                table_data.append([
                    txn.get("date", ""),
                    txn.get("description", "")[:30],  # Limit description length
                    txn.get("category", ""),
                    txn.get("type", ""),
                    amount_str
                ])
            
            # Create table with proper column widths
            table = Table(
                table_data,
                colWidths=[1.2*inch, 2.2*inch, 1.2*inch, 0.8*inch, 1.0*inch],
                hAlign='LEFT'
            )
            
            table.setStyle(TableStyle([
                # Header styling
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1e3a5f")),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('ALIGNMENT', (0, 0), (-1, 0), 'CENTER'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                ('TOPPADDING', (0, 0), (-1, 0), 10),
                
                # Alternating row colors for readability
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                
                # Text formatting
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor("#1e293b")),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                
                # Alignment
                ('ALIGNMENT', (0, 1), (0, -1), 'CENTER'),  # Date center
                ('ALIGNMENT', (1, 1), (1, -1), 'LEFT'),    # Description left
                ('ALIGNMENT', (2, 1), (2, -1), 'CENTER'),  # Category center
                ('ALIGNMENT', (3, 1), (3, -1), 'CENTER'),  # Type center
                ('ALIGNMENT', (4, 1), (4, -1), 'RIGHT'),   # Amount right
                
                # Padding and grid
                ('TOPPADDING', (0, 1), (-1, -1), 7),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 7),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor("#e2e8f0")),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                
                # Border styling - thicker header border
                ('LINEBELOW', (0, 0), (-1, 0), 1, colors.HexColor("#e2e8f0")),
            ]))
            
            elements.append(table)
        else:
            elements.append(Paragraph(
                "No transactions available.",
                ParagraphStyle(
                    'NoData',
                    parent=styles['Normal'],
                    fontSize=11,
                    textColor=colors.HexColor("#64748b"),
                    alignment=TA_CENTER
                )
            ))
        
        elements.append(Spacer(1, 30))
        
        # ================================================================
        # FOOTER SECTION
        # ================================================================
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor("#94a3b8"),
            alignment=TA_CENTER,
            spaceBefore=20,
            spaceAfter=0
        )
        
        elements.append(Paragraph(
            "Generated by BudgetBuddy Financial Tracker",
            footer_style
        ))
        elements.append(Paragraph(
            f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            footer_style
        ))
        
        # Build the PDF
        pdf.build(elements)
        return True
        
    except Exception as e:
        print(f"Error building PDF: {e}")
        return False



def login_required(f):
    """
    Decorate routes to require login.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated_function


def get_transaction_data(user_id):
    conn = sqlite3.connect("finance.db")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute(
        "SELECT date, amount, type, category, description FROM transactions WHERE user_id = ? ORDER BY date DESC",
        (user_id,)
    )
    transactions = cur.fetchall()
    conn.close()

    # Convert to list of dicts for PDF helper
    return [dict(txn) for txn in transactions]


def get_transaction_summary(user_id):
    conn = sqlite3.connect("finance.db")
    cur = conn.cursor()

    # Sum of all Income
    cur.execute(
        "SELECT SUM(amount) FROM transactions WHERE user_id=? AND type='income'",
        (user_id,)
    )
    total_income = cur.fetchone()[0] or 0  # if no income, default to 0

    # Sum of all Expenses
    cur.execute(
        "SELECT SUM(amount) FROM transactions WHERE user_id=? AND type='expenses'",
        (user_id,)
    )
    total_expenses = cur.fetchone()[0] or 0

    balance = total_income - total_expenses
    conn.close()

    return total_income, total_expenses, balance


def format_transactions(transactions):
    """Standardize transaction dates to YYYY-MM-DD"""
    transactions = [dict(txn) for txn in transactions]
    for txn in transactions:
        txn["date"] = txn["date"].split(" ")[0]
    return transactions

def get_category_summary(transactions):
    """Get spending breakdown by category"""
    category_summary = {}
    
    for txn in transactions:
        if txn.get("type") == "expense":
            category = txn.get("category", "Uncategorized")
            amount = float(txn.get("amount", 0))
            
            if category not in category_summary:
                category_summary[category] = 0
            category_summary[category] += amount
    
    # Sort by amount (descending)
    return dict(sorted(category_summary.items(), key=lambda x: x[1], reverse=True))


def get_last_month_expenses(user_id):
    """
    Helper function to get the previous month's total expenses.
    """
    from datetime import datetime, timedelta
    last_month = (datetime.now() - timedelta(days=30)).month
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT SUM(amount) FROM transactions WHERE user_id=? AND type='expenses' AND strftime('%m', date) = ?", (user_id, last_month))
        result = cur.fetchone()
    return result[0] if result[0] else 0

def calculate_financial_health(total_income, total_expenses):
    """
    Calculate a financial health score as 0-100 based on income and expenses.

    Returns:
        int: health score from 0 (worst) to 100 (best)
        None: if there is no data at all
    """

    total_expenses = total_expenses or 0
    total_income = total_income or 0
    # No transactions at all
    if total_income == 0 and total_expenses == 0:
        return None

    # No income (only expenses)
    if total_income == 0:
        return 0  

    expense_ratio = total_expenses / total_income

    # Health score decreases as expenses increase
    health_score = max(0, 100 - int(expense_ratio * 100))
    return health_score
