pyAS4
=====

Бібліотека Python для роботи з AS4 (OASIS ebXML AS4) протоколом обміну повідомленнями.

**pyAS4** - це дружелюбна обгортка навколо ZEEP та MTOM/XOP транспорту, яка спрощує створення та управління
AS4-сумісними повідомленнями для систем електронної доставки та B2B комунікацій.

Опис
----

pyAS4 надає удосконалений клієнт для роботи з AS4 веб-сервісами, включаючи:

- **AS4Send** - клієнт для відправлення AS4-повідомлень
- **AS4Receive** - клієнт для отримання AS4-повідомлень
- **Header** - конструктор заголовків AS4 для керування метаданими повідомлень
- Підтримка MTOM/XOP для передачі великих файлів
- Управління party identifiers та service/action деталями
- Обробка вхідних та вихідних повідомлень

Вимоги
------

- Python >= 3.12
- lxml >= 6.1.1
- zeep >= 4.3.3

Встановлення
------------

За допомогою uv::

    uv pip install pyAS4

Або з вихідного коду::

    git clone <repository-url>
    cd pyAS4
    uv pip install -e .

Використання
------------

Основний приклад
^^^^^^^^^^^^^^^^

.. code-block:: python

    from zeep.plugins import HistoryPlugin
    from pymtom_xop import MtomTransport

    from pyAS4.AS4Client import AS4Send
    from pyAS4.header import Header

    # Створіть транспорт та заголовок
    transport = MtomTransport()
    header = Header(
        c1_party_id="party1-id",
        c1_party_id_type="urn:fdc:peppol.eu:2017:identifiers:C1",
        c2_party_id="party2-id",
        c2_party_id_type="urn:fdc:peppol.eu:2017:identifiers:C2",
        c3_party_id="party3-id",
        c3_party_id_type="urn:fdc:peppol.eu:2017:identifiers:C3",
        c4_party_id="party4-id",
        c4_party_id_type="urn:fdc:peppol.eu:2017:identifiers:C4",
        service_type="urn:oasis:names:tc:ebcore:ebrs:ebms:binding:1.0",
        conversationid="my-conversation-id",
    )

    # Ініціалізуйте клієнт відправлення
    client = AS4Send(
        wsdl="http://example.com/as4-service?wsdl",
        transport=transport,
        plugins=[HistoryPlugin()],
        header=header,
    )

Відправлення повідомлень
^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    # Відправте повідомлення з вказаними корисними навантаженнями
    payloads = [
        {
            "content": b"<xml>payload content</xml>",
            "content_type": "application/xml",
        }
    ]

    client.send_message(payloads)

Отримання очікуючих повідомлень
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    from pyAS4.AS4Client import AS4Receive

    receiver = AS4Receive(
        wsdl="http://example.com/as4-service?wsdl",
        transport=transport,
        plugins=[HistoryPlugin()],
        header=header,
    )

    # Отримайте очікуючі повідомлення
    for message in receiver.receive_message():
        print(message)

Робота з заголовками AS4
^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    from pyAS4.header import Header

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
    │   ├── AS4Client.py          # AS4Client, AS4Send та AS4Receive
    │   ├── header.py            # Header клас для керування AS4 заголовками
    │   └── py.typed             # Маркер для типізованої бібліотеки
    ├── README.rst               # Цей файл
    ├── pyproject.toml           # Конфігурація проєкту (PEP 517/518)
    └── uv.lock                  # Зафіксовані залежності для uv

Архітектура
-----------

**AS4Send / AS4Receive**
    Базові клієнти для відправлення й отримання AS4-повідомлень через WSDL,
    транспорт і AS4-заголовок.

**Header**
    Клас для конструювання та керування ebXML AS4 заголовками повідомлень.
    Генерує коректний XML на основі стандартів OASIS ebXML.

**MtomTransport**
    Транспорт з підтримкою MTOM/XOP для обробки великих бінарних вкладень.

Стандарти та протоколи
----------------------

Проєкт реалізує наступні стандарти:

- **OASIS ebXML AS4 v3.0** - Асинхронна обробка SOAP повідомлень
- **PEPPOL** - Pan-European Public Procurement Online (ідентифікатори сторін)
- **MTOM/XOP** - SOAP з вкладеннями (передача великих файлів)

Автор
-----

Andrey Shapovalov (mt.andrey@gmail.com)

Ліцензія
--------

EUPL v1.2

Поточна версія
--------------

9

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
