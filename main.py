
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import pdfplumber
import io
import re

app = FastAPI()

# Configurar CORS para permitir chamadas do navegador
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def extrair_texto_pdf(file: UploadFile) -> str:
    with pdfplumber.open(io.BytesIO(file.file.read())) as pdf:
        texto = "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])
    return texto

def extrair_dados_apolice(texto: str) -> dict:
    dados = {}

    match_nome = re.search(r"Nome[:\s]+(?:Registro\s+do\s+)?Segurado[:\s]*(.+)", texto)
    if match_nome:
        dados["segurado"] = match_nome.group(1).strip()

    match_cpf = re.search(r"CPF[:\s/]+([0-9.\-]+)", texto)
    if match_cpf:
        dados["cpf"] = match_cpf.group(1)

    # Novo padrão HDI
    match_vigencia = re.search(
        r"Vig[êe]ncia[:\s]+das\s+24hs?\s+do\s+dia\s+(\d{2}/\d{2}/\d{4})\s+às\s+24hs?\s+do\s+dia\s+(\d{2}/\d{2}/\d{4})",
        texto, re.IGNORECASE
    )
    if not match_vigencia:
        match_vigencia = re.search(r"[Vv]ig[êe]ncia[:\s]+das?\s+\d{2}[:hs\s]*do\s+dia\s+(\d{2}/\d{2}/\d{4}).+?\s+(\d{2}/\d{2}/\d{4})", texto)
    if not match_vigencia:
        match_vigencia = re.search(r"Vig[êe]ncia[:\s]+das\s+24H\s+de\s+(\d{2}/\d{2}/\d{4})\s+\w+\s+24H\s+de\s+(\d{2}/\d{2}/\d{4})", texto)
    if not match_vigencia:
        match_vigencia = re.search(r"Vig[êe]ncia[:\s]+(\d{2}/\d{2}/\d{4}).+?(\d{2}/\d{2}/\d{4})", texto)
    if match_vigencia:
        dados["vigencia_inicio"] = match_vigencia.group(1)
        dados["vigencia_fim"] = match_vigencia.group(2)

    match_valor = re.search(r"Prêmio Total\s*[:R\$]*\s*([\d.,]+)", texto)
    if match_valor:
        dados["valor_total"] = float(match_valor.group(1).replace(".", "").replace(",", "."))

    match_bonus = re.search(r"Classe B[oô]nus[:\s]+(\d{1,2})", texto)
    if match_bonus:
        dados["classe_bonus"] = match_bonus.group(1)
    else:
        dados["classe_bonus"] = None

    match_cep = re.search(r"CEP[\s\-:]*([0-9]{5}-?[0-9]{3})", texto)
    if match_cep:
        dados["cep_pernoite"] = match_cep.group(1)

    match_chassi = re.search(r"Chassi[:\s]+([A-Z0-9]{10,17})", texto)
    if match_chassi:
        dados["chassi"] = match_chassi.group(1)

    match_modelo = re.search(r"Modelo[:\s]+([A-Z0-9\-\.\s\(\)]+)", texto)
    if match_modelo:
        dados["modelo_veiculo"] = match_modelo.group(1).strip()

    match_fipe = re.search(r"C[oó]d[.]? FIPE[:\s]+(\d{6}-\d)", texto)
    if match_fipe:
        dados["codigo_fipe"] = match_fipe.group(1)

    match_seguradora = re.search(r"(Allianz|Azul Seguros|HDI|Porto Seguro|Tokio Marine|Bradesco Auto|Liberty|Mapfre|SulAmérica)", texto, re.IGNORECASE)
    if match_seguradora:
        dados["seguradora"] = match_seguradora.group(1)

    match_placa = re.search(r"Placa[:/\s]+([A-Z]{3}\d{1}[A-Z0-9]{2}|[A-Z]{3}\-\d{4})", texto)
    if match_placa:
        dados["placa"] = match_placa.group(1)

    return dados

@app.post("/upload-apolice")
async def upload_apolice(file: UploadFile = File(...)):
    try:
        texto = extrair_texto_pdf(file)
        dados = extrair_dados_apolice(texto)
        return JSONResponse(content=dados)
    except Exception as e:
        return JSONResponse(status_code=500, content={"erro": str(e)})
