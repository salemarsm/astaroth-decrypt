#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WhatsApp Automation POC - Versão Educacional (Restrita)
------------------------------------------------------
Este script é uma Prova de Conceito (POC) simplificada baseada na análise do malware Astaroth.
Objetivo: Demonstrar como a automação de navegadores pode interagir com o WhatsApp Web.

RESTRICÕES DE SEGURANÇA:
1. Sem conexão com servidores de Comando e Controle (C2).
2. Limite estrito de 5 contatos coletados.
3. Envio de mensagem apenas para o próprio usuário/número teste.
4. Uso pedagógico para aulas de segurança cibernética.
"""

import os
import time
import platform
import logging
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options as ChromeOptions

# Configuração de logging básico
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Configurações da POC
WHATSAPP_URL = "https://web.whatsapp.com"
MAX_CONTACTS_TO_LIST = 5
TEST_MESSAGE = "POV: Demonstração de automação segura para aula de Cibersegurança."

def setup_browser():
    """Configura o Chrome em modo visível para que o aluno veja a interação."""
    logger.info("Configurando o navegador Chrome...")
    options = ChromeOptions()
    
    # Desativa flags de detecção de automação (técnica usada pelo malware)
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    
    # O malware tenta roubar o perfil do usuário para evitar login por QR Code.
    # Nesta POC, abrimos uma sessão limpa para que o usuário precise escanear o QR Code.
    return webdriver.Chrome(options=options)

def wait_for_login(driver):
    """Aguarda o usuário escanear o QR Code e o layout carregar."""
    logger.info("Por favor, escaneie o QR Code no WhatsApp Web.")
    try:
        # Aguarda a aparição de um elemento da lista de chats
        WebDriverWait(driver, 60).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='chat-list']"))
        )
        logger.info("Login detectado com sucesso!")
        return True
    except TimeoutException:
        logger.error("Tempo limite esgotado para o login.")
        return False

def list_contacts_poc(driver):
    """Coleta o nome dos primeiros 5 contatos visíveis na lista de chats."""
    logger.info(f"Coletando os primeiros {MAX_CONTACTS_TO_LIST} contatos visíveis...")
    time.sleep(2) # Pequena pausa para garantir que o DOM renderizou os nomes
    
    # Seletor CSS comum para os nomes na lista de conversas
    contacts = driver.find_elements(By.CSS_SELECTOR, "span[title]")
    
    names = []
    for contact in contacts:
        name = contact.get_attribute("title")
        if name and name not in names:
            names.append(name)
        if len(names) >= MAX_CONTACTS_TO_LIST:
            break
            
    print("\n--- Lista de Contatos Coletada (POC) ---")
    for i, name in enumerate(names, 1):
        print(f"{i}. {name}")
    print("---------------------------------------\n")
    return names

def send_test_message(driver):
    """Demonstra como o malware seleciona um chat e injeta uma mensagem."""
    # Nesta POC, assumimos que o usuário selecionou o próprio chat ou um chat específico manualmente.
    # O malware automatiza essa seleção buscando pelo nome/número no WPP.chat.get().
    
    logger.info("Demonstração de Envio: Clique em uma conversa para enviar a mensagem de teste.")
    input("Pressione ENTER aqui quando estiver com o chat de destino aberto no navegador...")
    
    try:
        # Busca a caixa de texto do WhatsApp Web
        chat_box = driver.find_element(By.CSS_SELECTOR, "div[contenteditable='true'][data-tab='10']")
        chat_box.click()
        chat_box.send_keys(TEST_MESSAGE)
        
        # O malware enviaria o comando via JS para ser mais rápido, 
        # aqui simulamos a interação humana para visualização.
        logger.info("Mensagem injetada na caixa de texto!")
        print(f"\n[!] Mensagem enviada para demonstração: {TEST_MESSAGE}\n")
        
        # Enviar (Opcional - usuário pode clicar no botão de enviar manualmente para controle total)
        # driver.find_element(By.CSS_SELECTOR, "span[data-testid='send']").click()
        
    except Exception as e:
        logger.error(f"Erro ao tentar injetar mensagem: {e}")

def main():
    driver = None
    try:
        driver = setup_browser()
        driver.get(WHATSAPP_URL)
        
        if wait_for_login(driver):
            list_contacts_poc(driver)
            send_test_message(driver)
            
            logger.info("POC concluída. Pressione ENTER no console para fechar o navegador.")
            input()
            
    except Exception as e:
        logger.error(f"Ocorreu um erro na execução: {e}")
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    main()
