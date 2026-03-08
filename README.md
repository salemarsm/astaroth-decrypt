# Astaroth Decryptor

[English](#english) | [Português](#português)

---

## English

Go-based tool to decrypt and decompress Astaroth malware payloads.

This tool was developed to analyze samples identified in the **Boto-cor-de-rosa** campaign, documented by **Acronis** in the post "[Boto-cor-de-rosa campaign reveals Astaroth WhatsApp-based worm activity in Brazil](https://www.acronis.com/pt/tru/posts/boto-cor-de-rosa-campaign-reveals-astaroth-whatsapp-based-worm-activity-in-brazil/)". The campaign uses multiple stages and advanced obfuscation techniques, including AutoIt scripts. This specific part is not documented in the Acronis publication, so I decided to delve deeper into the analysis.

### Features

- **Rolling XOR**: Implementation of the symmetric dynamic key encryption algorithm identified in Astaroth's AutoIt scripts.
- **LZNT1 Decompression**: Uses the Windows native API (`ntdll.dll`) to decompress data after XOR.
- **MZ Detection**: Verifies if the final result is a valid Windows executable (PE) file.

### Usage

1. Compile the project:

   ```bash
   go build -o decryptor.exe decryptor.go
   ```

2. Run it by passing the `.tda` or `.dmp` file:
   ```bash
   ./decryptor.exe -in malware_sample.tda -out payload_decrypted.bin
   ```

### Technical Specifications

- **Language**: Go 1.24+
- **Dependencies**: Only standard libraries and `syscall` for `ntdll.dll` interaction.
- **Compatibility**: Windows (due to the use of native APIs).

### Educational POCs (Restricted)

To support cybersecurity lessons regarding Astaroth's wormable capabilities, two restricted Proof of Concept (POC) scripts are provided:

1. **Python ([whatsapp_poc.py](whatsapp_poc.py))**: Uses Selenium.
   ```bash
   pip install selenium
   python whatsapp_poc.py
   ```
2. **Go ([whatsapp_poc.go](whatsapp_poc.go))**: Uses the Rod library.
   ```bash
   go run whatsapp_poc.go
   ```
   _These POCs are strictly for educational use, with a 5-contact limit and no C2 connectivity._

---

## Português

Ferramenta em Go para descriptografar e descompactar payloads do malware Astaroth.

Esta ferramenta foi desenvolvida para analisar amostras identificadas na campanha **Boto-cor-de-rosa**, documentada pela **Acronis** no post "[Boto-cor-de-rosa campaign reveals Astaroth WhatsApp-based worm activity in Brazil](https://www.acronis.com/pt/tru/posts/boto-cor-de-rosa-campaign-reveals-astaroth-whatsapp-based-worm-activity-in-brazil/)". A campanha utiliza diversos estágios e técnicas de ofuscação, incluindo o uso de scripts AutoIt. Essa parte não é documentada na publicação da Acronis e resolvi aprofundar a análise.

### Funcionalidades

- **Rolling XOR**: Implementação do algoritmo de criptografia simétrica com chave dinâmica identificado em scripts AutoIt do Astaroth.
- **LZNT1 Decompression**: Utiliza a API nativa do Windows (`ntdll.dll`) para descompactar os dados após o XOR.
- **Detecção MZ**: Verifica se o resultado final é um executável Windows (PE) válido.

### Uso

1. Compilar o projeto:

   ```bash
   go build -o decryptor.exe decryptor.go
   ```

2. Executar passando o arquivo `.tda` ou `.dmp`:
   ```bash
   ./decryptor.exe -in malware_sample.tda -out payload_decrypted.bin
   ```

### Especificações Técnicas

- **Linguagem**: Go 1.24+
- **Dependências**: Apenas bibliotecas padrão e `syscall` para interação com `ntdll.dll`.
- **Compatibilidade**: Windows (devido ao uso de APIs nativas).

---

_Disclaimer: This tool is intended for malware analysis and security research purposes only. / Esta ferramenta é destinada apenas para fins de análise de malware e pesquisa de segurança._
