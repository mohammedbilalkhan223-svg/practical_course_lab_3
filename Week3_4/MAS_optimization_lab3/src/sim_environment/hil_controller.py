import c104
import time
import random
from datetime import datetime


class ComObject:
    def __init__(
        self,
        tick_rate_ms=1000,
        command_timeout_ms=1000,
        conn_ip="10.51.6.211",
        conn_port=2404,
        addr_recv=0,
        addr_send=1,
        io_address=1,
        # take_type=c104.Type.M_ME_TB_1,
        take_type=c104.Type.M_ME_NB_1,
        send_type=c104.Type.C_SE_NA_1,
        cause=c104.Cot.ACTIVATION,
        qualifier=c104.Qoi.STATION,
    ):

        self.client = c104.Client(
            tick_rate_ms=tick_rate_ms, command_timeout_ms=command_timeout_ms
        )
        self.connection = self.client.add_connection(
            ip=conn_ip, port=conn_port, init=c104.Init.NONE
        )
        self.station_recv = self.connection.add_station(common_address=addr_recv)
        self.station_send = self.connection.add_station(common_address=addr_send)

        self.addr_recv = addr_recv
        self.addr_send = addr_send
        self.cause = cause
        self.qualifier = qualifier

        self.recv_points = []
        self.send_points = []

        # 6 devices in sim
        for i in range(8):
            pr = self.station_recv.add_point(io_address=io_address + i, type=take_type)
            self.recv_points.append(pr)

            if i < 6:
                ps = self.station_send.add_point(io_address=io_address + i, type=send_type)
                self.send_points.append(ps)

        # TODO: currently unused, do we need?
        # we only run client from Python side atm, right?
        self.server = None
        self.inp = None


if __name__ == "__main__":
    co = ComObject(
        1000,
        1000,
        "10.51.6.211",  # "10.51.6.213" "127.0.0.1"
        2404,  # 2404 5580
        0,
        1,
        1,
        c104.Type.M_ME_NB_1,  # c104.Type.M_ME_TB_1
        c104.Type.C_SE_NA_1,
        c104.Cot.ACTIVATION,
        c104.Qoi.STATION,
    )

    # running the client
    loop_counter = 0
    co.client.start()

    try:
        while co.client.is_running:
            if co.connection.is_connected:
                # from server
                co.connection.interrogation(co.addr_recv, co.cause, co.qualifier)

                print(f"------ {loop_counter} ------")
                # measurements are in real values
                print(f"received measurements 1: {co.recv_points[0].value}") # load 1 p
                print(f"received measurements 2: {co.recv_points[1].value}") # load 2 p
                print(f"received measurements 3: {co.recv_points[2].value}") # bat 1 p
                print(f"received measurements 4: {co.recv_points[3].value}") # bat 2 p
                print(f"received measurements 5: {co.recv_points[4].value}") # bat 1 soc
                print(f"received measurements 6: {co.recv_points[5].value}") # bat 2 soc
                print(f"received measurements 7: {co.recv_points[6].value}") # fc p 1
                print(f"received measurements 8: {co.recv_points[7].value}") # fc p 2

                print(f"------ sending ------")
                # values are x * nominal_power
                co.send_points[0].value = 0.5 # load 1 p
                co.send_points[0].transmit()
                co.send_points[1].value = 0.1 # load 2 p
                co.send_points[1].transmit()
                co.send_points[2].value = 0.1 # bss 1 p
                co.send_points[2].transmit()
                co.send_points[3].value = 0.3 # bss 2 p
                co.send_points[3].transmit()
                co.send_points[4].value = 0.5 # fc 1 p
                co.send_points[4].transmit()
                co.send_points[5].value = 0.1 # fc 2 p
                co.send_points[5].transmit()

                print(f"sending command 1: {co.send_points[0].value}")
                print(f"sending command 2: {co.send_points[1].value}")
                print(f"sending command 3: {co.send_points[2].value}")
                print(f"sending command 4: {co.send_points[3].value}")
                print(f"sending command 5: {co.send_points[4].value}")
                print(f"sending command 6: {co.send_points[5].value}")
            else:
                print(
                    "client is not connected --------------------------------------------------"
                )
                pass

            print(loop_counter, ": =====================")
            loop_counter += 1

            time.sleep(1)
    except KeyboardInterrupt:
        print("--- client stopped manually ---")
        co.client.stop()

    co.client.stop()
