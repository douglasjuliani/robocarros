# 🚗 Robô de carros

Procura carros na **OLX, Webmotors, Mercado Livre e iCarros** de hora em hora
(GitHub Actions) e manda por **e-mail** os anúncios **novos** que batem com seus filtros.

## Como configurar (uma vez só)

### 1. Crie uma senha de app do Gmail
O robô envia os e-mails por uma conta Gmail (pode ser a sua mesma):
1. A conta precisa ter **verificação em duas etapas** ativada.
2. Acesse https://myaccount.google.com/apppasswords, crie uma senha com o nome
   "robo-carros" e copie os 16 caracteres gerados.

(Outlook/Hotmail ou outro provedor também servem: use os segredos
`SMTP_SERVIDOR` e `SMTP_PORTA`, por exemplo `smtp-mail.outlook.com` e `587`.)

### 2. Suba este projeto para o GitHub
Crie um repositório **privado** e envie estes arquivos para ele.

### 3. Cadastre os segredos
No repositório: **Settings → Secrets and variables → Actions → New repository secret**

| Nome | Valor |
|---|---|
| `SMTP_USUARIO` | o Gmail que envia, ex.: `seuemail@gmail.com` |
| `SMTP_SENHA` | a senha de app do passo 1 |
| `EMAIL_PARA` | *(opcional)* quem recebe; vários separados por vírgula. Padrão: o próprio `SMTP_USUARIO` |
| `ML_ACCESS_TOKEN` | *(opcional)* token do Mercado Livre, só se a busca dele der erro 401/403 |

### 4. Ajuste suas buscas
Edite o `config.yaml`: marca, modelo, preço, ano, km, estado, cidades e
palavras a excluir (leilão, sinistro…). Dá para ter várias buscas.

### 5. Rode
Vá em **Actions → Robô de carros → Run workflow**. O 1º e-mail traz todos os
anúncios que existem hoje. Depois disso, o robô roda sozinho a cada hora e
manda e-mail só quando aparecer carro novo.

## Rodar no seu computador
```
pip install -r requirements.txt
python -m robo --simular      # mostra o e-mail no terminal, sem enviar
```

## Observações
- Os sites mudam o layout de vez em quando e alguns bloqueiam robôs; se uma
  plataforma falhar, as outras continuam funcionando, e o erro aparece no log
  do GitHub Actions. O ajuste fica em `robo/fontes/<plataforma>.py`.
- Os anúncios já vistos ficam em `dados/vistos.json` (salvo automaticamente).
- Respeite os termos de uso dos sites; o robô faz poucas requisições, com pausas.
