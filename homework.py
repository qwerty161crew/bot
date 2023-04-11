import logging
import os
import time
import http

import requests
import telegram
from dotenv import load_dotenv

from exceptions import ResponseError, StatusCodeError

load_dotenv()
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600

ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

MESSAGE = 'Изменился статус проверки работы '
API_ERROR = ('API сервиса ЯП недоступен: {error}.'
             'Параметры броска: {headers}, {params}, {endpoint}')
KEY_ERROR = 'Отсутствует ключ `homework_name` в ответе API'
VALUE_ERROR = 'В ответе API недопустимый статус работы: {status}'
MESSAGE_ERROR = 'Сбой в работе программы: {error}'
DEBAG_MESSAGE = "'{message}' - сообщение было отправлено пользователю"
ERROR_MESSAGE = '{error}. {message} - Сообщение было отправлено пользователю'
API_ERROR_MESSAGE = ('Статус запроса отличный от 200.'
                     'Статус код:{response}, параметры броска: {endpoint},'
                     '{headers}, {params}')
TYPE_ERROR = 'Запрос получил неожиданный тип данных: {response}'
LOGGIN_CRITICAL_MESSAGE = "Отсутсвует обязательная переменная окружения"
KEY_STATUS = 'Отсутствует ключ status в ответе API'
PARSE_STATUS = '{message}"{homework_name}"\n{verdicts}'
TOKEN_ERROR = 'Отсутствуют одна или несколько переменных окружения'
HOMEWOR_TYPE_ERROR = ('API запрос ожидает списка,'
                      'а получает: {response}')
KEY_ERROR_PARSE_STATUS = ('Отсутствует ключ `homework_name` в ответе API.'
                          'Функция - parse_status')
RESPONSE_ERROR = ('Произошла ошибка при запросе к ЯП,'
                  'были переданы неожиданные данные для сервиса.'
                  'Response вернул {response}')
RESPONSE_ERROR_TOKEN = ('Токен не прошел аунтификацию.'
                        'Учетные данные не были предоставлены')

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверка наличия токенов."""
    TOKENS = [[TELEGRAM_TOKEN, 'TELEGRAM_TOKEN'],
              [TELEGRAM_CHAT_ID, 'TELEGRAM_CHAT_ID'],
              [PRACTICUM_TOKEN, 'PRACTICUM_TOKEN']]
    for token, name in TOKENS:
        if token is None:
            logging.critical(
                f'Отсутсвует токен: {name}', LOGGIN_CRITICAL_MESSAGE)
            raise ValueError(LOGGIN_CRITICAL_MESSAGE)


def send_message(bot, message):
    """Отправка сообщения в Телеграм."""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message
        )
        logging.debug(DEBAG_MESSAGE.format(message=message))
    except telegram.error.TelegramError as error:
        logging.exception(ERROR_MESSAGE.format(error=error, message=message))


def get_api_answer(timestamp):
    """Получение данных с API YP."""
    payload = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
    except requests.RequestException as error:
        raise ConnectionError(API_ERROR.format(error=error,
                                               headers=HEADERS,
                                               params=payload,
                                               endpoint=ENDPOINT))
    if response.status_code != http.HTTPStatus.OK:
        raise StatusCodeError(API_ERROR_MESSAGE.format(
            response=response.status_code, headers=HEADERS, endpoint=ENDPOINT,
            params=payload))
    if response['code'] in "UnknowError":
        raise ResponseError(
            RESPONSE_ERROR.format(response=response['code']))
    if response['code'] in "Not_authenticated":
        raise ResponseError(RESPONSE_ERROR_TOKEN)
    return response.json()


def check_response(response):
    """Проверяем данные в response."""
    if not isinstance(response, dict):
        raise TypeError(TYPE_ERROR.format(response=type(response)))
    if 'homeworks' not in response.keys():
        raise KeyError(KEY_ERROR)
    if not isinstance(response['homeworks'], list):
        raise TypeError(HOMEWOR_TYPE_ERROR.format(
            response=type(response['homeworks'])))


def parse_status(homework):
    """извлекает из информации статус о домашней работе."""
    verdicts = HOMEWORK_VERDICTS[homework["status"]]
    if 'homework_name' not in homework:
        raise KeyError(KEY_ERROR_PARSE_STATUS)
    homework_name = homework['homework_name']
    if 'status' not in homework:
        raise KeyError(KEY_STATUS)
    if homework['status'] not in HOMEWORK_VERDICTS:
        raise ValueError(VALUE_ERROR.format(status=homework['status']))

    return PARSE_STATUS.format(message=MESSAGE,
                               homework_name=homework_name,
                               verdicts=verdicts)


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    while True:
        response = get_api_answer(timestamp)
        try:
            if check_response(response):
                raise ValueError('Возвращается пустой запрос')
        except ResponseError as error:
            raise (f'Данные из запроса не прошли проверку. Ошибка: {error}')
        timestamp = response.get('current_date')
        try:
            message = parse_status(response['homeworks'])
            send_message(bot, message)

        except Exception as error:
            send_message(bot, MESSAGE_ERROR.format(error=error))
            logging.error(ERROR_MESSAGE.format(error=error, message=message))
        time.sleep(RETRY_PERIOD)
        logging.basicConfig(
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            level=logging.INFO,
            filename=__file__ + '.log',
            handlers=['fileHandler', 'consoleHandler'])


if __name__ == '__main__':
    main()
