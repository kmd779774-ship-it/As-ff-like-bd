from flask import Flask, request, jsonify, send_from_directory, redirect
import os, json, sqlite3, time, uuid
from datetime import datetime, timezone
import requests

app = Flask(__name__, static_folder='.', static_url_path='')

# IMPORTANT: keep this server-side. Never put the Bohudur key in index.html.
BOHUDUR_API_KEY = 'u2CiJaRISdkoyEqlwtOerAD3gZsKLTQx'
BOHUDUR_BASE = 'https://request.bohudur.one'
LIKE_API = 'https://asfflikebdlikeapi.vercel.app/like'
INFO_API = 'https://ffxinfo-ffx.ffxapis.workers.dev/ffinfo'
REGION = 'BD'
ADMIN_URL = 'https://t.me/as_owner99'

DEFAULT_PACKAGES = [
    {'likes': 100, 'price': 5},
    {'likes': 200, 'price': 10},
    {'likes': 500, 'price': 25},
    {'likes': 1000, 'price': 40},
    {'likes': 2000, 'price': 60},
    {'likes': 5000, 'price': 100},
    {'likes': 10000, 'price': 200},
]

DB = os.path.join(os.path.dirname(__file__), 'store.db')

def db():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    c = db()
    c.executescript('''
    CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, name TEXT, email TEXT, balance REAL DEFAULT 0, created_at TEXT);
    CREATE TABLE IF NOT EXISTS orders (id TEXT PRIMARY KEY, user_id TEXT, uid TEXT, likes INTEGER, price REAL, status TEXT, paymentkey TEXT, created_at TEXT, result TEXT);
    CREATE TABLE IF NOT EXISTS payments (id TEXT PRIMARY KEY, user_id TEXT, amount REAL, status TEXT, paymentkey TEXT, created_at TEXT, result TEXT);
    ''')
    if not c.execute("SELECT 1 FROM settings WHERE key='packages'").fetchone():
        c.execute('INSERT INTO settings(key,value) VALUES(?,?)', ('packages', json.dumps(DEFAULT_PACKAGES)))
    if not c.execute("SELECT 1 FROM settings WHERE key='site'").fetchone():
        c.execute('INSERT INTO settings(key,value) VALUES(?,?)', ('site', json.dumps({
            'name':'AS LIKE BOT', 'developer':'ARYAN SHANTO', 'telegram':ADMIN_URL,
            'notice':'Trusted Free Fire Like Service',
            'banner':'https://images.unsplash.com/photo-1542751371-adc38448a05e?auto=format&fit=crop&w=1200&q=80'
        })))
    c.commit(); c.close()

init_db()

def setting(key, default=None):
    c=db(); r=c.execute('SELECT value FROM settings WHERE key=?',(key,)).fetchone(); c.close()
    if not r: return default
    try: return json.loads(r['value'])
    except Exception: return default

def save_setting(key, value):
    c=db(); c.execute('INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)',(key,json.dumps(value,ensure_ascii=False))); c.commit(); c.close()

def now(): return datetime.now(timezone.utc).isoformat()

def json_body(): return request.get_json(silent=True) or {}

@app.after_request
def cors(resp):
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    resp.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS'
    return resp

@app.route('/')
def index(): return send_from_directory('.', 'index.html')

@app.route('/admin')
def admin(): return send_from_directory('.', 'admin.html')

@app.route('/api/config')
def config():
    return jsonify({'site':setting('site',{}), 'packages':setting('packages',DEFAULT_PACKAGES), 'region':REGION, 'admin_url':ADMIN_URL})

@app.route('/api/info', methods=['POST'])
def info():
    uid=str(json_body().get('uid','')).strip()
    if not uid.isdigit(): return jsonify({'ok':False,'error':'UID must be numeric.'}),400
    try:
        r=requests.get(INFO_API, params={'uid':uid}, timeout=15, headers={'Accept':'application/json'})
        data=r.json()
        root=data.get('data') if isinstance(data.get('data'),dict) else data
        ident=root.get('identity',{}) if isinstance(root,dict) else {}
        profile=root.get('profile',{}) if isinstance(root,dict) else {}
        account=root.get('account_info',{}) if isinstance(root,dict) else {}
        rank=root.get('rank_info',{}) if isinstance(root,dict) else {}
        basic=root.get('BasicInformation',{}) if isinstance(root,dict) else {}
        out={
          'UID': str(ident.get('uid') or basic.get('UID') or uid),
          'Name': ident.get('username') or basic.get('Name') or basic.get('nickname') or 'Unknown',
          'Region': ident.get('region') or basic.get('Region') or data.get('server_used','N/A'),
          'Level': profile.get('level') or basic.get('Level','N/A'),
          'Likes': profile.get('likes') or basic.get('Likes','N/A'),
          'BRRank': rank.get('br_rank') or basic.get('Rank','N/A'),
          'CSRank': rank.get('cs_rank') or basic.get('CSRank','N/A'),
          'Exp': account.get('exp') or basic.get('Exp','N/A')
        }
        return jsonify({'ok':True,'data':out})
    except Exception as e:
        return jsonify({'ok':False,'error':'UID information is temporarily unavailable.'}),502

@app.route('/api/like', methods=['POST'])
def like():
    body=json_body(); uid=str(body.get('uid','')).strip(); region=str(body.get('region',REGION)).upper()
    if not uid.isdigit(): return jsonify({'ok':False,'error':'UID must be numeric.'}),400
    try:
        r=requests.get(LIKE_API, params={'uid':uid,'server_name':region}, timeout=20, headers={'Accept':'application/json'})
        data=r.json()
        likes=data.get('LikesGivenByAPI', data.get('likes_given',data.get('likes',0)))
        ok=int(data.get('status',0) or 0) in (1,2)
        return jsonify({'ok':ok,'data':data,'likes_given':int(likes or 0)})
    except Exception:
        return jsonify({'ok':False,'error':'Like API is temporarily unavailable.'}),502

@app.route('/api/user', methods=['POST'])
def user():
    b=json_body(); uid=str(b.get('id') or uuid.uuid4().hex); name=str(b.get('name','Web User')); email=str(b.get('email',''))
    c=db(); c.execute('INSERT OR IGNORE INTO users(id,name,email,created_at) VALUES(?,?,?,?)',(uid,name,email,now())); c.commit()
    r=c.execute('SELECT * FROM users WHERE id=?',(uid,)).fetchone(); c.close()
    return jsonify(dict(r))

@app.route('/api/order', methods=['POST'])
def order():
    b=json_body(); user_id=str(b.get('user_id','web')); uid=str(b.get('uid','')).strip(); likes=int(b.get('likes',0) or 0); price=float(b.get('price',0) or 0)
    if not uid.isdigit() or likes<=0 or price<0: return jsonify({'ok':False,'error':'Invalid order data.'}),400
    oid='AS'+str(int(time.time()*1000))[-10:]
    c=db(); c.execute('INSERT INTO orders(id,user_id,uid,likes,price,status,created_at) VALUES(?,?,?,?,?,?,?)',(oid,user_id,uid,likes,price,'PENDING_PAYMENT',now())); c.commit(); c.close()
    return jsonify({'ok':True,'order_id':oid})

@app.route('/api/payment/create', methods=['POST'])
def payment_create():
    if not BOHUDUR_API_KEY: return jsonify({'ok':False,'error':'Bohudur API key is not configured on the server.'}),500
    b=json_body(); amount=float(b.get('amount',0) or 0); name=str(b.get('name','AS LIKE USER')); email=str(b.get('email','webuser@example.com'))
    if amount<=0: return jsonify({'ok':False,'error':'Invalid amount.'}),400
    origin=request.host_url.rstrip('/')
    payload={'full_name':name,'email':email,'amount':amount,'return_type':'GET','redirect_url':origin+'/api/payment/return','cancel_url':origin+'/payment-cancel.html','metadata':{'user_id':str(b.get('user_id','web')),'order_id':str(b.get('order_id',''))}}
    try:
        r=requests.post(BOHUDUR_BASE+'/create/v2/',json=payload,headers={'Content-Type':'application/json','AH-BOHUDUR-API-KEY':BOHUDUR_API_KEY},timeout=20)
        data=r.json();
        if data.get('status')!='success': return jsonify({'ok':False,'error':data.get('message','Payment creation failed.')}),502
        pid=data.get('paymentkey',''); c=db(); c.execute('INSERT INTO payments(id,user_id,amount,status,paymentkey,created_at,result) VALUES(?,?,?,?,?,?,?)',(pid,str(b.get('user_id','web')),amount,'PENDING',pid,now(),json.dumps(data))); c.commit(); c.close()
        return jsonify({'ok':True,'paymentkey':pid,'payment_url':data.get('payment_url')})
    except Exception:
        return jsonify({'ok':False,'error':'Payment gateway connection failed.'}),502

@app.route('/api/payment/return')
def payment_return():
    key=request.args.get('paymentkey','').strip()
    if not key: return redirect('/payment-result.html?status=missing')
    if not BOHUDUR_API_KEY: return redirect('/payment-result.html?status=config')
    try:
        q=requests.post(BOHUDUR_BASE+'/query/v2/',json={'paymentkey':key},headers={'Content-Type':'application/json','AH-BOHUDUR-API-KEY':BOHUDUR_API_KEY},timeout=20).json()
        if q.get('status')!='COMPLETED': return redirect('/payment-result.html?status='+str(q.get('status','FAILED')).lower())
        ex=requests.post(BOHUDUR_BASE+'/execute/v2/',json={'paymentkey':key},headers={'Content-Type':'application/json','AH-BOHUDUR-API-KEY':BOHUDUR_API_KEY},timeout=20).json()
        status='success' if ex.get('status')=='EXECUTED' else 'failed'
        c=db(); c.execute('UPDATE payments SET status=?, result=? WHERE paymentkey=?',(ex.get('status',status.upper()),json.dumps(ex),key)); c.commit()
        meta=ex.get('metadata') or q.get('metadata') or {}
        if isinstance(meta,list): meta={}
        order_id=str(meta.get('order_id',''))
        if status=='success' and order_id:
            row=c.execute('SELECT * FROM orders WHERE id=?',(order_id,)).fetchone()
            if row:
                try:
                    lr=requests.get(LIKE_API,params={'uid':row['uid'],'server_name':REGION},timeout=20,headers={'Accept':'application/json'})
                    ld=lr.json(); given=int(ld.get('LikesGivenByAPI',ld.get('likes_given',ld.get('likes',0))) or 0)
                    new_status='COMPLETED' if given>=int(row['likes']) else 'ACTIVE'
                    c.execute('UPDATE orders SET status=?, result=? WHERE id=?',(new_status,json.dumps({'likes_given':given,'api':ld}),order_id))
                    c.commit()
                except Exception as e:
                    c.execute('UPDATE orders SET status=?, result=? WHERE id=?',('ACTIVE',json.dumps({'delivery_error':'Like API temporarily unavailable'}),order_id)); c.commit()
        c.close()
        return redirect('/payment-result.html?status='+status)
    except Exception:
        return redirect('/payment-result.html?status=error')

@app.route('/api/admin/stats')
def admin_stats():
    c=db(); users=c.execute('SELECT COUNT(*) n FROM users').fetchone()['n']; orders=c.execute('SELECT COUNT(*) n FROM orders').fetchone()['n']; payments=c.execute('SELECT COUNT(*) n FROM payments').fetchone()['n']; revenue=c.execute("SELECT COALESCE(SUM(amount),0) n FROM payments WHERE status='EXECUTED'").fetchone()['n']; c.close()
    return jsonify({'users':users,'orders':orders,'payments':payments,'revenue':revenue,'site':setting('site',{}),'packages':setting('packages',DEFAULT_PACKAGES)})

@app.route('/api/admin/settings', methods=['POST'])
def admin_settings():
    b=json_body()
    if 'site' in b and isinstance(b['site'],dict): save_setting('site',b['site'])
    if 'packages' in b and isinstance(b['packages'],list): save_setting('packages',b['packages'])
    return jsonify({'ok':True,'site':setting('site',{}),'packages':setting('packages',DEFAULT_PACKAGES)})

@app.route('/api/admin/orders')
def admin_orders():
    c=db(); rows=[dict(x) for x in c.execute('SELECT * FROM orders ORDER BY created_at DESC LIMIT 100').fetchall()]; c.close(); return jsonify(rows)

@app.route('/payment-result.html')
def payment_result(): return send_from_directory('.', 'payment-result.html')
@app.route('/payment-cancel.html')
def payment_cancel(): return send_from_directory('.', 'payment-cancel.html')

if __name__=='__main__':
    app.run(host='0.0.0.0',port=int(os.getenv('PORT','5000')),debug=False)
