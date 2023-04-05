import logging

import os
import time
import requests
import http

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

RETRY_PERIOD = 600
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
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message
        )
        logging.basicConfig(
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            level=logging.DEBUG)
    except MessageError as error:
        raise ('Сообщение не отправлено', error)
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.ERROR)


def get_api_answer(timestamp):
    """Получение данных с API YP."""
    payload = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
        if response.status_code != http.HTTPStatus.OK:
            raise OSError('Статус запроса отличный от 200')
        return response.json()
    except requests.RequestException as error:
        print(error)


def check_response(response):
    """Проверяем данные в response."""
        # if response.get('homeworks') is None:
        #     raise ResponseError('В ответе от сервера отсутсвует поле: homeworks')
    if response['current_date'] is None:
        raise ResponseError(
            'В ответе от сервера отсутсвует поле: current_date')
    # if type(response) != dict:
    #     raise TypeError('Запрос получил неожиданный тип данных')
    if type(response) != list:
        raise TypeError('API запрос передал неожиданный формат данных')


def parse_status(homework):
    """Анализируем статус если изменился."""
    if homework is None and homework['homework_name'] is None:
        raise HomeworkIsNone('Статус домашней работы пуcт')
    # if HOMEWORK_VERDICTS[homework['status']] is not str:
    #     raise TypeError('Функция не возвращает строку а что-то')
    # if homework['homework_name'] is not str:
    #     raise TypeError('Функция не возвращает строку')
    if homework['homework'] not in HOMEWORK_VERDICTS[homework['status']]:
        raise HomeworkIsNone('Такого статуса нету')
    return str(HOMEWORK_VERDICTS[homework['status']]), str(homework['homework_name'])


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
        message = parse_status(str(homework))

    bot_tg = Bot(token=TELEGRAM_TOKEN)

    while True:
        try:
            send_message(bot_tg, message)
            time.sleep(20)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot_tg, message)


if __name__ == '__main__':
    main()
