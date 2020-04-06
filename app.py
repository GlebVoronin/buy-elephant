from flask import Flask, request
import logging
import os
import json
import random

app = Flask(__name__)
country_or_city = False
logging.basicConfig(level=logging.INFO)
countries = {'москва': 'Россия', 'нью-йорк': 'США', 'париж': 'Франция'}
cities = {
    'москва': ['1652229/9dc0232e6bf55a09e3f5',
               '213044/61e11c2579a4b2ca1369'],
    'нью-йорк': ['1652229/a692038f7149927b9658',
                 '1652229/9bc4be62e575d010c84e'],
    'париж': ["1521359/24f5da3c735907bca6ce",
              '937455/3c24bf2e83fe720bef54']
}
sessionStorage = {}


@app.route('/post', methods=['POST'])
def main():
    logging.info('Request: %r', request.json)
    response = {
        'session': request.json['session'],
        'version': request.json['version'],
        'response': {
            'end_session': False
        }
    }
    handle_dialog(response, request.json)
    logging.info('Response: %r', response)
    return json.dumps(response)


def handle_dialog(res, req):
    user_id = req['session']['user_id']
    res['response']['buttons'] = [{'title': 'Помощь', 'hide': True}]
    if 'помощь' in req['request']['original_utterance'].lower():
        res['response']['text'] = 'Справка: вы можете назвать своё имя и' + \
                                  ' попытаться угадать названия 3 городов по фото'
        return
    if req['session']['new']:
        res['response']['text'] = 'Привет! Назови своё имя!'
        sessionStorage[user_id] = {
            'first_name': None,
            'game_started': False
        }
        return
    if sessionStorage[user_id]['first_name'] is None:
        first_name = get_first_name(req)
        if first_name is None:
            res['response']['text'] = 'Не расслышала имя. Повтори, пожалуйста!'
        else:
            sessionStorage[user_id]['first_name'] = first_name
            sessionStorage[user_id]['guessed_cities'] = []
            res['response'][
                'text'] = f'Приятно познакомиться, {first_name.title()}. Я Алиса. Отгадаешь город по фото?'
            res['response']['buttons'].extend([
                {
                    'title': 'Да',
                    'hide': True
                },
                {
                    'title': 'Нет',
                    'hide': True
                }
            ])
    else:
        if not sessionStorage[user_id]['game_started']:
            if 'да' in req['request']['nlu']['tokens']:
                if len(sessionStorage[user_id]['guessed_cities']) == 3:
                    res['response']['text'] = 'Ты отгадал все города!'
                    res['end_session'] = True
                else:
                    sessionStorage[user_id]['game_started'] = True
                    sessionStorage[user_id]['attempt'] = 1
                    play_game(res, req)
            elif 'нет' in req['request']['nlu']['tokens']:
                res['response']['text'] = 'Ну и ладно!'
                res['end_session'] = True
            else:
                res['response']['text'] = 'Не поняла ответа! Так да или нет?'
                res['response']['buttons'].extend([
                    {
                        'title': 'Да',
                        'hide': True
                    },
                    {
                        'title': 'Нет',
                        'hide': True
                    }
                ])
        else:
            play_game(res, req)


def play_game(res, req):
    global country_or_city
    user_id = req['session']['user_id']
    attempt = sessionStorage[user_id]['attempt']
    if attempt == 1:
        city = random.choice(list(cities))
        while city in sessionStorage[user_id]['guessed_cities']:
            city = random.choice(list(cities))
        sessionStorage[user_id]['city'] = city
        res['response']['card'] = {}
        res['response']['card']['type'] = 'BigImage'
        res['response']['card']['title'] = 'Что это за город?'
        res['response']['card']['image_id'] = cities[city][attempt - 1]
        res['response']['text'] = 'Тогда сыграем!'
        sessionStorage[user_id]['attempt'] += 1
    else:
        if not country_or_city:
            city = sessionStorage[user_id]['city']
            if get_city(req) == city:
                country_or_city = True
                res['response']['text'] = 'Правильно! А в какой стране этот город?'
                sessionStorage[user_id]['guessed_cities'].append(city)
                return
            else:
                if attempt == 3:
                    res['response']['buttons'] = [{'hide': True, 'title': 'Да'},
                                                  {'hide': True, 'title': 'Нет'},
                                                  {'hide': True,
                                                   'title': 'Покажи город на карте',
                                                   'url': f'https://yandex.ru/maps/?mode=search&text={city}'}]
                    res['response']['text'] = f'Вы пытались. Это {city.title()}. Сыграем ещё?'
                    sessionStorage[user_id]['guessed_cities'].append(city)
                    return
                else:
                    res['response']['card'] = {}
                    res['response']['card']['type'] = 'BigImage'
                    res['response']['card']['title'] = 'Неправильно. Вот тебе дополнительное фото'
                    res['response']['card']['image_id'] = cities[city][attempt - 1]
                    res['response']['text'] = 'А вот и не угадал!'
            sessionStorage[user_id]['attempt'] += 1
        else:
            country_or_city = False
            city = sessionStorage[user_id]['city']
            country = countries.get(sessionStorage[user_id]['city'], -1)
            if country == -1:
                res['response']['text'] = 'Не расслышала имя. Повтори, пожалуйста!'
                return
            if get_country(req) and get_country(req) == country.lower():
                res['response']['text'] = 'Правильно! Сыграем ещё?'
                res['response']['buttons'] = [{'hide': True, 'title': 'Да'},
                                              {'hide': True, 'title': 'Нет'},
                                              {'hide': True,
                                               'title': 'Покажи город на карте',
                                               'url': f'https://yandex.ru/maps/?mode=search&text={city}'}]
                sessionStorage[user_id]['game_started'] = False
                return
            else:
                res['response']['buttons'] = [{'hide': True, 'title': 'Да'},
                                              {'hide': True, 'title': 'Нет'},
                                              {'hide': True,
                                               'title': 'Покажи город на карте',
                                               'url': f'https://yandex.ru/maps/?mode=search&text={city}'}]
                res['response']['text'] = f'Вы пытались. Это {country.title()}. Сыграем ещё?'
                sessionStorage[user_id]['game_started'] = False
                return


def get_country(req):
    for entity in req['request']['nlu']['entities']:
        if entity['type'] == 'YANDEX.GEO':
            return entity['value'].get('country', None)


def get_city(req):
    for entity in req['request']['nlu']['entities']:
        if entity['type'] == 'YANDEX.GEO':
            return entity['value'].get('city', None)


def get_first_name(req):
    for entity in req['request']['nlu']['entities']:
        if entity['type'] == 'YANDEX.FIO':
            return entity['value'].get('first_name', None)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.environ.get('PORT', 33507))
