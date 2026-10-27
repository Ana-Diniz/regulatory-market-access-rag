# Regulatory Market Access RAG

Protótipo de recuperação e extração estruturada de informações em relatórios regulatórios (por exemplo, relatórios da Conitec). O sistema indexa PDFs locais, recupera trechos com ChromaDB e solicita a um modelo da API Groq uma extração estruturada, acompanhada de referências para conferência humana.

> **Status:** protótipo experimental. A presença de uma citação no documento **não comprova** que a interpretação do modelo está correta. Não utilize as saídas como decisões regulatórias sem revisão humana.

## Arquitetura

1. `ingest.py`: extrai texto de cada página com PyMuPDF e divide em blocos com `RecursiveCharacterTextSplitter`.
2. `build_db.py`: gera embeddings locais (`sentence-transformers/all-MiniLM-L6-v2`) e indexa os blocos no ChromaDB, na coleção `regulatory_reports`.
3. `extract.py`: recupera trechos da **mesma coleção**, solicita saída tipada ao modelo Groq e associa cada campo a um ID de fonte e trecho literal.
4. `schemas.py` e `provenance.py`: validam formato, valores permitidos e se o trecho citado aparece na fonte recuperada.

**Privacidade:** o PDF e os embeddings são processados localmente, mas o **texto dos trechos recuperados é enviado à API Groq** para extração. Os caminhos locais dos arquivos ficam apenas no mapa de auditoria local; o prompt externo contém IDs de fonte e páginas, sem os caminhos dos arquivos. Não envie documentos confidenciais sem autorização e avaliação dos termos do provedor.

## Requisitos e execução

Python 3.10+ e conexão com a internet para instalar dependências, baixar o modelo de embeddings na primeira execução e consultar a API Groq.

```bash
python -m venv .venv
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
# Linux/macOS: source .venv/bin/activate
python -m pip install -r requirements.txt
```

Copie `.env.example` para `.env` e preencha `GROQ_API_KEY`. Nunca versionar a chave.

Coloque PDFs com **texto selecionável** em `data/`. Arquivos digitalizados sem OCR podem não produzir trechos. Em seguida:

```bash
python build_db.py --input data --db chroma_db
python extract.py --db chroma_db --k 6
```

É possível indexar um único PDF com `--input data/arquivo.pdf` e escolher um modelo Groq disponível usando `--model` ou `GROQ_MODEL`.

O programa imprime um JSON com `tecnologia_avaliada`, `desfecho` e `ano_decisao`. Cada campo inclui `valor`, `status`, `fonte` (ID, documento e página) e `trecho`. Um campo só mantém o valor se o trecho informado estiver presente na fonte indicada; caso contrário, `valor` é `null`.

O status `trecho_localizado` confirma apenas uma correspondência textual; não verifica automaticamente a interpretação clínica ou regulatória. O ano representa a **publicação do relatório**, não necessariamente a decisão administrativa final.

## Testes

Os testes unitários de proveniência e schema não usam LLM, PDFs externos ou rede:

```bash
python -m unittest discover -s tests -v
```

A execução ponta a ponta com PDF real, ChromaDB e API Groq ainda requer validação em ambiente configurado.

## Limitações e próximos passos

- A busca semântica pode não recuperar o trecho correto; revisar resultados e métricas de recuperação.
- O fragmentador é baseado em caracteres/separadores, não em análise semântica do conteúdo.
- A normalização do desfecho exige revisão humana e pode depender do contexto da recomendação.
- Não há persistência relacional, interface de auditoria nem benchmark de qualidade.
- Planejado: avaliação com exemplos anotados, SQLite, interface de revisão e métricas de precisão de citações.
