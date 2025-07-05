# Sistema de Compartilhamento de Arquivos P2P

Um sistema peer-to-peer para compartilhamento de arquivos em rede local.

## 🚀 Começando

### Pré-requisitos
- Python 3.x instalado


## ⚙️ Execução
Abra 3  terminais e execute o seguinte comando em cada um deles:
1. Inicie o servidor central no primeiro terminal:
```bash
python server/server.py  
```
2. Inicie o cliente_a no segundo terminal:
```bash
python client_a/client.py
```
3. Inicie o cliente_b no terceiro terminal:
```bash
python client_b/client.py
```
## 🖥️ Como usar
### Após iniciar o cliente, você verá um menu com 3 opções:

* (1) Buscar arquivos - Procura por arquivos na rede

* (2) Baixar arquivo - Baixa um arquivo de outro peer

* (3) Sair da rede - Encerra a conexão
### Para usar essas opções, basta digitar o número correspondente e pressionar