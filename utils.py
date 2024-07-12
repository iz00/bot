"""
Utils para o bot.py.
Utilizam URLs APIs da Samsung Shop para extraírem informações de modelos e para adicionarem informações ao carrinho.

Função `informacoes_modelo`, que filtra as capacidades e as cores do modelo, assim como seus IDs associados.\n
Função `gerar_link`, que gera link de carrinho na Samsung Shop com o produto e desconto do Vale Mais - Troca Smart.
"""

import aiohttp, re
from bs4 import BeautifulSoup


async def informacoes_modelo(url: str) -> dict:
    """
    Retorna informações do modelo através de seu url na Samsung Shop.
    Retorna as capacidades e as cores, com seus IDs, se há estoque.\n
    Formato do dicionário retornado: `{capacidade: {"id": id, "cores": {cor: id}}}`
    """
    informacoes = dict()

    # Validação do formato do URL
    if not re.compile(r"^https://shop\.samsung\.com/br/.+/p.*").match(url):
        return {"erro": "Formato de URL inválido"}

    # Retirar parâmetros que possam estar no URL, como skuId
    if not url.endswith("/p"):
        url = url[: (url.find("/p")) + 2]

    # Retirar especificação de capacidade do URL, para que o primeiro ID seja o da menor capacidade
    url = re.sub(r"-\d+[gt]b", "", url)

    async with aiohttp.ClientSession() as sessao:
        # Requisição GET para pegar HTML do URL
        try:
            async with sessao.get(url) as resposta:
                resposta.raise_for_status()
                dados = await resposta.text()
        except aiohttp.ClientError as e:
            print(f"Requisição GET para pegar HTML do URL {url} falhou: {e}")
            return {"erro": "Página não encontrada"}

        # Pegar ID do modelo no HTML da página
        procura = re.search(
            r"https://shop\.samsung\.com/_v/segment/routing/vtex\.store@2\.x/product/(\d+)/",
            dados,
        )
        try:
            id = procura.group(1)
        except AttributeError:
            print(f"ID do modelo {url} não foi encontrado.")
            return {"erro": "Erro ao filtrar características do modelo"}

        # Pegar referenceId do modelo no HTML da página
        conteudo = BeautifulSoup(dados, "html.parser")
        ref = conteudo.find(
            "strong", class_="samsungbr-app-pdp-2-x-productReferenceId"
        ).text
        if not ref:
            print(f"referenceId do modelo {url} não foi encontrado.")
            return {"erro": "Erro ao filtrar características do modelo"}

        # URL da API para pegar as capacidades disponíveis para o modelo através do referenceId
        capacidades_url = f"https://searchapi.samsung.com/v6/front/b2c/product/card/detail/global?siteCode=br&modelList={ref}&commonCodeYN=N&saleSkuYN=N&onlyRequestSkuYN=N&keySummaryYN=Y&shopSiteCode=br"
        # Requisição GET para pegar as capacidades disponíveis para o modelo
        try:
            async with sessao.get(capacidades_url) as resposta:
                resposta.raise_for_status()
                dados = await resposta.json()
        except aiohttp.ClientError as e:
            print(
                f"Requisição GET para pegar as capacidades do modelo {ref} falhou: {e}"
            )
            return {"erro": "Erro ao filtrar características do modelo"}

        # Extrair as capacidades da resposta
        capacidades = [
            opcao["optionCode"]
            for produto in dados["response"]["resultData"]["productList"]
            for opcao_chip in produto["chipOptions"]
            if opcao_chip["fmyChipType"] == "MOBILE MEMORY"
            for opcao in opcao_chip["optionList"]
        ]

        for capacidade in capacidades:

            # Apenas pegar o ID das outras capacidades, porque da menor (primeira) o ID já foi extraído
            if capacidades.index(capacidade) != 0:
                # Alterar formato do URL para corresponder à capacidade
                url_especifico_capacidade = (
                    f"{url[:-2]}-{capacidade.lower().replace(' ', '')}/p"
                )
                try:
                    async with sessao.get(url_especifico_capacidade) as resposta:
                        resposta.raise_for_status()
                        dados = await resposta.text()
                except aiohttp.ClientError as e:
                    print(
                        f"Requisição GET para pegar HTML do URL {url_especifico_capacidade} falhou: {e}"
                    )
                    continue

                procura = re.search(
                    r"https://shop\.samsung\.com/_v/segment/routing/vtex\.store@2\.x/product/(\d+)/",
                    dados,
                )
                try:
                    id = procura.group(1)
                except AttributeError:
                    print(
                        f"ID do modelo {url_especifico_capacidade} não foi encontrado."
                    )
                    continue

            # URL da API para pegar as cores disponíveis para o modelo e a capacidade através do ID
            cores_url = f"https://shop.samsung.com/br/api/catalog_system/pub/products/search/?fq=productId:{id}"
            # Requisição GET para pegar as cores disponíveis para o modelo e a capacidade
            try:
                async with sessao.get(cores_url) as resposta:
                    resposta.raise_for_status()
                    dados = await resposta.json()
            except aiohttp.ClientError as e:
                print(
                    f"Requisição GET para pegar as cores do modelo de ID {id} falhou: {e}"
                )
                return {"erro": "Erro ao filtrar características do modelo"}

            cores = dict()

            # Extrair o nome da cor e o seu ID da resposta, apenas se a cor possui estoque
            for item in dados[0]["items"]:
                if item["sellers"][0]["commertialOffer"]["IsAvailable"]:
                    cores[item["name"]] = item["itemId"]

            # Se existe alguma cor com estoque para a capacidade, atualize o dicionário `informacoes`
            if cores:
                informacoes[capacidade] = dict()
                informacoes[capacidade]["cores"] = cores
                informacoes[capacidade]["id"] = id

    # Caso o modelo não tenha estoque para nenhuma capacidade
    if not informacoes:
        return {"erro": "O produto escolhido não está disponível no momento"}

    return informacoes


async def gerar_link(id_modelo: str | int, id_cor: str | int) -> str:
    """
    Gera link de carrinho na Samsung Shop com desconto do Vale Mais - Troca Smart,
    através do ID do modelo (dependente da capacidade) e do ID da cor (dependente da cor).\n
    Formato do link retornado: `https://shop.samsung.com/br/checkout?orderFormId={order_form_id}#/cart`
    """
    async with aiohttp.ClientSession() as sessao:
        # Cabeçalhos das requisições
        headers = {
            "accept": "application/json, text/plain, */*",
            "content-type": "application/json",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }

        # URL da API para criar um carrinho vazio
        url = "https://shop.samsung.com/br/api/checkout/pub/orderForm"
        # Requisição POST para criar um carrinho vazio
        try:
            async with sessao.post(url, headers=headers) as resposta:
                resposta.raise_for_status()
                dados = await resposta.json()
        except aiohttp.ClientError as e:
            print(f"Requisição POST para criar um carrinho vazio falhou: {e}")
            return None

        # Pegar orderFormId (ID do carrinho) da resposta
        order_form_id = dados.get("orderFormId")
        if not order_form_id:
            print("orderFormId não foi encontrado.")
            return None

        # URL da API para adicionar um produto ao carrinho
        url = f"https://shop.samsung.com/br/api/checkout/pub/orderForm/{order_form_id}/items"
        # Dados do produto a ser adicionado
        payload = {"orderItems": [{"id": id_cor, "quantity": 1, "seller": "1"}]}
        # Requisição POST para adicionar o produto ao carrinho
        try:
            async with sessao.post(url, headers=headers, json=payload) as resposta:
                resposta.raise_for_status()
        except aiohttp.ClientError as e:
            print(
                f"Requisição POST para adicionar item de ID {id_cor} ao carrinho falhou: {e}"
            )
            return None

        # URL da API para pegar a marketingTag associada ao modelo, capacidade e cor específicas
        # A marketingTag define o valor do Vale Mais - Troca Smart
        url = f"https://shop.samsung.com/br/tradein/vtex/getProductGroup/{id_modelo}/{id_cor}/MQ=="
        # Requisição GET para pegar a marketingTag
        try:
            async with sessao.get(url, headers=headers) as resposta:
                resposta.raise_for_status()
                dados = await resposta.json()
        except aiohttp.ClientError as e:
            print(
                f"Requisição GET para pegar a marketingTag do modelo de ID {id_modelo} falhou: {e}"
            )
            return None

        # Pegar marketingTag da resposta
        marketing_tag = dados[0].get("marketingTag")

        # Se o modelo não possui marketingTag, não oferece Vale Mais - Troca Smart
        if marketing_tag:

            # URL da API para adicionar a marketingTag ao carrinho
            url = f"https://shop.samsung.com/br/api/checkout/pub/orderForm/{order_form_id}/attachments/marketingData"
            # marketingTag a ser adicionada ao carrinho
            payload = {"marketingTags": [marketing_tag]}
            # Requisição POST para adicionar a marketingTag ao carrinho
            try:
                async with sessao.post(url, headers=headers, json=payload) as resposta:
                    resposta.raise_for_status()
            except aiohttp.ClientError as e:
                print(
                    f"Requisição POST para adicionar a marketingTag {marketing_tag} ao carrinho falhou: {e}"
                )
                return None

        # Retorna link do carrinho, com o orderFormId
        return f"https://shop.samsung.com/br/checkout?orderFormId={order_form_id}#/cart"
