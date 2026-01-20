import time
import c104

# ---- IEC-104 addresses ----
IP = "127.0.0.1"
PORT = 2404
COA = 1  # Common Address of ASDU (station common_address)

# Information Object Addresses (IOA)
IOA_NORM_MON = 1001  # M_ME_NA_1 (normalized measurement)
IOA_SCALED_MON = 1002  # M_ME_NB_1 (scaled measurement)
IOA_BIN_MON = 1003  # M_SP_NA_1 (single-point / binary)

IOA_NORM_CMD = 2001  # C_SE_NA_1 (normalized setpoint command)
IOA_SCALED_CMD = 2002  # C_SE_NB_1 (scaled setpoint command)
IOA_BIN_CMD = 2003  # C_SC_NA_1 (single command / binary command)


def main():
    server = c104.Server(ip=IP, port=PORT)
    station = server.add_station(common_address=COA)

    # ---- Monitoring points (server -> client) ----
    p_norm_mon = station.add_point(io_address=IOA_NORM_MON, type=c104.Type.M_ME_NA_1)
    p_scaled_mon = station.add_point(io_address=IOA_SCALED_MON, type=c104.Type.M_ME_NB_1)
    p_bin_mon = station.add_point(io_address=IOA_BIN_MON, type=c104.Type.M_SP_NA_1)

    # Initialize monitoring values using the correct value classes
    p_norm_mon.value = c104.NormalizedFloat(0.0)  # normalized expects NormalizedFloat :contentReference[oaicite:2]{index=2}
    p_scaled_mon.value = c104.Int16(0)            # scaled expects Int16 :contentReference[oaicite:3]{index=3}
    p_bin_mon.value = False                       # single-point expects bool :contentReference[oaicite:4]{index=4}

    # ---- Command points (client -> server) ----
    p_norm_cmd = station.add_point(io_address=IOA_NORM_CMD, type=c104.Type.C_SE_NA_1)
    p_scaled_cmd = station.add_point(io_address=IOA_SCALED_CMD, type=c104.Type.C_SE_NB_1)
    p_bin_cmd = station.add_point(io_address=IOA_BIN_CMD, type=c104.Type.C_SC_NA_1)

    # When a command arrives, update the corresponding monitoring point and transmit back
    def on_norm_cmd(point: c104.Point, previous_info: c104.Information, message: c104.IncomingMessage) -> c104.ResponseState:
        print(f"[SERVER] RX NORMALIZED CMD ioa={point.io_address} value={point.value}")
        p_norm_mon.value = point.value  # will be NormalizedFloat
        p_norm_mon.transmit(cause=c104.Cot.SPONTANEOUS)  # server -> client update :contentReference[oaicite:5]{index=5}
        return c104.ResponseState.SUCCESS

    def on_scaled_cmd(point: c104.Point, previous_info: c104.Information, message: c104.IncomingMessage) -> c104.ResponseState:
        print(f"[SERVER] RX SCALED CMD ioa={point.io_address} value={point.value}")
        p_scaled_mon.value = point.value  # will be Int16
        p_scaled_mon.transmit(cause=c104.Cot.SPONTANEOUS)
        return c104.ResponseState.SUCCESS

    def on_bin_cmd(point: c104.Point, previous_info: c104.Information, message: c104.IncomingMessage) -> c104.ResponseState:
        print(f"[SERVER] RX BINARY CMD ioa={point.io_address} value={point.value}")
        p_bin_mon.value = bool(point.value)
        p_bin_mon.transmit(cause=c104.Cot.SPONTANEOUS)
        return c104.ResponseState.SUCCESS

    p_norm_cmd.on_receive(callable=on_norm_cmd)
    p_scaled_cmd.on_receive(callable=on_scaled_cmd)
    p_bin_cmd.on_receive(callable=on_bin_cmd)

    server.start()
    print(f"[IEC104 SERVER] running on {IP}:{PORT}, COA={COA}")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[IEC104 SERVER] stopping...")
    finally:
        server.stop()
        print("[IEC104 SERVER] terminated")


if __name__ == "__main__":
    main()

