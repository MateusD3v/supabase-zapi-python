import logging
import os
import sys
from typing import Any

import requests
from dotenv import load_dotenv
from supabase import Client, create_client

MAX_CONTACTS = 3
REQUEST_TIMEOUT_SECONDS = 15

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
ZAPI_INSTANCE_ID = os.getenv("ZAPI_INSTANCE_ID")
ZAPI_TOKEN = os.getenv("ZAPI_TOKEN")
ZAPI_CLIENT_TOKEN = os.getenv("ZAPI_CLIENT_TOKEN")


def get_supabase_client() -> Client:
    """Cria o cliente do Supabase a partir das variáveis de ambiente."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("SUPABASE_URL e SUPABASE_KEY devem estar configurados no .env")

    return create_client(SUPABASE_URL, SUPABASE_KEY)


def fetch_contacts(supabase: Client, limit: int = MAX_CONTACTS) -> list[dict[str, Any]]:
    """Busca no máximo três contatos da tabela contatos."""
    safe_limit = max(1, min(limit, MAX_CONTACTS))
    logger.info("Buscando até %s contatos no Supabase...", safe_limit)

    response = (
        supabase.table("contatos").select("nome, telefone").limit(safe_limit).execute()
    )

    return response.data or []


def send_zapi_message(phone: str, name: str) -> bool:
    """Envia a mensagem personalizada para um contato usando a Z-API."""
    if not ZAPI_INSTANCE_ID or not ZAPI_TOKEN:
        raise ValueError(
            "ZAPI_INSTANCE_ID e ZAPI_TOKEN devem estar configurados no .env"
        )

    url = (
        f"https://api.z-api.io/instances/{ZAPI_INSTANCE_ID}"
        f"/token/{ZAPI_TOKEN}/send-text"
    )
    headers = {"Content-Type": "application/json"}

    if ZAPI_CLIENT_TOKEN:
        headers["Client-Token"] = ZAPI_CLIENT_TOKEN

    payload = {
        "phone": phone,
        "message": f"Olá, {name} tudo bem com você?",
    }

    response = None
    try:
        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.RequestException as error:
        logger.error("Erro ao enviar mensagem para %s: %s", phone, error)
        response_body = getattr(response, "text", "")
        if response_body:
            logger.error("Resposta da Z-API: %s", response_body)
        return False

    logger.info("Mensagem enviada com sucesso para %s (%s)", name, phone)
    return True


def main() -> int:
    """Executa a leitura dos contatos e o envio das mensagens."""
    try:
        supabase = get_supabase_client()
        contacts = fetch_contacts(supabase)
    except Exception:
        logger.exception("Falha ao buscar contatos no Supabase.")
        return 1

    if not contacts:
        logger.warning("Nenhum contato encontrado no Supabase.")
        return 0

    logger.info("Encontrados %s contatos.", len(contacts))
    failed_sends = 0

    for contact in contacts:
        name = str(contact.get("nome") or "").strip()
        phone = str(contact.get("telefone") or "").strip()

        if not name or not phone:
            logger.warning("Contato ignorado por conter dados incompletos: %s", contact)
            failed_sends += 1
            continue

        try:
            if not send_zapi_message(phone, name):
                failed_sends += 1
        except ValueError as error:
            logger.error("%s", error)
            return 1

    if failed_sends:
        logger.error("%s contato(s) não foram processados com sucesso.", failed_sends)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
