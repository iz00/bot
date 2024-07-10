""" Utils para o bot.py."""

import aiohttp, re
from bs4 import BeautifulSoup


async def informacoes_modelo(url):
    informacoes = dict()

    if not re.compile(r"^https://shop\.samsung\.com/br/.+/p.*").match(url):
        return {"erro": "Formato de URL inválido"}

    if not url.endswith("/p"):
        url = url[: (url.find("/p")) + 2]

    url = re.sub(r"-\d+[gt]b", "", url)

    async with aiohttp.ClientSession() as sessao:
        try:
            async with sessao.get(url) as resposta:
                resposta.raise_for_status()
                dados = await resposta.text()
        except aiohttp.ClientError as e:
            print(f"Request falhou: {e}")
            return {"erro": "Página não encontrada"}

        match = re.search(
            r"https://shop\.samsung\.com/_v/segment/routing/vtex\.store@2\.x/product/(\d+)/",
            dados,
        )
        try:
            id = match.group(1)
        except AttributeError:
            return {"erro": "Erro ao filtrar características do modelo"}

        conteudo = BeautifulSoup(dados, "html.parser")
        ref = conteudo.find(
            "strong", class_="samsungbr-app-pdp-2-x-productReferenceId"
        ).text
        if not ref:
            return {"erro": "Erro ao filtrar características do modelo"}

        capacidades_url = f"https://searchapi.samsung.com/v6/front/b2c/product/card/detail/global?siteCode=br&modelList={ref}&commonCodeYN=N&saleSkuYN=N&onlyRequestSkuYN=N&keySummaryYN=Y&shopSiteCode=br"

        try:
            async with sessao.get(capacidades_url) as resposta:
                resposta.raise_for_status()
                dados = await resposta.json()
        except aiohttp.ClientError as e:
            print(f"Request falhou: {e}")
            return {"erro": "Erro ao filtrar características do modelo"}

        capacidades = [
            option["optionCode"]
            for product in dados["response"]["resultData"]["productList"]
            for chip_option in product["chipOptions"]
            if chip_option["fmyChipType"] == "MOBILE MEMORY"
            for option in chip_option["optionList"]
        ]

        for capacidade in capacidades:
            if capacidades.index(capacidade) != 0:
                novo_url = f"{url[:-2]}-{capacidade.lower().replace(' ', '')}/p"
                try:
                    async with sessao.get(novo_url) as resposta:
                        resposta.raise_for_status()
                        dados = await resposta.text()
                except aiohttp.ClientError as e:
                    print(f"Request falhou: {e}")
                    continue
                match = re.search(
                    r"https://shop\.samsung\.com/_v/segment/routing/vtex\.store@2\.x/product/(\d+)/",
                    dados,
                )
                id = match.group(1)

            cores_url = f"https://shop.samsung.com/br/api/catalog_system/pub/products/search/?fq=productId:{id}"
            try:
                async with sessao.get(cores_url) as resposta:
                    resposta.raise_for_status()
                    dados = await resposta.json()
            except aiohttp.ClientError as e:
                print(f"Request falhou: {e}")
                return {"erro": "Erro ao filtrar características do modelo"}

            cores = dict()

            for item in dados[0]["items"]:
                if item["sellers"][0]["commertialOffer"]["IsAvailable"]:
                    cores[item["name"]] = item["itemId"]

            if cores:
                informacoes[capacidade] = dict()
                informacoes[capacidade]["cores"] = cores
                informacoes[capacidade]["id"] = id

    if not informacoes:
        return {"erro": "O produto escolhido não está disponível no momento"}

    return informacoes


async def gerar_link(id_modelo, id_capacidade_cor):
    async with aiohttp.ClientSession() as sessao:
        url = "https://shop.samsung.com/br/api/checkout/pub/orderForm"
        headers = {
            "accept": "application/json, text/plain, */*",
            "content-type": "application/json",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }
        try:
            async with sessao.post(url, headers=headers) as resposta:
                resposta.raise_for_status()
                dados = await resposta.json()
        except aiohttp.ClientError as e:
            print(f"Request para gerar orderFormId falhou: {e}")
            return None
        order_form_id = dados.get("orderFormId")

        url = f"https://shop.samsung.com/br/api/checkout/pub/orderForm/{order_form_id}/items"
        payload = {
            "orderItems": [{"id": id_capacidade_cor, "quantity": 1, "seller": "1"}]
        }
        try:
            async with sessao.post(url, headers=headers, json=payload) as resposta:
                resposta.raise_for_status()
        except aiohttp.ClientError as e:
            print(f"Request para colocar item no carrinho falhou: {e}")
            return None

        url = f"https://shop.samsung.com/br/tradein/vtex/getProductGroup/{id_modelo}/{id_capacidade_cor}/MQ=="
        try:
            async with sessao.get(url, headers=headers) as resposta:
                resposta.raise_for_status()
                dados = await resposta.json()
        except aiohttp.ClientError as e:
            print(f"Request para pegar marketingTag falhou: {e}")
            return None
        marketing_tag = dados[0].get("marketingTag")

        if marketing_tag:
            url = f"https://shop.samsung.com/br/api/checkout/pub/orderForm/{order_form_id}/attachments/marketingData"
            payload = {"marketingTags": [marketing_tag]}
            try:
                async with sessao.post(url, headers=headers, json=payload) as resposta:
                    resposta.raise_for_status()
            except aiohttp.ClientError as e:
                print(f"Request para colocar marketingTag falhou: {e}")
                return None

        return f"https://shop.samsung.com/br/checkout?orderFormId={order_form_id}#/cart"
