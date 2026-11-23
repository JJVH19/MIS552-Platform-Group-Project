"""BM25 + embedding-based vector retrieval + Reciprocal Rank Fusion.

A local lexical TF-IDF fallback is provided when sentence-transformers isn't
installed or its model isn't available. It is explicitly labeled lexical,
never misrepresented as semantic retrieval.
"""
from __future__ import annotations
import json, math, re
from collections import Counter
from functools import lru_cache
from pathlib import Path
from typing import Literal
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
TOKEN_RE = re.compile(r"[a-z0-9]+(?:[-'][a-z0-9]+)?")

def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())

def documents(kind: Literal['courts','events']) -> list[dict]:
    filename = 'facilities.json' if kind == 'courts' else 'events.json'
    return json.loads((ROOT / 'data' / filename).read_text(encoding='utf8'))

def text_for(item:dict,kind:str)->str:
    if kind == 'courts':
        return ' '.join([item['name'],item['city'],item['description'],
             'indoor' if item['indoor'] else 'outdoor', ' '.join(item['amenities']),
             'basketball court gym venue facility'])
    return ' '.join([item['name'],item['city'],item['description'],item['format'],
             item['skill_level'],item['date'],'basketball tournament event'])

class BM25:
    def __init__(self,texts:list[str],k1:float=1.5,b:float=.75):
        self.docs=[tokenize(x) for x in texts];self.n=len(self.docs)
        self.dl=[len(x) for x in self.docs];self.avgdl=sum(self.dl)/max(self.n,1)
        self.tf=[Counter(x) for x in self.docs];df=Counter()
        for doc in self.docs:df.update(set(doc))
        self.idf={t:math.log(1+(self.n-c+.5)/(c+.5)) for t,c in df.items()}
        self.k1=k1;self.b=b
    def score(self,q:str)->np.ndarray:
        result=[]
        for tf,dl in zip(self.tf,self.dl):
            score=0.0
            for term in set(tokenize(q)):
                if term not in tf:continue
                freq=tf[term];score+=self.idf.get(term,0)*(freq*(self.k1+1))/(freq+self.k1*(1-self.b+self.b*dl/max(self.avgdl,1)))
            result.append(score)
        return np.array(result,dtype=float)

@lru_cache(maxsize=1)
def _embedding_model():
    try:
        from sentence_transformers import SentenceTransformer
        return SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
    except Exception:
        return None

@lru_cache(maxsize=2)
def _prepared(kind:str):
    items=documents(kind);texts=[text_for(it,kind) for it in items]
    return items,texts,BM25(texts)

@lru_cache(maxsize=2)
def _vectors(kind:str):
    model=_embedding_model()
    if model is None:return None
    _,texts,_=_prepared(kind)
    path=ROOT/'indexes'/f'{kind}_embeddings.npy'
    matrix=None
    if path.exists():
        try:
            candidate=np.load(path)
            if candidate.shape[0]==len(texts): matrix=candidate
        except Exception:pass
    if matrix is None:
        matrix=model.encode(texts,normalize_embeddings=True,convert_to_numpy=True)
    return np.asarray(matrix,dtype=float)

def vector_scores(query:str,kind:str):
    model=_embedding_model();matrix=_vectors(kind)
    if model is None or matrix is None:return None
    q=model.encode([query],normalize_embeddings=True,convert_to_numpy=True)[0]
    return matrix @ q

def _rank(scores:np.ndarray):
    return sorted(range(len(scores)),key=lambda i:(-float(scores[i]),i))

def search(query:str,kind:Literal['courts','events']='courts',method:str='hybrid',k:int=5)->dict:
    if not query.strip():return {'results':[],'mode':'none','warning':'Enter a search query.'}
    if method not in ('keyword','semantic','hybrid'):raise ValueError('Invalid search method')
    items,texts,bm=_prepared(kind);keyword=bm.score(query);semantic=vector_scores(query,kind)
    warning=None
    if semantic is None:
        # Lexical fallback is not semantic: label this explicitly in the UI.
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        cv=TfidfVectorizer(ngram_range=(1,2));mat=cv.fit_transform(texts)
        semantic=cosine_similarity(cv.transform([query]),mat).ravel()
        mode='lexical TF-IDF fallback (no sentence-transformer model)'
        warning='Semantic model unavailable. Vector/hybrid rankings currently use lexical TF-IDF, not semantic embeddings.'
    else:mode='MiniLM semantic embeddings'
    r1=_rank(keyword);r2=_rank(semantic)
    if method=='keyword':order=r1;scores=keyword
    elif method=='semantic':order=r2;scores=semantic
    else:
        rrf=np.zeros(len(items),dtype=float)
        for ranking in (r1,r2):
            for rank,ix in enumerate(ranking,start=1):rrf[ix]+=1/(60+rank)
        order=_rank(rrf);scores=rrf
    out=[]
    for ix in order[:max(0,min(int(k),len(items)))]:
        record=dict(items[ix]);record['score']=round(float(scores[ix]),6)
        record['why_match']=f"Search match based on {method} ranking of its title, city, details and attributes; inspect the listing to verify constraints."
        out.append(record)
    return {'results':out,'mode':mode,'warning':warning}

def search_courts(query:str,method='hybrid',k=5)->list[dict]:
    return search(query,'courts',method,k)['results']

def search_events(query:str,method='hybrid',k=5)->list[dict]:
    return search(query,'events',method,k)['results']
