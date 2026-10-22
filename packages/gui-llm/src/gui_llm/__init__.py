"""
Entrypoint for the LLM GUI package.
"""

import argparse

from common.game_state import GameState
from common.publishers.socket_publisher import SocketPublisher
from common.subscribers.socket_subscriber import SocketSubscriber

from gui_llm.llm_gui import LLMGui


def parse_arguments() -> tuple[tuple[str, int], tuple[str, int]]:
    parser = argparse.ArgumentParser(description="Run the LLM GUI for Age of Ants.")
    parser.add_argument("--send-address", help="Address to send data to", type=str, default="localhost")
    parser.add_argument("--send-port", help="Port to send data to", type=int, default="8080")
    parser.add_argument("--bind-address", help="Address to bind to", type=str, default="localhost")
    parser.add_argument("--bind-port", help="Port to bind to", type=int, default="8081")
    args = parser.parse_args()
    return (args.send_address, int(args.send_port)), (args.bind_address, int(args.bind_port))

def main() -> None:
    send_address, bind_address = parse_arguments()
    publisher = SocketPublisher(send_address)
    subscriber = SocketSubscriber(bind_address, GameState)
    gui = LLMGui(subscriber, publisher)
    gui.run()


if __name__ == "__main__":
    main()
