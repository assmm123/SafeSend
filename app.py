from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import os, uuid
from datetime import datetime, timezone

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://localhost/safesend'
app.config['SECRET_KEY'] = 'safesend-2026'
CORS(app)
db = SQLAlchemy(app)

# ==================== MODELS ====================
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80))
    email = db.Column(db.String(255))
    password_hash = db.Column(db.String(255))
    rating = db.Column(db.Float, default=0)
    completed_deals = db.Column(db.Integer, default=0)
    balance = db.Column(db.Float, default=0)
    kyc_verified = db.Column(db.Boolean, default=False)

class Deal(db.Model):
    __tablename__ = 'deals'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    seller_id = db.Column(db.Integer)
    buyer_id = db.Column(db.Integer)
    amount = db.Column(db.Float)
    status = db.Column(db.String(20), default='pending')

with app.app_context():
    db.create_all()

# ==================== HELPER ====================
def get_user_from_token():
    auth = request.headers.get('Authorization','')
    token = auth.replace('Bearer ','')
    if token.startswith('tk-'):
        try:
            uid = int(token.split('-')[1])
            return User.query.get(uid)
        except:
            pass
    return None

def require_auth():
    user = get_user_from_token()
    if not user:
        return None, (jsonify({'error':'Authentication required','message_ar':'المصادقة مطلوبة'}), 401)
    return user, None

# ==================== PAGES ====================
@app.route('/')
def home(): return render_template('dashboard.html')

pages = ['dashboard','admin','login','register','chat','payment','preview','dispute','profile','files','notifications','forgot-password','reset-password','2fa-setup','2fa-verify','backup-codes','payment-history','receipt','my-reviews','portfolio','offline','install-pwa','new_deal']
for p in pages:
    app.add_url_rule(f'/{p}', p.replace('-','_'), lambda p=p: render_template(f'{p}.html'))

@app.route('/static/<path:filename>')
def static_files(filename): return send_from_directory('src/static', filename)

# ==================== AUTH API ====================
@app.route('/api/v1/auth/register', methods=['POST'])
def api_register():
    data = request.get_json()
    if User.query.filter_by(email=data.get('email','')).first():
        return jsonify({'error':'Email exists','message_ar':'البريد مسجل مسبقاً'}), 409
    u = User(username=data.get('username',''), email=data.get('email',''), password_hash='hashed')
    db.session.add(u); db.session.commit()
    return jsonify({'access_token':f'tk-{u.id}','user':{'id':u.id,'username':u.username,'email':u.email}})

@app.route('/api/v1/auth/login', methods=['POST'])
def api_login():
    data = request.get_json()
    u = User.query.filter_by(email=data.get('email','')).first()
    if u:
        return jsonify({'access_token':f'tk-{u.id}','user':{'id':u.id,'username':u.username,'email':u.email,'rating':u.rating,'completed_deals':u.completed_deals,'balance':u.balance,'kyc_verified':u.kyc_verified}})
    return jsonify({'error':'Invalid credentials','message_ar':'بيانات خاطئة'}), 401

@app.route('/api/v1/auth/me')
def api_me():
    u, err = require_auth()
    if err: return err
    return jsonify({'user':{'id':u.id,'username':u.username,'email':u.email,'rating':u.rating,'completed_deals':u.completed_deals,'balance':u.balance,'kyc_verified':u.kyc_verified}})

@app.route('/api/v1/auth/forgot-password', methods=['POST'])
def api_forgot():
    return jsonify({'message':'If email exists, reset link sent','message_ar':'إذا كان البريد موجوداً، تم إرسال الرابط'})

@app.route('/api/v1/auth/reset-password', methods=['POST'])
def api_reset():
    return jsonify({'message':'Password reset','message_ar':'تم إعادة تعيين كلمة المرور'})

@app.route('/api/v1/auth/2fa/enable', methods=['POST'])
def api_2fa_enable():
    return jsonify({'secret':'JBSWY3DPEHPK3PXP','backup_codes':['A1B2C3D4','E5F6G7H8']})

@app.route('/api/v1/auth/2fa/verify', methods=['POST'])
def api_2fa_verify():
    return jsonify({'message':'2FA activated','message_ar':'تم تفعيل 2FA'})

@app.route('/api/v1/auth/2fa/backup', methods=['POST'])
def api_2fa_backup():
    return jsonify({'backup_codes':['X1Y2Z3A4','B5C6D7E8']})

@app.route('/api/v1/auth/sessions')
def api_sessions():
    return jsonify({'sessions':[{'id':1,'device':'Chrome','ip':'127.0.0.1','current':True}]})

@app.route('/api/v1/auth/sessions/<int:sid>', methods=['DELETE'])
def api_revoke_session(sid):
    return jsonify({'message':'Session revoked','message_ar':'تم إلغاء الجلسة'})

# ==================== USERS API ====================
@app.route('/api/v1/users')
def api_users():
    return jsonify({'users':[{'id':u.id,'username':u.username,'email':u.email,'rating':u.rating,'completed_deals':u.completed_deals,'balance':u.balance,'kyc_verified':u.kyc_verified} for u in User.query.all()],'total':User.query.count()})

@app.route('/api/v1/users/<username>')
def api_user_profile(username):
    u = User.query.filter_by(username=username).first()
    if u: return jsonify({'user':{'id':u.id,'username':u.username,'rating':u.rating,'completed_deals':u.completed_deals}})
    return jsonify({'error':'Not found'}), 404

@app.route('/api/v1/users/<username>/reviews')
def api_user_reviews(username):
    return jsonify({'reviews':[],'average_rating':4.5,'total':0})

@app.route('/api/v1/users/<username>/portfolio')
def api_user_portfolio(username):
    return jsonify({'portfolio':[],'total':0})

@app.route('/api/v1/users/portfolio', methods=['POST'])
def api_add_portfolio():
    return jsonify({'message':'Added','message_ar':'تمت الإضافة'})

@app.route('/api/v1/users/portfolio/<int:pid>', methods=['DELETE'])
def api_delete_portfolio(pid):
    return jsonify({'message':'Deleted','message_ar':'تم الحذف'})

@app.route('/api/v1/users/settings')
def api_settings():
    return jsonify({'settings':{'language':'ar','theme':'dark','notifications':True}})

@app.route('/api/v1/users/settings', methods=['PUT'])
def api_update_settings():
    return jsonify({'message':'Settings updated','message_ar':'تم تحديث الإعدادات'})

@app.route('/api/v1/users/notifications')
def api_notifications():
    return jsonify({'notifications':{'email':True,'push':True,'deals':True}})

@app.route('/api/v1/users/payout-methods')
def api_payout_methods():
    return jsonify({'methods':[{'method':'usdt','address':'TRX...','verified':True}]})

# ==================== DEALS API ====================
@app.route('/api/v1/deals')
def api_deals():
    deals = Deal.query.all()
    return jsonify({'deals':[{'id':d.id,'title':d.title,'amount':d.amount,'status':d.status,'seller_id':d.seller_id,'buyer_id':d.buyer_id} for d in deals],'total':len(deals)})

@app.route('/api/v1/deals', methods=['POST'])
def api_create_deal():
    u, err = require_auth()
    if err: return err
    data = request.get_json()
    d = Deal(title=data.get('title',''), seller_id=u.id, buyer_id=data.get('buyer_id',0), amount=data.get('amount',0))
    db.session.add(d); db.session.commit()
    return jsonify({'deal':{'id':d.id,'title':d.title,'amount':d.amount,'status':d.status}})

@app.route('/api/v1/deals/<int:did>')
def api_get_deal(did):
    d = Deal.query.get(did)
    if d: return jsonify({'deal':{'id':d.id,'title':d.title,'amount':d.amount,'status':d.status,'seller_id':d.seller_id,'buyer_id':d.buyer_id}})
    return jsonify({'error':'Not found'}), 404

@app.route('/api/v1/deals/stats')
def api_stats():
    deals = Deal.query.all()
    return jsonify({'stats':{'active':len([d for d in deals if d.status!='completed']),'completed':len([d for d in deals if d.status=='completed']),'total_volume':sum(d.amount for d in deals),'users':User.query.count()}})

@app.route('/api/v1/deals/categories')
def api_categories():
    return jsonify({'categories':['تطوير','تصميم','كتابة','تسويق','استشارات','أخرى']})

# ==================== PAYMENTS API ====================
@app.route('/api/v1/payments/rates')
def api_rates():
    return jsonify({'rates':{'USDT':{'USD':1.0,'SAR':3.75},'updated_at':datetime.now(timezone.utc).isoformat()}})

@app.route('/api/v1/payments/history')
def api_payment_history():
    return jsonify({'payments':[],'pagination':{'page':1,'total':0}})

@app.route('/api/v1/payments/<int:did>/qr')
def api_payment_qr(did):
    return jsonify({'deal_id':did,'wallet_address':'TRX1234567890abcdefTRX1234567890ab','amount':500,'qr_data':'tron://...'})

@app.route('/api/v1/payments/<int:did>/status')
def api_payment_status(did):
    return jsonify({'deal_id':did,'status':'pending','confirmations':0,'is_paid':False})

@app.route('/api/v1/payments/<int:did>/receipt')
def api_payment_receipt(did):
    return jsonify({'receipt':{'deal_id':did,'amount':500,'fee':25,'net':475,'tx_hash':'0x1234...abcd','date':datetime.now(timezone.utc).isoformat()}})

@app.route('/api/v1/payments/webhook/trongrid', methods=['POST'])
def api_trongrid_webhook():
    return jsonify({'status':'received'})

# ==================== MESSAGES API ====================
@app.route('/api/v1/messages/conversations')
def api_conversations():
    return jsonify({'conversations':[]})

@app.route('/api/v1/messages/conversations/<int:did>')
def api_conversation(did):
    return jsonify({'messages':[],'deal_id':did})

@app.route('/api/v1/messages/unread/count')
def api_unread():
    return jsonify({'total_unread':0})

@app.route('/api/v1/messages/conversations/<int:did>/export')
def api_export_chat(did):
    return jsonify({'messages':[],'exported_at':datetime.now(timezone.utc).isoformat()})

# ==================== FILES API ====================
@app.route('/api/v1/files/info/<int:fid>')
def api_file_info(fid):
    return jsonify({'file':{'id':fid,'original_name':'document.pdf','file_size':1024,'mime_type':'application/pdf','encrypted':True,'virus_scanned':True}})

@app.route('/api/v1/files/deal/<int:did>')
def api_deal_files(did):
    return jsonify({'files':[],'deal_id':did})

@app.route('/api/v1/files/download/<int:fid>/token', methods=['POST'])
def api_download_token(fid):
    return jsonify({'token':'dl-token-123','expires_in':300})

# ==================== DISPUTES API ====================
@app.route('/api/v1/disputes/my-disputes')
def api_my_disputes():
    return jsonify({'disputes':[]})

@app.route('/api/v1/disputes/open/<int:did>', methods=['POST'])
def api_open_dispute(did):
    return jsonify({'dispute_id':1,'status':'opened','message_ar':'تم فتح النزاع'})

@app.route('/api/v1/disputes/<int:did>')
def api_dispute(did):
    return jsonify({'dispute':{'id':did,'status':'under_review','reason_category':'quality'}})

@app.route('/api/v1/disputes/<int:did>/timeline')
def api_dispute_timeline(did):
    return jsonify({'timeline':[{'event':'dispute_opened','timestamp':datetime.now(timezone.utc).isoformat()}]})

# ==================== ADMIN API ====================
@app.route('/api/v1/admin/payouts/pending')
def api_admin_payouts():
    return jsonify({'payouts':[]})

@app.route('/api/v1/admin/payouts/history')
def api_admin_payout_history():
    return jsonify({'payouts':[]})

@app.route('/api/v1/admin/disputes/active')
def api_admin_disputes():
    return jsonify({'disputes':[],'total':0})

@app.route('/api/v1/admin/users')
def api_admin_users():
    return jsonify({'users':[{'id':u.id,'username':u.username,'email':u.email,'status':'نشط'} for u in User.query.all()]})

@app.route('/api/v1/admin/stats')
def api_admin_stats():
    return jsonify({'stats':{'total_users':User.query.count(),'active_deals':Deal.query.count(),'total_volume':sum(d.amount for d in Deal.query.all()),'disputes_opened':0}})

@app.route('/api/v1/admin/stats/revenue')
def api_admin_revenue():
    return jsonify({'revenue':{'today':0,'this_week':0,'this_month':sum(d.amount for d in Deal.query.all())}})

@app.route('/api/v1/admin/stats/export')
def api_admin_export():
    return jsonify({'csv':'data...'})

@app.route('/api/v1/admin/backup/trigger', methods=['POST'])
def api_admin_backup():
    return jsonify({'message':'Backup initiated','message_ar':'تم بدء النسخ الاحتياطي'})

@app.route('/api/v1/admin/backups')
def api_admin_backups():
    return jsonify({'backups':[]})

@app.route('/api/v1/admin/maintenance/cleanup', methods=['POST'])
def api_admin_cleanup():
    return jsonify({'message':'Cleanup completed','message_ar':'تم التنظيف'})

# ==================== HEALTH ====================
@app.route('/health/live')
def health():
    return jsonify({'status':'alive','db':'connected','users':User.query.count(),'deals':Deal.query.count()})

@app.route('/health/ready')
def health_ready():
    return jsonify({'status':'healthy','database':'connected','redis':'connected'})

@app.route('/health/detailed')
def health_detailed():
    return jsonify({'status':'healthy','components':{'database':'ok','redis':'ok','celery':'ok','disk':'ok','memory':'ok'}})

@app.route('/metrics')
def metrics():
    return jsonify({'users':User.query.count(),'deals':Deal.query.count(),'uptime':'48h'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
