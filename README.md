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

É possível indexar um único PDF com `--input data/arquivo.pdf` e escolher um modelo Groq disponível usando `--model` ou `GROQ_MODEL`. O comando `extract.py` também aceita `--query` para escolher o texto da busca semântica.

**Limites da Groq:** a extração reserva por padrão até **700 tokens de saída** para funcionar em contas com limite de 1.000 tokens de saída por minuto (OTPM). Pode-se ajustar com `--max-output-tokens N`, conforme a cota da conta e o tamanho do JSON esperado. Isso não altera o limite de tokens de entrada, nem garante que requisições próximas não atinjam a cota por minuto. Se a Groq responder com HTTP 429, verifique o tipo de limite e aguarde a liberação da cota, sem necessidade de recriar o banco vetorial.

**Ao indexar vários PDFs**, selecione o relatório para a extração, evitando misturar evidências de documentos diferentes:

```bash
python extract.py --db chroma_db --k 6 --document data/arquivo.pdf
```

O caminho de `--document` deve corresponder a um PDF já indexado. Se houver apenas um relatório no banco, a seleção é automática. Com mais de um relatório, `--document` é obrigatório. A recuperação usa um filtro por documento antes de selecionar os trechos.

O programa imprime um JSON com **cinco campos independentes**:

- `tecnologia_avaliada`: nome do medicamento ou da tecnologia, sem a indicação clínica;
- `indicacao_clinica`: doença e/ou população-alvo descrita no relatório;
- `desfecho`: `Favorável`, `Desfavorável` ou `Condicionado`;
- `ano_relatorio`: ano de publicação do relatório;
- `ano_decisao`: ano de uma deliberação/decisão datada, quando houver evidência textual distinta. Se não houver, deve ser `null`.

Cada campo inclui `valor`, `status`, `fonte` (ID, documento e página) e `trecho`. O validador mantém o valor somente quando consegue localizar o trecho no documento, validar página/fonte e, para tecnologia, indicação e datas, localizar o valor no próprio trecho. Para `ano_decisao`, exige ainda palavras que indiquem contexto de deliberação/decisão (checagem heurística, **não** confirmação jurídica da data). Sem evidência suficiente, retorna `null`.

O status `trecho_localizado` confirma apenas uma correspondência textual; não verifica automaticamente a interpretação clínica ou regulatória. O ano da publicação e o da deliberação **não são intercambiáveis**.

## Testes

Os testes unitários de proveniência e schema não usam LLM, PDFs externos ou rede:

```bash
python -m unittest discover -s tests -v
```

**Validação ponta a ponta (28/10/2026, Windows/Python 3.11):** relatório público nº 546/2020 da Conitec, com 117 páginas (116 com texto extraível), foi dividido em 340 chunks, indexado com embeddings reais no ChromaDB e consultado via Groq. A execução manual reportada **antes da migração do schema** retornou `tecnologia_avaliada`, `desfecho` e `ano_decisao`, todos com `status: "trecho_localizado"`; o desfecho normalizado foi `Condicionado` com citação na página 15, e o ano `2020` foi associado à capa (página 1). Esse resultado confirma o funcionamento técnico **na versão anterior e nesse relatório**, não uma avaliação de acurácia em múltiplos documentos. **O novo schema de cinco campos ainda precisa ser validado com a API Groq e PDFs reais.**

Comando utilizado (após preencher `.env` localmente):

```powershell
.\\.venv\\Scripts\\python.exe extract.py --db chroma_db --k 8 --document data\\bedaquilina.pdf --query "bedaquilina recomendação final da Conitec incorporação tuberculose resistente 2020"
```

**Migração de schema:** a partir desta versão, `ano_relatorio` substitui o uso antigo de `ano_decisao` para o ano da publicação; `ano_decisao` passou a representar somente o ano da deliberação/decisão, com evidência específica. A indicação clínica foi extraída do campo `tecnologia_avaliada` para `indicacao_clinica`. Consumidores do JSON antigo precisam ser adaptados. A mudança não exige reconstrução do banco ChromaDB porque o índice guarda os trechos e seus metadados, não a saída estruturada da Groq.

## Limitações e próximos passos

- A busca semântica pode não recuperar o trecho correto; revisar resultados e métricas de recuperação.
- O fragmentador é baseado em caracteres/separadores, não em análise semântica do conteúdo.
- A normalização do desfecho exige revisão humana e pode depender do contexto da recomendação.
- Não há persistência relacional, interface de auditoria nem benchmark de qualidade.
- Planejado: avaliação com exemplos anotados, SQLite, interface de revisão e métricas de precisão de citações.
