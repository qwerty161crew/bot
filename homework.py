import logging
import os
import time
import http

import requests
import telegram
from dotenv import load_dotenv

from exceptions import TokenError, ResponseError

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
MESSAGE_ERROR = ('Сбой в работе программы: {error}. Параметры броска:'
                 ' {timestamp}')
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
HOMEWORK_TYPE_ERROR = ('API запрос ожидает списка,'
                       'а получает: {response}')
KEY_ERROR_HOMEWORK_NAME = ('Отсутствует ключ `homework_name` в ответе API.'
                           'Функция - parse_status')
RESPONSE_ERROR = ('Произошла ошибка при запросе к ЯП,'
                  'были переданы неожиданные данные для сервиса.'
                  'Response вернул {response}')
RESPONSE_ERROR_TOKEN = ('Токен не прошел аунтификацию.'
                        'Учетные данные не были предоставлены')
RESPONSE_KEY_ERROR = ('Запрос на сайт на сайт вернул ошибку: {key}.'
                      'Параметры запроса: {headers}, {payload}, {endpoint},'
                      '{response}')
LOGGING_CRITICAL = ('LOGGIN_CRITICAL_MESSAGE\n'
                    'Отсутсвуют токены: {not_found_token_names}')


TOKEN_NAMES_GET_VALUES = (
    ('TELEGRAM_TOKEN', lambda: TELEGRAM_TOKEN),
    ('TELEGRAM_CHAT_ID', lambda: TELEGRAM_CHAT_ID),
    ('PRACTICUM_TOKEN', lambda: PRACTICUM_TOKEN),
)

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверка наличия токенов."""
    not_found_token_names = [token_name for token_name, get_token_function
                             in TOKEN_NAMES_GET_VALUES
                             if get_token_function() is None]
    if not_found_token_names:
        logging.critical(LOGGING_CRITICAL.format(
            not_found_token_names=not_found_token_names
        )
        )
        raise TokenError('Отсутсвует обязательная переменная окружения')


def send_message(bot, message):
    """Отправка сообщения в Телеграм."""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message
        )
        logging.debug(DEBAG_MESSAGE.format(message=message))
        return True
    except telegram.error.TelegramError as error:
        logging.exception(ERROR_MESSAGE.format(error=error, message=message))
        return False


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
    json_answer = response.json()
    invalid_keys = ['error', 'code']
    for key in invalid_keys:
        if json_answer in invalid_keys:
            raise ValueError(RESPONSE_KEY_ERROR.format(
                key=key, headers=HEADERS, params=payload,
                endpoint=ENDPOINT, response=response[key]))
    if response.status_code == http.HTTPStatus.OK:
        return json_answer
    raise ResponseError(API_ERROR_MESSAGE.format(response=response.status_code,
                                                 headers=HEADERS,
                                                 params=payload,
                                                 endpoint=ENDPOINT))


def check_response(response):
    """Проверяем данные в response."""
    if not isinstance(response, dict):
        raise TypeError(TYPE_ERROR.format(response=type(response)))
    if 'homeworks' not in response.keys():
        raise KeyError(KEY_ERROR)
    if not isinstance(response['homeworks'], list):
        raise TypeError(HOMEWORK_TYPE_ERROR.format(
            response=type(response['homeworks'])))


def parse_status(homework):
    """извлекает из информации статус о домашней работе."""
    if 'homework_name' not in homework:
        raise KeyError(KEY_ERROR_HOMEWORK_NAME)
    homework_name = homework['homework_name']
    status = homework.get('status')
    if status is None:
        raise KeyError(KEY_STATUS)
    if status not in HOMEWORK_VERDICTS:
        raise ValueError(VALUE_ERROR.format(status=status))
    verdict = HOMEWORK_VERDICTS[status]
    return (PARSE_STATUS.format(
        homework_name=homework_name,
        verdicts=verdict)
    )


def main():
    """Основная логика работы бота."""
    last_error = None
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = 0
    while True:
        try:
            response = get_api_answer(timestamp)
            print(response)
            check_response(response)
            message = parse_status(response['homeworks'][0])
            if send_message(bot, message):
                timestamp = response.get('current_date', timestamp)
        except Exception as error:
            debug_message = logging.debug(MESSAGE_ERROR.format(
                error=error,
                timestamp=timestamp))
            if debug_message != last_error:
                if not send_message(bot, debug_message):
                    last_error = debug_message
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO,
        handlers=[logging.StreamHandler(),
                  logging.FileHandler(filename=__file__ + '.log',)])
    main()
