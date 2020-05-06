import requests
import json
from flask import Flask, jsonify, request, flash, render_template

front = Flask(__name__)
front.secret_key = "kjsadgjskagfkjasgf654654654asf"

@front.route('/')
def index():
    return render_template('index.html')

@front.route('/api/')
def api():
    return render_template('api.html')

# Вывод всех записей и их фильтрация по параметрам
@front.route('/cars/', methods=['GET'])
def cars():
    req = 'http://localhost:5000/api/allcars/'
    # Выводим все
    if len(request.args) == 0:
        cars = requests.get(req).json()
        flash('Все записи загружены', 'success')
        return render_template('cars.html', cars=cars)
    # Фильтруем
    else:
        # Собираем запрос из непустых параметров
        pars = dict(request.args)
        print(pars)
        req += '?'
        for par in pars:
            if pars[par] != '':
                req += par + '=' + pars[par] + '&'
        req = req[:len(req) - 1]
        cars = requests.get(req).json()
        if 'cars' in cars.keys():
            flash('Подходящие записи загружены', 'success')
        else:
            flash('Записей не найдено', 'error')
        return render_template('cars.html', cars=cars)

# Добавление и удаление авто
@front.route('/cars/', methods=['POST'])
def add_car():
    req = 'http://localhost:5000/api/allcars/'
    data = dict(request.form)
    if len(data) == 4:
        # Добавление авто
        resp = requests.post(req, json=data)
        if resp.status_code == 400:
            flash(resp.json()['error'], 'error')
        elif resp.status_code == 201:
            flash(resp.json()['success'], 'success')
        cars = requests.get(req).json()
        return render_template('cars.html', cars=cars, resp=resp)
    # Удаление авто
    add = data['id'] + '/'
    resp = requests.delete(req + add)
    if resp.status_code == 400:
        flash(resp.json()['error'], 'error')
    elif resp.status_code == 200:
        flash(resp.json()['success'], 'success')
    elif resp.status_code == 404:
        flash('Неверный формат индекса', 'error')
    cars = requests.get(req).json()
    return render_template('cars.html', cars=cars)

@front.route('/cars/stats/', methods=['GET'])
def get_stats():
    req = 'http://localhost:5000/api/allcars/stats/'
    resp = requests.get(req)
    return render_template('stats.html', stats=resp.json())

if __name__ == '__main__':
    front.run(debug=False, port=5001)
