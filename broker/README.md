# Media feedback Broker

Cloudflare Worker служит защищённым мостом между статическим Media Web и записью в GitHub. Он авторизует владельца, превращает браузерный отзыв в типизированную `record_media_entry`, создаёт request-only PR и сообщает состояние операции.

Broker никогда не правит канонические YAML напрямую.

Рабочий `POST /v1/feedback` работает по v6-схеме: Broker читает viewer digest из `media/generated/index.jsonl` на точном SHA текущего `main`, добавляет precondition и создаёт ветку/PR от того же SHA. Браузер сам digest не знает и не вычисляет.

## 1. GitHub App

Создайте один GitHub App и установите его только в `MrDragon13/ChatGPT-lib`.

Права репозитория:

- Metadata: Read-only
- Contents: Read and write
- Pull requests: Read and write
- Actions: Read-only

Право на изменение GitHub Actions workflows не требуется.

Адрес возврата (`callback`) для авторизации пользователя:

```text
https://<worker-host>/v1/auth/callback
```

Нужно сохранить App ID, Client ID, Client Secret, ID установки и числовой GitHub user ID владельца, которому разрешено редактирование.

Приватный ключ GitHub App должен быть в формате PKCS#8 PEM. Если GitHub выдал другой RSA PEM, преобразуйте его:

```bash
openssl pkcs8 -topk8 -nocrypt -in github-app.pem -out github-app-pkcs8.pem
```

Файлы приватного ключа нельзя коммитить.

## 2. Настройка Cloudflare Worker

`wrangler.jsonc` содержит публичные настройки репозитория и origin и два Rate Limiting binding. Namespace IDs `1001` и `1002` должны быть уникальны в Cloudflare-аккаунте.

Секреты хранятся в Worker, а не в репозитории:

```bash
cd broker
npx wrangler secret put GITHUB_APP_ID
npx wrangler secret put GITHUB_APP_CLIENT_ID
npx wrangler secret put GITHUB_APP_INSTALLATION_ID
npx wrangler secret put OWNER_GITHUB_USER_ID
npx wrangler secret put GITHUB_APP_CLIENT_SECRET
npx wrangler secret put BROKER_SESSION_SECRET
npx wrangler secret put GITHUB_APP_PRIVATE_KEY < github-app-pkcs8.pem
```

Для `BROKER_SESSION_SECRET` нужен случайный секрет с высокой энтропией.

Разрешённый рабочий origin:

```text
https://mrdragon13.github.io
```

Браузер не получает GitHub-токены и секреты Worker.

## 3. Секреты GitHub Actions для публикации

Для ручного процесса `Broker Deploy` нужны:

- `CLOUDFLARE_API_TOKEN` — токен с правом публикации Worker;
- `CLOUDFLARE_ACCOUNT_ID` — ID Cloudflare-аккаунта.

Рабочие секреты GitHub App остаются в Cloudflare и не копируются в GitHub Actions.

`Broker Deploy` запускается вручную из `main`. В поле `expected_sha` передаётся точный SHA уже проверенного `main`. Если SHA не совпадёт, публикация остановится.

## 4. URL Broker для сайта

После публикации Worker и проверки входа владельца создайте переменную репозитория:

```text
MEDIA_BROKER_URL=https://<worker-host>
```

Сборка Pages передаёт в Web только публичный адрес как `VITE_MEDIA_BROKER_URL`.

Если `MEDIA_BROKER_URL` не задан, сайт должен продолжать работать в режиме чтения.

## 5. Проверка

```bash
cd broker
npm ci
npm run test:run
npm run typecheck
```

Затем выполните одну контролируемую запись через опубликованный Broker и проверьте полный путь:

```text
POST /v1/feedback
  -> exact main SHA + viewer digest
  -> request-only media/op-<uuid> PR
  -> Media Command
  -> exact-head merge
  -> Media Pages
  -> GET /v1/operations/<uuid> == published
```

`MEDIA_BROKER_URL` должен указывать только на проверенный рабочий Worker.
