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

### [`modelos.py`](https://github.com/iz00/bot/blob/main/modelos.py)

Definição do dicionário global `MODELOS`, que armazena os modelos oferecidos pelo bot na lista de opções.

As chaves do dicionário são os nomes dos modelos que aparecerão para o usuário (*não necessariamente o mesmo nome da loja*).

Os valores do dicionário são os links do modelo correspondente na Samsung Shop, no formato: `https://shop.samsung.com/br/<modelo>/p`.

##

### [`utils.py`](https://github.com/iz00/bot/blob/main/utils.py)

Definição de funções utilitárias para o bot. Utilizam URLs APIs da Samsung Shop para extrair informações de modelos e para adicionar informações a um carrinho.

<br>

#### **`informacoes_modelo`**:
Filtra e retorna as capacidades e cores de um modelo (e seus IDs correspondentes), a partir de seu URL, se há estoque.

Utiliza os módulos: `re` para validar o `url`, `aiohttp` para realizar requisições a URLs APIs da Samsung Shop e `BeautifulSoup` para analisar o HTML retornado.

- **Parâmetro**: `url`, tipo `str`
- **Retorna**: tipo `dict`, no formato: `{capacidade: {"id": id, "cores": {cor: id}}}`, ex:
```
{
  "128 GB": {
    "id": 1234,
    "cores": {
      "Azul": 7654,
      "Verde": 7655,
    }
  },
  "256 GB": {
    "id": 4321,
    "cores": {
      "Azul": 5432,
    }
  },
}
```
- **Informações**:
  - Cada modelo com uma capacidade possui um ID próprio, e, para cada cor, existe outro ID próprio.
  - Todo modelo  possui uma `capacidade padrão`, que não está explícita no URL, as outras aparecem diretamente no URL, no formato: `https://shop.samsung.com/br/<modelo>-<capacidade>/p`, em que `capacidade` é algo como `128gb` ou `1tb`.
  - Cada modelo possui um `referenceId`, no formato: `AA-A000AAAAAAA`, que muda com a capacidade, mas, no caso do bot, qualquer `referenceId` do modelo serve.

Inicialmente, é feita a validação do formato do `url`, que precisa ser `https://shop.samsung.com/br/<modelo>/p`. Então são retirados quaisquer parâmetros que possam estar após o `/p`, e por fim retirada a especificação de capacidade, se estiver no `url`.

Uma requisição `GET` é feita para pegar o HTML do `url`, e, nele, procurar o `id` do modelo com a `capacidade padrão`. O HTML é analisado com `BeautifulSoup` e é extraído o `referenceId` do modelo.

São recuperadas as capacidades oferecidas pelo modelo através de uma requisição `GET` para a URL API, com o `referenceId`:
```
https://searchapi.samsung.com/v6/front/b2c/product/card/detail/global?siteCode=br&modelList=<referenceId>&commonCodeYN=N&saleSkuYN=N&onlyRequestSkuYN=N&keySummaryYN=Y&shopSiteCode=br
```

A `capacidade padrão` é determinada por uma requisição `GET` para a URL API, com o `id`:
```
https://shop.samsung.com/br/api/catalog_system/pub/products/search/?fq=productId:<id>
```

Então, para cada capacidade disponível, são extraídas as cores e seus respectivos IDs, apenas se há estoque (*parâmetro `IsAvailable`*), por uma requisição `GET` para a URL API, com o `id` (*mesmo URL para determinar a `capacidade padrão`*):
```
https://shop.samsung.com/br/api/catalog_system/pub/products/search/?fq=productId:<id>
```

Como para a `capacidade padrão`, a requisição com o `id` já foi feita, a resposta é apenas analisada. Para as outras capacidades, o processo de determinar o `id` e fazer a requisição é repetido, com o `url` sendo alterado para especificar a capacidade.

<br>

#### **`gerar_link`**:
Gera e retorna link de carrinho na Samsung Shop com um produto e com desconto aplicado da promoção Vale Mais - Troca Smart.

Utiliza o módulo: `aiohttp` para realizar requisições a URLs APIs da Samsung Shop.

- **Parâmetros**:
  - `id_modelo`, tipo `str` | `int`, é o ID do modelo e da capacidade escolhida.
  - `id_cor`, tipo `str` | `int`, é o ID da cor escolhida daquele modelo e capacidade específicas.
- **Retorna**: tipo `str`, no formato: `https://shop.samsung.com/br/checkout?orderFormId=<orderFormId>#/cart`.
- **Informações**:
  - Cada carrinho possui um ID próprio, chamado `orderFormId`.
  - O ID do produto adicionado ao carrinho é o ID da cor, que é um ID mais específico e também depende do modelo e da capacidade do produto.
  - A promoção Troca Smart retorna ao consumidor, após uma compra, um valor determinado pelo aparelho utilizado na troca (*o bot não lida com essa parte*).
  - O valor do Vale Mais - Troca Smart depende para cada modelo da loja, é um valor fixo que vira desconto na compra, e é especificado no parâmetro `marketingTag`, no formato: `GTI<valor>5117`.

Inicialmente, é criado um carrinho vazio e recuperado seu `orderFormId` através de uma requisição POST para a URL API:
```
https://shop.samsung.com/br/api/checkout/pub/orderForm
```

O produto, de ID `id_cor`, é adicionado ao carrinho criado por uma requisição `POST` para a URL API, com o payload `{"orderItems": [{"id": <id_cor>, "quantity": 1, "seller": "1"}]}`:
```
https://shop.samsung.com/br/api/checkout/pub/orderForm/<order_form_id>/items
```

A `marketingTag` do modelo é determinada por uma requisição `GET` para a URL API, com o `id_modelo` e o `id_cor` (*caso o modelo não ofereça desconto Vale Mais, a `marketingTag` será `None`, e, caso o modelo nem ofereça Troca Smart, o retorno da requisição será `[]`*):
```
https://shop.samsung.com/br/tradein/vtex/getProductGroup/<id_modelo>/<id_cor>/MQ==
```

Caso o modelo possua a `marketingTag`, ela é adicionada ao carrinho criado por uma requisição `POST` para a URL API, com o payload `{"marketingTags": [<marketing_tag>]}`:
```
https://shop.samsung.com/br/api/checkout/pub/orderForm/<order_form_id>/attachments/marketingData
```

##

### [`bot.py`](https://github.com/iz00/bot/blob/main/bot.py)

Código do bot do Telegram e do webserver.

Utiliza os módulos: `python-telegram-bot` para utilizar a `Telegram Bot API`, `Flask` e `uvicorn` para a configuração do webhook do bot.

A comunicação do bot ocorre através de [webhook](https://core.telegram.org/bots/api#setwebhook) com `Flask`, com base no [exemplo da documentação](https://docs.python-telegram-bot.org/en/v21.4/examples.customwebhookbot.html) do `python-telegram-bot`.

A restrição de acesso ao bot é implementada através do wrapper `restringir_acesso`, que checa o status do usuário no grupo, através do método `get_chat_member`, com o ID do grupo e o ID do usuário que tentou utilizar o bot. O wrapper é aplicado às funções associadas aos `Handler`s dos comandos `/start` e `/gerar`.

O processo de escolha do modelo e seus parâmetros, até o envio dos links, é implementado através de um `ConversationHandler`, que utiliza `InlineKeyboard`s e `CallbackQueryHandler`s, baseado no [exemplo da documentação](https://docs.python-telegram-bot.org/en/v21.4/examples.inlinekeyboard2.html) do `python-telegram-bot`. O `ConversationHandler` possui as etapas:

1. `entry_point` (*não é exatamente um state, dá início ao `ConversationHandler`*): Através do uso do comando `/gerar`, executa a função `escolha_modelo`, que apresenta ao usuário uma lista de `InlineKeyboardButton`s em um `InlineKeyboard`, cada um correspondente a um modelo do dicionário `MODELOS`, além de uma `InlineKeyboardButton` extra "Outro".
2. `MODELO`:
    - Através da escolha de algum dos `InlineKeyboardButton`s correspondentes a um modelo do `MODELOS`, executa a função `escolha_capacidade`, que executa a função `informacoes_modelo`
    - Através da escolha do `InlineKeyboardButton` extra "Outro", executa a função `informa_link`, que solicita ao usuário digitar o link do URL do modelo desejado na Samsung Shop.
4. `LINK` (*opcional*):
5. `CAPACIDADE`:
6. `COR`:
7. `QUANTIDADE`:

As informações de escolhas do usuário e do modelo são, durante a execução das funções correspondentes no `ConversationHandler`, armazenadas no `context.user_data`.

Constantemente mensagens são apagadas com `context.bot.delete_message`, isso tem o objetivo de limpar o chat, deixando apenas a mensagem do usuário com o comando `/gerar` e os links enviados pelo bot.

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

4. O `PORT` pode ser definido como qualquer valor acima de 1024 (portas não utilizadas por outros serviços), mas precisa ser equivalente à porta definida na instância nas regras de entrada do grupo de segurança.

5. O `ADMIN_CHAT_ID` é o ID do administrador do bot no Telegram, já o `GRUPO_ID` é o ID do grupo no Telegram que permitirá aos seus membros utilizarem as funções do bot.

6. Para obter o `TOKEN`, o [bot foi criado](https://core.telegram.org/bots/tutorial#obtain-your-bot-token) no Telegram através do [BotFather](https://t.me/BotFather), que retorna um `token` para o novo bot.

7. Para obter o `URL`, foi utilizada a ferramenta [`ngrok`](https://ngrok.com), já que o `URL` é o URL do webhook para o bot, e, mesmo que a instância disponibilize um IP e um DNS públicos, eles não podem ser definidos diretamente como o URL do webhook, pois não possuem certificados SSL válidos para HTTPS (*que também não podem ser atribuídos pois o domínio é de posse da Amazon*), e assim o Telegram não permite a comunicação. O `ngrok` é uma ferramenta de tunneling, que cria um túnel seguro (a partir do IP da instância) com suporte automático a HTTPS, permitindo o uso do URL como webhook. Para isso, é necessário a definição de um [`authtoken`](https://dashboard.ngrok.com/get-started/your-authtoken) e de um [`domínio estático`](https://dashboard.ngrok.com/cloud-edge/domains), que será o `URL`. Na instância, para instalar e configurar o `ngrok`, os seguintes comandos foram executados:
```
snap install ngrok
ngrok config add-authtoken <authtoken>
```

8. Para armazenar as variáveis de ambiente, foi criado o arquivo `/etc/bot_config` com as definições das variáveis:
```
URL=<domínio estático>
ADMIN_CHAT_ID=<ID do administrador do bot no Telegram>
PORT=<port do webhook>
TOKEN=<token>
GRUPO_ID=<ID do grupo no Telegram>
```

Para permitir que o tunneling do `ngrok` e o bot (webserver) sempre estejam executando, *mesmo com reinicializações da instância*, foi utilizado [`systemd`](https://systemd.io) com arquivos de unidade de serviço.

9. Para executar o tunneling do `ngrok`, foi criado o arquivo `/etc/systemd/system/ngrok.service`, com o conteúdo:
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

10. Para executar o bot (webserver), foi criado o arquivo `/etc/systemd/system/bot.service`, com o conteúdo:
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

11. E, finalmente, para iniciar os serviços, os seguintes comandos foram executados:
```
sudo systemctl daemon-reload
sudo systemctl enable ngrok.service
sudo systemctl start ngrok.service
sudo systemctl enable bot.service
sudo systemctl start bot.service
```

12. [*Bônus*] Caso alguma alteração seja feita ao código, para ser refletida na instância, os seguintes comandos podem ser executados:
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
- Utiliza [`ngrok`](https://ngrok.com) para o tunneling do URL do webhook, o que normalmente é uma solução temporária.

<hr>
