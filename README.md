# Astaroth Decryptor

Ferramenta em Go para descriptografar e descompactar payloads do malware Astaroth.

## Funcionalidades

- **Rolling XOR**: Implementação do algoritmo de criptografia simétrica com chave dinâmica identificado em scripts AutoIt do Astaroth.
- **LZNT1 Decompression**: Utiliza a API nativa do Windows (`ntdll.dll`) para descompactar os dados após o XOR.
- **Detecção MZ**: Verifica se o resultado final é um executável Windows (PE) válido.

## Uso

1. Compilar o projeto:

   ```bash
   go build -o decryptor.exe decryptor.go
   ```

2. Executar passando o arquivo `.tda` ou `.dmp`:
   ```bash
   ./decryptor.exe -in malware_sample.tda -out payload_decrypted.bin
   ```

## Especificações Técnicas

- **Linguagem**: Go 1.24+
- **Dependências**: Apenas bibliotecas padrão e `syscall` para interação com `ntdll.dll`.
- **Compatibilidade**: Windows (devido ao uso de APIs nativas).

---

_Aviso: Esta ferramenta é destinada apenas para fins de análise de malware e pesquisa de segurança._
