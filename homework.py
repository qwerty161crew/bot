import logging
import os
import sys
import time
import http

import requests
import telegram
from dotenv import load_dotenv

from exceptions import ResponseError

load_dotenv()
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600

ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

MESSAGE = 'Изменился статус проверки работы'
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
PARSE_STATUS = 'Изменился статус проверки работы "{homework_name}"\n{verdicts}'
TOKEN_ERROR = 'Отсутствуют одна или несколько переменных окружения'
HOMEWOR_TYPE_ERROR = ('API запрос ожидает списка,'
                      'а получает: {response}')
KEY_ERROR_HOMEWORK_NAME = ('Отсутствует ключ `homework_name` в ответе API.'
                           'Функция - parse_status')
RESPONSE_ERROR = ('Произошла ошибка при запросе к ЯП,'
                  'были переданы неожиданные данные для сервиса.'
                  'Response вернул {response}')
RESPONSE_ERROR_TOKEN = ('Токен не прошел аунтификацию.'
                        'Учетные данные не были предоставлены')
LOGGIN_ERROR = ('Сбой в работе программы: {error}. Параметры броска:'
                '{response}, {timestamp}')


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверка наличия токенов."""
    not_found_token_names = []
    if TELEGRAM_TOKEN is None:
        not_found_token_names.append('TELEGRAM_TOKEN')
    if TELEGRAM_CHAT_ID is None:
        not_found_token_names.append('TELEGRAM_CHAT_ID')
    if PRACTICUM_TOKEN is None:
        not_found_token_names.append('PRACTICUM_TOKEN')
    if len(not_found_token_names) > 0:
        logging.critical(
            f'LOGGIN_CRITICAL_MESSAGE\n'
            f'Отсутсвуют токены: {not_found_token_names!r}'
        )
        return False
    return True


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
    if "UnknowError" in response.json():
        raise ResponseError(
            RESPONSE_ERROR.format(response=response['code']))
    if "Not_authenticated" in response.json():
        raise ResponseError(RESPONSE_ERROR_TOKEN)
    if response.status_code == http.HTTPStatus.OK:
        return response.json()
    raise ConnectionError(API_ERROR_MESSAGE.format(
        response=response.status_code, headers=HEADERS, endpoint=ENDPOINT,
        params=payload))


def check_response(response):
    """Проверяем данные в response."""
    if not isinstance(response, dict):
        raise TypeError(TYPE_ERROR.format(response=type(response)))
    if 'homeworks' not in response.keys():
        raise KeyError(KEY_ERROR)
    if not isinstance(response['homeworks'], list):
        raise TypeError(HOMEWOR_TYPE_ERROR.format(
            response=type(response)))


def parse_status(homework):
    """извлекает из информации статус о домашней работе."""
    print(type(homework))
    if 'homework_name' not in homework:
        raise KeyError(KEY_ERROR_HOMEWORK_NAME)
    homework_name = homework['homework_name']
    if 'status' not in homework:
        raise KeyError(KEY_STATUS)
    if homework['status'] not in HOMEWORK_VERDICTS:
        raise ValueError(VALUE_ERROR.format(status=homework['status']))
    verdict = HOMEWORK_VERDICTS[homework["status"]]
    return (PARSE_STATUS.format(
        homework_name=homework_name,
        verdicts=verdict)
    )


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        sys.exit('Some tokens are invalid, stop the program.')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = 0
    response = get_api_answer(timestamp)
    try:
        while True:
            if check_response(response):
                raise ValueError('Возвращается пустой запрос')
            timestamp = response.get('current_date')
            try:
                message = parse_status(response['homeworks'][0])
                send_message(bot, message)

            except Exception as error:
                send_message(bot, MESSAGE_ERROR.format(error=error))
                logging.critical(LOGGIN_ERROR.format(
                    error=error, response=response,
                    timestamp=timestamp))
            time.sleep(RETRY_PERIOD)
    except ResponseError as error:
        raise (f'Данные из запроса не прошли проверку. Ошибка: {error}')


if __name__ == '__main__':
    main()
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO,
        filename=__file__ + '.log',
        handlers=['fileHandler', 'consoleHandler'])
