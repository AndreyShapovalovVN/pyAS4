pyAS4
=====

Бібліотека Python для роботи з AS4 (OASIS ebXML AS4) протоколом обміну повідомленнями.

**pyAS4** - це дружелюбна обгортка навколо ZEEP та MTOM/XOP транспорту, яка спрощує створення та управління
AS4-сумісними повідомленнями для систем електронної доставки та B2B комунікацій.

Опис
----

pyAS4 надає удосконалений клієнт для роботи з AS4 веб-сервісами, включаючи:

- **AS4Client** - розширений SOAP-клієнт з підтримкою ebXML AS4
- **Header** - конструктор заголовків AS4 для керування метаданими повідомлень
- Підтримка MTOM/XOP для передачі великих файлів
- Управління party identifiers та service/action деталями
- Обробка вхідних та вихідних повідомлень

Вимоги
------

- Python >= 3.10
- lxml >= 5.4.0
- zeep (SOAP клієнт)
- pymtom_xop (MTOM/XOP транспорт)
- requests (HTTP сесії)

Встановлення
-----------

За допомогою pip::

    pip install pyAS4

Або з вихідного коду::

    git clone <repository-url>
    cd pyAS4
    pip install -e .

Використання
-----------

Основний приклад
^^^^^^^^^^^^^^^^

.. code-block:: python

    from requests import Session
    from pyAS4 import AS4Client

    # Створіть HTTP сесію
    session = Session()

    # Ініціалізуйте AS4 клієнт
    client = AS4Client(
        wsdl="http://example.com/as4-service?wsdl",
        session=session,
        c1_party_id="party1-id",
        c1_party_id_type="urn:fdc:peppol.eu:2017:identifiers:C1",
        c2_party_id="party2-id",
        c2_party_id_type="urn:fdc:peppol.eu:2017:identifiers:C2",
        c3_party_id="party3-id",
        c3_party_id_type="urn:fdc:peppol.eu:2017:identifiers:C3",
        c4_party_id="party4-id",
        c4_party_id_type="urn:fdc:peppol.eu:2017:identifiers:C4",
        service_type="urn:oasis:names:tc:ebcore:ebrs:ebms:binding:1.0",
        conversationid="my-conversation-id"
    )

Відправлення повідомлень
^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    # Відправте повідомлення з вказаними корисними навантаженнями
    payloads = [
        b"<xml>payload content</xml>"
    ]

    client.submitMessage(payloads)

Отримання очікуючих повідомлень
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    # Отримайте список очікуючих повідомлень
    pending_messages = client.listPendingMessages()
    print(pending_messages)

Отримання повідомлення за ID
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    # Отримайте конкретне повідомлення за його ID
    message = client.retrieveMessage("message-id-123")
    print(message)

Робота з заголовками AS4
^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    from pyAS4 import Header

    # Створіть заголовок AS4
    header = Header(
        c1_party_id="sender-id",
        c1_party_id_type="urn:fdc:peppol.eu:2017:identifiers:C1",
        c2_party_id="recipient-id",
        c2_party_id_type="urn:fdc:peppol.eu:2017:identifiers:C2",
        c3_party_id="intermediary-id",
        c3_party_id_type="urn:fdc:peppol.eu:2017:identifiers:C3",
        c4_party_id="carrier-id",
        c4_party_id_type="urn:fdc:peppol.eu:2017:identifiers:C4",
        conversationid="unique-conversation-id",
        service="http://docs.oasis-open.org/ebxml-msg/as4/200902/service",
        service_type="urn:oasis:names:tc:ebcore:ebrs:ebms:binding:1.0",
        action="http://docs.oasis-open.org/ebxml-msg/as4/200902/action"
    )

Структура проєкту
-----------------

::

    pyAS4/
    ├── pyAS4/
    │   ├── __init__.py           # Точка входу бібліотеки
    │   ├── Communication.py      # AS4Client та сервіс комунікації
    │   ├── header.py            # Header клас для керування AS4 заголовками
    │   └── py.typed             # Маркер для типізованої бібліотеки
    ├── README.rst               # Цей файл
    ├── pyproject.toml           # Конфігурація проєкту (PEP 517/518)
    ├── setup.py                 # Скрипт встановлення
    └── requirements.txt         # Залежності проєкту

Архітектура
-----------

**AS4Client**
    Розширена версія ZEEP Client, яка автоматично налаштовує MTOM/XOP транспорт
    та керує конфігурацією ebXML AS4 повідомлень. Підтримує управління party identifiers
    та сервісними деталями.

**Header**
    Клас для конструювання та керування ebXML AS4 заголовками повідомлень.
    Генерує коректний XML на основі стандартів OASIS ebXML.

**MtomTransport**
    Транспорт з підтримкою MTOM/XOP для обробки великих бінарних вкладень.

Стандарти та протоколи
---------------------

Проєкт реалізує наступні стандарти:

- **OASIS ebXML AS4 v3.0** - Асинхронна обробка SOAP повідомлень
- **PEPPOL** - Pan-European Public Procurement Online (ідентифікатори сторін)
- **MTOM/XOP** - SOAP з вкладеннями (передача великих файлів)

Автор
-----

Andrey Shapovalov (mt.andrey@gmail.com)

Ліцензія
--------

MIT License

Поточна версія
--------------

8

Внески
------

Поточна версія розробляється в приватному репозиторії.

Контакти
--------

Для питань та пропозицій звертайтесь до:
- Email: mt.andrey@gmail.com

----

Примітка: Бібліотека розроблена для роботи з системами електронної доставки,
що відповідають стандартам OASIS ebXML AS4, та особливо для проєктів,
що використовують PEPPOL мережу.

