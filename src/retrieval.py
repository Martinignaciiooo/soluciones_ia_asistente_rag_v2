"""Recuperación híbrida con vectores recibidos de OpenRouter y ranking BM25."""
from __future__ import annotations
import hashlib
import json
import math
from pathlib import Path
from collections import Counter
from src.ingest import cargar_corpus
from src.lexical import RecuperadorLexico, Resultado, fusionar_rrf

class Retrieval:
    def __init__(self, encoder, data_dir=None, cache_dir='runtime'):
        self.encoder=encoder
        root=Path(__file__).resolve().parents[1]
        directory=Path(data_dir) if data_dir else root/'data/interna'
        self.fragments=cargar_corpus(directory,700,120)
        if not self.fragments:raise RuntimeError('No se encontraron documentos .md del manual en la carpeta del corpus.')
        counts=Counter(f.metadatos['archivo'] for f in self.fragments)
        self.manifest={'carpeta':'data/interna' if data_dir is None else str(directory),
                       'chunk_size_caracteres':700,'chunk_overlap_caracteres':120,
                       'modelo_embeddings':encoder.model_id,'fragmentos_indexados':len(self.fragments),
                       'archivos':[{'archivo':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
                                    'fragmentos':counts[p.name]} for p in sorted(directory.glob('*.md'))]}
        self.lexical=RecuperadorLexico(self.fragments)
        texts=[f.texto for f in self.fragments]
        fingerprint=hashlib.sha256((encoder.model_id+json.dumps(texts,ensure_ascii=False)).encode()).hexdigest()
        cache=Path(cache_dir)/'corpus_vectors.json'; cache.parent.mkdir(parents=True,exist_ok=True)
        saved=json.loads(cache.read_text()) if cache.exists() else {}
        if saved.get('fingerprint')==fingerprint: self.vectors=saved['vectors']
        else:
            self.vectors=encoder.encode(texts)
            cache.write_text(json.dumps({'fingerprint':fingerprint,'vectors':self.vectors}))
        (cache.parent/'corpus_manifest.json').write_text(json.dumps(self.manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    def search(self, query, k=4):
        v=self.encoder.encode([query])[0]
        scored=sorted([(sum(a*b for a,b in zip(v,other)),i) for i,other in enumerate(self.vectors)],reverse=True)
        semantic=[Resultado(self.fragments[i],float(s),'vectorial') for s,i in scored[:k] if s>=0.38]
        lexical=self.lexical.buscar(query,k)
        # El valor de RRF sólo ordena. No se usa como umbral de confianza.
        return fusionar_rrf([lexical,semantic],k)
