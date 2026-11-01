import json,csv,collections,re,pickle,sys
D='./hpo_sorgenti/'
g=json.load(open(D+'hp.json'))['graphs'][0]
cid=lambda u:u.split('/')[-1].replace('_',':')
lab={};obs=set()
for n in g['nodes']:
    if 'HP_' not in n['id']: continue
    i=cid(n['id']);lab[i]=n.get('lbl','')
    if n.get('meta',{}).get('deprecated'): obs.add(i)
par=collections.defaultdict(set)
for e in g['edges']:
    if e['pred']=='is_a': par[cid(e['sub'])].add(cid(e['obj']))
anc={}
def A(t):
    if t in anc: return anc[t]
    s={t}
    for p in par.get(t,()): s|=A(p)
    anc[t]=s; return s
sys.setrecursionlimit(10000)
it={r['subject_id']:r['translation_value'] for r in csv.DictReader(open(D+'hp-it.babelon.tsv'),delimiter='\t') if r['predicate_id']=='rdfs:label'}
AREAS={
 'V':['HP:0000478'],
 'U':['HP:0000364','HP:0011390','HP:0025112','HP:5200060','HP:5200062','HP:0002183','HP:0000360'],
 'M':['HP:0100022','HP:0003808','HP:0001270','HP:0031826','HP:0011443','HP:0001288','HP:0001324','HP:0001751','HP:0002650','HP:0002808','HP:0003307','HP:0001382','HP:0002172'],
 'L':['HP:0012759','HP:0000708','HP:0002167','HP:0011968','HP:0002015','HP:0002307','HP:0030190','HP:0100703','HP:6000463','HP:0003763','HP:0002360','HP:5200058','HP:4000079'],
 'F':['HP:0000271','HP:0000234','HP:0000464','HP:0040064','HP:0001507','HP:0000356','HP:0000163','HP:0001595','HP:0001000','HP:0001597'],
}
ALERT={'Crisi epilettiche':['HP:0001250'],'Malformazioni SNC':['HP:0002011'],'Cuore':['HP:0001626'],'Reni/genitali':['HP:0000119'],'Endocrino':['HP:0000818'],'Metabolismo':['HP:0001939'],'Immunità':['HP:0002715'],'Sangue':['HP:0001871'],'Respiro':['HP:0002086'],'Digerente':['HP:0025031'],'Tumori':['HP:0002664']}
for k,v in list(AREAS.items())+list(ALERT.items()):
    for x in v: assert x in lab,(k,x)
def areas_of(t):
    a=A(t); r=[k for k,v in AREAS.items() if a&set(v)]
    if 'HP:0001270' in a and 'L' in r: r.remove('L')
    return r
def alerts_of(t):
    a=A(t); return [k for k,v in ALERT.items() if a&set(v)]
FQ={'HP:0040280':1.0,'HP:0040281':0.9,'HP:0040282':0.55,'HP:0040283':0.17,'HP:0040284':0.025,'HP:0040285':0.0}
def fw(f):
    if not f: return None
    if f in FQ: return FQ[f]
    m=re.match(r'(\d+)/(\d+)$',f)
    if m: return int(m[1])/max(1,int(m[2]))
    m=re.match(r'([\d.]+)%$',f)
    if m: return float(m[1])/100
    return None
INH={'HP:0000006':'AD','HP:0000007':'AR','HP:0001417':'X','HP:0001419':'XR','HP:0001423':'XD','HP:0001427':'mitocondriale','HP:0001426':'multifattoriale','HP:0001442':'somatico (mosaico)','HP:0001450':'Y','HP:0003745':'sporadico','HP:0001425':'eterogeneo','HP:0010982':'poligenico','HP:0010984':'digenico','HP:0032113':'semidominante','HP:0001428':'mosaico somatico'}
ONS={'HP:0030674':'prenatale','HP:0011460':'embrionale','HP:0011461':'fetale','HP:0003577':'congenito','HP:0003623':'neonatale','HP:0003593':'infantile (1-12 mesi)','HP:0011463':'infanzia (1-5 a)','HP:0003621':'giovanile (5-15 a)','HP:0003581':'età adulta','HP:0011462':'giovane adulto','HP:0003596':'età adulta media','HP:0003584':'tardivo','HP:0410280':'pediatrico','HP:0034199':'tardo-fetale','HP:0034197':'terzo trimestre'}
dis={}
for l in open(D+'phenotype.hpoa'):
    if l.startswith('#') or l.startswith('database_id'): continue
    f=l.rstrip('\n').split('\t')
    db,name,q,h,ref,ev,on,fr,sex,mod,asp=f[:11]
    if not (db.startswith('OMIM') or db.startswith('DECIPHER')): continue
    d=dis.setdefault(db,{'id':db,'name':name,'P':{},'inh':set(),'ons':set()})
    if q=='NOT': continue
    if asp=='I': 
        if h in INH: d['inh'].add(INH[h])
        continue
    if asp=='C':
        if h in ONS: d['ons'].add(ONS[h])
        continue
    if asp!='P': continue
    w=fw(fr)
    old=d['P'].get(h,-1)
    val=w if w is not None else -0.5  # -0.5 = unknown frequency
    if old==-1 or (val>=0 and (old<0 or val>old)): d['P'][h]=val
genes=collections.defaultdict(set)
for r in csv.DictReader(open(D+'genes_to_disease.txt'),delimiter='\t'):
    genes[r['disease_id']].add(r['gene_symbol'])
out=[]
for d in dis.values():
    if not d['P']: continue
    rec={'id':d['id'],'name':d['name'],'genes':sorted(genes.get(d['id'],())),'inh':sorted(d['inh']),'ons':sorted(d['ons']),'areas':{k:[] for k in AREAS},'alerts':collections.Counter(),'n':len(d['P']),'terms':dict(d['P'])}
    for h,w in d['P'].items():
        ww=0.5 if w<0 else w
        if ww==0: continue
        for a in areas_of(h): rec['areas'][a].append((h,ww,w<0))
        for a in alerts_of(h): rec['alerts'][a]+=1
    for a in rec['areas']: rec['areas'][a].sort(key=lambda x:(-x[1],lab.get(x[0],'')))
    rec['score']={a:round(sum(x[1] for x in v),2) for a,v in rec['areas'].items()}
    out.append(rec)
out.sort(key=lambda r:re.sub(r'[^a-z0-9 ]','',r['name'].lower()))
used=set(h for r in out for h in r['terms'])
for h in used: A(h)
pickle.dump({'dis':out,'lab':lab,'it':it,'anc':{h:anc[h] for h in used},'AREAS':AREAS},open('data.pkl','wb'))
print(len(out))
import statistics
for a in AREAS: 
    s=[r['score'][a] for r in out]; print(a, sum(1 for x in s if x>0), statistics.mean(s), max(s))
