#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ═══════════════════════════════════════════════════════════════════════
# NEON DEFENDER — модуль локального (LAN) сетевого кооператива.
#
# Архитектура: HOST держит авторитетное состояние матча (враги, волны,
# столкновения, очки), CLIENT только отправляет свой ввод и отрисовывает
# то, что прислал HOST. Транспорт — TCP, сообщения — JSON-строки,
# разделённые "\n". Сеть работает в отдельных потоках и никогда не
# блокирует основной игровой цикл Pygame.
#
# Никакого интернета, внешних серверов и облака не используется —
# только сокеты внутри локальной сети (Wi-Fi/Ethernet).
# ═══════════════════════════════════════════════════════════════════════

import socket
import threading
import json
import time
import queue

NETWORK_PROTOCOL_VERSION = 1
DEFAULT_PORT = 5000
MAX_NAME_LEN = 16


def get_local_ip():
    """Определяет реальный LAN IP этого компьютера (не 127.0.0.1).
    Работает и без доступа в интернет: UDP-сокет не отправляет пакет
    при connect(), только выбирает исходящий сетевой интерфейс по
    таблице маршрутизации."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
    except Exception:
        try:
            ip = socket.gethostbyname(socket.gethostname())
        except Exception:
            ip = "127.0.0.1"
    finally:
        s.close()
    if ip.startswith("127."):
        try:
            ip = socket.gethostbyname(socket.gethostname())
        except Exception:
            pass
    return ip


def _send_line(sock, obj):
    data = (json.dumps(obj, ensure_ascii=False) + "\n").encode("utf-8")
    sock.sendall(data)


class _LineReader:
    """Читает JSON-сообщения, разделённые \\n, из потокового сокета."""

    def __init__(self, sock):
        self.sock = sock
        self.buf = b""

    def read_messages(self):
        msgs = []
        try:
            data = self.sock.recv(65536)
        except socket.timeout:
            return msgs
        except OSError:
            raise ConnectionError("socket closed")
        if not data:
            raise ConnectionError("connection closed")
        self.buf += data
        while b"\n" in self.buf:
            line, self.buf = self.buf.split(b"\n", 1)
            if not line:
                continue
            try:
                msgs.append(json.loads(line.decode("utf-8")))
            except Exception:
                pass
        return msgs


class LANServer:
    """LAN-сервер (HOST). Принимает до (max_players-1) клиентов
    (сам HOST — игрок с id=1)."""

    def __init__(self, port=DEFAULT_PORT, max_players=2):
        self.port = port
        self.max_players = max_players
        self.sock = None
        self.running = False
        self.clients = {}  # id -> dict(sock, reader, name)
        self.next_id = 2
        self.lock = threading.Lock()
        self.incoming = queue.Queue()
        self.events = queue.Queue()
        self._accept_thread = None

    def start(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind(("0.0.0.0", self.port))
            self.sock.listen(8)
            self.sock.settimeout(0.5)
        except OSError as e:
            raise ConnectionError("PORT_ERROR: %s" % e)
        self.running = True
        self._accept_thread = threading.Thread(target=self._accept_loop, daemon=True)
        self._accept_thread.start()

    def _accept_loop(self):
        while self.running:
            try:
                conn, addr = self.sock.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            with self.lock:
                full = len(self.clients) >= (self.max_players - 1)
                pid = self.next_id
                if not full:
                    self.next_id += 1
            if full:
                try:
                    _send_line(conn, {"type": "error", "reason": "SERVER_FULL"})
                    conn.close()
                except Exception:
                    pass
                continue
            conn.settimeout(0.5)
            client = {"sock": conn, "reader": _LineReader(conn), "name": "Player %d" % pid, "addr": addr}
            with self.lock:
                self.clients[pid] = client
            threading.Thread(target=self._client_loop, args=(pid, client), daemon=True).start()

    def _client_loop(self, pid, client):
        sock = client["sock"]
        reader = client["reader"]
        try:
            _send_line(sock, {"type": "welcome", "player_id": pid, "protocol": NETWORK_PROTOCOL_VERSION})
        except Exception:
            pass
        while self.running:
            try:
                msgs = reader.read_messages()
            except Exception:
                break
            for m in msgs:
                if m.get("type") == "hello":
                    if m.get("protocol") != NETWORK_PROTOCOL_VERSION:
                        try:
                            _send_line(sock, {"type": "error", "reason": "VERSION_MISMATCH"})
                        except Exception:
                            pass
                        self.running_client = False
                        break
                    name = str(m.get("name", "") or "")[:MAX_NAME_LEN].strip() or ("Player %d" % pid)
                    with self.lock:
                        client["name"] = name
                    self.events.put(("connected", pid, name))
                else:
                    m["_player_id"] = pid
                    self.incoming.put(m)
            time.sleep(0.005)
        with self.lock:
            self.clients.pop(pid, None)
        try:
            sock.close()
        except Exception:
            pass
        self.events.put(("disconnected", pid, None))

    def broadcast(self, obj):
        data = (json.dumps(obj, ensure_ascii=False) + "\n").encode("utf-8")
        with self.lock:
            items = list(self.clients.items())
        dead = []
        for pid, c in items:
            try:
                c["sock"].sendall(data)
            except Exception:
                dead.append(pid)
        if dead:
            with self.lock:
                for pid in dead:
                    self.clients.pop(pid, None)

    def get_incoming(self):
        out = []
        while True:
            try:
                out.append(self.incoming.get_nowait())
            except queue.Empty:
                break
        return out

    def get_events(self):
        out = []
        while True:
            try:
                out.append(self.events.get_nowait())
            except queue.Empty:
                break
        return out

    def player_names(self):
        with self.lock:
            return {pid: c["name"] for pid, c in self.clients.items()}

    def player_count(self):
        with self.lock:
            return len(self.clients)

    def stop(self):
        self.running = False
        with self.lock:
            clients = list(self.clients.values())
            self.clients.clear()
        for c in clients:
            try:
                c["sock"].close()
            except Exception:
                pass
        try:
            if self.sock:
                self.sock.close()
        except Exception:
            pass


class LANClient:
    """LAN-клиент. Подключается к HOST по IP:порт."""

    def __init__(self, name="Player"):
        self.sock = None
        self.reader = None
        self.running = False
        self.connected = False
        self.player_id = None
        self.name = (name or "Player")[:MAX_NAME_LEN]
        self.incoming = queue.Queue()
        self._thread = None

    def connect(self, ip, port=DEFAULT_PORT, timeout=4.0):
        """Блокирующий вызов — запускать в отдельном потоке, чтобы не
        морозить игровой цикл."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            s.connect((ip, int(port)))
        except socket.timeout:
            raise ConnectionError("SERVER_NOT_FOUND")
        except ConnectionRefusedError:
            raise ConnectionError("CONNECTION_ERROR")
        except OSError:
            raise ConnectionError("CONNECTION_FAILED")
        s.settimeout(0.5)
        self.sock = s
        self.reader = _LineReader(s)
        try:
            _send_line(s, {"type": "hello", "name": self.name, "protocol": NETWORK_PROTOCOL_VERSION})
        except Exception:
            raise ConnectionError("CONNECTION_FAILED")
        self.running = True
        self.connected = True
        self._thread = threading.Thread(target=self._recv_loop, daemon=True)
        self._thread.start()

    def _recv_loop(self):
        while self.running:
            try:
                msgs = self.reader.read_messages()
            except Exception:
                self.connected = False
                self.incoming.put({"type": "disconnected"})
                return
            for m in msgs:
                if m.get("type") == "welcome":
                    self.player_id = m.get("player_id")
                self.incoming.put(m)
            time.sleep(0.005)

    def send(self, obj):
        if not self.connected or not self.sock:
            return
        try:
            _send_line(self.sock, obj)
        except Exception:
            self.connected = False

    def get_incoming(self):
        out = []
        while True:
            try:
                out.append(self.incoming.get_nowait())
            except queue.Empty:
                break
        return out

    def disconnect(self):
        self.running = False
        self.connected = False
        try:
            if self.sock:
                self.sock.close()
        except Exception:
            pass
