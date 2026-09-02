# pyAS4

Бібліотека Python для роботи з AS4 (OASIS ebXML AS4) протоколом обміну повідомленнями.

**pyAS4** — це зручна обгортка навколо Zeep та MTOM/XOP-транспорту, яка спрощує створення й керування AS4-сумісними
повідомленнями для систем електронної доставки та B2B-комунікацій.

## Опис

pyAS4 надає удосконалений клієнт для роботи з AS4 веб-сервісами, включаючи:

- **AS4Send** - клієнт для відправлення AS4-повідомлень
- **AS4Receive** - клієнт для отримання AS4-повідомлень
- **Header** - конструктор заголовків AS4 для керування метаданими повідомлень
- Підтримка MTOM/XOP для передачі великих файлів
- Керування ідентифікаторами сторін і параметрами service/action
- Обробка вхідних та вихідних повідомлень

## Вимоги

- Python >= 3.12
- lxml >= 6.1.1
- zeep >= 4.3.3
- pymtom-xop-fork >= 0.0.3

## Встановлення

За допомогою uv:

    uv add pyAS4

Або за допомогою pip:

    python -m pip install pyAS4

Для розробки з вихідного коду:

    git clone https://github.com/AndreyShapovalovVN/pyAS4.git
    cd pyAS4
    uv sync --extra dev

## Використання

### Спільні параметри клієнтів

`AS4Send` і `AS4Receive` використовують однакові параметри інфраструктури:

- `wsdl` — URL або локальний шлях до WSDL AS4/Domibus-сервісу.

- `transport` — транспорт Zeep. Для `AS4Send` обов'язково потрібен
  `MtomTransport`, оскільки вихідні файли передаються як MTOM/XOP-вкладення.

- `plugins` — список плагінів Zeep, наприклад `[HistoryPlugin()]`. Якщо плагіни не потрібні, слід передати порожній
  список `[]`.

Різниця між клієнтами стосується лише даних AS4: для відправлення потрібен повний
`Header`, а для отримання достатньо `c4_party_id` (`finalRecipient`).

### Відправлення повідомлень

Контракт конструктора:

```python
AS4Send(
    wsdl: str,
transport: MtomTransport,
plugins: list[HistoryPlugin],
header: Header,
)
```

Повний `Header` потрібен для формування ebMS-заголовка, включно з інформацією про сторони C1–C4, сервіс, дію,
conversation ID і вкладення.

```python
from pymtom_xop import MtomTransport
from zeep.exceptions import Fault
from zeep.plugins import HistoryPlugin

from pyAS4.AS4Client import AS4Send
from pyAS4.header import Header

transport = MtomTransport()
plugins = [HistoryPlugin()]

header = Header(
    c1_party_id="original-sender",
    c1_party_id_type="urn:example:identifier:sender",
    c2_party_id="sender-gateway",
    c2_party_id_type="urn:example:identifier:gateway",
    c3_party_id="receiver-gateway",
    c3_party_id_type="urn:example:identifier:gateway",
    c4_party_id="final-recipient",
    c4_party_id_type="urn:example:identifier:recipient",
    service="http://example.eu/services/evidence",
    service_type="urn:oasis:names:tc:ebcore:ebrs:ebms:binding:1.0",
    action="http://example.eu/actions/submit-evidence",
)

sender = AS4Send(
    wsdl="https://domibus.example.eu/services/backend?wsdl",
    transport=transport,
    plugins=plugins,
    header=header,
)

payloads = [
    {
        "content": b"<EvidenceRequest>...</EvidenceRequest>",
        "content_type": "application/xml",
        "cid": "evidence-request.xml",
    },
    {
        "content": b"%PDF-1.7 ...",
        "content_type": "application/pdf",
        "cid": "supporting-document.pdf",
    },
]

try:
    response = sender.send_message(payloads)
except Fault as exc:
    print(f"Domibus відхилив повідомлення: {exc}")
```

Контракт одного елемента `payload`:

```python
from typing import NotRequired, TypedDict


class Payload(TypedDict):
    content: bytes | str
    content_type: str
    cid: NotRequired[str]
```

Сигнатура методу:

```python
def send_message(self, payload: Sequence[Payload]) -> Any:
    ...
```

- `content` (`bytes | str`) — обов'язковий вміст вкладення. Рядок кодується як UTF-8.

- `content_type` (`str`) — обов'язковий MIME-тип, наприклад `application/xml`
  або `application/pdf`.

- `cid` (`str`, необов'язковий) — Content-ID вкладення. Якщо значення не передано, бібліотека генерує UUID.

`send_message()` додає вкладення до MTOM-транспорту, формує `PayloadInfo`, викликає SOAP-операцію `submitMessage` і
повертає відповідь Zeep без додаткового перетворення. SOAP Fault та інші транспортні помилки логуються і передаються
виклику користувача.

### Отримання очікуючих повідомлень

Контракт конструктора:

```python
AS4Receive(
    wsdl: str,
transport: Transport,
plugins: list[HistoryPlugin],
header: Header | None = None,
*,
c4_party_id: str | None = None,
)
```

Рекомендований спосіб — передати лише `c4_party_id`. Це значення використовується як `finalRecipient` в операції
`listPendingMessages`. Тип ідентифікатора
`c4_party_id_type` для цього SOAP-виклику не потрібен.

```python
from pyAS4.AS4Client import AS4Receive

receiver = AS4Receive(
    wsdl="https://domibus.example.eu/services/backend?wsdl",
    transport=transport,
    plugins=plugins,
    c4_party_id="final-recipient",
)

for message in receiver.receive_message():
    print(message["messageId"])
    print(message["header"])
    for payload in message["payload"]:
        print(payload["content"])
```

Якщо повний `Header` уже існує, його також можна використати. У цьому випадку recipient береться з `header.c4_party_id`:

```python
receiver = AS4Receive(
    wsdl="https://domibus.example.eu/services/backend?wsdl",
    transport=transport,
    plugins=plugins,
    header=header,
)
```

Якщо одночасно передані `header` і `c4_party_id`, явний `c4_party_id` має пріоритет. Якщо не передано жодного з них,
конструктор піднімає `ValueError`.

`receive_message()` є генератором. Він викликає `listPendingMessages`, а потім
`retrieveMessage` для кожного знайденого message ID. Кожне повідомлення має контракт:

    {
        "messageId": str,
        "header": dict,
        "payload": list[dict[str, str]],
    }

Приклад скороченого результату:

    {
        "messageId": "uuid-message-id",
        "header": {
            "CollaborationInfo": {
                "service": "http://example.eu/services/evidence",
                "action": "http://example.eu/actions/submit-evidence",
                "conversationId": "conversation-id",
            },
            "PayloadInfo": [
                {"href": "cid:evidence.xml", "MimeType": "application/xml"}
            ],
        },
        "payload": [
            {
                "href": "cid:evidence.xml",
                "MimeType": "application/xml",
                "content": "<Evidence>...</Evidence>",
            }
        ],
    }

SOAP Fault під час отримання списку pending messages передається користувачу. Помилки завантаження окремих повідомлень
логуються, після чого генератор переходить до наступного повідомлення.

### Робота з заголовками AS4

```python
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
    action="http://docs.oasis-open.org/ebxml-msg/as4/200902/action",
)
```

## Структура проєкту

```text
pyAS4/
├── pyAS4/
│   ├── __init__.py           # Точка входу бібліотеки
│   ├── AS4Client.py          # AS4Client, AS4Send та AS4Receive
│   └── header.py             # Клас Header для керування AS4-заголовками
├── README.md                 # Цей файл
├── pyproject.toml            # Конфігурація проєкту (PEP 517/518)
└── uv.lock                   # Зафіксовані залежності для uv
```

## Архітектура

- **AS4Send / AS4Receive** — базові клієнти для відправлення й отримання AS4-повідомлень через WSDL, транспорт та
  плагіни Zeep. `AS4Send` використовує повний AS4-заголовок, тоді як `AS4Receive` може працювати лише з
  `finalRecipient`.

- **Header** — клас для конструювання та керування ebXML AS4-заголовками повідомлень. Генерує XML на основі стандартів
  OASIS ebXML.

- **MtomTransport** — транспорт із підтримкою MTOM/XOP для обробки великих бінарних вкладень.

## Стандарти та протоколи

Проєкт реалізує наступні стандарти:

- **OASIS ebXML AS4 v3.0** - Асинхронна обробка SOAP повідомлень
- **MTOM/XOP** - SOAP з вкладеннями (передача великих файлів)

## Автор

Andrey Shapovalov (mt.andrey@gmail.com)

## Ліцензія

EUPL v1.2

## Поточна версія

0.1.20

## Внески

Розробка ведеться у [репозиторії pyAS4 на GitHub](https://github.com/AndreyShapovalovVN/pyAS4).

## Контакти

Для питань та пропозицій звертайтеся:

- Email: mt.andrey@gmail.com

---

Примітка: Бібліотека розроблена для роботи з системами електронної доставки, що відповідають стандартам OASIS ebXML AS4,
та особливо для проєктів, що використовують OOTS мережу.
