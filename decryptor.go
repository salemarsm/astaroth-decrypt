package main

import (
	"flag"
	"fmt"
	"log"
	"os"
	"syscall"
	"unsafe"
)

// Constantes do algoritmo identificadas no script AutoIt
const (
	XOR_INITIAL_KEY uint32 = 0x3E8
	XOR_MULTIPLIER  uint32 = 0xD05
	XOR_INCREMENT   uint32 = 0xD6A
)

// Carrega as funções necessárias da ntdll.dll para descompactação LZNT1
var (
	ntdll                     = syscall.NewLazyDLL("ntdll.dll")
	procRtlGetCompressionWork = ntdll.NewProc("RtlGetCompressionWorkSpaceSize")
	procRtlDecompressFragment = ntdll.NewProc("RtlDecompressFragment")
)

func decrypt(data []byte) {
	key := XOR_INITIAL_KEY
	for i := 0; i < len(data); i++ {
		// Operação XOR: (chave >> 8) & 0xFF
		decryptedByte := data[i] ^ uint8((key>>8)&0xFF)
		data[i] = decryptedByte

		// Atualização da chave (Rolling Cipher)
		// NovaChave = ((Decriptado + Atual) & 0xFF) * 0xD05 + 0xD6A
		key = (uint32(decryptedByte+uint8(key&0xFF))*XOR_MULTIPLIER + XOR_INCREMENT) & 0xFFFF
	}
}

func decompress(compressed []byte) ([]byte, error) {
	var workspaceSize, fragmentSize uint32
	// Formato 2 = COMPRESSION_FORMAT_LZNT1
	r, _, _ := procRtlGetCompressionWork.Call(
		uintptr(2),
		uintptr(unsafe.Pointer(&workspaceSize)),
		uintptr(unsafe.Pointer(&fragmentSize)),
	)
	if r != 0 {
		return nil, fmt.Errorf("RtlGetCompressionWorkSpaceSize failed with error: %X", r)
	}

	workspace := make([]byte, workspaceSize)

	// Estima o tamanho de saída (o malware usa 2x, mas vamos usar um buffer maior por segurança)
	uncompressedSize := uint32(len(compressed) * 10)
	uncompressed := make([]byte, uncompressedSize)
	var finalSize uint32

	r, _, _ = procRtlDecompressFragment.Call(
		uintptr(2), // Format
		uintptr(unsafe.Pointer(&uncompressed[0])), // UncompressedBuffer
		uintptr(uncompressedSize),                 // UncompressedBufferSize
		uintptr(unsafe.Pointer(&compressed[0])),   // CompressedBuffer
		uintptr(len(compressed)),                  // CompressedBufferSize
		uintptr(0),                                // UncompressedChunkOffset
		uintptr(unsafe.Pointer(&finalSize)),       // FinalUncompressedSize
		uintptr(unsafe.Pointer(&workspace[0])),    // WorkSpace
	)

	if r != 0 {
		return nil, fmt.Errorf("RtlDecompressFragment failed with error: %X", r)
	}

	return uncompressed[:finalSize], nil
}

func main() {
	inputFile := flag.String("in", "", "Arquivo criptografado (*.tda, *.dmp)")
	outputFile := flag.String("out", "payload_decrypted.bin", "Arquivo de saída")
	flag.Parse()

	if *inputFile == "" {
		fmt.Println("Uso: decryptor.exe -in <arquivo> [-out <saida>]")
		os.Exit(1)
	}

	fmt.Printf("[*] Lendo arquivo: %s\n", *inputFile)
	data, err := os.ReadFile(*inputFile)
	if err != nil {
		log.Fatalf("[-] Erro ao ler arquivo: %v", err)
	}

	fmt.Println("[*] Descriptografando (Rolling XOR)...")
	decrypt(data)

	fmt.Println("[*] Descompactando (LZNT1)...")
	decompressed, err := decompress(data)
	if err != nil {
		fmt.Printf("[!] Erro na descompactação (pode ser payload não compactado): %v\n", err)
		decompressed = data // Se falhar, salva pelo menos a parte descriptografada
	}

	err = os.WriteFile(*outputFile, decompressed, 0644)
	if err != nil {
		log.Fatalf("[-] Erro ao salvar arquivo: %v", err)
	}

	fmt.Printf("[+] Sucesso! Payload salvo em: %s\n", *outputFile)

	// Verifica assinatura MZ
	if len(decompressed) > 2 && decompressed[0] == 0x4D && decompressed[1] == 0x5A {
		fmt.Println("[+] Cabeçalho MZ detectado. É provável que seja um arquivo PE (DLL/EXE) válido.")
	} else {
		fmt.Println("[?] Cabeçalho MZ não detectado. O arquivo pode precisar de processamento adicional ou não é um PE.")
	}
}
