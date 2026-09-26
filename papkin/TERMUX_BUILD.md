# Сборка APK через Termux + GitHub Actions

Этот проект уже подготовлен для Android. На телефоне не нужно компилировать
весь Android toolchain вручную: Termux отправляет проект в GitHub, а GitHub
Actions собирает APK на Linux-машине.

## 1. Один раз в Termux

```bash
pkg update -y
pkg install -y git gh
termux-setup-storage
gh auth login
```

## 2. Проект должен лежать в GitHub

Из папки проекта:

```bash
cd ~/downloads/papkin
git add .
git commit -m "Android APK build"
git push origin main
```

Если `origin` ещё не настроен, сначала создайте пустой репозиторий на GitHub
и выполните `git remote add origin <адрес-репозитория>`.

## 3. Запустить сборку

```bash
cd ~/downloads/papkin
gh workflow run build-android.yml --ref main
```

Посмотреть запуски:

```bash
gh run list --workflow=build-android.yml --limit 5
```

Дождаться последнего запуска:

```bash
gh run watch "$(gh run list --workflow=build-android.yml --branch main --limit 1 --json databaseId --jq '.[0].databaseId')" --exit-status
```

## 4. Скачать APK в Загрузки телефона

```bash
cd ~/downloads/papkin && rm -rf /tmp/neondefender-apk && mkdir -p /tmp/neondefender-apk && RUN_ID="$(gh run list --workflow=build-android.yml --branch main --limit 1 --json databaseId --jq '.[0].databaseId')" && gh run download "$RUN_ID" -n NeonDefender-APK -D /tmp/neondefender-apk && APK="$(find /tmp/neondefender-apk -type f -name '*.apk' | head -n 1)" && test -n "$APK" && cp "$APK" ~/storage/downloads/NeonDefender-2.0.0.apk && echo "Готово: ~/storage/downloads/NeonDefender-2.0.0.apk"
```

## Если сборка упала

Показать ошибки последнего запуска:

```bash
gh run view "$(gh run list --workflow=build-android.yml --branch main --limit 1 --json databaseId --jq '.[0].databaseId')" --log-failed
```

Если предыдущая сборка оставила битый кэш:

```bash
rm -rf .buildozer
git add .
git commit -m "Clean Android build"
git push origin main
```
