import os
import logging
import requests
from dotenv import load_dotenv
from supabase import create_client, Client

# Configuração de Logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Carrega variáveis de ambiente
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
ZAPI_INSTANCE_ID = os.getenv("ZAPI_INSTANCE_ID")
ZAPI_TOKEN = os.getenv("ZAPI_TOKEN")
ZAPI_CLIENT_TOKEN = os.getenv("ZAPI_CLIENT_TOKEN")

def get_supabase_client() -> Client:
    """Inicializa o cliente do Supabase."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("SUPABASE_URL e SUPABASE_KEY devem estar configurados no .env")
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def fetch_contacts(supabase: Client, limit: int = 3):
    """Busca contatos da tabela 'contatos' no Supabase."""
    try:
        logger.info(f"Buscando até {limit} contatos no Supabase...")
        response = supabase.table("contatos").select("nome, telefone").limit(limit).execute()
        return response.data
    except Exception as e:
        logger.error(f"Erro ao buscar contatos: {e}")
        return []

def send_zapi_message(phone: str, name: str):
    """Envia mensagem via Z-API."""
    if not all([ZAPI_INSTANCE_ID, ZAPI_TOKEN]):
        logger.error("Configurações da Z-API incompletas no .env")
        return False

    url = f"https://api.z-api.io/instances/{ZAPI_INSTANCE_ID}/token/{ZAPI_TOKEN}/send-text"
    
    headers = {
        "Content-Type": "application/json"
    }
    
    # Se houver Client-Token, adiciona no header
    if ZAPI_CLIENT_TOKEN:
        headers["Client-Token"] = ZAPI_CLIENT_TOKEN

    payload = {
        "phone": phone,
        "message": f"Olá, {name} tudo bem com você?"
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        logger.info(f"Mensagem enviada com sucesso para {name} ({phone})")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Erro ao enviar mensagem para {phone}: {e}")
        if response.text:
            logger.error(f"Resposta da API: {response.text}")
        return False

def main():
    try:
        supabase = get_supabase_client()
        contacts = fetch_contacts(supabase, limit=3)

        if not contacts:
            logger.warning("Nenhum contato encontrado no Supabase.")
            return

        logger.info(f"Encontrados {len(contacts)} contatos.")

        for contact in contacts:
            nome = contact.get("nome")
            telefone = contact.get("telefone")

            if nome and telefone:
                send_zapi_message(telefone, nome)
            else:
                logger.warning(f"Contato com dados incompletos: {contact}")

    except Exception as e:
        logger.critical(f"Erro fatal na execução: {e}")

if __name__ == "__main__":
    main()
