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

<hr>

## Considerações

- Não é possível parar ou utilizar outras funções do bot enquanto ele está gerando e enviando os links.
- Funciona apenas para modelos de [smartphones](https://www.samsung.com/br/smartphones/) e [tablets](https://www.samsung.com/br/tablets/) na Samsung Shop.
- Dicionário [`MODELOS`](https://github.com/iz00/bot/blob/main/modelos.py) precisa ser manualmente atualizado.
- Utiliza [`ngrok`](https://ngrok.com) para o tunneling do URL utilizado como webhook, o que normalmente é uma solução temporária.
