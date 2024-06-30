""" Utils para o bot.py.

Definição das variáveis globais MODELOS_OPCOES e CAPACIDADES_OPCOES, com as opções a serem apresentadas ao usuário.
Função filtrar_modelos, que usa BeautifulSoup para filtrar os modelos com estoque e suas cores no MODELOS_OPCOES.
Função checar_imei, que valida IMEI, retorna informações do dispositivo correspondente e atualiza CAPACIDADES_OPCOES.
Função gerar_link, que usa Playwright para gerar link do carrinho na loja com o produto e o desconto."""

import requests
from modelos import MODELOS
from bs4 import BeautifulSoup
from json import loads
from playwright._impl._errors import TimeoutError
from playwright.async_api import async_playwright
from re import match

# Dicionário com os modelos e suas cores disponíveis (com estoque)
MODELOS_OPCOES = dict()
# Set com as capacidades disponíveis para o IMEI informado
CAPACIDADES_OPCOES = set()


def filtrar_modelos() -> bool:
    """Filtra os modelos e as cores disponíveis na loja através do dicionário MODELOS.
    Atualiza o dicionário global MODELOS_OPCOES apenas com modelos e cores em estoque.
    """
    MODELOS_OPCOES.clear()

    # Pega o HTML da página na loja de cada modelo
    for modelo, url in MODELOS.items():
        try:
            resposta = requests.get(url)
            resposta.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Request falhou: {e}")
            return False

        conteudo = BeautifulSoup(resposta.content, "html.parser")

        # Encontra o div que contém as opções de cores
        div_cores = conteudo.find("div", {"id": "selector-color"}).find(
            "div", class_="samsungbr-app-pdp-2-x-selectorWrapper"
        )
        if not div_cores:
            return False

        # Lista para armazenar as cores disponíveis para o modelo
        cores = []

        # Encontra todos os botões das opções de cores
        botoes_cores = div_cores.find_all("button")

        for botao in botoes_cores:
            # Se não existe estoque da cor, passe para a próxima opção
            if botao.find("div", class_="samsungbr-app-pdp-2-x-outOfStock"):
                continue

            # Encontra o nome da cor e armazena na lista de cores
            div_nome_cor = botao.find("div", class_="samsungbr-app-pdp-2-x-variantName")
            if div_nome_cor:
                cor = div_nome_cor.text.strip()
                cores.append(cor)

        # Se o modelo tem alguma cor disponível, ele aparece como uma opção para o usuário
        if cores:
            MODELOS_OPCOES[modelo] = {"url": url, "cores": cores}

    return True


def checar_imei(imei) -> dict:
    """Checa IMEI informado pelo usuário, retorna dicionário vazio caso inválido.
    Atualiza o dicionário global CAPACIDADES_OPCOES e retorna informações do dispositivo se validado.
    """

    url = f"https://shop.samsung.com/br/tradein/trocafone/checkImei/{imei}/true"
    headers = {
        "Accept": "application/json, text/javascript, */*; q=0.01",
    }

    # Caso o formato do IMEI é inválido
    if not match(pattern=r"^\d{15}$", string=imei):
        return {}

    try:
        resposta = requests.get(url, headers=headers)
        resposta.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Request falhou: {e}")
        return {}

    dados = resposta.json()

    # Caso IMEI não corresponde a um dispositivo ou dispositivo não está disponível para Troca Smart
    if "is_imei_valid" in dados and not dados["is_imei_valid"]:
        return {}

    # Atualiza dicionário global com as capacidades disponíveis do dispositivo
    CAPACIDADES_OPCOES.clear()
    for produto in dados["products"]:
        CAPACIDADES_OPCOES.add(produto["attributes"]["storage"]["label"])

    # Retorna dicionário com a marca e o modelo do dispositivo
    return {"marca": dados["brand"]["name"], "modelo": dados["model"]["name"]}


async def gerar_link(url, cor, marca, modelo, capacidade, imei) -> dict:
    """Gera link de carrinho na Samsung Shop com desconto da Troca Smart."""

    async with async_playwright() as p:
        # Abre um contexto no Chromium no modo headless
        browser = await p.chromium.launch(chromium_sandbox=False, headless=True)
        contexto = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            bypass_csp=True,
            ignore_https_errors=True,
            java_script_enabled=True,
        )

        try:
            # Setar e pegar orderFormId para gerar o link do carrinho
            pagina = await contexto.new_page()
            await pagina.goto(
                "https://shop.samsung.com/br/api/checkout/pub/orderForm?refreshOutdatedData=true",
                wait_until="domcontentloaded",
            )
            conteudo = await pagina.inner_html("pre")
            order_form_id = loads(conteudo).get("orderFormId")

            pagina = await contexto.new_page()

            # Vai para a página da loja do modelo e cor escolhidos
            await pagina.goto(url, wait_until="domcontentloaded")

            # Impedir que o request que termina em /shippingData coloque o CEP placeholder no carrinho
            await pagina.route("**/shippingData", lambda route: route.abort())

            # Scrollar para carregar os elementos
            await pagina.evaluate("window.scrollTo(0, 1000);")

            # Clicar na cor escolhida
            await pagina.click(
                selector=f'.samsungbr-app-pdp-2-x-variantName:has-text("{cor}")'
            )

            # Clicar no botão de iniciar a Troca Smart
            # A cada tentativa, interage com a página (scroll) para carregar o botão
            for i in range(3):
                try:
                    await pagina.click(
                        selector=".samsungbr-samsung-tradein-standalone-1-x-bonusTradeinPdpBtn",
                        timeout=10000,
                    )
                    break
                except TimeoutError:
                    await pagina.evaluate(f"window.scrollTo(0, {1000 + i});")
                    continue

            # Inserir a marca do dispositivo da Troca Smart
            await pagina.click(selector="#react-select-2-input")
            await pagina.fill(selector="#react-select-2-input", value=marca)
            await pagina.press(selector="#react-select-2-input", key="Enter")

            # Inserir o modelo do dispositivo da Troca Smart
            await pagina.click(selector="#react-select-3-input")
            await pagina.fill(selector="#react-select-3-input", value=modelo)
            await pagina.press(selector="#react-select-3-input", key="Enter")

            # Inserir a capacidade do dispositivo da Troca Smart
            await pagina.click(selector="#react-select-4-input")
            await pagina.fill(selector="#react-select-4-input", value=capacidade)
            await pagina.press(selector="#react-select-4-input", key="Enter")

            # Continuar para próxima etapa
            await pagina.click(
                selector=".samsungbr-samsung-tradein-standalone-1-x-modalFooterBtn__continue"
            )

            # Informar que o dispositivo está em boas condições
            await pagina.click(selector=".aut_tradein_condition_yes")

            # Continuar para próxima etapa
            await pagina.click(
                selector=".samsungbr-samsung-tradein-standalone-1-x-modalFooterBtn__continue"
            )

            # Inserir o IMEI do dispositivo da Troca Smart
            await pagina.fill(
                selector=".samsungbr-samsung-tradein-standalone-1-x-checkImeiInput",
                value=imei,
            )

            # Esperar a confirmação da validação do IMEI
            await pagina.wait_for_selector(
                ".samsungbr-samsung-tradein-standalone-1-x-checkImeiTextValid"
            )

            # Terminar processo da Troca Smart e voltar para a página da loja
            await pagina.click(
                selector=".samsungbr-samsung-tradein-standalone-1-x-modalFooterBtn__continue"
            )

            # Inserir um CEP placeholder (de SP), apenas para poder completar a compra
            await pagina.fill(selector="#postal-code", value="01153000")
            await pagina.press(selector="#postal-code", key="Enter")

            # Escolher a opção de não incluir Samsung Care+
            await pagina.click(selector='p:has-text("Não incluir Samsung Care+")')

            # Esperar a confirmação do CEP para poder completar a compra
            try:
                await pagina.wait_for_selector(
                    ".samsungbr-app-pdp-2-x-shippingButtonSelectType"
                )

            # Caso o CEP não seja confirmado, não existe estoque para a região do CEP placeholder
            except TimeoutError:
                return {"erro": "O produto escolhido não está disponível no momento."}

            # Clicar para comprar o produto
            await pagina.click(selector="#button-buy-product")

            # Fazer com que todas as operações sejam feitas no mesmo orderFormId
            nova_pagina = await contexto.new_page()
            await nova_pagina.goto(
                "https://shop.samsung.com/br/api/checkout/pub/orderForm?refreshOutdatedData=true",
                wait_until="domcontentloaded",
            )

        # Caso algum elemento não seja encontrado na página
        except TimeoutError:
            return {"erro": "Houve um erro ao gerar o link."}

        finally:
            # Fechar browser
            await contexto.close()
            await browser.close()

        # Montar e retornar link do carrinho com o orderFormId
        return {
            "link": f"https://shop.samsung.com/br/checkout?orderFormId={order_form_id}#/cart"
        }
