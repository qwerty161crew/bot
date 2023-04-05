import logging

import os
import time
import requests


from telegram import Bot


from dotenv import load_dotenv
from exceptions import TokenError, ResponseError, HomeworkIsNone, MessageError
load_dotenv()
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 1
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверка наличия токенов."""
    if TELEGRAM_TOKEN is None:
        raise TokenError('Отсутсвует токен телеграм API')
    if PRACTICUM_TOKEN is None:
        raise TokenError('Отсутсвует токен API Practicum')
    if TELEGRAM_CHAT_ID is None:
        raise TokenError('Отсутсвует id чата')


def send_message(bot, message):
    """Отправка сообщения в Телеграм."""
    bot(
        text=message
    )
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.DEBUG)
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.ERROR)


def get_api_answer(timestamp):
    """Получение данных с API YP."""
    payload = {'from_date': timestamp}
    response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
    try:
        if response.status_code == 200:
            return response.json()
    except requests.RequestException as error:
        print(error)
        return


def check_response(response):
    """Проверяем данные в response."""
    if response.get('homeworks') is None:
        raise ResponseError('В ответе от сервера отсутсвует поле: homeworks')
    if response.get('current_date') is None:
        raise ResponseError(
            'В ответе от сервера отсутсвует поле: current_date')
    if type(response) != dict and type(response['homeworks']) != list:
        raise TypeError('Запрос получил неожиданный тип данных')


def parse_status(homework):
    """Анализируем статус если изменился."""
    if homework is None and homework['homework_name'] is None:
        raise HomeworkIsNone('Статус домашней работы пуcт')
    return HOMEWORK_VERDICTS[homework['status']], homework['homework_name']


def main():
    """Основная логика работы бота."""
    try:
        check_tokens()
    except TokenError as exc:
        print(exc)
        return

    timestamp = int(time.time())
    response = get_api_answer(timestamp)
    try:
        check_response(response)
    except ResponseError as exc:
        print(exc)
        return

    for homework in response['homeworks']:
        message = parse_status(homework)

    bot_tg = Bot(token=TELEGRAM_TOKEN)
    bot = bot_tg.send_message(chat_id=TELEGRAM_CHAT_ID)

    while True:
        try:
            send_message(bot, message)
            # time.sleep(RETRY_PERIOD)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'


if __name__ == '__main__':
    main()
