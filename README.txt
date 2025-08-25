# Chatbot SIGNA — Desafio técnico

Chatbot que responde a perguntas sobre a SIGNA, com base no conteúdo público do site https://www.signa.pt/ usando um pipeline de RAG (Retrieval-Augmented Generation)

## Ferramentas e dependências

httpx / requests / BeautifulSoup4 : Scraping. httpx/requests é utilizado para baixar HTML e BeautifulSoup4 para parsear/remover ruídos dessas URLs, deixando as mesmas mais limpas.
    São utilizadas na ingestão, em app/inject.py

markdownify : Utilizado para converter o HTML em markdown, preservando títulos, listas e links para melhorar a qualidade do texto para embeddings.
    Utilizado em app/inject.py

tqdm : É barra de progresso para loops de scraping/ingestão
    Utilizado em app/ingest.py

sentence-transformers : Gerar embeddings semânticos(vetores) de cada chunk de texto.
    Utilizado em app/ingest.py

faiss : índice vetorial para busca semântica rápida
    Utilizado em app/ingest.py para criação/salvamento do índice.
    Utilizado em app/rag.py para consulta.

FastAPI / Flask : Frameworks web para expor a API do chatbot.
    Utilizado em app/app_api.py

dotenv : carregar .env (chaves de API, domínio, configuirações).
    Utilizado em app/llm_client.py, app/app_api.py e app/ingest.py

huggingface_hub / OpenAI API : acesso ao modelo de linguagem.
    Utilizado em app/llm_client.py


jsonlines (jsonl) : Salvar metadados dos chunks indexados.
    Utilizado em app/ingest.py para gravar meta.jsonl
    Utilizado em app/rag.py onde os índices retornam Ids e o meta.jsonl é reaberto para reconstruir o contexto a ser passado para ao LLM.

## Arquitetura

-Gerar seed_urls.txt (generate_seed_urls.py),
    Gera a lista de páginas relevantes do domínio signa.pt (FAQ, categorias, setores, etc).
    Remove links inúteis (login, carrinho, orçamento).
    Salva os resultados em demo_data/seed_urls.txt.
    
-Seed URLs (demo_data/seed_urls.txt)
    Define os links que serão os pontos de partida para crawling do site.

-Ingestão (app/ingest.py)
    Lê seed_urls.txt.
    Faz scraping das páginas.
    Remove tags e elementos irrelevantes (script, style, footer, menus).
    Converte HTML em markdown para preservar estrutura.
    Divide o texto em chunks menores para facilitar o uso do LLM.
    Gera embeddings.
    Salva no índice data/index.faiss e nos metadados data/meta.jsonl.

Índice Vetorial (data/)
    index.faiss armazena os vetores (embeddings).
    meta.jsonl armazena informações dos links (URL de origem, título, etc).

RAG (Retrieval-Augmented Generation) (app/rag.py)
    Recebe a pergunta do usuário.
    Sistema gera embedding da pergunta.
    Busca no FAISS os chunks mais semelhantes.
    Monta o prompt com contexto e pergunta.
    Passa para o LLM via llm_client.py.

Resposta Final
    O modelo gera resposta embasada nos documentos. O mesmo é rodado via API (app_api.py).

## Como executar 

### 1) Ambiente
Utilizei o anaconda prompt por questões de costume, mas pode ser criado diretamente do prompt de comando usual, com as bibliotecas presentes em requirements.txt

conda create -n signa-chatbot python=3.11 -y
conda activate signa-chatbot
pip install -r requirements.txt
conda install -n signa-chatbot -c conda-forge faiss-cpu=1.7.4
(aceitar as atualizações de bibliotecas já existentes no ambiente)

Utilizei faiss-cpu e não gpu pois como é apenas um domínio(signa.pt), cpu já é o suficiente.

1.1) instalar a LLM ollama https://ollama.com/download

Em um promp com o ambiente criado, ir para o diretório do projeto e rodar o seguinte comando: ollama run llama3.1

Isso baixa o LLM e mantém o servidor local ativo em http://localhost:11434.

Para testar se o servidor está ativo, ir no navegador e digitar http://localhost:11434

Se aparecer "Ollama is running", o servidor está ativado e pronto para uso.

Obs 1: o arquivo .env deve ser configurado de acordo como irá rodar o projeto. Utilizei o LLM ollama para rodar em servidor local, por isso o parâmetro `OPENAI_API_KEY` está vazio.
    `OLLAMA_BASE_URL=http://localhost:11434`:  para rodar a API do Ollama, abrindo um servidor HTTP local na porta 11434 (verificar se o firewall está bloqueando essa porta, caso não funcione).
    `OLLAMA_MODEL=llama3.1`: modelo que o ollama vai usar.

0bs 2: llm_client.py possui função para rodar com OpenAI, mas teria que configurar o .env e um servidor na nuvem para rodar o mesmo.

### 2) Ingestão (crawler e índice) - não é necessário executar, só está aqui para fins de como foram gerados index.faiss e meta.jsonl

Comando utilizado: python app/ingest.py --seed demo_data/seed_urls.txt
Isso gera embeddings para cada chunk e salva em `data/index.faiss` e as informações necessárias para reconstituir de onde veio cada embedding são salvas em `data/meta.jsonl`.

### 3) Subir a API 
Em outro prompt de comando com o mesmo ambiente, ir até o diretório pai do projeto e rodar o comando:
uvicorn app.app_api:app --reload --port 8000

Abra http://localhost:8000 no navegador e faça perguntas.

### 4) CLI (caso queria rodar via prompt)

python app/app_cli.py ask "Aqui vai sua pergunta"

## Limitações
- Baseia-se apenas no que foi indexado do site público.
- O crawler é simples e evita rotas dinâmicas (por ex. carrinho/orçamento).

