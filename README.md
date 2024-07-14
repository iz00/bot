<hr>

<div align="center">

  # Samsung Shop Troca Smart Telegram Bot

</div>

[Bot do Telegram](https://core.telegram.org/bots) facilitador na geração de links de carrinhos na [Samsung Shop](https://www.samsung.com/br/) com um produto escolhido e o seu respectivo desconto na promoção [Vale Mais - Troca Smart](https://www.samsung.com/br/trade-in/).

<hr>

## Uso do Bot

#### Comandos:
- **/start**: Retorna informações do funcionamento e utilização do bot.
- **/gerar**: Inicia o processo de geração do link do carrinho, através das etapas:
  - *Solicitação do modelo*: O bot apresenta uma lista de opções clicáveis, cada uma correspondente a um modelo de Smartphone/Tablet, além de uma opção extra "Outro".
  - *Solicitação de link*: Caso o usuário escolha a opção "Outro", é solicitado a informar o link do modelo na Samsung Shop, no formato: `https://shop.samsung.com/br/<modelo>/p`.
  - *Solicitação da capacidade*: O bot apresenta uma lista de opções clicáveis, cada uma correspondente a uma capacidade do modelo escolhido ou informado.
  - *Solicitação da cor*: O bot apresenta uma lista de opções clicáveis, cada uma correspondente a uma cor do modelo escolhido ou informado.
  - *Solicitação da quantidade de links*: O bot apresenta uma lista de opções clicáveis, cada uma correspondente a uma quantidade de links de carrinhos a serem gerados.
  - *Envio dos links dos carrinhos*: O bot gera e envia a quantidade solicitada de links de carrinhos, com o modelo e seus parâmetros escolhidos.

<hr>

## Funcionalidades Adicionais

- **Restrição de acesso**: O bot só permite o acesso às suas funcionalidade se o usuário é membro efetivo de determinado grupo do Telegram. Caso um usuário fora do grupo tente utilizá-lo, o bot responderá com uma mensagem negando o acesso.
- **Filtragem de capacidades e cores do modelo**: Após um modelo ser escolhido ou informado pelo usuário, o bot filtra na Samsung Shop as opções de capacidade oferecidas, assim como suas cores, e apresenta ao usuário apenas os parâmetros que possuem estoque. Caso o modelo esteja sem estoque, o usuário é informado e solicitado a escolher outro modelo.
- **Geração de link de carrinho com qualquer modelo de Smartphone/Tablet**: Mesmo que o modelo escolhido ou informado pelo usuário não ofereça o desconto da promoção Vale Mais - Troca Smart, ou nem mesmo ofereça a promoção Troca Smart, o link do carrinho com o modelo e seus parâmetros escolhidos ainda será gerado.

<hr>

## Arquivos e Implementação

<hr>

## Deploy

O deploy do bot foi feito através do serviço de [VPS](https://aws.amazon.com/pt/what-is/vps/) [**EC2**](https://docs.aws.amazon.com/pt_br/AWSEC2/latest/UserGuide/concepts.html) da [AWS](https://aws.amazon.com/pt/).

1. Uma [**instância EC2**](https://console.aws.amazon.com/ec2/home) foi criada com as características:
    - [Imagem de máquina da Amazon](https://docs.aws.amazon.com/pt_br/AWSEC2/latest/UserGuide/AMIs.html): `Ubuntu Server 24.04 LTS (HVM)`
    - [Tipo de instância](https://docs.aws.amazon.com/pt_br/AWSEC2/latest/UserGuide/instance-types.html): `t2.micro`
    - [Grupo de segurança](https://docs.aws.amazon.com/pt_br/vpc/latest/userguide/vpc-security-groups.html):
      - Regras de entrada (Tipo | Protocolo | Intervalo de portas | Origem):
        - `HTTPS` | `TCP` | `443` | `0.0.0.0/0`
        - `HTTP` | `TCP` | `80` | `0.0.0.0/0`
        - `TCP personalizado` | `TCP` | `<port do webhook>` | `0.0.0.0/0`
        - `SSH` | `TCP` | `22` | `0.0.0.0/0`
      - Regra de saída (Tipo | Protocolo | Intervalo de portas | Origem):
        - `HTTPS` | `TCP` | `443` | `0.0.0.0/0`
    - Outras configurações seguem no padrão.

2. A conexão com a instância (no estado `Executando`) foi feita através da `chave SSH`, do `nome do usuário` e do `DNS público` da instância:
```
ssh -i "<chave SSH>" <nome do usuário>@<DNS público>
```

3. Após estabelecida a conexão com a instância, para colocar o código do bot na instância, criar um ambiente virtual e instalar os requerimentos, os seguintes comandos foram executados:
```
sudo su
sudo apt update
sudo apt install python3-pip
git clone https://github.com/iz00/bot.git
cd bot
python3 -m venv env
source env/bin/activate
python3 -m pip install -r requirements.txt
```

O bot utiliza algumas variáveis de ambiente: `URL`, `PORT`, `ADMIN_CHAT_ID`, `TOKEN` e `GRUPO_ID`.

5. O `PORT` pode ser definido como qualquer valor acima de 1024 (portas não utilizadas por outros serviços), mas precisa ser equivalente à porta definida na instância nas regras de entrada do grupo de segurança.

6. O `ADMIN_CHAT_ID` é o ID do administrador do bot no Telegram, já o `GRUPO_ID` é o ID do grupo no Telegram que permitirá aos seus membros utilizarem as funções do bot.

7. Para obter o `TOKEN`, o [bot foi criado](https://core.telegram.org/bots/tutorial#obtain-your-bot-token) no Telegram através do [BotFather](https://t.me/BotFather), que retorna um `token` para o novo bot.

8. Para obter o `URL`, foi utilizada a ferramenta [`ngrok`](https://ngrok.com), já que o `URL` é o URL do webhook para o bot, e, mesmo que a instância disponibilize um IP e um DNS públicos, eles não podem ser definidos diretamente como o URL do webhook, pois não possuem certificados SSL válidos para HTTPS (*que também não podem ser atribuídos pois o domínio é de posse da Amazon*), e assim o Telegram não permite a comunicação. O `ngrok` é uma ferramenta de tunneling, que cria um túnel seguro (a partir do IP da instância) com suporte automático a HTTPS, permitindo o uso do URL como webhook. Para isso, é necessário a definição de um [`authtoken`](https://dashboard.ngrok.com/get-started/your-authtoken) e de um [`domínio estático`](https://dashboard.ngrok.com/cloud-edge/domains), que será o `URL`. Na instância, para instalar e configurar o `ngrok`, os seguintes comandos foram executados:
```
snap install ngrok
ngrok config add-authtoken <authtoken>
```

9. Para armazenar as variáveis de ambiente, foi criado o arquivo `/etc/bot_config` com as definições das variáveis:
```
URL=<domínio estático>
ADMIN_CHAT_ID=<ID do administrador do bot no Telegram>
PORT=<port do webhook>
TOKEN=<token>
GRUPO_ID=<ID do grupo no Telegram>
```

Para permitir que o tunneling do `ngrok` e o bot (webserver) sempre estejam executando, *mesmo com reinicializações da instância*, foi utilizado [`systemd`](https://systemd.io) com arquivos de unidade de serviço.

10. Para executar o tunneling do `ngrok`, foi criado o arquivo `/etc/systemd/system/ngrok.service`, com o conteúdo:
```
[Unit]
Description=ngrok HTTP tunnel
After=network.target

[Service]
ExecStart=/path/to/ngrok http --domain=<domínio estático> <port do webhook>
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
```

11. Para executar o bot (webserver), foi criado o arquivo `/etc/systemd/system/bot.service`, com o conteúdo:
```
[Unit]
Description=Telegram Bot
After=network.target

[Service]
EnvironmentFile=/etc/bot_config
ExecStart=/path/to/python3 /path/to/bot/bot.py
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
```

12. E, finalmente, para iniciar os serviços, os seguintes comandos foram executados:
```
sudo systemctl daemon-reload
sudo systemctl enable ngrok.service
sudo systemctl start ngrok.service
sudo systemctl enable bot.service
sudo systemctl start bot.service
```

13. [*Bônus*] Caso alguma alteração seja feita ao código, para ser refletida na instância, os seguintes comandos podem ser executados:
```
git pull
sudo systemctl daemon-reload
sudo systemctl restart bot.service
```

<hr>

## Considerações

- Não é possível parar ou utilizar outras funções do bot enquanto ele está gerando e enviando os links.
- Funciona apenas para modelos de [smartphones](https://www.samsung.com/br/smartphones/) e [tablets](https://www.samsung.com/br/tablets/) na Samsung Shop.
- Dicionário [`MODELOS`](https://github.com/iz00/bot/blob/main/modelos.py) precisa ser manualmente atualizado.
- Utiliza [`ngrok`](https://ngrok.com) para o tunneling do URL utilizado como webhook, o que normalmente é uma solução temporária.

<hr>
