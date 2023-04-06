import logging

import os
import time
import requests
import http
import telegram

from telegram import Bot


from dotenv import load_dotenv
from exceptions import TokenError, ResponseError
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
    except telegram.error.TelegramError as error:
        logging.error(error)
        telegram.error.TelegramError(f'Ошибка при отправку сообщения: {error}')


def get_api_answer(timestamp):
    """Получение данных с API YP."""
    payload = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
        if response.status_code != http.HTTPStatus.OK:
            raise OSError('Статус запроса отличный от 200')
        return response.json()
    except requests.RequestException as error:
        raise RuntimeError(f'API сервиса ЯП недоступен: {error}')


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
    """извлекает из информации статус о домашней работе."""
    if 'homework_name' not in homework:
        raise KeyError('Отсутствует ключ `homework_name` в ответе API')
    homework_name = homework['homework_name']
    if 'status' not in homework:
        raise KeyError('Отсутствует ключ status в ответе API')
    if homework['status'] not in HOMEWORK_VERDICTS:
        raise ValueError('В ответе API недокументированный статус работы')
    verdict = HOMEWORK_VERDICTS[homework['status']]
    return f'Изменился статус проверки работы "{homework_name}"\n{verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        return
    timestamp = int(time.time())
    response = get_api_answer(timestamp)
    if check_response(response):
        if len(response['homeworks']) != 0:
            message = parse_status(response['homeworks'][0])

    bot = Bot(token=TELEGRAM_TOKEN)
    while True:
        try:
            send_message(bot, message)
            time.sleep(5)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)


if __name__ == '__main__':
    main()
