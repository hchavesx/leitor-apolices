from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
import pdfplumber
import io
import re

app = FastAPI()

def extrair_texto_pdf(file: UploadFile) -> str:
    with pdfplumber.open(io.BytesIO(file.file.read())) as pdf:
        texto = "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])
    return texto

def extrair_dados_apolice(texto: str) -> dict:
    dados = {}

    match_nome = re.search(r"Nome:\s*(.+)", texto)
    if match_nome:
        dados["segurado"] = match_nome.group(1).strip()

    match_cpf = re.search(r"CPF[:\s]+([0-9.\-]+)", texto)
    if match_cpf:
        dados["cpf"] = match_cpf.group(1)

    match_vigencia = re.search(r"às 24h de (\d{2}/\d{2}/\d{4}) às 24h de (\d{2}/\d{2}/\d{4})", texto)
    if match_vigencia:
        dados["vigencia_inicio"] = match_vigencia.group(1)
        dados["vigencia_fim"] = match_vigencia.group(2)

    match_valor = re.search(r"Prêmio Total\s*R\$\s*([\d,.]+)", texto)
    if match_valor:
        dados["valor_total"] = float(match_valor.group(1).replace(".", "").replace(",", "."))

    match_bonus = re.search(r"Classe de B[oô]nus[:\s]+(.+?)\n", texto)
    if match_bonus:
        dados["classe_bonus"] = match_bonus.group(1).strip()
    else:
        dados["classe_bonus"] = None

    match_cep = re.search(r"CEP[\s\-:]*([0-9]{5}-?[0-9]{3})", texto)
    if match_cep:
        dados["cep_pernoite"] = match_cep.group(1)

    match_chassi = re.search(r"Chassi[:\s]+([A-Z0-9]{10,17})", texto)
    if match_chassi:
        dados["chassi"] = match_chassi.group(1)

    match_modelo = re.search(r"Modelo[:\s]+([A-Z0-9\-\.\s]+)", texto)
    if match_modelo:
        dados["modelo_veiculo"] = match_modelo.group(1).strip()

    return dados

@app.post("/upload-apolice")
async def upload_apolice(file: UploadFile = File(...)):
    try:
        texto = extrair_texto_pdf(file)
        dados = extrair_dados_apolice(texto)
        return JSONResponse(content=dados)
    except Exception as e:
        return JSONResponse(status_code=500, content={"erro": str(e)})
