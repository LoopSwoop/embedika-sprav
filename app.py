import sqlite3, json, requests
import datetime, time, atexit
from flask import Flask, jsonify, make_response, request, g
from rfc3339 import rfc3339

DATABASE = './Cars.db'

app = Flask(__name__)

# Выводим и сохраняем логи
logs = []

def write_logs():
    global logs
    with open('logs.log', 'a', encoding='utf-8', errors='ignore') as fo:
        for el in logs:
            fo.write(el + '\n')
        logs = []

@app.before_request
def start_timer():
    g.start = time.time()

@app.after_request
def log_request(response):
    if request.path == '/favicon.ico':
        return response
    elif request.path.startswith('/static'):
        return response

    now = time.time()
    duration = round(now - g.start, 2)
    dt = datetime.datetime.fromtimestamp(now)
    timestamp = rfc3339(dt, utc=False, use_system_timezone=True)

    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    host = request.host
    if request.method == 'POST':
        args = request.json
    else:
        args = dict(request.args)

    log_params = [
        ('method', request.method),
        ('path', request.path),
        ('status', response.status_code),
        ('duration', duration),
        ('time', timestamp),
        ('ip', ip),
        ('host', host),
        ('params', args)
    ]

    request_id = request.headers.get('X-Request-ID')
    if request_id:
        log_params.append(('request_id', request_id))

    parts = []
    for name, value in log_params:
        part = f'{name}={value}'
        parts.append(part)
    line = " ".join(parts)

    global logs
    logs.append(line)

    app.logger.info(line)

    return response


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)

    db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()
    global logs
    if len(logs) > 9:
        with open('logs.log', 'a', encoding='utf-8', errors='ignore') as fo:
            for el in logs:
                fo.write(el + '\n')
            logs = []

def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

def modify_db(query, args=()):
    conn = get_db()
    cur = conn.execute(query, args)
    conn.commit()
    cur.close()

@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)

# Получаем все автомобили
@app.route('/api/allcars/', methods=['GET'])
def get_all_cars():
    args = dict(request.args)
    # Нет аргументов - выводим все машины
    if args == {}:
        cars = query_db('SELECT * FROM Cars')
        cars = [dict(car) for car in cars]
        return make_response(jsonify({'cars': cars}), 200)
    # В ссылке присутствуют аргументы, собираем запрос по частям
    # Базовый запрос без аргументов
    quer = 'SELECT * FROM Cars WHERE '
    # Возможные части запроса
    parts = {
        'id': 'id = ?',
        'num': 'num = ?',
        'model': 'model = ?',
        'color': 'color = ?',
        'year': 'year = ?'
    }
    # Добавляем все подходящие строки к запросу
    for arg in args:
        try:
            quer += parts[arg] + ' AND '
        except KeyError:
            make_response(jsonify({'error': 'Параметр не найден'}), 400)
    # Убираем ' AND ' на конце
    quer = quer[:len(quer) - 5]
    # Приводим аргументы к нужному нам виду и собираем их в список
    vals = []
    for arg in args:
        # Эти у нас должны быть int
        if arg == 'id' or arg == 'year':
            try:
                args[arg] = int(args[arg])
            except ValueError:
                return make_response(jsonify({'error': 'Неверное значение параметра'}), 400)
        vals.append(args[arg])
    cars = query_db(quer, vals)
    cars = [dict(car) for car in cars]
    # Если ничего не нашлось выводим ошибку
    if cars == []:
        return make_response(jsonify({'error': 'Записи не найдены'}), 404)
    return make_response(jsonify({'cars': cars}), 200)

# Добавляем новый автомобиль
@app.route('/api/allcars/', methods=['POST'])
def add_car():
    # Извлекаем из JSON предоставленного вместе с запросом нужные данные
    try:
        num = request.json['num'].strip()
        model = request.json['model'].strip()
        color = request.json['color'].strip()
        year = request.json['year'].strip()
    except KeyError:
        # Сообщаем, что не все данные предоставлены
        return make_response(jsonify({'error': 'Недостаточно параметров'}), 400)
    else:
        vals = (None, num, model, color, year)
        car = query_db('''SELECT * FROM Cars WHERE num = ? AND model = ?
                    AND color = ? AND year = ?''', vals[1:])
        # Есть ли в базе такой же автомобиль
        if car == []:
            modify_db('INSERT INTO Cars VALUES (?, ?, ?, ?, ?)', vals)
            return make_response(jsonify({'success': 'Запись успешно добавлена'}), 201)
        else:
            return make_response(jsonify({'error': 'Запись уже существует'}), 400)

# Удаяем существующий автомобиль
@app.route('/api/allcars/<int:car_id>/', methods=['DELETE'])
def del_car(car_id):
    car = query_db('SELECT * FROM Cars WHERE id = ?', [car_id])
    if car == []:
        return make_response(jsonify({'error': 'Запись для удаления не найдена'}), 400)
    else:
        modify_db('DELETE FROM Cars WHERE id = ?', (car_id,))
        return make_response(jsonify({'success': 'Запись успешно удалена'}), 200)

# Выводим статистику
@app.route('/api/allcars/stats/', methods=['GET'])
def show_stats():
    records = query_db('SELECT COUNT(id) FROM Cars')
    records = records[0][0]
    colors = query_db('SELECT DISTINCT color FROM Cars ORDER BY color')
    colors = [str(color[0]) for color in colors]
    years = query_db('SELECT DISTINCT year FROM Cars ORDER BY year')
    years = [str(year[0]) for year in years]
    models = query_db('SELECT DISTINCT model FROM Cars ORDER BY model')
    models = [str(model[0]) for model in models]
    return make_response(jsonify({'records': records, 'models': models,
            'colors': colors, 'years': years}), 200)

# Запускаем сервер, отвечающий за API
if __name__ == '__main__':
    atexit.register(write_logs)
    app.run(debug=True)
