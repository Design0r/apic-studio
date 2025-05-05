import sys
from threading import Thread

sys.path.append(r"C:\Users\TheApic\GitHub\apic-studio")
from apic_studio.connector import router
from apic_studio.network import Server


def main():
    Thread(target=lambda: Server(router=router)).start()


if __name__ == "__main__":
    main()
