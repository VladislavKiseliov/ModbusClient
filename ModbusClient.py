import logging
import signal
import time

from pymodbus.client import ModbusSerialClient
from pymodbus.exceptions import ModbusException

# --- Настройка логирования ---
logging.basicConfig()
log = logging.getLogger()
log.setLevel(logging.INFO)

# --- Параметры соединения ---
METHOD = "rtu"
PORT = "COM1"  # Замените на ваш порт
BAUDRATE = 9600
PARITY = "N"
BYTESIZE = 8
STOPBITS = 1
TIMEOUT = 1

# --- Параметры запроса ---
SLAVE_ID = 2
REGISTER_ADDRESS = 0
COUNT = 1
POLLING_INTERVAL = 0.5

# Глобальная переменная для управления завершением
keep_running = True

# Имя файла для записи
LOG_FILE = "modbus_data.txt"


def signal_handler(sig, frame):
    """Обработчик сигнала для корректного завершения по Ctrl+C"""
    global keep_running
    print("\nПолучен сигнал завершения (Ctrl+C). Закрываем соединение...")
    keep_running = False


def write_to_file(toc, P_kg):
    """Записывает данные в файл с датой и временем"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] toc = {toc:.3f}, P_kg = {P_kg:.3f}\n")


def main():
    global keep_running

    print(f"Попытка подключения к {PORT}...")
    print("Для остановки опроса нажмите Ctrl+C")

    signal.signal(signal.SIGINT, signal_handler)

    # --- Создание клиента Modbus ---
    client = ModbusSerialClient(
        method=METHOD,
        port=PORT,
        baudrate=BAUDRATE,
        parity=PARITY,
        bytesize=BYTESIZE,
        stopbits=STOPBITS,
        timeout=TIMEOUT,
    )

    try:
        # --- Подключение к устройству ---
        connection = client.connect()
        if not connection:
            print("Ошибка подключения к Modbus устройству!")
            log.error("Не удалось установить соединение с портом/устройством.")
            return
        print("Подключение успешно.")
        print("-" * 40)

        request_counter = 0

        # --- Бесконечный цикл опроса ---
        while keep_running:
            request_counter += 1
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{timestamp}] Запрос #{request_counter}...")

            try:
                # Чтение Holding Registers
                response = client.read_holding_registers(
                    address=REGISTER_ADDRESS, count=COUNT, slave=SLAVE_ID
                )

                # Обработка ответа
                if not hasattr(response, "isError") or response.isError():
                    print(f"  Ошибка Modbus: {response}")
                    log.warning(f"Ошибка при запросе #{request_counter}: {response}")
                else:
                    if response.registers:
                        raw_value = response.registers[0]
                        toc = ((16.0 * raw_value) / 65535.0) + 4.0
                        P_kg = ((toc - 4) * (163 - 5)) / (16.0)
                        print(f"  Регистр 40001: {toc:.3f} (0x{raw_value:04X})")
                        print(f"  Регистр 40001: {P_kg:.3f} кг")

                        # 📥 Записываем в файл
                        write_to_file(toc, P_kg)
                    else:
                        print(
                            "  Предупреждение: Получен пустой ответ (нет данных в registers)"
                        )

            except ModbusException as e:
                print(f"  Modbus Exception: {e}")
                log.error(f"Modbus Exception в запросе #{request_counter}: {e}")
            except Exception as e:
                print(f"  Общая ошибка: {e}")
                log.exception(f"Общая ошибка в запросе #{request_counter}")

            # Задержка
            if keep_running:
                time.sleep(POLLING_INTERVAL)

    except Exception as e:
        print(f"Критическая ошибка: {e}")
        log.exception("Критическая ошибка в основном цикле")
    finally:
        client.close()
        print("\nСоединение закрыто. Программа завершена.")


if __name__ == "__main__":
    main()
