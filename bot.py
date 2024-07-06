#!/usr/bin/env python

"""
Telegram bot que gera links para o carrinho da loja da Samsung com um produto escolhido e desconto da Troca Smart.

A comunicação do bot ocorre através de webhook com Flask.
O bot funciona através do `ConversationHandler`, que define a ordem de algumas callback functions.
A ordem das funções, definida nas etapas (`states`), pede ao usuário escolher o modelo e a cor do produto escolhido,
o IMEI do dispositivo a ser utilizado na Troca Smart e sua capacidade de armazenamento.
Os modelos e suas cores são filtrados com web scraping com BeautifulSoup,
para serem apresentados nos botões para os usuários apenas se estão com estoque.
Os botões funcionam através de `InlineKeyboard`.
O link é gerado com automação de browser com Playwright, no Chromium.

Uso:
O bot solicita informações sobre um produto através de `InlineKeyboard` com múltiplos `CallbackQueryHandlers` 
organizados em um `ConversationHandler`, e também solicita informações do dispositivo da Troca Smart.
Com essas informações o bot gera o link do carrinho com o produto e o desconto.
Envie /start para informações de como utilizar.
Envie /gerar para iniciar o processo de geração do link.
Escolha um modelo, uma cor, informe o IMEI e escolha uma capacidade.
"""

import asyncio, logging, uvicorn
from modelos import MODELOS
from utils import (
    filtrar_modelos,
    checar_imei,
    gerar_link,
)
from asgiref.wsgi import WsgiToAsgi
from dataclasses import dataclass
from flask import Flask, Response, abort, make_response, request
from http import HTTPStatus
from os import getenv
from re import escape
from telegram import ChatMember, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.error import TelegramError
from telegram.ext import (
    Application,
    CallbackContext,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    ConversationHandler,
    ExtBot,
    MessageHandler,
    TypeHandler,
    filters,
)

# Habilitar logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Definições para o webhook
URL = getenv("URL")
PORT = int(getenv("PORT"))

# ID do chat do admin no Telegram e TOKEN do bot gerado pelo BotFather
ADMIN_CHAT_ID = int(getenv("ADMIN_CHAT_ID"))
TOKEN = getenv("TOKEN")

# ID do grupo para restrição de acesso
GRUPO_ID = getenv("GRUPO_ID")

# Definição das etapas do `ConversationHandler`
MODELO, COR, IMEI, CAPACIDADE = range(4)

# Todas as possibilidades de cores e de capacidades para as patterns nos `CallbackQueryHandlers`
CORES = ["Azul", "Azul Claro", "Azul Escuro", "Cinza", "Lavanda", "Rosa", "Verde"]
CAPACIDADES = ["16GB", "32GB", "64GB", "128GB", "256GB", "512GB", "1TB"]


@dataclass
class WebhookUpdate:
    """Dataclass simples para fazer wrap em um tipo customizado de update."""

    user_id: int
    payload: str


class CustomContext(CallbackContext[ExtBot, dict, dict, dict]):
    """Classe CallbackContext customizada que faz `user_data` disponível para updates do tipo `WebhookUpdate`."""

    @classmethod
    def from_update(
        cls,
        update: object,
        application: "Application",
    ) -> "CustomContext":
        if isinstance(update, WebhookUpdate):
            return cls(application=application, user_id=update.user_id)
        return super().from_update(update, application)


def restringir_acesso(func):
    """Restringir acesso aos comandos do bot apenas a usuários em determinado grupo."""

    async def wrapper(
        update: Update, context: CustomContext, *args, **kwargs
    ):
        user_id = update.effective_user.id

        # Tenta pegar o `ChatMember` do usuário no grupo
        try:
            membro = await context.bot.get_chat_member(
                chat_id=GRUPO_ID, user_id=user_id
            )
        except TelegramError:
            pass
        else:
            # Checa status do usuário no grupo
            if membro.status in [
                ChatMember.ADMINISTRATOR,
                ChatMember.MEMBER,
                ChatMember.OWNER,
                ChatMember.RESTRICTED,
            ]:
                return await func(update, context, *args, **kwargs)

        # Se usuário no grupo não foi encontrado (nunca esteve lá ou saiu)
        await update.message.reply_text(
            "Desculpe, você não tem permissão para usar este bot."
        )

    return wrapper


@restringir_acesso
async def start(update: Update, context: CustomContext) -> None:
    """Envia a mensagem com instruções quando o comando /start é enviado pelo usuário."""
    await update.message.reply_text(
        "Use o comando /gerar para iniciar a geração do link do carrinho."
    )


@restringir_acesso
async def escolha_modelo(update: Update, context: CustomContext) -> int:
    """Inicia o `ConversationHandler` e solicita ao usuário escolher um modelo."""
    # Filtra os modelos que possuem estoque para apresentá-los ao usuário
    context.user_data["modelos_opcoes"] = await filtrar_modelos()

    # Caso não sejam retornados modelos, informa ao usuário e termina o `ConversationHandler`
    if not context.user_data["modelos_opcoes"]:
        await update.message.reply_text("Ocorreu um erro ao gerar a lista de modelos.")
        return ConversationHandler.END

    keyboard = [
        [InlineKeyboardButton(modelo, callback_data=modelo)]
        for modelo in context.user_data["modelos_opcoes"].keys()
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("Escolha o modelo:", reply_markup=reply_markup)

    return MODELO


async def escolha_cor(update: Update, context: CustomContext) -> int:
    """Salva o modelo escolhido e solicita ao usuário escolher uma cor para o modelo."""
    query = update.callback_query
    await query.answer()

    context.user_data["modelo"] = query.data

    keyboard = [
        [InlineKeyboardButton(cor, callback_data=cor)]
        for cor in sorted(
            context.user_data["modelos_opcoes"][context.user_data["modelo"]]
        )
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text("Escolha a cor:", reply_markup=reply_markup)

    return COR


async def escolha_imei(update: Update, context: CustomContext) -> int:
    """Salva a cor escolhida e solicita ao usuário informar o IMEI do dispositivo a ser utilizado na Troca Smart."""
    query = update.callback_query
    await query.answer()

    context.user_data["cor"] = query.data

    message = await query.edit_message_text(
        "Informe o IMEI do dispositivo a ser utilizado na Troca Smart."
    )

    # Salva o id da mensagem do bot para ser excluída depois
    context.user_data["bot_message_id"] = message.message_id

    return IMEI


async def escolha_capacidade(update: Update, context: CustomContext) -> int:
    """Salva o IMEI informado e solicita ao usuário escolher a capacidade do dispositivo a ser utilizado na Troca Smart."""
    context.user_data["imei"] = update.message.text.replace(" ", "")
    # Salva o id da mensagem do usuário para ser excluída depois
    context.user_data["user_message_id"] = update.message.message_id

    dispositivo_imei = await checar_imei(context.user_data["imei"])

    # Caso IMEI não é válido, informa ao usuário e solicita um novo IMEI
    while not dispositivo_imei:
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=context.user_data["bot_message_id"],
            text=f"IMEI {context.user_data['imei']} é inválido.\nInforme o IMEI do dispositivo a ser utilizado na Troca Smart.",
        )
        await context.bot.delete_message(
            chat_id=update.effective_chat.id,
            message_id=context.user_data["user_message_id"],
        )

        return IMEI

    # Caso IMEI é válido, salva a marca e o modelo do dispositivo correspondente
    context.user_data["imei_marca"] = dispositivo_imei["marca"]
    context.user_data["imei_modelo"] = dispositivo_imei["modelo"]

    keyboard = [
        [
            InlineKeyboardButton(capacidade, callback_data=capacidade)
            for capacidade in sorted(
                dispositivo_imei["capacidades_opcoes"],
                key=lambda x: CAPACIDADES.index(x),
            )
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Escolha a capacidade do dispositivo a ser utilizado na Troca Smart:",
        reply_markup=reply_markup,
    )

    return CAPACIDADE


async def envia_link(update: Update, context: CustomContext) -> int:
    """Gera e envia ao usuário o link para o carrinho com o modelo e o desconto da Troca Smart."""
    query = update.callback_query
    await query.answer()

    # Pega url do modelo na loja com o dicionário `MODELOS`
    url = MODELOS[context.user_data["modelo"]]
    cor = context.user_data["cor"]

    imei = context.user_data["imei"]
    imei_marca = context.user_data["imei_marca"]
    imei_modelo = context.user_data["imei_modelo"]
    imei_capacidade = query.data

    # Deleta as outras mensagens e gera o link
    await context.bot.delete_message(
        chat_id=update.effective_chat.id, message_id=query.message.message_id
    )

    link = await gerar_link(url, cor, imei_marca, imei_modelo, imei_capacidade, imei)

    await context.bot.delete_message(
        update.effective_chat.id, context.user_data["bot_message_id"]
    )
    await context.bot.delete_message(
        update.effective_chat.id, context.user_data["user_message_id"]
    )

    # Envia o link do carrinho para o usuário, ou o erro caso ocorra
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=link["erro"] if "erro" in link else f"Link gerado: {link['link']}",
    )

    # Termina o `ConversationHandler`
    return ConversationHandler.END


async def webhook_update(update: WebhookUpdate, context: CustomContext) -> None:
    """Lida com updates customizados."""
    chat_member = await context.bot.get_chat_member(
        chat_id=update.user_id, user_id=update.user_id
    )
    payloads = context.user_data.setdefault("payloads", [])
    payloads.append(update.payload)
    combined_payloads = "</code>\n• <code>".join(payloads)
    text = (
        f"O usuário {chat_member.user.mention_html()} enviou um novo payload. "
        f"Até agora o usuário enviou os seguintes payloads: \n\n• <code>{combined_payloads}</code>"
    )
    await context.bot.send_message(
        chat_id=ADMIN_CHAT_ID, text=text, parse_mode=ParseMode.HTML
    )


async def main() -> None:
    """Começa o bot. Cria a aplicação do bot e uma aplicação web para lidar com os requests."""
    context_types = ContextTypes(context=CustomContext)

    # Cria a `application` e passa o `TOKEN` do bot
    # `Updater` é None porque o webhook customizado que irá lidar com os updates
    application = (
        Application.builder()
        .token(TOKEN)
        .updater(None)
        .context_types(context_types)
        .build()
    )

    # Setup do `ConversationHandler` com as etapas (`states`)
    # Cada handler é associado a uma interação do usuário em resposta às solicitações do bot
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("gerar", escolha_modelo)],
        states={
            MODELO: [
                CallbackQueryHandler(escolha_cor, pattern="^" + escape(modelo) + "$")
                for modelo in MODELOS.keys()
            ],
            COR: [
                CallbackQueryHandler(escolha_imei, pattern="^" + cor + "$")
                for cor in CORES
            ],
            IMEI: [MessageHandler(filters.TEXT & ~filters.COMMAND, escolha_capacidade)],
            CAPACIDADE: [
                CallbackQueryHandler(envia_link, pattern="^" + capacidade + "$")
                for capacidade in CAPACIDADES
            ],
        },
        fallbacks=[CommandHandler("gerar", escolha_modelo)],
    )

    # Responda ao comando start
    application.add_handler(CommandHandler("start", start))

    # Adicionar `ConversationHandler` a `application` que vai ser utilizada para lidar com updates
    application.add_handler(conv_handler)

    application.add_handler(TypeHandler(type=WebhookUpdate, callback=webhook_update))

    # Passar as configurações do webhook para o Telegram
    await application.bot.set_webhook(
        url=f"{URL}/telegram", allowed_updates=Update.ALL_TYPES
    )

    # Configurar webserver
    flask_app = Flask(__name__)

    @flask_app.post("/telegram")  # type: ignore[misc]
    async def telegram() -> Response:
        """Lidar com updates vindos do Telegram colocando-os na `update_queue`."""
        await application.update_queue.put(
            Update.de_json(data=request.json, bot=application.bot)
        )
        return Response(status=HTTPStatus.OK)

    @flask_app.route("/submitpayload", methods=["GET", "POST"])  # type: ignore[misc]
    async def custom_updates() -> Response:
        """
        Lidar com updates do webhook também colocando-os na `update_queue`, se os parâmetros
        requeridos foram passados corretamente.
        """
        try:
            user_id = int(request.args["user_id"])
            payload = request.args["payload"]
        except KeyError:
            abort(
                HTTPStatus.BAD_REQUEST,
                "Por favor passe ambos `user_id` e `payload` como parâmetros.",
            )
        except ValueError:
            abort(HTTPStatus.BAD_REQUEST, "`user_id` deve ser uma string!")

        await application.update_queue.put(
            WebhookUpdate(user_id=user_id, payload=payload)
        )
        return Response(status=HTTPStatus.OK)

    @flask_app.get("/healthcheck")  # type: ignore[misc]
    async def health() -> Response:
        """Para o endpoint health, responder apenas com uma mensagem de texto simples."""
        response = make_response("O bot ainda está funcionando bem :)", HTTPStatus.OK)
        response.mimetype = "text/plain"
        return response

    webserver = uvicorn.Server(
        config=uvicorn.Config(
            app=WsgiToAsgi(flask_app),
            port=PORT,
            use_colors=False,
            host="0.0.0.0",
        )
    )

    # Executar a application e o webserver juntos
    async with application:
        await application.start()
        await webserver.serve()
        await application.stop()


if __name__ == "__main__":
    asyncio.run(main())
