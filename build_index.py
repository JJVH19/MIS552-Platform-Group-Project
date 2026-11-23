"""Generate persisted semantic embeddings. Requires sentence-transformers and initial model download."""
from pathlib import Path
import numpy as np
from features.retrieval import ROOT, _prepared, _embedding_model

def main():
    model=_embedding_model()
    if model is None:raise RuntimeError('Install sentence-transformers and download MiniLM before building the semantic index')
    for kind in ('courts','events'):
        _,texts,_=_prepared(kind)
        vectors=model.encode(texts,normalize_embeddings=True,convert_to_numpy=True)
        (ROOT / "indexes").mkdir(parents=True, exist_ok=True)
        out=ROOT/'indexes'/f'{kind}_embeddings.npy';np.save(out,vectors)
        print(f'{kind}: {vectors.shape} -> {out}')
if __name__=='__main__':main()
