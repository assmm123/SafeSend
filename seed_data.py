"""
Seed Data - SafeSend
بيانات تجريبية حقيقية للنظام
"""
import sys
sys.path.insert(0, '.')

# Mock data للعرض
users = [
    {'id':1,'username':'Ahmed','email':'ahmed@email.com','rating':4.8,'completed_deals':45,'balance':12500,'kyc':True},
    {'id':2,'username':'Sara','email':'sara@email.com','rating':4.5,'completed_deals':18,'balance':3200,'kyc':True},
    {'id':3,'username':'Mona','email':'mona@email.com','rating':4.2,'completed_deals':7,'balance':800,'kyc':False},
    {'id':4,'username':'Ali','email':'ali@email.com','rating':3.9,'completed_deals':3,'balance':150,'kyc':False},
]

deals = [
    {'id':1,'title':'تصميم موقع احترافي','seller_id':1,'buyer_id':3,'amount':500,'status':'funded','created':'2024-05-01'},
    {'id':2,'title':'ترجمة مستندات قانونية','seller_id':2,'buyer_id':4,'amount':200,'status':'delivered','created':'2024-05-05'},
    {'id':3,'title':'تطوير تطبيق جوال','seller_id':1,'buyer_id':3,'amount':1500,'status':'pending_payment','created':'2024-05-10'},
    {'id':4,'title':'استشارة تقنية','seller_id':4,'buyer_id':2,'amount':50,'status':'completed','created':'2024-05-08'},
    {'id':5,'title':'تصميم شعار','seller_id':2,'buyer_id':1,'amount':100,'status':'disputed','created':'2024-05-12'},
]

messages = [
    {'id':1,'deal_id':1,'sender_id':3,'content':'مرحباً، هل يمكنك البدء بالتصميم؟','created_at':'2024-05-01 10:30'},
    {'id':2,'deal_id':1,'sender_id':1,'content':'نعم، سأرسل المسودة خلال يومين','created_at':'2024-05-01 10:32'},
    {'id':3,'deal_id':1,'sender_id':3,'content':'ممتاز، في انتظارك','created_at':'2024-05-01 10:33'},
    {'id':4,'deal_id':2,'sender_id':4,'content':'هل انتهيت من الترجمة؟','created_at':'2024-05-06 14:00'},
    {'id':5,'deal_id':2,'sender_id':2,'content':'نعم، تم الإرسال','created_at':'2024-05-06 14:05'},
]

print("✅ Seed data ready")
print(f"   {len(users)} users")
print(f"   {len(deals)} deals")
print(f"   {len(messages)} messages")
