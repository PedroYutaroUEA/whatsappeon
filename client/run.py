from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))
from client.chat_client import ChatClient

HOST, PORT = "127.0.0.1", 5000
P = 0xFFFFFFFEFFFFFC2F
G = 5


def main():
    client = ChatClient(HOST, PORT, P, G)
    client.run()

if __name__ == "__main__":
    main()