import logging

import os
import time
import requests
import http
import telegram


from dotenv import load_dotenv
from exceptions import APIerror, ResponseError
load_dotenv()
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    filename='py_log.log')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
MESSAGE = 'Изменился статус проверки работы '
RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
API_ERROR = 'API сервиса ЯП недоступен: {error}. Статус код:{response},'
'параметры броска: {HEADERS}, {ENDPOINT}'
KEYERROR = 'Отсутствует ключ `homework_name` в ответе API'
VALUEERROR = 'В ответе API недопустимый статус работы{homework}'


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверка наличия токенов."""
    for token in TELEGRAM_TOKEN, PRACTICUM_TOKEN, TELEGRAM_CHAT_ID:
        if token is None:
            logging.critical("Отсутсвует обязательное переменное окружение")
            raise KeyError(f'Отсутсвует токен:{token}')


def send_message(bot, message):
    """Отправка сообщения в Телеграм."""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message
        )
        logging.debug(f"'{message}' - сообщение было отправлено пользователю ")
    except telegram.error.TelegramError as error:
        logging.exception(
            error, f'{message} - это сообщение не дошло до пользователя')


def get_api_answer(timestamp):
    """Получение данных с API YP."""
    payload = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
    except requests.RequestException as error:
        raise APIerror(API_ERROR.format(error=error, HEADERS=HEADERS,
                                        ENDPOINT=ENDPOINT,
                                        response=response.status_code))
    if response.status_code != http.HTTPStatus.OK:
        raise APIerror(
            f'Статус запроса отличный от 200.'
            f'Статус код:{response.status_code},'
            f'параметры броска: {ENDPOINT}, {HEADERS}')
    return response.json()


def check_response(response):
    """Проверяем данные в response."""
    if response['current_date'] is None:
        raise ResponseError(
            'В ответе от сервера отсутсвует поле: current_date')
    if not isinstance(response, dict):
        raise TypeError(
            'Запрос получил неожиданный тип данных:', type(response))
    if 'homeworks' not in response.keys():
        raise KeyError(KEYERROR)
    if not isinstance(response['homeworks'], list):
        raise TypeError(
            'API запрос ожидает списка,'
            f'а получает:{type(response["homeworks"])}')


def parse_status(homework):
    """извлекает из информации статус о домашней работе."""
    if 'homework_name' not in homework:
        raise KeyError('Отсутствует ключ `homework_name` в ответе API')
    homework_name = homework['homework_name']
    if 'status' not in homework:
        raise KeyError('Отсутствует ключ status в ответе API')
    if homework['status'] not in HOMEWORK_VERDICTS:
        raise ValueError(VALUEERROR.format(homework=homework['status']))

    return (f'{MESSAGE}"{homework_name}"\n'
            f'{HOMEWORK_VERDICTS[homework["status"]]}')


def main():
    """Основная логика работы бота."""
    if check_tokens() is None:
        print()

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = 0

    while True:
        response = get_api_answer(timestamp)

        if check_response(response):
            if len(response['homeworks']) != 0:
                raise ValueError('Возвращается пустой запрос')
        try:
            message = parse_status(response['homeworks'][0])
            send_message(bot, message)
            time.sleep(RETRY_PERIOD)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
