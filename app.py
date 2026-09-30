"""ICU Atlas: local research-workspace demo. Synthetic examples only; never upload restricted data."""
import os
import re
import secrets
import sqlite3
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
from flask import Flask, g, jsonify, request, send_from_directory, session
from werkzeug.security import generate_password_hash, check_password_hash

ROOT = Path(__file__).resolve().parent
# On Render, set ICU_ATLAS_DATA_DIR=/var/data and attach a paid persistent disk
# mounted at /var/data. The default is local-only runtime state.
INSTANCE = Path(os.environ.get('ICU_ATLAS_DATA_DIR', str(ROOT / 'instance'))).expanduser().resolve()
INSTANCE.mkdir(parents=True, exist_ok=True)
SECRET_FILE = INSTANCE / 'flask-secret.txt'
if not SECRET_FILE.exists():
    SECRET_FILE.write_text(secrets.token_hex(40))
    os.chmod(SECRET_FILE, 0o600)
app = Flask(__name__, static_folder='static', static_url_path='/static')
app.secret_key = os.environ.get('ICU_ATLAS_SECRET', SECRET_FILE.read_text().strip())
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax', PERMANENT_SESSION_LIFETIME=60*60*24*14, MAX_CONTENT_LENGTH=1024*1024)
DB = INSTANCE / 'atlas.sqlite3'

def utc(): return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
def db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB)
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA foreign_keys = ON')
    return g.db
@app.teardown_appcontext
def close_db(exc):
    connection = g.pop('db', None)
    if connection: connection.close()

def init_db():
    con = sqlite3.connect(DB)
    con.executescript('''
    PRAGMA foreign_keys = ON;
    CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL, created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS datasets (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), name TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'Candidate', version TEXT NOT NULL DEFAULT '', source_url TEXT NOT NULL DEFAULT '', access TEXT NOT NULL DEFAULT 'Credentialed', description TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS models (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), name TEXT NOT NULL, family TEXT NOT NULL DEFAULT 'Other', description TEXT NOT NULL DEFAULT '', parameters TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS experiments (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), name TEXT NOT NULL, dataset_id INTEGER NOT NULL REFERENCES datasets(id) ON DELETE RESTRICT, model_id INTEGER NOT NULL REFERENCES models(id) ON DELETE RESTRICT, status TEXT NOT NULL DEFAULT 'Planned', landmark_hours INTEGER NOT NULL DEFAULT 24, split TEXT NOT NULL DEFAULT 'Temporal holdout', seed INTEGER NOT NULL DEFAULT 42, cohort_size INTEGER, auroc REAL, auprc REAL, brier REAL, mae REAL, rmse REAL, r2 REAL, evidence TEXT NOT NULL DEFAULT 'Author-entered aggregate', summary TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS observations (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), experiment_id INTEGER REFERENCES experiments(id) ON DELETE SET NULL, theme TEXT NOT NULL DEFAULT 'Methodology', sentiment TEXT NOT NULL DEFAULT 'Neutral', body TEXT NOT NULL, created_at TEXT NOT NULL);
    CREATE INDEX IF NOT EXISTS idx_experiments_user ON experiments(user_id);
    CREATE INDEX IF NOT EXISTS idx_observations_user ON observations(user_id);
    ''')
    user = con.execute('SELECT id FROM users WHERE email=?', ('demo@icuatlas.app',)).fetchone()
    if not user:
        cur = con.execute('INSERT INTO users(name,email,password_hash,created_at) VALUES(?,?,?,?)', ('Alex Morgan', 'demo@icuatlas.app', generate_password_hash('demo1234'), utc()))
        u = cur.lastrowid
        datasets = [
            ('MIMIC-IV','Primary candidate','3.1','https://physionet.org/content/mimiciv/3.1/','Credentialed','Single-center development configuration. This workspace contains no MIMIC patient records.'),
            ('eICU-CRD','External candidate','2.0','https://physionet.org/content/eicu-crd/2.0/','Credentialed','Multicenter external-test configuration. This workspace contains no eICU patient records.'),
        ]
        ds=[]
        for name,role,version,url,access,desc in datasets:
            ds.append(con.execute('INSERT INTO datasets(user_id,name,role,version,source_url,access,description,created_at) VALUES(?,?,?,?,?,?,?,?)',(u,name,role,version,url,access,desc,utc())).lastrowid)
        models=[
            ('Poly-hypergraph net','Hypergraph','Illustrative multi-relation temporal architecture; not a trained model.','Temporal encoder + history-only hyperedges'),
            ('Temporal convolution','Sequence','Matched 24-hour causal convolution baseline.','Kernel 3 · 2 layers'),
            ('GRU baseline','Sequence','Matched 24-hour recurrent baseline.','Hidden size 64'),
            ('Pairwise graph net','Graph','Pairwise historical-context control.','Same temporal encoder'),
        ]
        ms=[]
        for row in models:
            ms.append(con.execute('INSERT INTO models(user_id,name,family,description,parameters,created_at) VALUES(?,?,?,?,?,?)',(u,*row,utc())).lastrowid)
        ex=[
            ('Proposed model · internal holdout',ds[0],ms[0],'Completed',24,'Chronological test',42,3100,.842,.427,.118,1.82,2.49,.69,'DEMO SYNTHETIC','Illustrative metrics only. Never cite in a paper.'),
            ('TCN · matched baseline',ds[0],ms[1],'Completed',24,'Chronological test',42,3100,.817,.391,.127,2.04,2.76,.62,'DEMO SYNTHETIC','Illustrative metrics only. Never cite in a paper.'),
            ('GRU · matched baseline',ds[0],ms[2],'Completed',24,'Chronological test',42,3100,.803,.372,.134,2.18,2.91,.58,'DEMO SYNTHETIC','Illustrative metrics only. Never cite in a paper.'),
            ('Pairwise graph · control',ds[0],ms[3],'Completed',24,'Chronological test',42,3100,.825,.401,.124,1.97,2.64,.65,'DEMO SYNTHETIC','Illustrative metrics only. Never cite in a paper.'),
            ('External prototype · eICU',ds[1],ms[0],'Completed',24,'External candidate',42,2500,.782,.312,.145,2.31,3.18,.49,'DEMO SYNTHETIC','Illustrative numbers, not eICU findings or external validation.'),
            ('eICU TCN · reference',ds[1],ms[1],'Completed',24,'External candidate',42,2500,.764,.298,.151,2.44,3.31,.45,'DEMO SYNTHETIC','Illustrative numbers, not eICU findings.'),
        ]
        ids=[]
        for row in ex:
            ids.append(con.execute('INSERT INTO experiments(user_id,name,dataset_id,model_id,status,landmark_hours,split,seed,cohort_size,auroc,auprc,brier,mae,rmse,r2,evidence,summary,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(u,*row,utc(),utc())).lastrowid)
        observations=[
            (ids[0],'Leakage audit','Attention','Graph neighbors should be drawn only from historical reference stays; audit timestamps before any real run.'),
            (ids[0],'Interpretation','Neutral','A shorter ICU stay is not necessarily better: death can shorten the remaining-stay target.'),
            (ids[4],'Transportability','Caution','External evaluation requires harmonized mortality endpoint, unit coding and 24-hour features.'),
            (ids[1],'Missingness','Opportunity','Compare naturally observed laboratory ordering strata instead of calling random blocks MNAR.'),
        ]
        for exid,theme,sentiment,body in observations:
            con.execute('INSERT INTO observations(user_id,experiment_id,theme,sentiment,body,created_at) VALUES(?,?,?,?,?,?)',(u,exid,theme,sentiment,body,utc()))
    con.commit(); con.close()
init_db()

def err(message, status=400): return jsonify({'error':message}), status
def current_user(): return session.get('user_id')
def logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if not current_user(): return err('Please sign in to continue.',401)
        return f(*args, **kwargs)
    return wrap
@app.before_request
def csrf_check():
    if request.path.startswith('/api/') and request.method in ('POST','PUT','PATCH','DELETE') and request.path not in ('/api/auth/login','/api/auth/register'):
        if not current_user(): return err('Please sign in to continue.',401)
        if request.headers.get('X-CSRF-Token') != session.get('csrf'): return err('Session expired. Refresh and try again.',403)

def payload():
    val=request.get_json(silent=True)
    return val if isinstance(val,dict) else {}
def one_user_row(table, pk):
    return db().execute(f'SELECT * FROM {table} WHERE id=? AND user_id=?',(pk,current_user())).fetchone()
def records(table):
    if table=='experiments':
        return [dict(r) for r in db().execute('''SELECT e.*,d.name AS dataset_name,m.name AS model_name,m.family AS model_family FROM experiments e JOIN datasets d ON d.id=e.dataset_id JOIN models m ON m.id=e.model_id WHERE e.user_id=? ORDER BY e.updated_at DESC,e.id DESC''',(current_user(),))]
    if table=='observations':
        return [dict(r) for r in db().execute('''SELECT o.*,e.name AS experiment_name FROM observations o LEFT JOIN experiments e ON e.id=o.experiment_id WHERE o.user_id=? ORDER BY o.created_at DESC,o.id DESC''',(current_user(),))]
    return [dict(r) for r in db().execute(f'SELECT * FROM {table} WHERE user_id=? ORDER BY id DESC',(current_user(),))]
@app.get('/')
def index():return send_from_directory(ROOT/'static','index.html')

@app.get('/healthz')
def healthz():
    try:
        db().execute('SELECT 1')
        return jsonify({'status':'ok'})
    except sqlite3.Error:
        return jsonify({'status':'unavailable'}), 503
@app.get('/api/auth/me')
def me():
    u=current_user()
    if not u:return jsonify({'user':None})
    row=db().execute('SELECT id,name,email FROM users WHERE id=?',(u,)).fetchone()
    return jsonify({'user':dict(row) if row else None,'csrf':session.get('csrf')})
@app.post('/api/auth/login')
def login():
    x=payload(); email=str(x.get('email','')).strip().lower(); pw=str(x.get('password',''))
    row=db().execute('SELECT * FROM users WHERE email=?',(email,)).fetchone()
    if not row or not check_password_hash(row['password_hash'],pw):return err('Incorrect email or password.',401)
    session.clear(); session['user_id']=row['id']; session['csrf']=secrets.token_urlsafe(32);session.permanent=True
    return jsonify({'user':{'id':row['id'],'name':row['name'],'email':row['email']},'csrf':session['csrf']})
@app.post('/api/auth/register')
def register():
    x=payload(); name=str(x.get('name','')).strip(); email=str(x.get('email','')).strip().lower(); pw=str(x.get('password',''))
    if len(name)<2 or len(name)>90 or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email) or len(pw)<8: return err('Enter a name, valid email and password of at least 8 characters.')
    try:
        c=db().execute('INSERT INTO users(name,email,password_hash,created_at) VALUES(?,?,?,?)',(name,email,generate_password_hash(pw),utc()));db().commit()
    except sqlite3.IntegrityError:return err('That email is already registered.',409)
    session.clear();session['user_id']=c.lastrowid;session['csrf']=secrets.token_urlsafe(32);session.permanent=True
    return jsonify({'user':{'id':c.lastrowid,'name':name,'email':email},'csrf':session['csrf']}),201
@app.post('/api/auth/logout')
def logout():session.clear();return jsonify({'ok':True})
@app.get('/api/bootstrap')
@logged_in
def bootstrap():return jsonify({'datasets':records('datasets'),'models':records('models'),'experiments':records('experiments'),'observations':records('observations')})

FIELDS={
 'datasets': ['name','role','version','source_url','access','description'],
 'models': ['name','family','description','parameters'],
 'experiments': ['name','dataset_id','model_id','status','landmark_hours','split','seed','cohort_size','auroc','auprc','brier','mae','rmse','r2','evidence','summary'],
 'observations': ['experiment_id','theme','sentiment','body'],
}
TEXT_LIMIT={'name':120,'role':50,'version':50,'source_url':500,'access':50,'description':3000,'family':50,'parameters':2000,'status':50,'split':100,'evidence':60,'summary':3000,'theme':80,'sentiment':30,'body':3000}

def validate(table, values, old=None):
    data={}
    for k,v in values.items():
        if k not in FIELDS[table]:continue
        if k in ('dataset_id','model_id','experiment_id','landmark_hours','seed','cohort_size'):
            if v is None or v=='':
                if k in ('experiment_id','cohort_size'):data[k]=None;continue
                return None,f'{k.replace("_"," ")} is required.'
            try: v=int(v)
            except (ValueError,TypeError):return None,f'{k} must be an integer.'
            if k not in ('seed',) and v<=0:return None,f'{k} must be positive.'
            if k=='landmark_hours' and v>720:return None,'Landmark must be at most 720 hours.'
            if k=='cohort_size' and v>100000000:return None,'Cohort size is too large.'
        elif k in ('auroc','auprc','brier','mae','rmse','r2'):
            if v is None or v=='':data[k]=None;continue
            try:v=float(v)
            except (ValueError,TypeError):return None,f'{k} must be numeric.'
            if not (-1e8<v<1e8):return None,f'{k} must be finite.'
            if k in ('auroc','auprc','brier') and not 0<=v<=1:return None,f'{k} must be between 0 and 1.'
            if k in ('mae','rmse') and v<0:return None,f'{k} cannot be negative.'
            if k=='r2' and v>1:return None,'R² cannot exceed 1.'
        else:
            v=str(v or '').strip()
            if len(v)>TEXT_LIMIT.get(k,2000):return None,f'{k} is too long.'
            if k=='source_url' and v and not v.startswith(('https://','http://')):return None,'Source URL must start with http:// or https://.'
        data[k]=v
    merged={**(dict(old) if old else {}),**data}
    mandatory={'datasets':['name'],'models':['name'],'experiments':['name','dataset_id','model_id'],'observations':['body']}[table]
    for field in mandatory:
        if not merged.get(field):return None,f'{field.replace("_"," ").capitalize()} is required.'
    if table=='experiments':
        for kind in ('datasets','models'):
            fk='dataset_id' if kind=='datasets' else 'model_id'
            if not one_user_row(kind,merged[fk]):return None,f'Select one of your {kind}.'
        if merged.get('evidence') not in ('DEMO SYNTHETIC','Author-entered aggregate','Verified by author'):
            data['evidence']='Author-entered aggregate'
    if table=='observations' and merged.get('experiment_id') and not one_user_row('experiments',merged['experiment_id']):return None,'Select one of your experiments.'
    return data,None

@app.route('/api/<kind>',methods=['GET','POST'])
@logged_in
def collection(kind):
    if kind not in FIELDS:return err('Unknown resource.',404)
    if request.method=='GET':return jsonify(records(kind))
    x=payload(); data,error=validate(kind,x)
    if error:return err(error)
    data['user_id']=current_user();data['created_at']=utc()
    if kind=='experiments':data['updated_at']=utc()
    cols=list(data);sql=f'INSERT INTO {kind} ({",".join(cols)}) VALUES ({",".join("?" for _ in cols)})'
    try: c=db().execute(sql,[data[k] for k in cols]);db().commit()
    except sqlite3.IntegrityError:return err('Could not save this record. Check references.',409)
    return jsonify({'id':c.lastrowid}),201
@app.route('/api/<kind>/<int:pk>',methods=['GET','PATCH','DELETE'])
@logged_in
def item(kind,pk):
    if kind not in FIELDS:return err('Unknown resource.',404)
    row=one_user_row(kind,pk)
    if not row:return err('Record not found.',404)
    if request.method=='GET':return jsonify(dict(row))
    if request.method=='DELETE':
        try:db().execute(f'DELETE FROM {kind} WHERE id=? AND user_id=?',(pk,current_user()));db().commit()
        except sqlite3.IntegrityError:return err('This item is used by an experiment. Remove those runs first.',409)
        return jsonify({'ok':True})
    data,error=validate(kind,payload(),row)
    if error:return err(error)
    if not data:return err('No valid fields to update.')
    if kind=='experiments':data['updated_at']=utc()
    cols=list(data); db().execute(f'UPDATE {kind} SET {",".join(k+"=?" for k in cols)} WHERE id=? AND user_id=?',[data[k] for k in cols]+[pk,current_user()]);db().commit()
    return jsonify({'ok':True})

if __name__=='__main__':app.run(host='0.0.0.0',port=int(os.environ.get('PORT','8000')),debug=False)
