# 🚗 Robô de carros

Procura carros na **OLX, Webmotors, Mercado Livre e iCarros** de hora em hora
(GitHub Actions) e manda os anúncios **novos** que batem com seus filtros pelo **WhatsApp**.

## Como configurar (uma vez só)

### 1. Ative o WhatsApp (CallMeBot, gratuito)
1. Salve o número **+34 694 29 84 96** nos seus contatos.
2. Mande para ele pelo WhatsApp: `I allow callmebot to send me messages`
3. Ele responde com sua **apikey**. Guarde-a.

### 2. Suba este projeto para o GitHub
Crie um repositório **privado** e envie estes arquivos para ele.

### 3. Cadastre os segredos
No repositório: **Settings → Secrets and variables → Actions → New repository secret**

| Nome | Valor |
|---|---|
| `WHATSAPP_TELEFONE` | seu número com DDI, ex.: `+5548999998888` |
| `CALLMEBOT_APIKEY` | a apikey recebida no passo 1 |
| `ML_ACCESS_TOKEN` | *(opcional)* token do Mercado Livre, só se a busca dele der erro 401/403 |

### 4. Ajuste suas buscas
Edite o `config.yaml`: marca, modelo, preço, ano, km, estado, cidades e
palavras a excluir (leilão, sinistro…). Dá para ter várias buscas.

### 5. Rode
Vá em **Actions → Robô de carros → Run workflow**. Na 1ª execução o robô só
registra os anúncios que já existem e manda uma mensagem de "ativado".
Depois disso, ele roda sozinho a cada hora e avisa só o que for novo.

## Rodar no seu computador
```
pip install -r requirements.txt
python -m robo --simular      # mostra as mensagens no terminal, sem enviar
```

## Observações
- Os sites mudam o layout de vez em quando e alguns bloqueiam robôs; se uma
  plataforma falhar, as outras continuam funcionando, e o erro aparece no log
  do GitHub Actions. O ajuste fica em `robo/fontes/<plataforma>.py`.
- Os anúncios já vistos ficam em `dados/vistos.json` (salvo automaticamente).
- Respeite os termos de uso dos sites; o robô faz poucas requisições, com pausas.
