import serial
import time

class ArduinoController:
    """Контроллер для управления Arduino Nano и реле"""
    
    def __init__(self, port: str = '/dev/ttyUSB0', baudrate: int = 9600):
        try:
            self.arduino = serial.Serial(port, baudrate, timeout=2)
            time.sleep(2)
            print(f"[+] Arduino подключена на {port}")
            self.is_connected = True
        except Exception as e:
            print(f"[-] Ошибка подключения к Arduino: {e}")
            self.arduino = None
            self.is_connected = False
    
    def open_lock(self, duration: int = 7) -> bool:
        """Открывает замок на заданное время"""
        if not self.is_connected or not self.arduino or not self.arduino.is_open:
            print("[-] Arduino не подключена")
            return False
        
        try:
            command = f"OPEN:{duration}\n"
            self.arduino.write(command.encode())
            print(f"[+] Команда открытия замка отправлена ({duration}сек)")
            return True
        except Exception as e:
            print(f"[-] Ошибка при отправке команды: {e}")
            return False
    
    def close_lock(self) -> bool:
        """Закрывает замок"""
        if not self.is_connected or not self.arduino or not self.arduino.is_open:
            return False
        
        try:
            self.arduino.write(b"CLOSE\n")
            return True
        except Exception as e:
            return False
    
    def close(self):
        """Закрывает соединение"""
        if self.arduino:
            self.arduino.close()
            print("[+] Arduino отключена")
