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
    level=logging.INFO,
    filename='py_log.log')
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
    try:
        if TELEGRAM_TOKEN is None:
            raise TokenError('Отсутсвует токен телеграм API')
        if PRACTICUM_TOKEN is None:
            raise TokenError('Отсутсвует токен API Practicum')
        if TELEGRAM_CHAT_ID is None:
            raise TokenError('Отсутсвует id чата')
    except TokenError as error:
        logging.critical("Отсутсвует обязательное переменное окружение", error)


def send_message(bot, message):
    """Отправка сообщения в Телеграм."""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message
        )
        logging.debug("Сообщение было отправлено")
    except MessageError as error:
        logging.error("Критическая ошибка:", error)


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
    if response['current_date'] is None:
        raise ResponseError(
            'В ответе от сервера отсутсвует поле: current_date')
    if not isinstance(response, dict):
        raise TypeError('Запрос получил неожиданный тип данных')
    if 'homeworks' not in response.keys():
        raise KeyError('Поле "homeworks" пустое')
    if not isinstance(response['homeworks'], list):
        raise TypeError('API запрос ожидает списка')
    if 'homeworks' not in response.keys():
        raise KeyError('homeworks is not list')


def parse_status(homework):
    """Анализируем статус если изменился."""
    if homework is None:
        raise KeyError('Статус домашней работы пуcт')
    if 'homework_name' not in homework:
        raise KeyError('Отсутствует ключ homework_name в ответе API')
    if homework['status'] not in HOMEWORK_VERDICTS:
        raise TypeError('Такого статуса нету')
    try:
        if isinstance(HOMEWORK_VERDICTS[homework['status']], str) and isinstance(homework['homework_name'], str):
            return f'Изменился статус проверки работы "{homework["homework_name"]}" {HOMEWORK_VERDICTS[homework["status"]]}'
    except TypeError:
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

    while True:
        try:
            message = parse_status(response['homeworks'])
            bot = Bot(token=TELEGRAM_TOKEN)
            send_message(bot, message)
            time.sleep(5)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)


if __name__ == '__main__':
    main()
