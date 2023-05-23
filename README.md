## Диплом python backend, netology.ru. Интернет-магазин на Django - backend.

### Запуск:
1. Создать БД на сервере (Postgresql)
2. В файле settings.py изменить данные для отправки почты на ящики пользователей. 
! Для этого лучше использовать свой почтовый сервер !
(Например, почта yandex, rambler блокировалась в рамках защиты от спама, не отправлялась. 
Пришлось на vps развернуть свой почтовый сервер mailcow. В сети много туториалов, не долго.)
3. Редактировать файл .env под свои данные БД.
4. В папке backend создать пакет migrations с файлом __init__.py (т.к. migrations, venv и т.д. в .gitignore)
5. Применить миграции и запустить сервер:
```shell
python manage.py makemigrations
python manage.py migrate
python manage.py runserver
```
4. Создать супер-юзера. 
(Супер-юзер пригодиться для безопасного перевода обычного пользователя в ранг менеджера магазина)
```shell
python manage.py createsuperuser
```
5. Далее с помощью запросов из requests_test.http сначала создаём юзеров и менеджеров магазина.
Далее активируем их через ссылку в письме на почте у каждого юзера.
Далее запросы: используя токены из БД менеджером загружаем файл с товарами.
Далее запросы: наполняем корзину, редактируем корзину, оформляем заказ. 
На почту пользователю приходит письмо с подтверждением заказа и общей суммой.
Далее запросы: каждый менеджер магазина видит, что заказали из его магазина.

### Что реализовано:
- пользователь может авторизоваться;
- есть возможность отправки данных для регистрации и получения email с подтверждением регистрации;
- пользователь может добавлять в корзину товары от разных магазинов;
- пользователь может подтверждать заказ с вводом адреса доставки;
- пользователь получает email с подтверждением после ввода адреса доставки;
- пользователь может переходить на страницу "Заказы" и открывать созданный заказ;
- менеджеры могут загружать yaml-файлы с товарами на сайт(в папку медиа), в БД хранятся ссылки на файлы;
- файлы можно загружать не только через форму, но и через админ-панель;
- менеджеры могут из загруженных файлов выгружать товары в БД;
- менеджеры видят товары, которые заказали из их магазина.

### Какие были "подводные камни":
- почта от популярных почтовых серверов не заработала. 
Пришлось развернуть свой почтовый сервер Mailcow. Работает отлично.
- использовал две формы forms: одна страничка для аутентификации пользователя - логин, пароль.
Другая страничка для выбора и загрузки файла. Обнаружил, что данные формы в браузерах, не сохраняют токен на localhost,
это сделано на уровне джанго в целях безопасности https://code.djangoproject.com/ticket/10560
Много на это потратил времени, чтобы выяснить. Выход: или на удалённом сервере развернуть проект для тестирования,
или через Postman. Сделал запрос загрузки файлов с товарами на сервер через Postman.
В файле requests_test.http есть описание как это сделать в Postman.