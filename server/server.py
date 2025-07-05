import socket
import threading

all_files = {}
HOST = '0.0.0.0'
PORT = 1234
shutdown_flag = False

def handle_client(conn, addr):
    global shutdown_flag
    peer = None
    print(f"[+] Conectado: {addr[0]}")

    try:
        while True:
            data = conn.recv(1024).decode().strip()
            if not data:
                break

            parts = data.split()
            if not parts:
                continue

            cmd = parts[0]

            if cmd == "SHUTDOWN":
                print("[!] Servidor encerrando por comando remoto.")
                shutdown_flag = True
                conn.sendall(b"SHUTTINGDOWN\n")
                break

            elif cmd == "JOIN":
                peer_info = parts[1] 
                ip, port = peer_info.split(":")
                peer = (ip, port)
                all_files[peer] = []
                conn.sendall(b"CONFIRMJOIN\n")

            elif cmd == "CREATEFILE" and peer:
                filename = parts[1]
                size = int(parts[2])
                all_files[peer].append({"filename": filename, "size": size})
                conn.sendall(f"CONFIRMCREATEFILE {filename}\n".encode())

            elif cmd == "DELETEFILE" and peer:
                filename = parts[1]
                all_files[peer] = [f for f in all_files[peer] if f["filename"] != filename]
                conn.sendall(f"CONFIRMDELETEFILE {filename}\n".encode())

            elif cmd == "SEARCH":
                pattern = parts[1].lower()
                requesting_addr = addr                
                results = []
                
                for (user_ip, user_port), files in all_files.items():
                    if (user_ip, user_port) == requesting_addr:
                        continue
                        
                    for file in files:
                        if pattern in file["filename"].lower():
                            results.append(f"FILE {file['filename']} {user_ip}:{user_port} {file['size']}")
                
                if results:
                    response = "\n".join(results) + "\nENDSEARCH\n"
                    conn.sendall(response.encode())
                else:
                    conn.sendall(b"NENHUM_ARQUIVO_ENCONTRADO\n")

            elif cmd == "LEAVE" and peer:
                conn.sendall(b"CONFIRMLEAVE\n")
                break

    except Exception as e:
        print(f"[!] Erro com {addr[0]}: {e}")
    finally:
        if cmd != "SHUTDOWN":
            print(f"[-] Desconectado: {addr[0]}")
        if peer and peer in all_files:
            del all_files[peer]
        conn.close()

def start_server():
    global shutdown_flag
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        print(f"[i] Servidor ouvindo na porta {PORT}...")

        while not shutdown_flag:
            try:
                s.settimeout(1.0)
                conn, addr = s.accept()
                threading.Thread(target=handle_client, args=(conn, addr)).start()
            except socket.timeout:
                continue

        print("[x] Servidor finalizado.")

if __name__ == '__main__':
    start_server()
