package main

import (
	"fmt"
	"time"

	"github.com/go-rod/rod"
	"github.com/go-rod/rod/lib/input"
	"github.com/go-rod/rod/lib/launcher"
)

/*
WhatsApp Automation POC - Versão Educacional (Go)
------------------------------------------------
Este script demonstra a automação do WhatsApp Web em Go usando a biblioteca Rod.
Objetivo: Prova de Conceito (POC) restrita para fins didáticos.

RESTRIÇÕES:
1. Sem C2 ou conexões externas.
2. Limite de 5 contatos.
3. Demonstração de injeção de mensagem segura.
*/

const (
	WhatsAppURL       = "https://web.whatsapp.com"
	MaxContactsToList = 5
	TestMessage       = "POV: Demonstração de automação em Go para aula de Cibersegurança."
)

func main() {
	fmt.Println("[*] Iniciando POC de automação WhatsApp em Go...")

	// Configura o navegador
	// O Rod permite controlar o navegador via DevTools Protocol (CDP)
	l := launcher.New().
		Headless(false). // Deixa o navegador visível para o aluno
		Devtools(true).
		Leakless(false) // DESATIVADO: Para evitar bloqueio de antivírus

	/*
	   DICA PARA AULA (Sessão Logada / Session Hijacking):
	   - Para usar sua sessão real do Chrome (e pular o QR Code), descomente a linha abaixo
	     e altere 'SeuUsuario' para o nome do seu usuário Windows.
	   - IMPORTANTE: O Chrome deve estar COMPLETAMENTE FECHADO antes de rodar o script.
	*/
	// l.UserDataDir("C:\\Users\\SeuUsuario\\AppData\\Local\\Google\\Chrome\\User Data")

	url := l.MustLaunch()

	// Inicializa o browser
	browser := rod.New().ControlURL(url).MustConnect()
	defer browser.MustClose()

	// Abre o WhatsApp Web
	page := browser.MustPage(WhatsAppURL)

	fmt.Println("[!] Por favor, escaneie o QR Code no navegador (ou use a sessão logada)...")

	// Aguarda o login detectando a lista de conversas
	page.MustElement("[data-testid='chat-list']").MustWaitVisible()
	fmt.Println("[+] Login detectado com sucesso!")

	// Pequena pausa para garantir carregamento total
	time.Sleep(2 * time.Second)

	// --- INÍCIO DA CAPACIDADE REAL-TIME (WORM-LIKE) ---
	fmt.Println("[*] Iniciando monitoramento em tempo real (Goroutines)...")
	seenNames := make(map[string]bool)

	// Coleta inicial para não repetir o que já está na tela
	initialElements := page.MustElements("span[title]")
	for _, el := range initialElements {
		name := el.MustText()
		if name != "" {
			seenNames[name] = true
		}
	}

	// Goroutine que monitora novos contatos em segundo plano
	go func() {
		for {
			time.Sleep(3 * time.Second) // Escaneia a cada 3 segundos

			elements := page.MustElements("span[title]")
			for _, el := range elements {
				name, err := el.Text()
				if err != nil || name == "" {
					continue
				}

				if !seenNames[name] {
					seenNames[name] = true
					fmt.Printf("\a\n[REAL-TIME] Novo contato/atividade detectada: %s\n", name)
					fmt.Print("[!] Pressione ENTER para simular injeção no chat selecionado...")
				}
			}
		}
	}()
	// --- FIM DA CAPACIDADE REAL-TIME ---

	// Demonstração de injeção de mensagem
	fmt.Println("\n[!] Demonstração: Selecione um chat no navegador e pressione ENTER aqui para simular a injeção.")
	fmt.Print("[-] (O monitoramento continua rodando em segundo plano enquanto você decide...)\n")

	var inputStr string
	fmt.Scanln(&inputStr)

	// Busca a caixa de texto (contenteditable)
	chatBox := page.MustElement("div[contenteditable='true'][data-tab='10']")
	chatBox.MustClick().MustInput(TestMessage)

	chatBox.MustType(input.Enter)

	fmt.Printf("[+] Mensagem injetada: %s\n", TestMessage)
	fmt.Println("[*] POC concluída. O navegador será fechado em 5 segundos.")
	time.Sleep(5 * time.Second)
}
