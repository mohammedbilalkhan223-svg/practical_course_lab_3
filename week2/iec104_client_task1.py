import time
import c104

SERVER_IP = "127.0.0.1"
SERVER_PORT = 2404
COA = 1

IOA_NORM_MON = 1001
IOA_SCALED_MON = 1002
IOA_BIN_MON = 1003

IOA_NORM_CMD = 2001
IOA_SCALED_CMD = 2002
IOA_BIN_CMD = 2003


def main():
    client = c104.Client(tick_rate_ms=200, command_timeout_ms=5000)

    # INTERROGATION makes client ask for station data after connect (nice for labs)
    conn = client.add_connection(ip=SERVER_IP, port=SERVER_PORT, init=c104.Init.INTERROGATION)
    station = conn.add_station(common_address=COA)

    # Monitoring points (server -> client)
    p_norm_mon = station.add_point(io_address=IOA_NORM_MON, type=c104.Type.M_ME_NA_1)
    p_scaled_mon = station.add_point(io_address=IOA_SCALED_MON, type=c104.Type.M_ME_NB_1)
    p_bin_mon = station.add_point(io_address=IOA_BIN_MON, type=c104.Type.M_SP_NA_1)

    def on_mon(point: c104.Point, previous_info: c104.Information, message: c104.IncomingMessage) -> c104.ResponseState:
        print(f"[CLIENT] RX MON {point.type} ioa={point.io_address} value={point.value}")
        return c104.ResponseState.SUCCESS

    p_norm_mon.on_receive(callable=on_mon)
    p_scaled_mon.on_receive(callable=on_mon)
    p_bin_mon.on_receive(callable=on_mon)

    # Command points (client -> server)
    p_norm_cmd = station.add_point(io_address=IOA_NORM_CMD, type=c104.Type.C_SE_NA_1)
    p_scaled_cmd = station.add_point(io_address=IOA_SCALED_CMD, type=c104.Type.C_SE_NB_1)
    p_bin_cmd = station.add_point(io_address=IOA_BIN_CMD, type=c104.Type.C_SC_NA_1)

    client.start()
    print(f"[IEC104 CLIENT] connected to {SERVER_IP}:{SERVER_PORT}, COA={COA}")

    # Give the connection a moment
    time.sleep(1.0)

    try:
        # ---- Task: send all types in one loop ----
        for k in range(10):
            # 1) Normalized: must be NormalizedFloat, range [-1..1]
            norm_val = ((k % 21) - 10) / 10.0  # -1.0 .. +1.0
            p_norm_cmd.value = c104.NormalizedFloat(norm_val)
            p_norm_cmd.transmit(cause=c104.Cot.ACTIVATION)
            print(f"[CLIENT] TX NORMALIZED CMD {norm_val}")
            time.sleep(0.5)

            # 2) Scaled: must be Int16
            scaled_val = (k * 100) - 300  # example values
            p_scaled_cmd.value = c104.Int16(scaled_val)
            p_scaled_cmd.transmit(cause=c104.Cot.ACTIVATION)
            print(f"[CLIENT] TX SCALED CMD {scaled_val}")
            time.sleep(0.5)

            # 3) Binary: bool
            bin_val = (k % 2 == 0)
            p_bin_cmd.value = bin_val
            p_bin_cmd.transmit(cause=c104.Cot.ACTIVATION)
            print(f"[CLIENT] TX BINARY CMD {bin_val}")
            time.sleep(0.5)

    except KeyboardInterrupt:
        print("\n[IEC104 CLIENT] stopping...")
    finally:
        client.stop()
        print("[IEC104 CLIENT] terminated")


if __name__ == "__main__":
    main()

