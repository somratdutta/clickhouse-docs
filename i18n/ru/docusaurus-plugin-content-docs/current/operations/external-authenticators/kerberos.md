---
description: 'Существующие и правильно настроенные пользователи ClickHouse могут быть аутентифицированы через протокол аутентификации Kerberos.'
slug: /operations/external-authenticators/kerberos
title: 'Kerberos'
---

import SelfManaged from '@site/i18n/ru/docusaurus-plugin-content-docs/current/_snippets/_self_managed_only_no_roadmap.md';


# Kerberos

<SelfManaged />

Существующие и правильно настроенные пользователи ClickHouse могут быть аутентифицированы через протокол аутентификации Kerberos.

В настоящее время Kerberos может использоваться только как внешний аутентификатор для существующих пользователей, которые определены в `users.xml` или в локальных путях контроля доступа. Эти пользователи могут использовать только HTTP-запросы и должны быть в состоянии аутентифицироваться с использованием механизма GSS-SPNEGO.

Для этого подхода Kerberos должен быть настроен в системе и должен быть включен в конфигурации ClickHouse.

## Включение Kerberos в ClickHouse {#enabling-kerberos-in-clickhouse}

Чтобы включить Kerberos, необходимо добавить раздел `kerberos` в `config.xml`. Этот раздел может содержать дополнительные параметры.

#### Параметры: {#parameters}

- `principal` - каноническое имя службы, которое будет получено и использовано при принятии контекстов безопасности.
    - Этот параметр является необязательным, если его опустить, будет использоваться имя по умолчанию.

- `realm` - подмир, который будет использован для ограничения аутентификации только для тех запросов, чья подмир инициатора совпадает с ним.
    - Этот параметр является необязательным, если его опустить, дополнительная фильтрация по подмиру применяться не будет.

- `keytab` - путь к файлу ключей службы.
    - Этот параметр является необязательным, если его опустить, путь к файлу ключей службы должен быть установлен в переменной окружения `KRB5_KTNAME`.

Пример (добавляется в `config.xml`):

```xml
<clickhouse>
    <!- ... -->
    <kerberos />
</clickhouse>
```

С указанием principal:

```xml
<clickhouse>
    <!- ... -->
    <kerberos>
        <principal>HTTP/clickhouse.example.com@EXAMPLE.COM</principal>
    </kerberos>
</clickhouse>
```

С фильтрацией по подмиру:

```xml
<clickhouse>
    <!- ... -->
    <kerberos>
        <realm>EXAMPLE.COM</realm>
    </kerberos>
</clickhouse>
```

:::note
Вы можете определить только один раздел `kerberos`. Наличие нескольких разделов `kerberos` заставит ClickHouse отключить аутентификацию Kerberos.
:::

:::note
Разделы `principal` и `realm` не могут быть указаны одновременно. Наличие обоих разделов `principal` и `realm` заставит ClickHouse отключить аутентификацию Kerberos.
:::

## Kerberos как внешний аутентификатор для существующих пользователей {#kerberos-as-an-external-authenticator-for-existing-users}

Kerberos может использоваться как метод проверки личности локально определенных пользователей (пользователей, определенных в `users.xml` или в локальных путях контроля доступа). В настоящее время **только** запросы по протоколу HTTP могут быть *керберизованы* (через механизм GSS-SPNEGO).

Формат имени принципала Kerberos обычно следует этому шаблону:

- *primary/instance@REALM*

Часть */instance* может встречаться ноль или более раз. **Ожидается, что *primary* часть канонического имени принципала инициатора будет совпадать с керберизованным именем пользователя для успешной аутентификации**.

### Включение Kerberos в `users.xml` {#enabling-kerberos-in-users-xml}

Для включения аутентификации Kerberos для пользователя укажите раздел `kerberos` вместо `password` или аналогичных разделов в определении пользователя.

Параметры:

- `realm` - подмир, который будет использован для ограничения аутентификации только для тех запросов, чья подмир инициатора совпадает с ним.
    - Этот параметр является необязательным, если его опустить, дополнительная фильтрация по подмиру применяться не будет.

Пример (добавляется в `users.xml`):

```xml
<clickhouse>
    <!- ... -->
    <users>
        <!- ... -->
        <my_user>
            <!- ... -->
            <kerberos>
                <realm>EXAMPLE.COM</realm>
            </kerberos>
        </my_user>
    </users>
</clickhouse>
```

:::note
Обратите внимание, что аутентификация Kerberos не может использоваться вместе с каким-либо другим механизмом аутентификации. Наличие любых других разделов, таких как `password`, совместно с `kerberos`, заставит ClickHouse завершить работу.
:::

:::info Напоминание
Обратите внимание, что теперь, как только пользователь `my_user` использует `kerberos`, Kerberos должен быть включен в основной файл `config.xml`, как описано выше.
:::

### Включение Kerberos с помощью SQL {#enabling-kerberos-using-sql}

Когда [Управление доступом на основе SQL и управление учетными записями](/operations/access-rights#access-control-usage) включено в ClickHouse, пользователи, идентифицированные Kerberos, также могут быть созданы с использованием SQL-запросов.

```sql
CREATE USER my_user IDENTIFIED WITH kerberos REALM 'EXAMPLE.COM'
```

...или без фильтрации по подмиру:

```sql
CREATE USER my_user IDENTIFIED WITH kerberos
```
