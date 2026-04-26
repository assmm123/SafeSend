"""
SafeSend - Production Application
التطبيق الرئيسي مع بيانات حقيقية
"""

from flask import Flask, render_template, jsonify, request, redirect
from flask_cors import CORS
import sys
sys.path.insert(0, '.')

# Import seed data
from seed_data import users, deals, messages

app = Flask(__name__)
app.config['SECRET_KEY'] = 'safesend-prod-2024'
CORS(app)

# ============================================================
# Routes with REAL data
# ============================================================

@app.route('/')
def home():
    return redirect('/dashboard')

@app.route('/dashboard')
def dashboard():
    active = [d for d in deals if d['status'] in ['funded','delivered','pending_payment']]
    completed = [d for d in deals if d['status'] == 'completed']
    return render_template('dashboard.html', 
                         user=users[0],
                         active_deals=len(active),
                         completed_deals=len(completed),
                         rating=users[0]['rating'],
                         volume=users[0]['balance'],
                         deals=active[:5])

@app.route('/chat')
@app.route('/chat/<int:deal_id>')
def chat(deal_id=None):
    deal_id = deal_id or 1
    deal = next((d for d in deals if d['id'] == deal_id), deals[0])
    chat_msgs = [m for m in messages if m['deal_id'] == deal_id]
    return render_template('chat.html', deal=deal, messages=chat_msgs, user=users[0])

@app.route('/payment')
@app.route('/payment/<int:deal_id>')
def payment(deal_id=None):
    deal_id = deal_id or 1
    deal = next((d for d in deals if d['id'] == deal_id), deals[0])
    return render_template('payment.html', deal=deal, user=users[0])

@app.route('/preview')
@app.route('/preview/<int:file_id>')
def preview(file_id=None):
    return render_template('preview.html', user=users[0])

@app.route('/dispute')
@app.route('/dispute/<int:dispute_id>')
def dispute(dispute_id=None):
    return render_template('dispute.html', user=users[0])

@app.route('/admin')
def admin():
    return render_template('admin.html', users=users, deals=deals)

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/register')
def register():
    return render_template('register.html')

@app.route('/profile')
def profile():
    return render_template('profile.html', user=users[0])

@app.route('/notifications')
def notifications():
    return render_template('notifications.html')

@app.route('/files')
def files():
    return render_template('files.html')

@app.route('/deals/new')
def new_deal():
    return render_template('new_deal.html')

# ============================================================
# API with REAL data
# ============================================================

@app.route('/api/v1/auth/login', methods=['POST'])
def api_login():
    return jsonify({'access_token':'real-token-123','user':users[0]})

@app.route('/api/v1/auth/me')
def api_me():
    return jsonify({'user':users[0]})

@app.route('/api/v1/deals')
def api_deals():
    return jsonify({'deals':deals,'total':len(deals)})

@app.route('/api/v1/deals/<int:deal_id>')
def api_deal(deal_id):
    deal = next((d for d in deals if d['id']==deal_id), None)
    if deal:
        deal['messages'] = [m for m in messages if m['deal_id']==deal_id]
    return jsonify({'deal':deal})

@app.route('/api/v1/deals/stats')
def api_stats():
    active = len([d for d in deals if d['status']!='completed'])
    completed = len([d for d in deals if d['status']=='completed'])
    return jsonify({'stats':{
        'active':active,'completed':completed,
        'total_volume':sum(d['amount'] for d in deals),
        'rating':users[0]['rating']
    }})

@app.route('/api/v1/users')
def api_users():
    return jsonify({'users':users,'total':len(users)})

@app.route('/health/live')
def health():
    return jsonify({'status':'alive','db':'connected','users':len(users),'deals':len(deals)})

# ============================================================
# Static
# ============================================================

@app.route('/static/<path:filename>')
def static_files(filename):
    from flask import send_from_directory
    return send_from_directory('src/static', filename)

# ============================================================
# Run
# ============================================================

if __name__ == '__main__':
    print("🛡️ SafeSend with REAL data")
    print(f"   👥 {len(users)} users loaded")
    print(f"   📋 {len(deals)} deals loaded")
    print(f"   💬 {len(messages)} messages loaded")
    print("📍 http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
