#!/usr/bin/env python

""" Telegram bot que gera links para o carrinho da loja da Samsung com um produto escolhido e desconto da Troca Smart.

O bot funciona através do ConversationHandler, que define a ordem de algumas callback functions.
A ordem das funções, definida nas etapas (states), pede ao usuário escolher o modelo e a cor do produto escolhido,
o IMEI do dispositivo a ser utilizado na Troca Smart e sua capacidade de armazenamento.
Os modelos e suas cores são filtrados com web scraping com BeautifulSoup,
para serem apresentados nos botões para os usuários apenas se estão com estoque.
Os botões funcionam através de InlineKeyboard.
O link é gerado com automação de browser com Playwright, no Chromium.

Uso:
O bot solicita informações sobre um produto através de InlineKeyboard com múltiplos CallbackQueryHandlers 
organizados em um ConversationHandler, e também solicita informações do dispositivo da Troca Smart.
Com essas informações o bot gera o link do carrinho com o produto e o desconto.
Envie /start para informações de como utilizar.
Envie /gerar para iniciar o processo de geração do link.
Escolha um modelo, uma cor, informe o IMEI e escolha uma capacidade.
Pressione Ctrl-C na linha de comando para parar o bot.
"""

import logging
from modelos import MODELOS
from utils import (
    filtrar_modelos,
    checar_imei,
    gerar_link,
)
from re import escape
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

# Habilitar logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Leitura do token do bot, gerado pelo BotFather
with open("token.txt", "r") as file:
    TOKEN = file.read().strip()

# Definição das etapas do ConversationHandler
MODELO, COR, IMEI, CAPACIDADE = range(4)

# Todas as possibilidades de cores e de capacidades para as patterns nos CallbackQueryHandlers
CORES = ["Azul", "Azul Claro", "Azul Escuro", "Cinza", "Lavanda", "Rosa", "Verde"]
CAPACIDADES = ["16GB", "32GB", "64GB", "128GB", "256GB", "512GB", "1TB"]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Envia a mensagem quando o comando /start é enviado pelo usuário."""
    await update.message.reply_text(
        "Use o comando /gerar para iniciar a geração do link do carrinho."
    )


async def escolha_modelo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia o ConversationHandler e solicita ao usuário escolher um modelo."""
    # Filtra os modelos que possuem estoque para apresentá-los ao usuário
    context.user_data["modelos_opcoes"] = await filtrar_modelos()

    # Caso não sejam retornados modelos, informa ao usuário e termina o ConversationHandler
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


async def escolha_cor(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
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


async def escolha_imei(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
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


async def escolha_capacidade(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Salva o IMEI informado e solicita ao usuário escolher a capacidade do dispositivo a ser utilizado na Troca Smart."""
    context.user_data["imei"] = update.message.text.replace(" ", "")
    # Salva o id da mensagem do usuário para ser excluída depois
    context.user_data["user_message_id"] = update.message.message_id

    dispositivo_imei = await checar_imei(context.user_data["imei"])

    # Caso IMEI não é válido, informa ao usuário e termina o ConversationHandler
    if not dispositivo_imei:
        await context.bot.delete_message(
            chat_id=update.effective_chat.id,
            message_id=context.user_data["bot_message_id"],
        )
        await context.bot.delete_message(
            chat_id=update.effective_chat.id,
            message_id=context.user_data["user_message_id"],
        )
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"IMEI {context.user_data['imei']} é inválido.",
        )

        return ConversationHandler.END

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


async def envia_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Gera e envia ao usuário o link para o carrinho com o modelo e o desconto da Troca Smart."""
    query = update.callback_query
    await query.answer()

    # Pega url do modelo na loja com o dicionário MODELOS
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

    # Termina o ConversationHandler
    return ConversationHandler.END


def main() -> None:
    """Começa o bot."""
    # Cria a Application e passa o token do bot
    application = Application.builder().token(TOKEN).build()

    # Setup do ConversationHandler com as etapas (states)
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

    # Adicionar ConversationHandler a application que vai ser utilizada para lidar com updates
    application.add_handler(conv_handler)

    # Bot irá operar até usuário pressionar Ctrl + C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
