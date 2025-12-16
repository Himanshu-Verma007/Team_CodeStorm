from flask import Flask, jsonify, request, send_from_directory
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
import os
import sqlite3
from datetime import datetime

app = Flask(__name__)

LETTERS_DIR = 'generated_letters'
if not os.path.exists(LETTERS_DIR):
    os.makedirs(LETTERS_DIR)

# Database setup
DATABASE = 'customers.db'

def init_db():
    """Initialize the database and create tables if they don't exist"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            address TEXT NOT NULL,
            credit_score INTEGER NOT NULL,
            pre_approved_limit INTEGER NOT NULL,
            monthly_salary INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Check if we have any customers, if not, add default ones
    cursor.execute('SELECT COUNT(*) FROM customers')
    count = cursor.fetchone()[0]
    
    if count == 0:
        # Insert default customers
        default_customers = [
            ("Rajesh Kumar", "+91-9876543210", "123 MG Road, Bangalore, Karnataka - 560001", 750, 500000, 80000),
            ("Priya Sharma", "+91-9123456789", "456 Park Street, Kolkata, West Bengal - 700016", 650, 200000, 50000),
            ("Amit Patel", "+91-9988776655", "789 Marine Drive, Mumbai, Maharashtra - 400020", 720, 300000, 120000)
        ]
        
        cursor.executemany('''
            INSERT INTO customers (name, phone, address, credit_score, pre_approved_limit, monthly_salary)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', default_customers)
        
        conn.commit()
    
    conn.close()

def get_customer_by_id(customer_id):
    """Fetch customer data from database"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, name, phone, address, credit_score, pre_approved_limit, monthly_salary
        FROM customers WHERE id = ?
    ''', (customer_id,))
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            "id": row[0],
            "name": row[1],
            "kyc_details": {
                "phone": row[2],
                "address": row[3]
            },
            "credit_score": row[4],
            "pre_approved_limit": row[5],
            "monthly_salary": row[6]
        }
    return None

def get_all_customers():
    """Fetch all customers from database"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, name, phone, address, credit_score, pre_approved_limit, monthly_salary
        FROM customers ORDER BY id
    ''')
    
    rows = cursor.fetchall()
    conn.close()
    
    customers = []
    for row in rows:
        customers.append({
            "id": row[0],
            "name": row[1],
            "phone": row[2],
            "address": row[3],
            "credit_score": row[4],
            "pre_approved_limit": row[5],
            "monthly_salary": row[6]
        })
    
    return customers

def add_customer_to_db(name, phone, address, credit_score, pre_approved_limit, monthly_salary):
    """Add new customer to database"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO customers (name, phone, address, credit_score, pre_approved_limit, monthly_salary)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (name, phone, address, credit_score, pre_approved_limit, monthly_salary))
    
    conn.commit()
    customer_id = cursor.lastrowid
    conn.close()
    
    return customer_id

# Initialize database on startup
init_db()

def verification_agent(customer_id):
    customer = get_customer_by_id(customer_id)
    
    if not customer:
        return {"status": "error", "message": "Customer not found"}
    
    return {
        "status": "success",
        "name": customer["name"],
        "kyc_details": customer["kyc_details"]
    }

def underwriting_agent(customer_id, loan_amount, tenure_months=60):
    customer = get_customer_by_id(customer_id)
    
    if not customer:
        return {"status": "error", "reason": "Customer not found"}
    
    credit_score = customer["credit_score"]
    pre_approved_limit = customer["pre_approved_limit"]
    monthly_salary = customer["monthly_salary"]
    
    if credit_score < 700:
        return {
            "status": "rejected",
            "reason": f"Credit score ({credit_score}) is below the minimum requirement of 700"
        }
    
    if loan_amount > 2 * pre_approved_limit:
        return {
            "status": "rejected",
            "reason": f"Requested loan amount (Rs{loan_amount:,}) exceeds 2x the pre-approved limit (Rs{2*pre_approved_limit:,})"
        }
    
    if loan_amount <= pre_approved_limit:
        return {
            "status": "approved",
            "reason": f"Loan amount (Rs{loan_amount:,}) is within pre-approved limit (Rs{pre_approved_limit:,})",
            "interest_rate": 10.5,
            "tenure_months": tenure_months
        }
    
    if pre_approved_limit < loan_amount <= 2 * pre_approved_limit:
        total_amount = loan_amount * 1.12
        emi = total_amount / tenure_months
        max_emi = monthly_salary * 0.5
        
        if emi <= max_emi:
            return {
                "status": "approved",
                "reason": f"Salary verification passed. EMI (Rs{emi:,.2f}) is within 50% of monthly salary (Rs{monthly_salary:,})",
                "interest_rate": 12.0,
                "tenure_months": tenure_months,
                "emi": emi,
                "salary_verification_required": True
            }
        else:
            return {
                "status": "rejected",
                "reason": f"EMI (Rs{emi:,.2f}) exceeds 50% of monthly salary (Rs{max_emi:,.2f})"
            }

def sanction_letter_generator(customer_id, loan_amount, interest_rate, tenure_months, approval_status):
    """Generates a PDF sanction letter using reportlab"""
    try:
        customer = get_customer_by_id(customer_id)
        
        if not customer:
            print(f"ERROR: Customer {customer_id} not found!")
            return None
        
        # Create filename
        filename = f"Sanction_Letter_{customer_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        filepath = os.path.join(LETTERS_DIR, filename)
        
        print(f"Creating PDF at: {filepath}")
        
        # Create PDF
        c = canvas.Canvas(filepath, pagesize=letter)
        width, height = letter
        
        # Add Tata Capital Header
        c.setFont("Helvetica-Bold", 20)
        c.drawString(1*inch, height - 1*inch, "TATA CAPITAL")
        
        c.setFont("Helvetica", 10)
        c.drawString(1*inch, height - 1.3*inch, "Financial Services Limited")
        c.line(1*inch, height - 1.5*inch, width - 1*inch, height - 1.5*inch)
        
        # Title
        c.setFont("Helvetica-Bold", 16)
        c.drawString(1*inch, height - 2*inch, "LOAN SANCTION LETTER")
        
        # Date
        c.setFont("Helvetica", 11)
        c.drawString(1*inch, height - 2.5*inch, f"Date: {datetime.now().strftime('%d %B, %Y')}")
        
        # Customer Details
        c.setFont("Helvetica-Bold", 12)
        c.drawString(1*inch, height - 3*inch, "Customer Details:")
        
        c.setFont("Helvetica", 11)
        y_position = height - 3.3*inch
        c.drawString(1.2*inch, y_position, f"Name: {customer['name']}")
        y_position -= 0.25*inch
        c.drawString(1.2*inch, y_position, f"Phone: {customer['kyc_details']['phone']}")
        y_position -= 0.25*inch
        c.drawString(1.2*inch, y_position, f"Address: {customer['kyc_details']['address']}")
        
        # Loan Details
        y_position -= 0.5*inch
        c.setFont("Helvetica-Bold", 12)
        c.drawString(1*inch, y_position, "Loan Details:")
        
        y_position -= 0.3*inch
        c.setFont("Helvetica", 11)
        c.drawString(1.2*inch, y_position, f"Loan Amount: Rs {loan_amount:,}")
        y_position -= 0.25*inch
        c.drawString(1.2*inch, y_position, f"Interest Rate: {interest_rate}% per annum")
        y_position -= 0.25*inch
        c.drawString(1.2*inch, y_position, f"Tenure: {tenure_months} months")
        y_position -= 0.25*inch
        
        total_payable = loan_amount * (1 + interest_rate/100)
        emi = total_payable / tenure_months
        c.drawString(1.2*inch, y_position, f"Estimated EMI: Rs {emi:,.2f}")
        
        # Approval Status
        y_position -= 0.5*inch
        c.setFont("Helvetica-Bold", 14)
        if approval_status == "approved":
            c.setFillColorRGB(0, 0.5, 0)
            c.drawString(1*inch, y_position, "STATUS: APPROVED")
        else:
            c.setFillColorRGB(0.8, 0, 0)
            c.drawString(1*inch, y_position, f"STATUS: {approval_status.upper()}")
        
        # Footer
        c.setFillColorRGB(0, 0, 0)
        c.setFont("Helvetica-Oblique", 9)
        c.drawString(1*inch, 1*inch, "This is a system-generated letter. No signature is required.")
        c.drawString(1*inch, 0.75*inch, "For queries, contact: support@tatacapital.com | 1800-123-4567")
        
        # IMPORTANT: Save the PDF
        c.save()
        
        print(f"PDF created successfully: {filename}")
        print(f"File exists: {os.path.exists(filepath)}")
        
        return filename
        
    except Exception as e:
        print(f"ERROR generating PDF: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tata Capital AI Loan Simulation</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 900px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
            overflow: hidden;
        }
        header {
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        header h1 { font-size: 2.5em; margin-bottom: 10px; }
        header h2 { font-size: 1.2em; opacity: 0.9; }
        
        .add-customer-section {
            padding: 30px;
            background: #f0f8ff;
            border-bottom: 2px solid #e0e0e0;
        }
        .add-customer-section h3 {
            color: #333;
            margin-bottom: 15px;
            font-size: 1.5em;
        }
        .toggle-button {
            padding: 10px 20px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-weight: 600;
        }
        .toggle-button:hover { background: #5568d3; }
        .customer-form {
            margin-top: 20px;
            padding: 20px;
            background: white;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .customer-form.hidden { display: none; }
        .form-row {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
        }
        .form-group { margin-bottom: 20px; }
        .form-group label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: #333;
        }
        .form-group input, .form-group textarea, .form-group select {
            width: 100%;
            padding: 12px 15px;
            border: 2px solid #ddd;
            border-radius: 8px;
            font-size: 1em;
        }
        .form-group textarea { font-family: inherit; resize: vertical; }
        .form-group input:focus, .form-group textarea:focus, .form-group select:focus {
            outline: none;
            border-color: #667eea;
        }
        .add-button {
            width: 100%;
            padding: 12px;
            background: #4caf50;
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 1em;
            font-weight: 600;
            cursor: pointer;
            margin-top: 10px;
        }
        .add-button:hover { background: #45a049; }
        .status-message {
            margin-top: 15px;
            padding: 12px;
            border-radius: 5px;
            text-align: center;
            font-weight: 600;
            display: none;
        }
        .status-message.success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
            display: block;
        }
        .status-message.error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
            display: block;
        }
        
        .input-section {
            padding: 30px;
            background: #f8f9fa;
            border-bottom: 2px solid #e0e0e0;
        }
        .start-button {
            width: 100%;
            padding: 15px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 1.1em;
            font-weight: 600;
            cursor: pointer;
        }
        .start-button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }
        
        .simulation-section { padding: 30px; }
        .simulation-section h3 {
            color: #333;
            margin-bottom: 20px;
            font-size: 1.5em;
        }
        .chat-window {
            background: #ffffff;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            padding: 20px;
            min-height: 400px;
            max-height: 600px;
            overflow-y: auto;
            font-family: 'Courier New', monospace;
        }
        .placeholder {
            color: #999;
            text-align: center;
            padding: 50px 20px;
            font-style: italic;
        }
        .chat-message {
            padding: 12px 15px;
            margin-bottom: 10px;
            border-radius: 8px;
            line-height: 1.6;
        }
        .master-agent { background: #e3f2fd; border-left: 4px solid #2196f3; }
        .verification-agent { background: #e8f5e9; border-left: 4px solid #4caf50; }
        .underwriting-agent { background: #fff3e0; border-left: 4px solid #ff9800; }
        .success-message { background: #e8f5e9; border-left: 4px solid #4caf50; color: #2e7d32; font-weight: 600; }
        .error-message { background: #ffebee; border-left: 4px solid #f44336; color: #c62828; font-weight: 600; }
        .divider { text-align: center; color: #bbb; margin: 15px 0; }
        .pdf-link {
            display: inline-block;
            padding: 10px 20px;
            background: #4caf50;
            color: white !important;
            text-decoration: none;
            border-radius: 5px;
            font-weight: 600;
        }
        .loading {
            text-align: center;
            color: #667eea;
            font-weight: 600;
            padding: 20px;
        }
        
        @media (max-width: 600px) {
            .form-row { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🏦 Tata Capital</h1>
            <h2>AI-Powered Loan Approval Simulation</h2>
        </header>

        <div class="add-customer-section">
            <h3>➕ Add New Customer</h3>
            <button id="toggle-form-btn" class="toggle-button">Show Form</button>
            
            <div id="customer-form" class="customer-form hidden">
                <div class="form-group">
                    <label for="customer-name">Full Name:</label>
                    <input type="text" id="customer-name" placeholder="e.g., Rahul Verma">
                </div>
                
                <div class="form-group">
                    <label for="customer-phone">Phone Number:</label>
                    <input type="tel" id="customer-phone" placeholder="e.g., +91-9876543210">
                </div>
                
                <div class="form-group">
                    <label for="customer-address">Address:</label>
                    <textarea id="customer-address" placeholder="e.g., 456 Street Name, City, State - PIN" rows="2"></textarea>
                </div>
                
                <div class="form-row">
                    <div class="form-group">
                        <label for="credit-score">Credit Score:</label>
                        <input type="number" id="credit-score" placeholder="e.g., 750" min="300" max="900">
                    </div>
                    
                    <div class="form-group">
                        <label for="pre-approved-limit">Pre-approved Limit (₹):</label>
                        <input type="number" id="pre-approved-limit" placeholder="e.g., 500000" min="50000" step="10000">
                    </div>
                </div>
                
                <div class="form-group">
                    <label for="monthly-salary">Monthly Salary (₹):</label>
                    <input type="number" id="monthly-salary" placeholder="e.g., 80000" min="10000" step="5000">
                </div>
                
                <button id="add-customer-btn" class="add-button">Add Customer</button>
                <div id="customer-status" class="status-message"></div>
            </div>
        </div>

        <div class="input-section">
            <div class="form-group">
                <label for="customer-select">Select Customer:</label>
                <select id="customer-select">
                    <option value="">-- Choose a Customer --</option>
                </select>
            </div>

            <div class="form-group">
                <label for="loan-amount">Loan Amount (₹):</label>
                <input type="number" id="loan-amount" placeholder="Enter loan amount" min="10000" step="10000">
            </div>

            <button id="start-btn" class="start-button">Start Simulation</button>
        </div>

        <div class="simulation-section">
            <h3>🤖 AI Agent Conversation Log</h3>
            <div id="chat-window" class="chat-window">
                <p class="placeholder">Click "Start Simulation" to begin the loan approval process...</p>
            </div>
        </div>
    </div>

    <script>
        const startButton = document.getElementById('start-btn');
        const customerSelect = document.getElementById('customer-select');
        const loanAmountInput = document.getElementById('loan-amount');
        const chatWindow = document.getElementById('chat-window');

        function loadCustomers() {
            fetch('/get_customers')
            .then(response => response.json())
            .then(customers => {
                customerSelect.innerHTML = '<option value="">-- Choose a Customer --</option>';
                customers.forEach(customer => {
                    const option = document.createElement('option');
                    option.value = customer.id;
                    option.textContent = `Customer ${customer.id}: ${customer.name} (Credit: ${customer.credit_score}, Limit: ₹${(customer.pre_approved_limit/100000).toFixed(1)}L)`;
                    customerSelect.appendChild(option);
                });
            });
        }

        loadCustomers();

        startButton.addEventListener('click', function() {
            const customerId = customerSelect.value;
            const loanAmount = loanAmountInput.value;

            if (!customerId) { alert('Please select a customer'); return; }
            if (!loanAmount || loanAmount < 10000) { alert('Please enter a valid loan amount (minimum ₹10,000)'); return; }

            chatWindow.innerHTML = '<p class="loading">⏳ Starting simulation...</p>';
            startButton.disabled = true;
            startButton.textContent = 'Processing...';

            fetch('/start_simulation', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ customer_id: customerId, loan_amount: loanAmount })
            })
            .then(response => response.json())
            .then(data => displayLog(data.log))
            .catch(error => chatWindow.innerHTML = `<p class="error-message">❌ Error: ${error.message}</p>`)
            .finally(() => {
                startButton.disabled = false;
                startButton.textContent = 'Start Simulation';
            });
        });

        function displayLog(log) {
            chatWindow.innerHTML = '';
            log.forEach((message, index) => {
                setTimeout(() => {
                    const div = document.createElement('div');
                    if (message === '---') {
                        div.className = 'divider';
                        div.textContent = '• • •';
                    } else {
                        div.className = 'chat-message';
                        if (message.includes('Master Agent')) div.classList.add('master-agent');
                        else if (message.includes('Verification Agent')) div.classList.add('verification-agent');
                        else if (message.includes('Underwriting Agent')) div.classList.add('underwriting-agent');
                        else if (message.includes('REJECTED') || message.includes('❌')) div.classList.add('error-message');
                        else if (message.includes('APPROVED') || message.includes('✅')) div.classList.add('success-message');
                        div.innerHTML = message;
                    }
                    chatWindow.appendChild(div);
                    chatWindow.scrollTop = chatWindow.scrollHeight;
                }, index * 300);
            });
        }

        document.getElementById('toggle-form-btn').addEventListener('click', function() {
            const form = document.getElementById('customer-form');
            const btn = this;
            if (form.classList.contains('hidden')) {
                form.classList.remove('hidden');
                btn.textContent = 'Hide Form';
            } else {
                form.classList.add('hidden');
                btn.textContent = 'Show Form';
            }
        });

        document.getElementById('add-customer-btn').addEventListener('click', function() {
            const name = document.getElementById('customer-name').value.trim();
            const phone = document.getElementById('customer-phone').value.trim();
            const address = document.getElementById('customer-address').value.trim();
            const creditScore = document.getElementById('credit-score').value;
            const preApprovedLimit = document.getElementById('pre-approved-limit').value;
            const monthlySalary = document.getElementById('monthly-salary').value;
            const status = document.getElementById('customer-status');

            if (!name || !phone || !address || !creditScore || !preApprovedLimit || !monthlySalary) {
                status.textContent = 'Please fill in all fields';
                status.className = 'status-message error';
                setTimeout(() => status.className = 'status-message', 5000);
                return;
            }

            if (creditScore < 300 || creditScore > 900) {
                status.textContent = 'Credit score must be between 300 and 900';
                status.className = 'status-message error';
                setTimeout(() => status.className = 'status-message', 5000);
                return;
            }

            this.disabled = true;
            this.textContent = 'Adding...';

            fetch('/add_customer', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name, phone, address,
                    credit_score: creditScore,
                    pre_approved_limit: preApprovedLimit,
                    monthly_salary: monthlySalary
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    status.textContent = data.message;
                    status.className = 'status-message success';
                    
                    const option = document.createElement('option');
                    option.value = data.customer_id;
                    option.textContent = `Customer ${data.customer_id}: ${name} (Credit: ${creditScore}, Limit: ₹${(parseInt(preApprovedLimit)/100000).toFixed(1)}L)`;
                    customerSelect.appendChild(option);
                    
                    customerSelect.value = data.customer_id;

                    document.getElementById('customer-name').value = '';
                    document.getElementById('customer-phone').value = '';
                    document.getElementById('customer-address').value = '';
                    document.getElementById('credit-score').value = '';
                    document.getElementById('pre-approved-limit').value = '';
                    document.getElementById('monthly-salary').value = '';
                    
                    document.getElementById('customer-form').classList.add('hidden');
                    document.getElementById('toggle-form-btn').textContent = 'Show Form';
                } else {
                    status.textContent = 'Error adding customer';
                    status.className = 'status-message error';
                }
                setTimeout(() => status.className = 'status-message', 5000);
            })
            .catch(error => {
                status.textContent = 'Network error. Please try again.';
                status.className = 'status-message error';
                setTimeout(() => status.className = 'status-message', 5000);
            })
            .finally(() => {
                this.disabled = false;
                this.textContent = 'Add Customer';
            });
        });
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return HTML_TEMPLATE

@app.route('/start_simulation', methods=['POST'])
def start_simulation():
    data = request.json
    customer_id = data.get('customer_id')
    loan_amount = float(data.get('loan_amount', 0))
    
    log = []
    log.append("🤖 Master Agent: Hello! Welcome to Tata Capital AI Loan Processing System.")
    log.append(f"🤖 Master Agent: Processing loan application for Customer ID: {customer_id}")
    log.append(f"🤖 Master Agent: Requested Loan Amount: Rs{loan_amount:,}")
    log.append("---")
    
    log.append("🔍 Master Agent: Initiating KYC verification...")
    verification_result = verification_agent(customer_id)
    
    if verification_result["status"] == "error":
        log.append(f"❌ Verification Agent: {verification_result['message']}")
        return jsonify({"log": log})
    
    log.append(f"✅ Verification Agent: KYC verification successful!")
    log.append(f"📋 Verification Agent: Customer Name - {verification_result['name']}")
    log.append(f"📋 Verification Agent: Phone - {verification_result['kyc_details']['phone']}")
    log.append(f"📋 Verification Agent: Address - {verification_result['kyc_details']['address']}")
    log.append("---")
    
    log.append("📊 Master Agent: Forwarding to Underwriting Agent for credit assessment...")
    underwriting_result = underwriting_agent(customer_id, loan_amount)
    
    customer = get_customer_by_id(customer_id)
    log.append(f"💳 Underwriting Agent: Credit Score - {customer['credit_score']}")
    log.append(f"💰 Underwriting Agent: Pre-approved Limit - Rs{customer['pre_approved_limit']:,}")
    
    if underwriting_result.get("salary_verification_required"):
        log.append(f"📄 Underwriting Agent: Salary verification required (Monthly Salary: Rs{customer['monthly_salary']:,})")
    
    log.append(f"🔎 Underwriting Agent: {underwriting_result['reason']}")
    log.append("---")
    
    if underwriting_result["status"] == "rejected":
        log.append(f"❌ Master Agent: Loan application has been REJECTED.")
        log.append(f"📌 Master Agent: Reason - {underwriting_result['reason']}")
        log.append("🤖 Master Agent: Thank you for choosing Tata Capital. You may reapply after improving your eligibility.")
    
    elif underwriting_result["status"] == "approved":
        log.append("✅ Master Agent: Loan application has been APPROVED! 🎉")
        log.append("📝 Master Agent: Generating sanction letter...")
        
        filename = sanction_letter_generator(
            customer_id,
            loan_amount,
            underwriting_result["interest_rate"],
            underwriting_result["tenure_months"],
            "approved"
        )
        
        if filename:
            log.append(f"✅ Sanction Letter Agent: PDF generated successfully!")
            log.append(f"📄 Sanction Letter Agent: <a href='/download/{filename}' target='_blank' class='pdf-link'>Download Your Sanction Letter</a>")
            log.append("---")
            log.append("🤖 Master Agent: Congratulations! Your loan has been approved. Please download your sanction letter above.")
        else:
            log.append(f"❌ Sanction Letter Agent: Error generating PDF. Please contact support.")
    
    return jsonify({"log": log})

@app.route('/download/<filename>')
def download_file(filename):
    """Serve the generated PDF files"""
    try:
        # Get absolute path
        abs_path = os.path.abspath(LETTERS_DIR)
        print(f"Looking for file in: {abs_path}")
        print(f"Filename requested: {filename}")
        print(f"Full path: {os.path.join(abs_path, filename)}")
        print(f"File exists: {os.path.exists(os.path.join(abs_path, filename))}")
        
        return send_from_directory(abs_path, filename, as_attachment=True)
    except Exception as e:
        print(f"Download error: {str(e)}")
        return jsonify({"error": str(e)}), 404


@app.route('/get_customers')
def get_customers():
    """Return all customers from database"""
    customers = get_all_customers()
    return jsonify(customers)

@app.route('/add_customer', methods=['POST'])
def add_customer():
    data = request.json
    
    customer_id = add_customer_to_db(
        data.get('name'),
        data.get('phone'),
        data.get('address'),
        int(data.get('credit_score')),
        int(data.get('pre_approved_limit')),
        int(data.get('monthly_salary'))
    )
    
    return jsonify({
        "status": "success",
        "message": f"Customer {data.get('name')} added successfully!",
        "customer_id": customer_id
    })

if __name__ == '__main__':
    app.run(debug=True, port=5001)
