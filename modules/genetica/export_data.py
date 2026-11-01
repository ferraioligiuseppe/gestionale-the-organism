import json,gzip,pickle,math,collections,csv
D='./hpo_sorgenti/'
g=json.load(open(D+'hp.json'))['graphs'][0]
cid=lambda u:u.split('/')[-1].replace('_',':')
lab={};obs=set();syn={}
for n in g['nodes']:
    if 'HP_' not in n['id']: continue
    i=cid(n['id']);lab[i]=n.get('lbl','')
    m=n.get('meta',{})
    if m.get('deprecated'): obs.add(i)
    syn[i]=[s['val'] for s in m.get('synonyms',[])][:4]
par=collections.defaultdict(set)
for e in g['edges']:
    if e['pred']=='is_a': par[cid(e['sub'])].add(cid(e['obj']))
import sys;sys.setrecursionlimit(10000)
anc={}
def A(t):
    if t in anc: return anc[t]
    s={t}
    for p in par.get(t,()): s|=A(p)
    anc[t]=s;return s
PA='HP:0000118'
pheno=[t for t in lab if t not in obs and PA in A(t)]
it={r['subject_id']:r['translation_value'] for r in csv.DictReader(open(D+'hp-it.babelon.tsv'),delimiter='\t') if r['predicate_id']=='rdfs:label'}
d=pickle.load(open('data.pkl','rb'))
dis=d['dis'];N=len(dis)
cnt=collections.Counter()
for r in dis:
    cl=set()
    for t in r['terms']: cl|=A(t)
    for a in cl: cnt[a]+=1
ic={t:round(-math.log(max(cnt[t],1)/N),3) for t in pheno}
idx={t:i for i,t in enumerate(sorted(pheno))}
terms=[]
for t in sorted(pheno):
    terms.append([t, it.get(t,''), lab[t], sorted(idx[p] for p in par.get(t,()) if p in idx), ic[t], syn.get(t,[])])
D_=[]
for r in dis:
    tt=[[idx[t], round(w,3)] for t,w in r['terms'].items() if t in idx and w!=0]
    D_.append([r['id'],r['name'],r['genes'],r['inh'],tt])
out={'version':'HPO 2026-09-01 / annotazioni 2026-09-02','n_diseases':N,'terms':terms,'diseases':D_}
with gzip.open('./data/hpo_genetica.json.gz','wt',encoding='utf-8') as f: json.dump(out,f,separators=(',',':'),ensure_ascii=False)
print(len(terms),N)
