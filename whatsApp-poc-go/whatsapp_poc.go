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
		Leakless(false) // DESATIVADO: O 'leakless' ajuda a limpar processos, mas o Windows Defender costuma pará-lo como falso positivo.

	/*
	   DICA PARA AULA (Sessão Logada):
	   - O malware Astaroth (vbiud.py) USA a sessão logada apontando para: .UserDataDir(caminho_do_perfil)
	   - Nesta POC, NÃO usamos .UserDataDir(). Isso cria um perfil temporário limpo.
	   - Isso obriga o scan do QR Code, o que é mais SEGURO para uma demonstração em aula.
	*/

	url := l.MustLaunch()

	// Inicializa o browser
	browser := rod.New().ControlURL(url).MustConnect()
	defer browser.MustClose()

	// Abre o WhatsApp Web
	page := browser.MustPage(WhatsAppURL)

	fmt.Println("[!] Por favor, escaneie o QR Code no navegador...")

	// Aguarda o login detectando a lista de conversas
	// O malware usaria seletores internos mais complexos ou WA-JS
	page.MustElement("[data-testid='chat-list']").MustWaitVisible()
	fmt.Println("[+] Login detectado com sucesso!")

	// Pequena pausa para garantir carregamento total
	time.Sleep(2 * time.Second)

	// Listagem dos primeiros contatos (POC)
	fmt.Println("[*] Coletando os primeiros contatos visíveis...")
	// Buscamos elementos que possuem o atributo 'title', comum para nomes de contatos
	elements := page.MustElements("span[title]")

	names := make(map[string]bool)
	fmt.Println("\n--- Lista de Contatos Coletada (POC Go) ---")
	count := 0
	for _, el := range elements {
		name := el.MustText()
		if name != "" && !names[name] {
			names[name] = true
			count++
			fmt.Printf("%d. %s\n", count, name)
		}
		if count >= MaxContactsToList {
			break
		}
	}
	fmt.Println("-------------------------------------------\n")

	// Demonstração de injeção de mensagem
	fmt.Println("[!] Demonstração: Selecione um chat no navegador e pressione ENTER aqui para simular a injeção.")
	var inputStr string
	fmt.Scanln(&inputStr)

	// Busca a caixa de texto (contenteditable)
	// O seletor 'div[contenteditable="true"]' é o padrão do WPP Web para a área de digitação
	chatBox := page.MustElement("div[contenteditable='true'][data-tab='10']")
	chatBox.MustClick().MustInput(TestMessage)

	// O malware dispararia o evento de 'Enter' ou usaria WPP.chat.send()
	// Aqui apenas injetamos o texto para demonstrar a capacidade
	chatBox.MustType(input.Enter)

	fmt.Printf("[+] Mensagem injetada: %s\n", TestMessage)
	fmt.Println("[*] POC concluída. O navegador será fechado em 5 segundos.")
	time.Sleep(5 * time.Second)
}
